"""Coarse application workflows; numerical kernels remain in their native solvers."""
import argparse
import json
import os
from pathlib import Path
import subprocess

from .contracts import Series, import_csv, relative_file, write_inflow
from .pipeline import artifact_record, MPI_RANK_KEYS


def execute(component, operation, request_path):
    request_path = Path(request_path).resolve()
    request = json.loads(request_path.read_text())
    if request.get("version") != 1 or request.get("component") != component:
        raise ValueError("Wrong application request version/component")
    case = Path(request["case_directory"])
    if not case.is_absolute():
        case = Path.cwd() / case
    case = case.resolve()
    if operation in ("prepare", "validate"):
        for source in request.get("inputs", {}).values():
            source_path = Path(source)
            Series(source_path if source_path.is_absolute() else Path.cwd() / source_path)
    if operation == "prepare":
        case.mkdir(parents=True, exist_ok=False)
        substitutions = {}
        if "sample" in request:
            sample = request["sample"]
            series = Series(sample["manifest"])
            substitutions[sample["placeholder"]] = format(
                series.at(sample["time_s"], sample["channel"]) * sample.get("scale", 1), ".17g")
        for name, text in request.get("files", {}).items():
            destination = relative_file(case, name)
            destination.parent.mkdir(parents=True, exist_ok=True)
            for token, value in substitutions.items(): text = text.replace(token, value)
            destination.write_text(text)
        if "inflow" in request:
            spec = request["inflow"]
            manifest = Path(spec["manifest"])
            if not manifest.is_absolute(): manifest = Path.cwd() / manifest
            write_inflow(manifest, spec["channel"], case / "inflow.csv")
    elif operation == "run":
        if component == "heart":
            spec = request["import"]
            source = Path(spec["source"])
            if not source.is_absolute(): source = request_path.parent / source
            import_csv(source, spec["mapping"], case / "heart")
        else:
            command = request["command"]
            if not isinstance(command, list) or not command or not all(isinstance(x, str) for x in command):
                raise ValueError("Application command must be an argv array")
            mpi = request.get("mpi")
            if mpi:
                if any(key in os.environ for key in MPI_RANK_KEYS):
                    raise ValueError("Nested MPI launch is forbidden")
                if mpi["launcher"] not in ("mpiexec", "mpirun", "srun") or mpi["ranks"] < 1:
                    raise ValueError("Invalid MPI configuration")
                command = [mpi["launcher"], *mpi.get("args", []), "-n", str(mpi["ranks"]), *command]
            subprocess.run(command, cwd=case, check=True, timeout=request.get("timeout_s", 3600))
    elif operation == "export":
        for spec in request.get("exports", []):
            source = relative_file(case, spec["source"])
            import_csv(source, spec["mapping"], relative_file(case, spec["destination"]))
    elif operation == "diagnostics":
        # No universal physiological criterion is inferred from finite output.
        records = {name: artifact_record(case, value) for name, value in request["outputs"].items()}
        (case / "diagnostics.json").write_text(json.dumps({"outputs": records,
            "validation": "artifact-integrity-only"}, indent=2) + "\n")
        if request.get("diagnostics_command"):
            subprocess.run(request["diagnostics_command"], cwd=case, check=True)
    elif operation != "validate":
        raise ValueError("Unsupported workflow operation")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("component")
    parser.add_argument("operation", choices=["prepare", "validate", "run", "export", "diagnostics"])
    parser.add_argument("request")
    arguments = parser.parse_args()
    execute(arguments.component, arguments.operation, arguments.request)
