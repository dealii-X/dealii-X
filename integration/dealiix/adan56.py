"""ADAN56 with MOX aortic-valve flow at inlet 0 and unchanged RCR terminals."""
import argparse
import csv
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from .contracts import Series, import_csv, write_inflow
from .sources import git, sha256
from .pipeline import MPI_RANK_KEYS


def prepare(manifest, source, destination, final_time=8., refinements=5):
    series = Series(manifest)
    if series.metadata["anatomy"] != "ascending-aorta":
        raise ValueError("ADAN56 inlet 0 requires ascending-aorta data")
    if series.times[0] != 0 or not 0 < final_time <= series.times[-1]:
        raise ValueError("Retain source time origin 0 and stay inside measured coverage")
    if refinements < 0: raise ValueError("Negative refinement level")
    root = Path(destination)
    root.mkdir(parents=True, exist_ok=True)
    source = Path(source).resolve()
    template = source / "tutorials/04_adan56/parameters.prm.in"
    mesh = source / "tutorials/04_adan56/network.vtk"
    text = template.read_text().replace("@SOURCE_DIR@", str(source))
    def setting(name, value):
        nonlocal text
        text, count = re.subn(r"(?m)^(\s*set " + re.escape(name) + r"\s*=)[^\n]*",
                             lambda m: m[1] + " " + str(value), text)
        if count != 1: raise ValueError(f"ADAN56 template must contain one {name}")
    setting("Final time", final_time)
    setting("Number of global refinement", refinements)
    setting("Output directory", "output/adan56")
    setting("Absolute error tolerance", "1e-12")
    setting("Relative error tolerance", "1e-8")
    setting("Inflow function", "0")  # CSV takes precedence; remove the former fitted cardiac waveform.
    text = text.replace("# Derived from inflow.txt using a Fourier-series fit of the supporting-data waveform",
                        "# Cardiac waveform supplied by Inflow CSV file at inlet boundary 0.")
    text = text.replace("subsection MetricFlowSystem<1, 3>",
                        "subsection MetricFlowSystem<1, 3>\n  set Inflow CSV file = inflow.csv\n  set Inflow CSV period = 0\n  set Output terminal CSV file = terminals.csv", 1)
    write_inflow(manifest, "Q", root / "inflow.csv")
    (root / "case.prm").write_text(text)
    receipt = {"network": "ADAN56", "inlet_boundary_id": 0, "terminal_boundary_ids": list(range(1, 32)),
               "source_git_sha": git("rev-parse", "HEAD", cwd=source),
               "mesh_sha256": sha256(mesh), "template_sha256": sha256(template),
               "case_sha256": sha256(root / "case.prm"), "inflow_sha256": sha256(root / "inflow.csv"),
               "heart_manifest": series.metadata, "time_interval_s": [0, final_time],
               "refinements": refinements, "pressure_role": "comparison-only",
               "terminal_closure": "ADAN56 original RCR; compatibility with MOX 0D pending",
               "periodic_repetition": False, "numerical_validation": "not-run"}
    (root / "coupling.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def split_terminal_traces(source, destination, boundary_ids):
    """Adapt the consolidated native boundary CSV to the existing organ DAG."""
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    rows = {boundary: [] for boundary in boundary_ids}
    with Path(source).open() as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames
        for row in reader:
            boundary = int(row["boundary_id"])
            rows[boundary].append(row)
    if any(len(values) < 2 for values in rows.values()):
        raise ValueError("Incomplete consolidated terminal traces")
    for boundary, values in rows.items():
        with (destination / f"terminal_{boundary}.csv").open("w") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(values)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest")
    parser.add_argument("binary")
    parser.add_argument("source")
    parser.add_argument("--final-time", type=float, default=8.)
    parser.add_argument("--refinements", type=int, default=5)
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    if any(key in os.environ for key in MPI_RANK_KEYS):
        raise ValueError("Run the ADAN56 orchestration adapter once outside an MPI launcher")
    receipt = prepare(args.manifest, args.source, ".", args.final_time, args.refinements)
    if args.prepare_only: return
    binary = Path(args.binary).resolve()
    receipt["binary_sha256"] = sha256(binary)
    process = subprocess.run([str(binary), "case.prm"], stderr=subprocess.PIPE, text=True)
    sys.stderr.write(process.stderr)
    Path("solver-diagnostics.log").write_text(process.stderr)
    process.check_returncode()
    receipt["solver_diagnostics"] = {"idas_error_reports": process.stderr.count("[IDAS ERROR]"),
                                     "log_sha256": sha256("solver-diagnostics.log")}
    heart = Series(args.manifest)
    split_terminal_traces("output/adan56/terminals.csv", "output/adan56",
                         [0, *receipt["terminal_boundary_ids"]])
    with Path("output/adan56/terminal_0.csv").open() as stream:
        inlet = list(csv.DictReader(stream))
    if len(inlet) < 2 or abs(float(inlet[-1]["time_s"]) - args.final_time) > 1e-12:
        raise ValueError("Native inlet output did not reach the requested final time")
    error = max(abs(float(row["flow_m3_s"]) + heart.at(float(row["time_s"]), "Q")) for row in inlet)
    receipt["inlet_flow_check"] = {"max_absolute_error_m3_s": error, "tolerance_m3_s": 1e-12}
    if error > 1e-12: raise ValueError("ADAN56 inlet trace does not match the prescribed cardiac flow")
    for terminal in receipt["terminal_boundary_ids"]:
        mapping = {"time_column": "time_s", "time_unit": "s", "anatomy": f"ADAN56-terminal-{terminal}",
                   "provenance": {"source": "MetricFlowX ADAN56 boundary trace", "coupling": receipt},
                   "channels": [{"name": "P", "column": "pressure_Pa", "quantity": "pressure", "unit": "Pa",
                                 "reference": "ADAN56-tube-law-and-original-RCR-datum"},
                                {"name": "Q", "column": "flow_m3_s", "quantity": "flow", "unit": "m3/s",
                                 "positive_direction": "out-of-network"}]}
        exported = import_csv(f"output/adan56/terminal_{terminal}.csv", mapping, f"terminals/{terminal}")
        if abs(Series(exported).times[-1] - args.final_time) > 1e-12:
            raise ValueError(f"Incomplete output at terminal {terminal}")
    receipt["execution"] = "completed"
    receipt["numerical_validation"] = "pending conservation, convergence and MOX 0D compatibility"
    Path("coupling.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__": main()
