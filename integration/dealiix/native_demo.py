"""Small real MetricFlowX run, followed by terminal-data preparation (not an organ model)."""
import argparse
import json
from pathlib import Path
import subprocess

from .contracts import Series, import_csv, write_inflow
from .sources import git, sha256


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest")
    parser.add_argument("binary")
    parser.add_argument("source")
    args = parser.parse_args()
    series = Series(args.manifest)
    for time in (0, .01): series.at(time, "Q")
    write_inflow(args.manifest, "Q", "inflow.csv")
    source = Path(args.source).resolve()
    text = (source / "parameters/constant.prm.in").read_text().replace("@SOURCE_DIR@", str(source))
    replacements = {"set Final time                        = 1.1": "set Final time = 0.01",
                    "set Number of global refinement  = 4": "set Number of global refinement = 1",
                    "set Time interval between each output = 0.005": "set Time interval between each output = 0.002",
                    "set Output filename              = solution": "set Output filename = solution\n  set Inflow CSV file = inflow.csv\n  set Output directory = output",
                    "set Numerical flux type          = HLL": "set Numerical flux type = HLL_HDG",
                    "set Absolute error tolerance = 1e-06": "set Absolute error tolerance = 1e-12",
                    "set Relative error tolerance = 1e-05": "set Relative error tolerance = 1e-8"}
    for original, replacement in replacements.items():
        if text.count(original) != 1: raise ValueError("Demo parameter template changed upstream")
        text = text.replace(original, replacement)
    Path("case.prm").write_text(text)
    subprocess.run([str(Path(args.binary).resolve()), "case.prm"], check=True)
    mapping = {"time_column": "time_s", "time_unit": "s", "anatomy": "synthetic-terminal-1",
               "provenance": {"synthetic": True, "source": "native-MetricFlowX-boundary-trace",
                              "binary_sha256": sha256(args.binary),
                              "source_git_sha": git("rev-parse", "HEAD", cwd=source),
                              "physiological_validation": False},
               "channels": [{"name": "P", "column": "pressure_Pa", "quantity": "pressure", "unit": "Pa",
                             "reference": "synthetic-fixture-pressure-datum"},
                            {"name": "Q", "column": "flow_m3_s", "quantity": "flow", "unit": "m3/s",
                             "positive_direction": "out-of-network"}]}
    import_csv("output/terminal_1.csv", mapping, "terminal")


if __name__ == "__main__": main()
