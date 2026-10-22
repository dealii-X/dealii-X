"""File-coupled DAG runner. Commands are argv arrays, never shell fragments."""
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

from .contracts import Series, copy_series, relative_file
from .sources import sha256

NAME = re.compile(r"^[A-Za-z0-9_-]+$")
MPI_RANK_KEYS = ("OMPI_COMM_WORLD_RANK", "PMI_RANK", "PMIX_RANK", "SLURM_PROCID")


def validate(pipeline):
    if pipeline.get("version") != 1:
        raise ValueError("Unsupported pipeline version")
    stages = {s["id"]: s for s in pipeline["stages"]}
    if not stages or len(stages) != len(pipeline["stages"]):
        raise ValueError("Stage ids must be nonempty and unique")
    for ident, stage in stages.items():
        if not NAME.fullmatch(ident):
            raise ValueError("Invalid stage id")
        for output, artifact in stage.get("outputs", {}).items():
            if not NAME.fullmatch(output):
                raise ValueError("Invalid artifact name")
            relative_file(Path.cwd(), artifact["path"])
            if artifact.get("kind") not in ("file", "timeseries"):
                raise ValueError("Unknown artifact kind")
        parents = set(stage.get("after", []))
        for name, binding in stage.get("inputs", {}).items():
            if not NAME.fullmatch(name):
                raise ValueError("Invalid input name")
            producer = stages[binding["stage"]]
            output = producer["outputs"][binding["output"]]
            if binding.get("kind", output["kind"]) != output["kind"]:
                raise ValueError("Incompatible artifact kinds")
            parents.add(binding["stage"])
        if ident in parents or not parents.issubset(stages):
            raise ValueError("Invalid stage dependencies")
        stage["dependencies"] = sorted(parents)
        command = stage["command"]
        if not isinstance(command, list) or not command or any(not isinstance(a, str) for a in command):
            raise ValueError("Command must be a nonempty argv array")
        if stage.get("mpi", {}).get("ranks", 1) < 1:
            raise ValueError("MPI rank count must be positive")
    remaining = set(stages)
    while remaining:
        ready = {s for s in remaining if not (set(stages[s]["dependencies"]) & remaining)}
        if not ready:
            raise ValueError("Cyclic pipeline")
        remaining -= ready
    return stages


def artifact_record(stage_dir, artifact):
    path = relative_file(stage_dir, artifact["path"])
    if not path.is_file():
        raise ValueError(f"Missing output artifact: {path}")
    if artifact["kind"] == "timeseries":
        series = Series(path)
        return {**artifact, "sha256": sha256(path), "data_sha256": series.metadata["sha256"]}
    return {**artifact, "sha256": sha256(path)}


def run_pipeline(pipeline_path, run_directory, workers=1):
    if workers < 1:
        raise ValueError("Worker count must be positive")
    pipeline_path = Path(pipeline_path).resolve()
    document = json.loads(pipeline_path.read_text())
    stages = validate(document)
    run_directory = Path(run_directory).resolve()
    run_directory.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(pipeline_path, run_directory / "pipeline.json")
    records = {}

    def execute(ident):
        stage = stages[ident]
        directory = run_directory / ("stage-" + ident)
        directory.mkdir()
        record = {"status": "RUNNING", "started": datetime.now(timezone.utc).isoformat(),
                  "profile": stage.get("profile", {}), "inputs": {}, "outputs": {}}
        try:
            substitutions = {"source": str(pipeline_path.parent), "run": str(run_directory), "stage": str(directory)}
            for name, binding in stage.get("inputs", {}).items():
                producer = run_directory / ("stage-" + binding["stage"])
                artifact = stages[binding["stage"]]["outputs"][binding["output"]]
                # Verify again immediately before use, not just when producer finished.
                current = artifact_record(producer, artifact)
                expected = records[binding["stage"]]["outputs"][binding["output"]]
                if current != expected:
                    raise ValueError("Producer artifact changed after completion")
                path = relative_file(producer, artifact["path"])
                destination = directory / "inputs" / name
                if artifact["kind"] == "timeseries":
                    copied = copy_series(path, destination)
                    series = Series(copied)
                    if "anatomy" in binding and binding["anatomy"] != series.metadata["anatomy"]:
                        raise ValueError("Incompatible anatomical interface")
                    for channel in binding.get("channels", []):
                        if channel not in [c["name"] for c in series.metadata["channels"]]:
                            raise ValueError(f"Missing channel {channel}")
                    interval = binding.get("time_interval_s")
                    if interval:
                        for channel in series.metadata["channels"]:
                            series.at(interval[0], channel["name"])
                            series.at(interval[1], channel["name"])
                else:
                    destination.mkdir(parents=True)
                    copied = destination / path.name
                    shutil.copyfile(path, copied)
                substitutions["input_" + name] = str(copied)
                record["inputs"][name] = current
            command = [arg.format_map(substitutions) for arg in stage["command"]]
            environment = {**os.environ, **stage.get("profile", {}).get("environment", {})}
            mpi = stage.get("mpi")
            if mpi:
                if any(key in os.environ for key in MPI_RANK_KEYS):
                    raise ValueError("Nested MPI launch is forbidden")
                launcher = mpi.get("launcher", "mpirun")
                if launcher not in ("mpirun", "mpiexec", "srun"):
                    raise ValueError("Unsupported MPI launcher")
                command = [launcher, *(mpi.get("args", [])),
                           "-n", str(mpi["ranks"]), *command]
            record["argv"] = command
            record["executable"] = shutil.which(command[0], path=environment.get("PATH"))
            with (directory / "stdout.log").open("w") as stdout, (directory / "stderr.log").open("w") as stderr:
                subprocess.run(command, cwd=directory, env=environment, stdout=stdout,
                               stderr=stderr, check=True, timeout=stage.get("timeout_s", 3600))
            record["outputs"] = {name: artifact_record(directory, artifact)
                                 for name, artifact in stage.get("outputs", {}).items()}
            record["status"] = "COMPLETED"
        except Exception as error:
            record.update(status="FAILED", error=str(error))
        record["finished"] = datetime.now(timezone.utc).isoformat()
        (directory / "provenance.json").write_text(json.dumps(record, indent=2) + "\n")
        return record

    pending = set(stages)
    running = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        while pending or running:
            for ident in sorted(pending.copy()):
                parents = stages[ident]["dependencies"]
                if not all(parent in records for parent in parents):
                    continue
                pending.remove(ident)
                if any(records[parent]["status"] != "COMPLETED" for parent in parents):
                    records[ident] = {"status": "CANCELLED", "reason": "A parent did not complete"}
                else:
                    running[pool.submit(execute, ident)] = ident
            if running:
                done, _ = wait(running, return_when=FIRST_COMPLETED)
                for future in done:
                    records[running.pop(future)] = future.result()
    result = {"version": 1, "pipeline_sha256": sha256(pipeline_path), "stages": records,
              "source_revisions": document.get("source_revisions", {}),
              "scientific_validation": "not-established-by-workflow-execution"}
    (run_directory / "provenance.json").write_text(json.dumps(result, indent=2) + "\n")
    return all(record["status"] == "COMPLETED" for record in records.values())
