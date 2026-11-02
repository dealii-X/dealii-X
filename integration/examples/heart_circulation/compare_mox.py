#!/usr/bin/env python3
"""Compare completed ADAVN/ADAN56 runs with the original MOX histories."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "integration"))
from dealiix.mox import catalog, cycle_samples, cycle_window, plot_pv, read_history, verified_file

import numpy as np

os.environ.setdefault("MPLCONFIGDIR", "/tmp/dealiix-mox-comparison-matplotlib")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

MODELS = ("adavn_full", "adan56")
LABELS = {"adavn_full": "ADAVN full", "adan56": "ADAN56"}
COLORS = {"adavn_full": "#1876b5", "adan56": "#d86a16"}
STYLES = {"adavn_full": "-", "adan56": "--"}
CASES = {"normal_pressure": "Baseline", "severe_hypertension": "Severe systemic hypertension"}
MMHG = catalog()["pressure_conversion_Pa_per_mmHg"]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def terminal_traces(path, boundaries):
    rows = {boundary: [] for boundary in boundaries}
    with Path(path).open() as stream:
        for row in csv.DictReader(stream):
            boundary = int(row["boundary_id"])
            if boundary in rows:
                rows[boundary].append([float(row[name]) for name in
                                       ("time_s", "pressure_Pa", "flow_m3_s")])
    result = {}
    for boundary, values in rows.items():
        array = np.asarray(values)
        if (len(array) < 2 or not np.isfinite(array).all()
                or not np.all(np.diff(array[:, 0]) > 0)):
            raise ValueError(f"Invalid native boundary trace: {path}, boundary {boundary}")
        result[boundary] = dict(zip(("time", "pressure", "flow"), array.T))
    return result


def drain_boundaries(directory):
    network = directory / "network"
    provenance = json.loads((network / "provenance.json").read_text())
    drains = set(provenance["central_drain_nodes"])
    mapping = json.loads((network / "mapping.json").read_text())
    boundaries = {}
    for row in mapping:
        for endpoint in (0, 1):
            node = row[f"node{endpoint}"]
            if node in drains:
                boundaries[row[f"boundary{endpoint}"]] = row["name"]
    if len(boundaries) != len(drains) or 0 in boundaries or 255 in boundaries:
        raise ValueError("ADAVN central venous drains were not identified uniquely")
    return boundaries


def select_cycle(trace, window):
    t = trace["time"]
    if t[0] > window["start_s"] or t[-1] < window["end_s"] - 1e-9:
        raise ValueError("Native output does not cover the requested last beat")
    times = cycle_samples(trace, window)
    return {name: times if name == "time" else np.interp(times, t, values)
            for name, values in trace.items()}


def load_case(assets, results, case):
    definition = catalog()["cases"][case]
    raw = verified_file(assets, definition["filename"])
    heart = read_history(raw, extra_fields=("QPV", "QVENSYS", "QVENPUL"))
    window = cycle_window(heart, case)
    data = dict(heart=heart, window=window, models={}, source_sha256=digest(raw))
    for model in MODELS:
        directory = results / case / model
        receipt = json.loads((directory / "provenance.json").read_text())
        if (receipt["case"] != case or receipt["model"] != model
                or receipt["sha256"] != data["source_sha256"]
                or receipt["parameters_sha256"] != digest(directory / "parameters.prm")):
            raise ValueError(f"Prepared inputs differ from the completed case: {directory}")
        boundaries = drain_boundaries(directory) if model == "adavn_full" else {}
        traces = terminal_traces(directory / "output/terminals.csv", [0, *boundaries])
        inlet = traces[0]
        if abs(inlet["time"][-1] - window["source_end_s"]) > 1e-9:
            raise ValueError(f"Incomplete simulation: {directory}")
        inlet["flow"] *= -1  # Native terminal orientation is out of the network.
        last = select_cycle(inlet, window)
        reference = np.interp(last["time"], heart["time"], heart["pressure_AA"])
        duration = last["time"][-1] - last["time"][0]
        mean = lambda y: float(np.trapezoid(y, last["time"]) / duration)
        metrics = json.loads((directory / "comparison.json").read_text())
        recomputed = mean((last["pressure"] - reference)**2)**.5 / MMHG
        if not np.isclose(recomputed, metrics["pressure_rmse_mmHg"], atol=1e-9, rtol=1e-9):
            raise ValueError("Recomputed pressure error disagrees with the native comparison report")
        item = dict(last=last, metrics=metrics,
                    source_revision=receipt["source_revision"],
                    parameters_sha256=receipt["parameters_sha256"],
                    native_terminal_sha256=digest(directory / "output/terminals.csv"))
        if boundaries:
            times = inlet["time"]
            for boundary in boundaries:
                if not np.array_equal(traces[boundary]["time"], times):
                    raise ValueError("ADAVN central-drain timestamps disagree")
            # Sum only the three central reservoirs, never internal peripheral links.
            venous = {"time": times,
                      "flow": sum(traces[boundary]["flow"] for boundary in boundaries)}
            item.update(venous=select_cycle(venous, window), central_drain_boundaries=boundaries)
        data["models"][model] = item
    return data


def style_axis(axis):
    axis.spines[["top", "right"]].set_visible(False)
    axis.grid(alpha=.18)


def save_figure(figure, output, name):
    for extension in ("png", "pdf", "svg"):
        figure.savefig(output / f"{name}.{extension}", dpi=200)
    plt.close(figure)


def systemic_figure(cases, output):
    fig, axes = plt.subplots(2, 2, figsize=(13, 8))
    for column, (case, data) in enumerate(cases.items()):
        heart, window = data["heart"], data["window"]
        time = cycle_samples(heart, window)
        phase_time = time - window["start_s"]
        for row, field, scale in ((0, "pressure_AA", 1/MMHG), (1, "QAV", 1)):
            axes[row, column].plot(phase_time, np.interp(time, heart["time"], heart[field])*scale,
                                   color="#202020", lw=2.5, label="MOX")
        for model, item in data["models"].items():
            t = item["last"]["time"] - window["start_s"]
            axes[0, column].plot(t, item["last"]["pressure"]/MMHG,
                                 STYLES[model], color=COLORS[model], lw=2, label=LABELS[model])
            axes[1, column].plot(t, item["last"]["flow"]*1e6,
                                 STYLES[model], color=COLORS[model], lw=1.6,
                                 marker="o" if model == "adavn_full" else "s",
                                 markevery=7 if model == "adavn_full" else 9,
                                 markersize=4, markerfacecolor="white", label=LABELS[model])
        axes[0, column].set(title=f"{CASES[case]}  |  T = {window['period_s']:.5g} s\n"
                                  f"Source time: {window['start_s']:.3f}–{window['end_s']:.3f} s",
                            ylabel="Aortic pressure [mmHg]", ylim=(40, 155))
        axes[1, column].set(ylabel="Aortic-valve / inlet flow [mL/s]", ylim=(-25, 750))
        errors = "\n".join(f"{LABELS[m]} pressure RMSE: {data['models'][m]['metrics']['pressure_rmse_mmHg']:.2f} mmHg"
                           for m in MODELS)
        axes[0, column].text(.025, .025, errors, transform=axes[0, column].transAxes,
                             fontsize=9, va="bottom")
        for axis in axes[:, column]:
            axis.set(xlim=(0, window["period_s"]), xlabel="Time in last beat [s]")
            style_axis(axis)
    fig.suptitle("MOX vs completed 1D simulations: systemic inlet", fontsize=17, y=.985)
    fig.legend(*axes[0, 0].get_legend_handles_labels(), loc="upper center",
               bbox_to_anchor=(.5, .94), ncol=3, frameon=False)
    fig.text(.5, .025, "Flow is prescribed from MOX; pressure is predicted. No pressure offset or fitted phase shift.",
             ha="center", fontsize=10)
    fig.subplots_adjust(top=.84, bottom=.12, hspace=.38, wspace=.25)
    save_figure(fig, output, "systemic_comparison")


def pressure_volume_figure(cases, output):
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.6))
    for axis, (case, data) in zip(axes, cases.items()):
        heart, window = data["heart"], data["window"]
        time = cycle_samples(heart, window)
        volume = np.interp(time, heart["time"], heart["volume_LV"])
        axis.plot(volume, np.interp(time, heart["time"], heart["pressure_LV"])/MMHG,
                  color=".6", lw=1.8, ls=":", label="MOX ventricular pressure (reference)")
        axis.plot(volume, np.interp(time, heart["time"], heart["pressure_AA"])/MMHG,
                  color="#202020", lw=2.5, label="MOX aortic pressure")
        for model, item in data["models"].items():
            v = np.interp(item["last"]["time"], heart["time"], heart["volume_LV"])
            axis.plot(v, item["last"]["pressure"]/MMHG, STYLES[model],
                      color=COLORS[model], lw=2, label=LABELS[model]+" aortic pressure")
        axis.set(title=CASES[case], xlabel="MOX left-ventricular volume [mL]",
                 ylabel="Pressure [mmHg]", xlim=(60, 175), ylim=(0, 155))
        style_axis(axis)
    fig.suptitle("Aortic pressure against the shared MOX ventricular volume", fontsize=16, y=.98)
    fig.legend(*axes[0].get_legend_handles_labels(), loc="lower center",
               bbox_to_anchor=(.5, .035), ncol=2, fontsize=9, frameon=False)
    fig.text(.5, .01, "The 1D models predict aortic pressure, not ventricular PV loops or ventricular volume.",
             ha="center", fontsize=10)
    fig.subplots_adjust(top=.84, bottom=.27, wspace=.25)
    save_figure(fig, output, "aortic_pressure_LV_volume")


def venous_figure(cases, output):
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.9))
    for axis, (case, data) in zip(axes, cases.items()):
        heart, window = data["heart"], data["window"]
        time = cycle_samples(heart, window)
        axis.plot(time-window["start_s"], np.interp(time, heart["time"], heart["QVENSYS"]),
                  color="#202020", lw=2.3, label="MOX systemic venous return")
        trace = data["models"]["adavn_full"]["venous"]
        axis.plot(trace["time"]-window["start_s"], trace["flow"]*1e6,
                  color=COLORS["adavn_full"], lw=2, label="ADAVN: IVC + SVC + coronary sinus")
        axis.set(title=CASES[case], xlabel="Time in last beat [s]",
                 ylabel="Flow toward central venous reservoirs [mL/s]", xlim=(0, window["period_s"]))
        style_axis(axis)
    fig.suptitle("Systemic venous return", fontsize=17, y=.98)
    fig.legend(*axes[0].get_legend_handles_labels(), loc="lower center",
               bbox_to_anchor=(.5, .06), ncol=2, fontsize=9, frameon=False)
    fig.text(.5, .015, "ADAVN retains fixed central venous reservoirs. ADAN56 has no venous network.",
             ha="center", fontsize=10)
    fig.subplots_adjust(top=.82, bottom=.25, wspace=.25)
    save_figure(fig, output, "venous_return_comparison")


def circulation_figure(case, data, output):
    heart, window = data["heart"], data["window"]
    time = cycle_samples(heart, window)
    t = time-window["start_s"]
    fig, axes = plt.subplots(2, 2, figsize=(13.5, 8.2))
    panels = ((axes[0, 0], ("pressure_RA", "pressure_RV"), (r"$p_{RA}$ MOX", r"$p_{RV}$ MOX"), 1/MMHG),
              (axes[0, 1], ("pressure_LA", "pressure_LV"), (r"$p_{LA}$ MOX", r"$p_{LV}$ MOX"), 1/MMHG),
              (axes[1, 0], ("QPV", "QVENPUL"), (r"$Q_{PV}$ MOX", r"$Q_{VEN}^{PUL}$ MOX"), 1),
              (axes[1, 1], ("QAV", "QVENSYS"), (r"$Q_{AV}$ MOX", r"$Q_{VEN}^{SYS}$ MOX"), 1))
    for axis, fields, labels, scale in panels:
        for field, label, color in zip(fields, labels, ("#1876b5", "#d86a16")):
            axis.plot(t, np.interp(time, heart["time"], heart[field])*scale,
                      color=color, label=label, lw=2)
        axis.set(xlim=(0, window["period_s"]), xlabel="Time in last beat [s]")
        style_axis(axis)
    for model, item in data["models"].items():
        trace = item["last"]
        axes[1, 1].plot(trace["time"]-window["start_s"], trace["flow"]*1e6,
                        color="#1876b5", ls="--" if model == "adavn_full" else ":",
                        marker="o" if model == "adavn_full" else "s", markevery=8,
                        markersize=4, markerfacecolor="white", label=r"$Q_{in}$ "+LABELS[model])
    venous = data["models"]["adavn_full"]["venous"]
    axes[1, 1].plot(venous["time"]-window["start_s"], venous["flow"]*1e6,
                    color="#d86a16", ls="--", lw=2, label=r"$Q_{VEN}$ ADAVN")
    axes[0, 0].set(title="Right heart — MOX reference", ylabel="Pressure [mmHg]")
    axes[0, 1].set(title="Left heart — MOX reference", ylabel="Pressure [mmHg]")
    axes[1, 0].set(title="Pulmonary circulation — MOX reference", ylabel="Flow [mL/s]")
    axes[1, 1].set(title="Systemic flows — MOX and 1D outputs", ylabel="Flow [mL/s]")
    for axis in axes.flat:
        axis.legend(loc="upper right", fontsize=8, frameon=True)
    fig.suptitle(f"{CASES[case]}: comparison in the MOX circulation layout\n"
                 f"Source time {window['start_s']:.3f}–{window['end_s']:.3f} s", fontsize=16, y=.98)
    fig.text(.5, .02, "Only the systemic panel contains 1D predictions; cardiac and pulmonary signals are supplied MOX data.",
             ha="center", fontsize=10)
    fig.subplots_adjust(top=.87, bottom=.11, hspace=.42, wspace=.26)
    save_figure(fig, output, f"circulation_{case}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assets", type=Path, default=ROOT / "assets")
    parser.add_argument("--results", type=Path, default=ROOT / "build/integration/heart_circulation")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.size": 11, "axes.titlesize": 12, "axes.labelsize": 11,
                         "svg.fonttype": "none", "pdf.fonttype": 42})
    cases = {case: load_case(args.assets, args.results, case) for case in CASES}
    systemic_figure(cases, args.output)
    pressure_volume_figure(cases, args.output)
    venous_figure(cases, args.output)
    for case, data in cases.items():
        circulation_figure(case, data, args.output)
    plot_pv(args.assets, args.output / "mox_reference")
    report = {"scope": "Completed one-way MOX forcing; no heart or pulmonary feedback",
              "pressure_conversion_Pa_per_mmHg": MMHG,
              "curve_adjustments": "None: no pressure offsets, fitted phase shifts or inflow clipping",
              "time_origin": "Nominal last beat from supplied periods/counts; source zero is retained",
              "flow_error_sampling": "Evaluated at native output times; plotted model samples are joined linearly",
              "figures_are_local": True, "cases": {}}
    rows = []
    for case, data in cases.items():
        report["cases"][case] = dict(window=data["window"], source_sha256=data["source_sha256"], models={})
        for model, item in data["models"].items():
            m = item["metrics"]
            row = dict(case=case, model=LABELS[model],
                       MOX_mean_aortic_pressure_mmHg=m["mean_MOX_pressure_mmHg"],
                       model_mean_aortic_pressure_mmHg=m["mean_inlet_pressure_mmHg"],
                       pressure_bias_mmHg=m["mean_inlet_pressure_mmHg"]-m["mean_MOX_pressure_mmHg"],
                       pressure_RMSE_mmHg=m["pressure_rmse_mmHg"],
                       max_inlet_flow_error_percent_of_peak=100*m["max_inlet_flow_error_fraction_of_peak"])
            rows.append(row)
            report["cases"][case]["models"][model] = {
                **{key: value for key, value in item.items() if key not in ("last", "venous")}, **row}
            last = item["last"]
            columns = [last["time"], last["time"]-data["window"]["start_s"],
                       last["pressure"]/MMHG, last["flow"]*1e6,
                       np.interp(last["time"], data["heart"]["time"], data["heart"]["pressure_AA"])/MMHG,
                       np.interp(last["time"], data["heart"]["time"], data["heart"]["QAV"])]
            np.savetxt(args.output/f"last_beat_{case}_{model}.csv", np.column_stack(columns), delimiter=",",
                       header="time_s,time_in_beat_s,model_pressure_mmHg,model_inflow_mL_s,MOX_aortic_pressure_mmHg,MOX_QAV_mL_s", comments="")
            if "venous" in item:
                trace = item["venous"]
                np.savetxt(args.output/f"venous_return_{case}.csv", np.column_stack((
                    trace["time"], trace["time"]-data["window"]["start_s"], trace["flow"]*1e6,
                    np.interp(trace["time"], data["heart"]["time"], data["heart"]["QVENSYS"]))),
                    delimiter=",", header="time_s,time_in_beat_s,ADAVN_central_outflow_mL_s,MOX_QVENSYS_mL_s", comments="")
    with (args.output / "pressure_summary.csv").open("w") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (args.output / "comparison_report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
