#!/usr/bin/env python3
"""Generate the real cardiac-data -> ADAN56 file-coupled pipeline."""
import argparse
import json
from pathlib import Path
import sys

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--binary", required=True)
parser.add_argument("--source", required=True)
parser.add_argument("--assets", default="assets")
parser.add_argument("--output", required=True)
parser.add_argument("--final-time", type=float, default=8.)
parser.add_argument("--refinements", type=int, default=5)
args = parser.parse_args()
integration = Path(__file__).resolve().parents[1]
profile = {"environment": {"PYTHONPATH": str(integration)}}
pipeline = {"version": 1, "source_revisions": json.loads((integration / "sources.json").read_text()),
            "stages": [
                {"id": "heart", "profile": profile,
                 "command": [sys.executable, "-m", "dealiix", "import-csv",
                             str(Path(args.assets).resolve() / "electromechanics.csv"),
                             str(integration / "examples/mox-heart-mapping.json"), "heart"],
                 "outputs": {"waveform": {"kind": "timeseries", "path": "heart/manifest.json"}}},
                {"id": "adan56", "profile": profile,
                 "inputs": {"heart": {"stage": "heart", "output": "waveform", "channels": ["Q", "P"],
                                      "time_interval_s": [0, args.final_time], "anatomy": "ascending-aorta"}},
                 "command": [sys.executable, "-m", "dealiix.adan56", "{input_heart}",
                             str(Path(args.binary).resolve()), str(Path(args.source).resolve()),
                             "--final-time", str(args.final_time), "--refinements", str(args.refinements)],
                 "outputs": {f"terminal_{i}": {"kind": "timeseries", "path": f"terminals/{i}/manifest.json"}
                             for i in range(1, 32)}}]}
Path(args.output).write_text(json.dumps(pipeline, indent=2) + "\n")
