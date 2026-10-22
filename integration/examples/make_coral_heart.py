#!/usr/bin/env python3
"""Generate a real heart CSV-import workflow using installed plugin registry names."""
import argparse
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("directory")
args = parser.parse_args()
directory = Path(args.directory).resolve()
directory.mkdir(parents=True, exist_ok=False)
examples = Path(__file__).resolve().parent
request = {"version": 1, "component": "heart", "case_directory": "case",
           "import": {"source": str(examples / "heart.csv"),
                      "mapping": json.loads((examples / "heart-mapping.json").read_text())},
           "outputs": {"waveform": {"kind": "timeseries", "path": "heart/manifest.json"}}}
request_path = directory / "request.json"
request_path.write_text(json.dumps(request, indent=2) + "\n")
nodes = {"0": {"type": "std::string", "value": str(request_path), "qualified_id": "0"}}
edges = {}
for ident, operation in enumerate(["prepare", "run", "diagnostics"], start=1):
    nodes[str(ident)] = {"type": "dealiix::heart::" + operation, "qualified_id": str(ident)}
    edges[str(ident)] = {"source": ident - 1, "target": ident, "source_output": 0, "target_input": 0}
(directory / "graph.json").write_text(json.dumps({"version": 1, "author": "deal.II-X", "workflow": {"nodes": nodes, "edges": edges}}, indent=2) + "\n")
