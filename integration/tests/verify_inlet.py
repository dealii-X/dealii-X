#!/usr/bin/env python3
"""Quantitative gate: exported outward inlet flow must match -Q_prescribed."""
import argparse
import csv
import json
from pathlib import Path

from dealiix.contracts import Series

parser = argparse.ArgumentParser()
parser.add_argument("manifest")
parser.add_argument("terminal_csv")
parser.add_argument("--channel", default="Q")
parser.add_argument("--absolute-tolerance", type=float, default=1e-12)
args = parser.parse_args()
series = Series(args.manifest)
with open(args.terminal_csv, newline="") as source:
    rows = list(csv.DictReader(source))
if len(rows) < 2: raise ValueError("Missing inlet time history")
errors = [abs(float(row["flow_m3_s"]) + series.at(float(row["time_s"]), args.channel)) for row in rows]
result = {"max_absolute_flow_error_m3_s": max(errors), "tolerance_m3_s": args.absolute_tolerance,
          "passed": max(errors) <= args.absolute_tolerance, "samples": len(rows)}
print(json.dumps(result, indent=2))
raise SystemExit(0 if result["passed"] else 1)
