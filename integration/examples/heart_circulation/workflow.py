#!/usr/bin/env python3
"""MOX QAV -> native MetricFlowX; preserve the complete supplied history."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import shlex
import socket
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "integration"))
from dealiix.assets import download_assets
from dealiix.mox import cardiac_inputs, catalog, plot_pv
RELEASE = "https://github.com/dealii-X/dealii-X/releases/download/assets/"
REVISION = "9e013df07eeaa585bd140bbd629bfbf4d9a5bee4"
THREAD_VARIABLES = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
                    "DEAL_II_NUM_THREADS", "NUMEXPR_NUM_THREADS")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command, **kwargs):
    print("+", " ".join(map(str, command)), flush=True)
    subprocess.run(list(map(str, command)), check=True, **kwargs)


def parameters(args, out, final_time):
    template = Path(__file__).with_name("parameters") / f"{args.model}.prm.in"
    return (template.read_text()
            .replace("@DATA_DIR@", str(out))
            .replace("@REFINEMENTS@", str(args.refinements))
            .replace("@FINAL_TIME@", format(final_time, ".12g")))


def prepare(args, source, out):
    run(["git", "-C", source, "merge-base", "--is-ancestor", REVISION, "HEAD"])
    out.mkdir(parents=True, exist_ok=True)
    if (out / "output").exists():
        raise ValueError(f"Results already exist: {out}/output; choose a fresh --output")
    raw_dir = args.assets or ROOT / "assets"
    if not args.assets:
        download_assets(raw_dir, RELEASE.rstrip("/"))
    receipt = cardiac_inputs(raw_dir, args.case, out)
    if args.model == "adavn_full":
        network = out / "network"
        if args.adavn_network and not network.exists():
            shutil.copytree(args.adavn_network, network)
        if not (network / "provenance.json").exists():
            cache = args.adavn_cache
            if not cache:
                cache = ROOT / "build/integration/adan_sources"
                command = [sys.executable, source / "tools/adan/download_sources.py",
                           "--data-dir", cache]
                if args.geometry == "anatomical":
                    if os.environ.get("ADAVN_ATLAS_PERMISSION") != "1":
                        raise ValueError("Anatomical atlas download requires ADAVN_ATLAS_PERMISSION=1; "
                                         "or supply an existing authorized --adavn-cache")
                    command += ["--include-atlas", "--include-veins", "--atlas-permission"]
                run(command)
            with (out / "prepare_network.log").open("w") as log:
                run([sys.executable, source / "tools/adan/prepare_full.py",
                     "--data-dir", cache, "--output-dir", network,
                     "--geometry", args.geometry], stdout=log, stderr=subprocess.STDOUT)
        provenance = json.loads((network / "provenance.json").read_text())
        if provenance["geometry_mode"] != args.geometry:
            raise ValueError("Prepared geometry differs from requested geometry")
        for name, checksum in provenance["sha256"].items():
            if digest(network / name) != checksum:
                raise ValueError(f"Prepared network checksum mismatch: {name}")
    else:
        (out / "network").mkdir(exist_ok=True)
        shutil.copy2(source / "tutorials/04_adan56/network.vtk", out / "network/network.vtk")
    (out / "parameters.prm").write_text(parameters(args, out, receipt["time_end_s"]))
    plot_pv(raw_dir, out / "mox_reference")
    receipt.update(model=args.model, ranks=32 if args.model == "adavn_full" else 4,
                   threads_per_rank=1, source_revision=subprocess.check_output(
                       ["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip(),
                   executable=str(args.executable) if args.executable else None,
                   executable_sha256=digest(args.executable) if args.executable else None,
                   parameters_sha256=digest(out / "parameters.prm"),
                   cardiac_period_s=catalog()["cases"][args.case]["period_s"],
                   cardiac_period_basis="MOX: 0.8 s normal, 10% faster severe (0.8/1.1 s)",
                   final_tolerances_start_s=4.8,
                   inputs_sha256={str(path.relative_to(out)): digest(path)
                                  for path in [out / "inflow.csv", out / "heart_reference.csv",
                                               *(out / "network").glob("*")] if path.is_file()},
                   coupling="one-way QAV; no clipping, repetition, pressure shift or phase alignment")
    (out / "provenance.json").write_text(json.dumps(receipt, indent=2) + "\n")


def plot(args, out):
    import numpy as np
    os.environ.setdefault("MPLCONFIGDIR", "/tmp/heart-circulation-matplotlib")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    receipt = json.loads((out / "provenance.json").read_text())
    window = receipt["analysis_cycle"]
    period = receipt["cardiac_period_s"]
    heart = np.genfromtxt(out / "heart_reference.csv", delimiter=",", names=True)
    times, pressure, flow = [], [], []
    with (out / "output/terminals.csv").open() as f:
        for row in csv.DictReader(f):
            if int(row["boundary_id"]) == 0:
                times.append(float(row["time_s"]))
                pressure.append(float(row["pressure_Pa"]))
                flow.append(-float(row["flow_m3_s"]))  # outward -> into network
    t, p, q = map(np.array, (times, pressure, flow))
    if (len(t) < 2 or abs(t[-1] - receipt["time_end_s"]) > 1e-9
            or not np.isfinite(np.column_stack((t, p, q))).all()):
        raise ValueError("Simulation did not finish the supplied history")
    if not np.all(np.diff(t) > 0):
        raise ValueError("Repeated/misordered inlet export")
    start, end = window["start_s"], window["end_s"]
    if t[0] > start or t[-1] < end:
        raise ValueError("Insufficient last-beat coverage")
    sample_t = np.concatenate(([start], t[(t > start) & (t < end)], [end]))
    p, q = np.interp(sample_t, t, p), np.interp(sample_t, t, q)
    t = sample_t
    reference = np.interp(t, heart["time_s"], heart["pressure_Pa"])
    prescribed = np.interp(t, heart["time_s"], heart["flow_m3_s"])
    volume = np.interp(t, heart["time_s"], heart["volume_LV_mL"])
    if len(t) < 100:
        raise ValueError("Insufficient last-beat sampling")
    mmhg = catalog()["pressure_conversion_Pa_per_mmHg"]
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.4), constrained_layout=True)
    for pp, label in ((p, args.model + " inlet"), (reference, "MOX ascending aorta (0D)")):
        axes[0].plot(t - start, pp / mmhg, label=label)
        axes[1].plot(prescribed * 1e6, pp / mmhg, label=label)
        axes[2].plot(volume, pp / mmhg, label=label)
    axes[0].set(xlabel="Time in last cycle [s]", ylabel="Pressure [mmHg]")
    axes[1].set(xlabel="Aortic-valve flow [mL/s]", ylabel="Pressure [mmHg]", title="Pressure–flow loop")
    axes[2].set(xlabel="MOX left-ventricular volume [mL]", ylabel="Aortic pressure [mmHg]", title="Aortic pressure vs MOX LV volume")
    axes[0].legend(fontsize=8)
    for ax in axes:
        ax.grid(alpha=.25)
    fig.suptitle(f"{args.model}, {receipt['case']}: MOX forcing, {start:.4f}–{end:g} s")
    for ext in ("png", "pdf", "svg"):
        fig.savefig(out / f"pressure_loops.{ext}", dpi=180)
    plt.close(fig)
    error = p - reference
    duration = t[-1] - t[0]
    average = lambda value: float(np.trapezoid(value, t) / duration)
    metrics = dict(case=receipt["case"], analysis_cycle=window, last_cycle_start_s=start, last_cycle_end_s=float(t[-1]),
                   samples=len(t), mean_inlet_pressure_mmHg=average(p)/mmhg,
                   mean_MOX_pressure_mmHg=average(reference)/mmhg,
                   pressure_rmse_mmHg=average(error**2)**.5/mmhg,
                   maximum_pressure_difference_mmHg=float(np.max(np.abs(error)))/mmhg,
                   max_inlet_flow_error_m3_s=float(np.max(np.abs(q-prescribed))),
                   pressure_difference_includes_model_and_closure_differences=True,
                   pressure_volume_plot="Aortic pressures against shared MOX LV volume; not an LV pressure-volume loop")
    metrics["max_inlet_flow_error_fraction_of_peak"] = metrics["max_inlet_flow_error_m3_s"] / float(np.max(np.abs(prescribed)))
    metrics["inlet_flow_acceptance_fraction_of_peak"] = 1e-3
    if metrics["max_inlet_flow_error_fraction_of_peak"] > 1e-3:
        raise ValueError(f"Inlet did not reproduce QAV: {metrics}")
    previous = np.interp(t - period, times, pressure)
    metrics["last_vs_previous_pressure_rmse_mmHg"] = average((p-previous)**2)**.5/mmhg
    mass = np.genfromtxt(out / "output/mass_conservation.csv", delimiter=",", names=True)
    mass_t = np.concatenate(([start], mass["t"][(mass["t"] > start) & (mass["t"] < end)], [end]))
    last_mass = {name: np.interp(mass_t, mass["t"], mass[name]) for name in mass.dtype.names}
    delta_volume = float(last_mass["total_volume"][-1] - last_mass["total_volume"][0])
    integrated_flux = float(np.trapezoid(last_mass["net_flux"], last_mass["t"]))
    stroke_volume = float(np.trapezoid(prescribed, t))
    metrics["last_cycle_mass_defect_m3"] = delta_volume - integrated_flux
    metrics["last_cycle_mass_defect_fraction_of_stroke_volume"] = abs(delta_volume-integrated_flux)/abs(stroke_volume)
    metrics["last_cycle_max_mass_imbalance_m3_s"] = float(np.max(np.abs(last_mass["imbalance"])))
    metrics["last_cycle_minimum_network_volume_m3"] = float(np.min(last_mass["total_volume"]))
    import meshio
    collection = ET.parse(out / "output" / f"{args.model}.pvd").findall(".//DataSet")
    final = max(collection, key=lambda entry: float(entry.attrib["timestep"]))
    if abs(float(final.attrib["timestep"]) - receipt["time_end_s"]) > 1e-9:
        raise ValueError("Final VTK time disagrees with supplied history")
    final_mesh = out / "output" / final.attrib["file"]
    pieces = ET.parse(final_mesh).findall(".//Piece")
    minimum_area, exported_points = float("inf"), 0
    for piece in pieces:
        mesh = meshio.read(final_mesh.parent / piece.attrib["Source"])
        for field in ("area", "velocity", "pressure"):
            if not np.isfinite(mesh.point_data[field]).all():
                raise ValueError(f"Nonfinite final VTK field: {field}")
        minimum_area = min(minimum_area, float(np.min(mesh.point_data["area"])))
        exported_points += len(mesh.points)
    if minimum_area <= 0 or len(pieces) != receipt["ranks"]:
        raise ValueError("Invalid final MPI mesh output")
    metrics["final_vtk_minimum_sampled_area_m2"] = minimum_area
    metrics["final_vtk_exported_points"] = exported_points
    metrics["final_vtk_rank_pieces"] = len(pieces)
    native = json.loads((out / "output/initialization_statistics.json").read_text())
    if native["ramp_last_relative_factor"] != 1 or native["ramp_last_absolute_factor"] != 1:
        raise ValueError("Final tolerance ramp did not reach the configured precision")
    metrics["final_relative_tolerance_multiplier"] = native["ramp_last_relative_factor"]
    metrics["final_absolute_tolerance_multiplier"] = native["ramp_last_absolute_factor"]
    (out / "comparison.json").write_text(json.dumps(metrics, indent=2) + "\n")
    np.savetxt(out / "last_cycle.csv", np.column_stack((t,p,reference,q,prescribed,volume)),
               delimiter=",", header="time_s,inlet_pressure_Pa,MOX_pressure_Pa,inlet_flow_m3_s,QAV_m3_s,MOX_LV_volume_mL", comments="")
    print(json.dumps(metrics, indent=2))


def main():
    for key in THREAD_VARIABLES:
        os.environ[key] = "1"
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("model", choices=("adavn_full", "adan56"))
    p.add_argument("--stage", choices=("prepare", "run", "plot", "all"), default="prepare")
    p.add_argument("--case", choices=tuple(catalog()["cases"]), default="normal_pressure")
    p.add_argument("--assets", type=Path, help="Use already downloaded, checksum-verified MOX assets")
    p.add_argument("--adavn-network", type=Path, help="Reuse a checksum-verified prepared full network")
    p.add_argument("--source", type=Path, default=os.environ.get("METRIC_FLOW_SOURCE", ROOT / "applications/circulation/metric-flow-x"))
    p.add_argument("--executable", type=Path, default=os.environ.get("BLOOD_FLOW_EXECUTABLE"))
    p.add_argument("--output", type=Path)
    p.add_argument("--adavn-cache", type=Path, default=os.environ.get("ADAVN_SOURCE_CACHE"))
    p.add_argument("--geometry", choices=("anatomical", "metric"), default="anatomical")
    p.add_argument("--refinements", type=int, default=3)
    p.add_argument("--launcher", default=os.environ.get("MPIEXEC", "mpiexec"))
    p.add_argument("--submit", action="store_true", help="Submit execution and plotting to a dedicated Slurm job")
    p.add_argument("--partition", default="gpu")
    p.add_argument("--dependency", help="Optional Slurm dependency, e.g. afterok:12345")
    p.add_argument("--allow-local", action="store_true", help="Explicitly permit execution outside Slurm")
    args = p.parse_args()
    if args.refinements < 0:
        p.error("--refinements must be nonnegative")
    out = (args.output or ROOT / "build/integration/heart_circulation" / args.case / args.model).resolve()
    if args.stage in ("prepare", "all"):
        args.source = args.source.resolve()
        args.executable = args.executable.resolve() if args.executable else None
        if args.executable and not args.executable.is_file():
            p.error("Missing blood_flow executable")
        prepare(args, args.source, out)
    if args.submit and args.stage in ("run", "all"):
        receipt = json.loads((out / "provenance.json").read_text())
        if args.executable is None and receipt["executable"] is None:
            p.error("Set --executable or BLOOD_FLOW_EXECUTABLE before submitting")
        base = [sys.executable, str(Path(__file__).resolve()), args.model,
                "--case", args.case, "--output", str(out), "--launcher", args.launcher]
        if args.executable:
            base += ["--executable", str(args.executable.resolve())]
        batch = out / "run.sbatch"
        batch.write_text("#!/usr/bin/env bash\nset -euo pipefail\n" +
                         shlex.join(base + ["--stage", "run"]) + "\n" +
                         shlex.join(base + ["--stage", "plot"]) + "\n")
        command = ["sbatch", "--parsable", "--partition", args.partition,
                   "--nodes", "1", "--ntasks", str(receipt["ranks"]),
                   "--cpus-per-task", "1", "--hint=nomultithread", "--mem=32G",
                   "--time=02:00:00", "--job-name", "mox-" + args.case + "-" + args.model,
                   "--output", str(out / "slurm-%j.log"), str(batch)]
        if args.dependency:
            command[1:1] = ["--dependency", args.dependency]
        job = subprocess.check_output(command, text=True).strip()
        (out / "slurm_job_id.txt").write_text(job + "\n")
        print("Submitted Slurm job", job)
        return
    if args.stage in ("run", "all"):
        if not os.environ.get("SLURM_JOB_ID") and not args.allow_local:
            p.error("Use --submit for Slurm, or explicitly select --allow-local on a standalone machine")
        receipt = json.loads((out / "provenance.json").read_text())
        if receipt["case"] != args.case or receipt["model"] != args.model:
            raise ValueError("Prepared case/model differs from requested run")
        for name, checksum in receipt["inputs_sha256"].items():
            if digest(out / name) != checksum:
                raise ValueError(f"Prepared input changed: {name}")
        supplied_executable = args.executable or receipt["executable"]
        if not supplied_executable:
            p.error("Set --executable or BLOOD_FLOW_EXECUTABLE to a build of the pinned MetricFlowX source")
        executable = Path(supplied_executable).resolve()
        if receipt["executable"] is None:
            receipt.update(executable=str(executable), executable_sha256=digest(executable))
            (out / "provenance.json").write_text(json.dumps(receipt, indent=2) + "\n")
        if str(executable) != receipt["executable"] or digest(executable) != receipt["executable_sha256"] or digest(out / "parameters.prm") != receipt["parameters_sha256"]:
            raise ValueError("Prepared executable/parameters changed")
        if (out / "output").exists():
            raise ValueError("Refusing to overwrite an existing simulation")
        env = os.environ.copy()
        mpi_temp = tempfile.mkdtemp(prefix=f"mox-mpi-{env.get('SLURM_JOB_ID', 'local')}-")
        env["TMPDIR"] = mpi_temp
        env["OMPI_MCA_shmem_mmap_relocate_backing_file"] = "1"
        env["OMPI_MCA_shmem_mmap_backing_file_base_dir"] = mpi_temp
        # OpenMPI on this site can expand the batch affinity mask. Choose one
        # OS CPU per physical core from the inherited allocation and let each
        # newly launched rank bind itself before exec, without a nested launcher.
        cores = {}
        for cpu in sorted(os.sched_getaffinity(0)):
            topology = Path(f"/sys/devices/system/cpu/cpu{cpu}/topology")
            key = ((topology / "physical_package_id").read_text().strip(),
                   (topology / "core_id").read_text().strip())
            cores.setdefault(key, cpu)
        selected_cpus = list(cores.values())[:receipt["ranks"]]
        if len(selected_cpus) != receipt["ranks"]:
            raise ValueError("Fewer allocated physical cores than requested MPI ranks")
        binding_dir = out / "rank_bindings"
        binding_dir.mkdir(exist_ok=True)
        env["DEALIIX_RANK_CPUS"] = ",".join(map(str, selected_cpus))
        env["DEALIIX_BINDING_DIR"] = str(binding_dir)
        runtime = dict(host=socket.gethostname(), slurm_job_id=env.get("SLURM_JOB_ID"),
                       batch_allowed_os_cpus=sorted(os.sched_getaffinity(0)),
                       selected_os_cpus=selected_cpus,
                       ranks=receipt["ranks"], computational_threads_per_rank=1,
                       mpi_binding="Each new rank binds to one allocated physical core before solver exec")
        (out / "runtime.json").write_text(json.dumps(runtime, indent=2) + "\n")
        with (out / "run.log").open("w") as log:
            launch = [args.launcher, "--bind-to", "none", "-n", str(receipt["ranks"]),
                      sys.executable, Path(__file__).with_name("rank_entry.py")]
            run(launch + [executable, out / "parameters.prm"],
                cwd=out, env=env, stdout=log, stderr=subprocess.STDOUT)
        for rank, cpu in enumerate(selected_cpus):
            recorded = json.loads((binding_dir / f"rank_{rank:02d}.json").read_text())
            if recorded["rank"] != rank or recorded["allowed_os_cpus"] != [cpu]:
                raise ValueError(f"Rank {rank} did not bind to its allocated core")
    if args.stage in ("plot", "all"):
        plot(args, out)


if __name__ == "__main__":
    main()
