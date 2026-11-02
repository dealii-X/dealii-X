"""MOX input histories and four-chamber PV comparison, without running a solver."""
import csv
import hashlib
import json
import os
from pathlib import Path

CATALOG = Path(__file__).resolve().parents[1] / "mox-datasets.json"
CHAMBERS = (("RA", "Right atrium"), ("LA", "Left atrium"),
            ("RV", "Right ventricle"), ("LV", "Left ventricle"))


def catalog():
    return json.loads(CATALOG.read_text())


def verified_file(directory, name):
    path = Path(directory) / name
    expected = catalog()["files"][name]
    data = path.read_bytes()
    if len(data) != expected["bytes"] or any(
        hashlib.new(algorithm, data).hexdigest() != expected[algorithm]
        for algorithm in ("sha1", "sha256")
    ):
        raise ValueError(f"MOX dataset checksum mismatch: {path}")
    return path


def read_history(path, extra_fields=()):
    import numpy as np
    fields = ["time", "QAV", "pressure_AA", "pARSYS"]
    fields += [name for chamber, _ in CHAMBERS
               for name in (f"volume_{chamber}", f"pressure_{chamber}")]
    fields += list(extra_fields)
    with Path(path).open() as stream:
        rows = list(csv.DictReader(line for line in stream if line.strip()))
    values = np.array([[float(row[key]) for key in fields] for row in rows])
    if len(rows) < 2 or not np.isfinite(values).all():
        raise ValueError("MOX history needs at least two finite samples")
    data = dict(zip(fields, values.T))
    if abs(data["time"][0]) > 1e-12 or not (np.diff(data["time"]) > 0).all():
        raise ValueError("MOX times must increase strictly from zero")
    if any((data[f"volume_{chamber}"] <= 0).any() for chamber, _ in CHAMBERS):
        raise ValueError("Nonpositive MOX chamber volume")
    conversion = catalog()["pressure_conversion_Pa_per_mmHg"]
    error = float(np.max(np.abs(data["pressure_AA"] - data["pARSYS"] * conversion)))
    if error > 1e-3:
        raise ValueError("pressure_AA no longer matches MOX pARSYS")
    return data


def cycle_window(data, case):
    """Keep the final nominal beat, tolerating only source sampling truncation."""
    import numpy as np
    definition = catalog()["cases"][case]
    period, beats = definition["period_s"], definition["heartbeats"]
    nominal_end = period * beats
    end = float(data["time"][-1])
    spacing = float(np.median(np.diff(data["time"])))
    if abs(end - nominal_end) > spacing + 1e-9:
        raise ValueError(f"History duration disagrees with {beats} beats for {case}")
    return {"start_s": (beats - 1) * period, "end_s": min(end, nominal_end),
            "nominal_end_s": nominal_end, "source_end_s": end,
            "missing_tail_s": max(0., nominal_end - end),
            "period_s": period, "heartbeats": beats}


def cycle_samples(data, window):
    import numpy as np
    times = data["time"]
    interior = times[(times > window["start_s"]) & (times < window["end_s"])]
    return np.concatenate(([window["start_s"]], interior, [window["end_s"]]))


def cardiac_inputs(directory, case, output):
    import numpy as np
    definition = catalog()["cases"][case]
    raw = verified_file(directory, definition["filename"])
    data = read_history(raw)
    window = cycle_window(data, case)
    output = Path(output)
    fields = ["time_s", "flow_m3_s", "pressure_Pa"]
    fields += [name for chamber, _ in CHAMBERS
               for name in (f"volume_{chamber}_mL", f"pressure_{chamber}_Pa")]
    columns = [data["time"], data["QAV"] * 1e-6, data["pressure_AA"]]
    columns += [data[name] for chamber, _ in CHAMBERS
                for name in (f"volume_{chamber}", f"pressure_{chamber}")]
    with (output / "heart_reference.csv").open("w") as stream:
        writer = csv.writer(stream)
        writer.writerow(fields)
        writer.writerows(zip(*columns))
    with (output / "inflow.csv").open("w") as stream:
        writer = csv.writer(stream)
        writer.writerow(("time_s", "flow_m3_s"))
        writer.writerows(zip(columns[0], columns[1]))
    return dict(case=case, samples=len(data["time"]), time_start_s=0.,
                time_end_s=float(data["time"][-1]), analysis_cycle=window,
                minimum_QAV_mL_s=float(np.min(data["QAV"])),
                maximum_QAV_mL_s=float(np.max(data["QAV"])),
                source_file=raw.name, **catalog()["files"][raw.name])


def plot_pv(directory, output):
    """Reproduce MOX panel order, physical units and baseline/pathology colors."""
    import numpy as np
    os.environ.setdefault("MPLCONFIGDIR", "/tmp/dealiix-mox-matplotlib")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(2, 2, figsize=(14, 8.4))
    report = {"origin": "Supplied MOX cardiac histories; not a 1D network prediction",
              "pressure_conversion_Pa_per_mmHg": catalog()["pressure_conversion_Pa_per_mmHg"],
              "cases": {}}
    for case, definition in catalog()["cases"].items():
        raw = verified_file(directory, definition["filename"])
        data = read_history(raw)
        window = cycle_window(data, case)
        times = cycle_samples(data, window)
        columns = [times]
        headers = ["time_s"]
        stats = {}
        for axis, (chamber, title) in zip(axes.flat, CHAMBERS):
            volume = np.interp(times, data["time"], data[f"volume_{chamber}"])
            pressure = np.interp(times, data["time"], data[f"pressure_{chamber}"])
            pressure /= report["pressure_conversion_Pa_per_mmHg"]
            axis.plot(volume, pressure, color=definition["color"], lw=2,
                      label=definition["label"])
            axis.set(title=title, xlabel="V [mL]", ylabel="p [mmHg]")
            axis.spines[["top", "right"]].set_visible(False)
            columns.extend((volume, pressure))
            headers.extend((f"volume_{chamber}_mL", f"pressure_{chamber}_mmHg"))
            stats[chamber] = {"min_volume_mL": float(min(volume)),
                              "max_volume_mL": float(max(volume)),
                              "min_pressure_mmHg": float(min(pressure)),
                              "max_pressure_mmHg": float(max(pressure))}
        np.savetxt(output / f"PV_last_beat_{case}.csv", np.column_stack(columns),
                   delimiter=",", header=",".join(headers), comments="")
        report["cases"][case] = dict(window=window, chambers=stats,
                                     source=catalog()["files"][raw.name])
    limits = (((60, 120), (3.5, 8.2)), ((40, 90), (8.5, 20)),
              ((80, 180), (0, 30)), ((60, 170), (0, 150)))
    for axis, (xlim, ylim) in zip(axes.flat, limits):
        axis.set(xlim=xlim, ylim=ylim)
        axis.title.set(fontsize=18, fontweight="bold")
        axis.xaxis.label.set_fontsize(16)
        axis.yaxis.label.set_fontsize(16)
        axis.tick_params(labelsize=13)
    report["reference_image_name"] = catalog()["reference_image"]
    report["reference_image_in_dataset"] = False
    fig.suptitle("MOX four-chamber PV loops — supplied reference data", fontsize=16, y=.99)
    fig.subplots_adjust(hspace=.62, wspace=.3, top=.90, bottom=.09)
    fig.legend(*axes[0, 0].get_legend_handles_labels(), loc="center",
               bbox_to_anchor=(.52, .505), frameon=True)
    for extension in ("png", "pdf", "svg"):
        fig.savefig(output / f"PV_loops_comparisons.{extension}", dpi=180)
    plt.close(fig)
    (output / "PV_comparison.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assets", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    plot_pv(args.assets, args.output)


if __name__ == "__main__":
    main()
