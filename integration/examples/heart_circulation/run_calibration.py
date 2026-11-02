#!/usr/bin/env python3
"""Run one serial MPI case per model concurrently, then compare all four cases."""
import argparse
import concurrent.futures
import datetime
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--results", type=Path, required=True)
    p.add_argument("--assets", type=Path, required=True)
    p.add_argument("--baseline", type=Path, required=True)
    p.add_argument("--launcher", default="mpiexec")
    p.add_argument("--allow-local", action="store_true")
    args = p.parse_args()
    if not args.allow_local:
        p.error("Explicit --allow-local is required for this workstation campaign")
    if sys.platform != "darwin":
        p.error("This is the local macOS controller; use workflow.py/Slurm on Linux")
    root = args.results.resolve()
    status = root/"run_status.json"
    if status.exists():
        p.error("This campaign already has a run status; do not launch it twice")
    if not (root/"calibration_campaign.json").is_file():
        p.error("Prepare the calibration campaign first")
    directory = Path(__file__).resolve().parent
    lock = threading.RLock()
    stopping = threading.Event()
    active = {}
    now = lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
    state = dict(status="running", pid=os.getpid(), started_at=now(),
                 issue="https://github.com/dealii-X/dealii-X/issues/42", jobs=[
                     dict(case=case, model=model, status="queued")
                     for model in ("adan56", "adavn_full")
                     for case in ("normal_pressure", "severe_hypertension")])

    def save():
        with lock:
            temporary = status.with_suffix(".tmp")
            temporary.write_text(json.dumps(state, indent=2)+"\n")
            temporary.replace(status)

    def stop(signum, frame):
        stopping.set()
        with lock:
            for process in active.values():
                if process.poll() is None:
                    try:
                        os.killpg(process.pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
            state.update(status="cancelled", finished_at=now())
            save()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    save()
    awake = (subprocess.Popen(["/usr/bin/caffeinate", "-i", "-w", str(os.getpid())])
             if sys.platform == "darwin" else None)

    def run_model(model):
        for job in [row for row in state["jobs"] if row["model"] == model]:
            if stopping.is_set():
                return
            out = root/job["case"]/model
            with lock:
                job.update(status="running", started_at=now(), directory=str(out))
                save()
            for stage in ("run", "plot"):
                command = [sys.executable, str(directory/"workflow.py"), model,
                           "--case", job["case"], "--stage", stage, "--output", str(out),
                           "--allow-local", "--launcher", args.launcher]
                print(now(), stage, job["case"], model, flush=True)
                with (out/f"{stage}_controller.log").open("w") as log:
                    process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                                               start_new_session=True)
                    with lock:
                        active[model] = process
                        job.update(stage=stage, process_pid=process.pid)
                        save()
                    code = process.wait()
                with lock:
                    active.pop(model, None)
                    if code or stopping.is_set():
                        job.update(status="cancelled" if stopping.is_set() else "failed",
                                   failed_stage=stage, returncode=code, finished_at=now())
                        save()
                        break
            with lock:
                if job["status"] == "running":
                    job.update(status="completed", finished_at=now())
                save()

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as workers:
            futures = [workers.submit(run_model, model) for model in ("adan56", "adavn_full")]
            for future in futures:
                future.result()
        if stopping.is_set():
            return
        if any(row["status"] != "completed" for row in state["jobs"]):
            state.update(status="completed_with_failures", finished_at=now())
            save()
            return
        state.update(status="postprocessing")
        save()
        output = root/"comparisons"
        for script, destination in (("compare_mox.py", output),
                                    ("arterial_pressure_mox.py", output/"arterial_compartment")):
            subprocess.run([sys.executable, str(directory/script), "--assets", str(args.assets.resolve()),
                            "--results", str(root), "--output", str(destination)], check=True)
        report = []
        for job in state["jobs"]:
            case, model = job["case"], job["model"]
            before = json.loads((args.baseline/case/model/"comparison.json").read_text())
            after = json.loads((root/case/model/"comparison.json").read_text())
            report.append(dict(case=case, model=model,
                original_inlet_pressure_RMSE_mmHg=before["pressure_rmse_mmHg"],
                fitted_inlet_pressure_RMSE_mmHg=after["pressure_rmse_mmHg"],
                inlet_pressure_RMSE_reduction_mmHg=before["pressure_rmse_mmHg"]-after["pressure_rmse_mmHg"],
                original_mean_inlet_pressure_mmHg=before["mean_inlet_pressure_mmHg"],
                fitted_mean_inlet_pressure_mmHg=after["mean_inlet_pressure_mmHg"]))
        (root/"fit_assessment.json").write_text(json.dumps(report, indent=2)+"\n")
        state.update(status="completed", finished_at=now(), comparisons=str(output))
        save()
    except Exception as exc:
        state.update(status="controller_failed", error=str(exc), finished_at=now())
        save()
        raise
    finally:
        if awake is not None and awake.poll() is None:
            awake.terminate()


if __name__ == "__main__":
    main()
