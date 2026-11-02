#!/usr/bin/env python3
"""Compare blood-volume-weighted arterial pressure from saved VTK with MOX."""
import argparse
import csv
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import meshio
import numpy as np

from compare_mox import (ROOT, CASES, MODELS, LABELS, COLORS, STYLES, MMHG,
                         digest, save_figure, style_axis)
from dealiix.mox import catalog, cycle_samples, cycle_window, read_history, verified_file
import matplotlib.pyplot as plt


def spatial_integrals(length, area, pressure):
    """Integrate p*A exactly for the piecewise-linear saved fields, in SI."""
    if (not np.isfinite(length).all() or not np.isfinite(area).all()
            or not np.isfinite(pressure).all() or np.any(length <= 0)
            or np.any(area <= 0)):
        raise ValueError("Invalid saved arterial geometry, area or pressure")
    volume = float(np.sum(length * np.mean(area, axis=1)))
    pressure_volume = float(np.sum(length * (
        2*pressure[:, 0]*area[:, 0] + pressure[:, 0]*area[:, 1]
        + pressure[:, 1]*area[:, 0] + 2*pressure[:, 1]*area[:, 1]) / 6))
    volume_mean = pressure_volume / volume
    length_mean = float(np.sum(length * np.mean(pressure, axis=1)) / np.sum(length))
    tolerance = 1e-12 * max(1., float(np.max(np.abs(pressure))))
    if not np.min(pressure)-tolerance <= volume_mean <= np.max(pressure)+tolerance:
        raise ValueError("Arterial pressure average is outside its spatial bounds")
    return volume_mean, length_mean, volume, float(pressure.min()), float(pressure.max())


def arterial_ids(directory, model, receipt):
    name = "network/adavn_full.vtk" if model == "adavn_full" else "network/network.vtk"
    mesh_path = directory / name
    if digest(mesh_path) != receipt["inputs_sha256"][name]:
        raise ValueError(f"Network differs from the completed run: {mesh_path}")
    mesh = meshio.read(mesh_path)
    ids = np.concatenate(mesh.cell_data["vessel_id"]).ravel().astype(int)
    if len(np.unique(ids)) != len(ids):
        raise ValueError("Expected unique material IDs in the prepared source mesh")
    types = (np.concatenate(mesh.cell_data["source_vessel_type"]).ravel()
             if model == "adavn_full" else np.ones(len(ids)))
    return ids, ids[types == 1]


def snapshot(path, expected_ids, arteries):
    mesh = meshio.read(path)
    if any(block.type != "line" for block in mesh.cells):
        raise ValueError("Expected saved linear VTK cells")
    edges = np.concatenate([block.data for block in mesh.cells])
    raw_ids = mesh.point_data["vessel_id"].ravel()
    if not np.isfinite(raw_ids).all() or not np.array_equal(raw_ids, np.rint(raw_ids)):
        raise ValueError("Invalid saved vessel IDs")
    ids = raw_ids.astype(int)
    if not np.array_equal(ids[edges[:, 0]], ids[edges[:, 1]]):
        raise ValueError("A saved line crosses two material IDs")
    if set(np.unique(ids)) != set(expected_ids):
        raise ValueError("Incomplete or duplicated partition scope; use the complete output")
    edges = edges[np.isin(ids[edges[:, 0]], arteries)]
    length = np.linalg.norm(mesh.points[edges[:, 1]]-mesh.points[edges[:, 0]], axis=1)
    area = mesh.point_data["area"].ravel()[edges].astype(float)
    pressure = mesh.point_data["pressure"].ravel()[edges].astype(float)
    return spatial_integrals(length, area, pressure), len(edges), float(length.sum())


def history(directory, model, window, source_hash):
    receipt = json.loads((directory / "provenance.json").read_text())
    if (receipt["model"] != model or receipt["sha256"] != source_hash
            or receipt["parameters_sha256"] != digest(directory / "parameters.prm")):
        raise ValueError(f"Prepared inputs differ from the completed run: {directory}")
    expected_ids, arteries = arterial_ids(directory, model, receipt)
    pvd = directory / "output" / f"{model}.pvd"
    records = ET.parse(pvd).findall(".//DataSet")
    times = np.array([float(row.attrib["timestep"]) for row in records])
    if (len(times) < 2 or not np.isfinite(times).all() or not np.all(np.diff(times) > 0)
            or abs(times[0]) > 1e-12 or abs(times[-1]-window["end_s"]) > 1e-9):
        raise ValueError(f"Incomplete native VTK time coverage: {pvd}")
    values, hashes = [], {str(pvd.relative_to(directory)): digest(pvd)}
    shape = None
    for row in records:
        pvtu = pvd.parent / row.attrib["file"]
        pieces = ET.parse(pvtu).findall(".//Piece")
        if len(pieces) != 1:
            raise ValueError("This analysis supports the completed one-process runs only")
        vtu = pvtu.parent / pieces[0].attrib["Source"]
        value, cells, length = snapshot(vtu, expected_ids, arteries)
        current_shape = (cells, length)
        if shape is not None and current_shape != shape:
            raise ValueError("Saved arterial geometry changes during the run")
        shape = current_shape
        values.append(value)
        hashes[str(pvtu.relative_to(directory))] = digest(pvtu)
        hashes[str(vtu.relative_to(directory))] = digest(vtu)
    columns = ("volume_mean_pressure_Pa", "length_mean_pressure_Pa", "volume_m3",
               "minimum_pressure_Pa", "maximum_pressure_Pa")
    trace = dict(time=times, **dict(zip(columns, np.asarray(values).T)))
    metadata = dict(arterial_material_ids=len(arteries), all_material_ids=len(expected_ids),
                    saved_arterial_lines=shape[0], arterial_length_m=shape[1],
                    source_revision=receipt["source_revision"],
                    parameters_sha256=receipt["parameters_sha256"],
                    input_mesh_sha256={k: v for k, v in receipt["inputs_sha256"].items()
                                       if k.endswith(".vtk")}, native_files_sha256=hashes)
    return trace, metadata


def plot_comparison(cases, output, last_beat):
    fig, axes = plt.subplots(1, 2, figsize=(13.2, 5.6), sharey=True)
    for axis, (case, data) in zip(axes, cases.items()):
        heart, window = data["heart"], data["window"]
        start = window["start_s"] if last_beat else 0.
        times = cycle_samples(heart, window) if last_beat else heart["time"]
        axis.plot(times-start, np.interp(times, heart["time"], heart["pARSYS"]),
                  color="#202020", lw=2.5, label="MOX pARSYS (systemic 0D)")
        for model, item in data["models"].items():
            trace = item["trace"]
            t = cycle_samples(trace, window) if last_beat else trace["time"]
            p = np.interp(t, trace["time"], trace["volume_mean_pressure_Pa"])/MMHG
            axis.plot(t-start, p, STYLES[model], lw=2, color=COLORS[model],
                      label=LABELS[model]+": arterial volume mean")
        axis.set(title=CASES[case], xlabel="Time in last beat [s]" if last_beat else "Time [s]",
                 xlim=(0, window["period_s"] if last_beat else window["end_s"]))
        if last_beat:
            labels = [f"MOX beat mean: {data['MOX_beat_mean_mmHg']:.2f} mmHg"]
            labels += [f"{LABELS[model]} beat mean: {data['models'][model]['summary']['beat_mean_mmHg']:.2f} mmHg"
                       for model in MODELS]
            axis.text(.025, .975, "\n".join(labels), transform=axis.transAxes,
                      fontsize=9, va="top")
        style_axis(axis)
    axes[0].set(ylabel="Pressure [mmHg]")
    fig.suptitle("Mean pressure across the resolved arterial compartment", fontsize=17, y=.98)
    fig.legend(*axes[0].get_legend_handles_labels(), loc="upper center",
               bbox_to_anchor=(.5, .93), ncol=3, frameon=False, fontsize=9.5)
    fig.text(.5, .055, r"1D spatial mean: $\overline{p}(t)=\sum_e\int_e pA\,ds\,/\,\sum_e\int_e A\,ds$; veins and lumped peripheral storage excluded.",
             ha="center", fontsize=10)
    fig.text(.5, .018, "Calculated from saved piecewise-linear VTK fields; MOX pARSYS is a 0D compartment pressure, not a measured spatial average.",
             ha="center", fontsize=9)
    fig.subplots_adjust(top=.79, bottom=.17, wspace=.12)
    save_figure(fig, output, "arterial_mean_pressure_comparison" if last_beat else "arterial_mean_pressure_history")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assets", type=Path, default=ROOT / "assets")
    parser.add_argument("--results", type=Path, default=ROOT / "build/integration/heart_circulation")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    report = dict(spatial_mean="sum(integral(p*A ds))/sum(integral(A ds)) over all resolved systemic arterial 1D vessels",
                  excluded="All venous vessels, all lumped peripheral/RCR storage, heart and pulmonary circulation",
                  MOX_reference="pARSYS in mmHg; equal to pressure_AA/133.322 in supplied histories",
                  reconstruction="Exact integral of the product of linear p and A on saved VTK lines; original degree-2 FE interiors are not recoverable from these endpoint-only files",
                  temporal_mean="Time average of instantaneous spatial mean over each case's last nominal beat; linearly interpolate saved times at the beat start, without extrapolation",
                  cases={})
    cases, rows = {}, []
    for case, label in CASES.items():
        raw = verified_file(args.assets, catalog()["cases"][case]["filename"])
        heart = read_history(raw)
        window = cycle_window(heart, case)
        t = cycle_samples(heart, window)
        reference = np.interp(t, heart["time"], heart["pARSYS"])
        duration = t[-1]-t[0]
        mox_mean = float(np.trapezoid(reference, t)/duration)
        data = dict(heart=heart, window=window, MOX_beat_mean_mmHg=mox_mean, models={})
        report["cases"][case] = dict(window=window, source_sha256=digest(raw), models={})
        for model in MODELS:
            trace, metadata = history(args.results/case/model, model, window, digest(raw))
            sample_t = cycle_samples(trace, window)
            p = np.interp(sample_t, trace["time"], trace["volume_mean_pressure_Pa"])/MMHG
            ref = np.interp(sample_t, heart["time"], heart["pARSYS"])
            average = lambda y: float(np.trapezoid(y, sample_t)/duration)
            mean = average(p)
            row = dict(case=case, model=model, MOX_beat_mean_mmHg=mox_mean,
                       beat_mean_mmHg=mean, bias_mmHg=mean-mox_mean,
                       pressure_RMSE_mmHg=average((p-ref)**2)**.5,
                       beat_mean_arterial_volume_mL=average(np.interp(sample_t, trace["time"], trace["volume_m3"]))*1e6)
            rows.append(row)
            data["models"][model] = dict(trace=trace, summary=row)
            report["cases"][case]["models"][model] = dict(summary=row, **metadata)
            columns = [trace["time"], trace["volume_mean_pressure_Pa"]/MMHG,
                       trace["length_mean_pressure_Pa"]/MMHG, trace["volume_m3"]*1e6,
                       trace["minimum_pressure_Pa"]/MMHG, trace["maximum_pressure_Pa"]/MMHG]
            np.savetxt(args.output/f"arterial_pressure_history_{case}_{model}.csv",
                       np.column_stack(columns), delimiter=",", comments="",
                       header="time_s,volume_mean_pressure_mmHg,length_mean_pressure_mmHg,arterial_volume_mL,minimum_pressure_mmHg,maximum_pressure_mmHg")
            print(f"{case}/{model}: last-beat spatial mean {mean:.3f} mmHg; MOX {mox_mean:.3f} mmHg", flush=True)
        cases[case] = data
    plot_comparison(cases, args.output, True)
    plot_comparison(cases, args.output, False)
    with (args.output/"arterial_mean_pressure_summary.csv").open("w") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (args.output/"arterial_pressure_comparison.json").write_text(json.dumps(report, indent=2)+"\n")


if __name__ == "__main__":
    main()
