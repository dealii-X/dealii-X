"""Execution-time artifact handoff shared by Electron and Slurm stages."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
from datetime import datetime, timezone

from .contracts import Series, copy_series, relative_file
from .pipeline import artifact_record
from .sources import sha256


def execute(spec_path, command):
    spec = json.loads(Path(spec_path).read_text())
    root = Path(spec["pipelineDirectory"]).resolve()
    stage = Path(spec["stageDirectory"]).resolve()
    if not stage.is_relative_to(root) or stage == root:
        raise ValueError("Stage directory must be inside pipeline directory")
    record = {"version": 1, "started": datetime.now(timezone.utc).isoformat(),
              "command": command, "profile": spec.get("profile", {}), "inputs": {}, "outputs": {}}
    try:
        for name, binding in spec.get("inputs", {}).items():
            if not name or Path(name).name != name or name in (".", ".."):
                raise ValueError("Invalid input name")
            producer = relative_file(root, binding["producerDirectory"])
            output = binding["artifact"]
            provenance = json.loads((producer / "provenance.json").read_text())
            if provenance.get("status") != "COMPLETED":
                raise ValueError("Producer did not complete")
            current = artifact_record(producer, output)
            if current != provenance["outputs"][binding["output"]]:
                raise ValueError("Producer output changed after completion")
            source = relative_file(producer, output["path"])
            destination = relative_file(stage, binding["destination"])
            if destination.exists():
                raise ValueError("Refusing to replace stage input")
            if output["kind"] == "timeseries":
                copy_series(source, destination)
                series = Series(destination / "manifest.json")
                if binding.get("anatomy", series.metadata["anatomy"]) != series.metadata["anatomy"]:
                    raise ValueError("Incompatible anatomical interface")
                for channel in binding.get("channels", []):
                    if channel not in [c["name"] for c in series.metadata["channels"]]:
                        raise ValueError(f"Missing channel {channel}")
                for channel in series.metadata["channels"]:
                    for time in binding.get("timeInterval", []):
                        series.at(time, channel["name"])
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, destination)
            record["inputs"][name] = current
        environment = {**os.environ, **spec.get("profile", {}).get("environment", {})}
        result = subprocess.run(command, cwd=stage, env=environment, check=True)
        for name, output in spec.get("outputs", {}).items():
            record["outputs"][name] = artifact_record(stage, output)
        record.update(status="COMPLETED", returncode=result.returncode)
        return 0
    except Exception as error:
        record.update(status="FAILED", error=str(error))
        raise
    finally:
        record["finished"] = datetime.now(timezone.utc).isoformat()
        record["spec_sha256"] = sha256(spec_path)
        (stage / "provenance.json").write_text(json.dumps(record, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("spec")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        parser.error("An argv command after -- is required")
    raise SystemExit(execute(args.spec, command))


if __name__ == "__main__":
    main()
