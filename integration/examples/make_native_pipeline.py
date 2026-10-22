#!/usr/bin/env python3
"""Generate a portable CLI pipeline using explicitly selected native build artifacts."""
import argparse
import json
from pathlib import Path
import sys

parser = argparse.ArgumentParser()
parser.add_argument("--binary", required=True)
parser.add_argument("--source", required=True)
parser.add_argument("--output", required=True)
parser.add_argument("--poisson-binary", help="Optional native ImmersX scalar-transfer test receiver")
args = parser.parse_args()
integration = Path(__file__).resolve().parents[1]
profile = {"environment": {"PYTHONPATH": str(integration)}}
pipeline = {"version": 1, "source_revisions": json.loads((integration / "sources.json").read_text()),
            "stages": [
                {"id": "heart", "profile": profile,
                 "command": [sys.executable, "-m", "dealiix", "import-csv",
                             str(integration / "examples/heart.csv"), str(integration / "examples/heart-mapping.json"), "heart"],
                 "outputs": {"waveform": {"kind": "timeseries", "path": "heart/manifest.json"}}},
                {"id": "circulation", "profile": profile,
                 "inputs": {"heart": {"stage": "heart", "output": "waveform", "channels": ["Q"],
                                      "time_interval_s": [0, .01], "anatomy": "synthetic-aorta"}},
                 "command": [sys.executable, "-m", "dealiix.native_demo", "{input_heart}",
                             str(Path(args.binary).resolve()), str(Path(args.source).resolve())],
                 "outputs": {"terminal": {"kind": "timeseries", "path": "terminal/manifest.json"}}},
                {"id": "boundary-data", "profile": profile,
                 "inputs": {"terminal": {"stage": "circulation", "output": "terminal", "channels": ["P", "Q"],
                                         "anatomy": "synthetic-terminal-1"}},
                 "command": [sys.executable, "-m", "dealiix", "validate", "{input_terminal}"]}
            ]}
if args.poisson_binary:
    pipeline["stages"].append({"id": "poisson-transfer-test", "profile": profile,
        "inputs": {"terminal": {"stage": "circulation", "output": "terminal", "channels": ["P"],
                                "time_interval_s": [.006, .006]}},
        "command": [sys.executable, "-m", "dealiix.poisson_demo", "{input_terminal}",
                    str(Path(args.poisson_binary).resolve())],
        "outputs": {"report": {"kind": "file", "path": "result.json"}}})
Path(args.output).write_text(json.dumps(pipeline, indent=2) + "\n")
