#!/usr/bin/env python3
"""Prepare a first MOX load-fitting experiment from completed, unchanged runs."""
import argparse
import csv
import json
from pathlib import Path
import re
import shutil

import meshio
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import spsolve
from scipy.optimize import brentq

from compare_mox import ROOT, CASES, MODELS, MMHG, digest
from dealiix.mox import catalog, cycle_samples, cycle_window, read_history, verified_file


def targets(assets, case):
    raw = verified_file(assets, catalog()["cases"][case]["filename"])
    heart = read_history(raw, extra_fields=("QARSYS", "pVENSYS"))
    t = heart["time"]
    window = cycle_window(heart, case)
    last = cycle_samples(heart, window)
    mean = lambda y: float(np.trapezoid(np.interp(last, t, y), last)/(last[-1]-last[0]))
    dp = np.gradient(heart["pARSYS"], t, edge_order=2)
    mask = ((t > window["start_s"]-window["period_s"]) & (t < t[-1]-.003))
    dia = mask & (np.abs(heart["QAV"]) < .1) & (dp < -.1)
    if np.count_nonzero(dia) < 20:
        raise ValueError("Insufficient diastolic samples to estimate compliance")
    compliance = (heart["QAV"]-heart["QARSYS"])[dia]/dp[dia]
    x = np.column_stack((heart["QARSYS"][mask], np.gradient(heart["QARSYS"], t)[mask]))
    resistance, inertance = np.linalg.lstsq(x, (heart["pARSYS"]-heart["pVENSYS"])[mask], rcond=None)[0]
    return dict(mean_pressure_Pa=mean(heart["pARSYS"])*MMHG,
                mean_QAV_m3_s=mean(heart["QAV"])*1e-6,
                total_arterial_compliance_m3_Pa=float(np.median(compliance))*1e-6/MMHG,
                inferred_R_mmHg_s_mL=float(resistance), inferred_L_mmHg_s2_mL=float(inertance),
                diastolic_C_samples=int(dia.sum()), source_sha256=digest(raw))


def wall_compliance(data, arterial, pressure, stiffness):
    """Sum L*dA/dp at uniform target pressure; a quasi-static calibration proxy."""
    d = {name: values[arterial] for name, values in data.items()}
    a0, length = d["a_d"], d["L"]
    if "adavn_E_e" not in d:
        beta = 4*np.sqrt(np.pi)/3*d["E"]*stiffness*d["h_wall"]
        root = np.sqrt(a0)+(pressure-d["p_d"]-d["p0"])*a0/beta
        if np.any(root <= 0):
            return float("inf")
        return float(np.sum(length*2*a0*root/beta))

    def law(area):
        s = np.sqrt(area/a0)
        strain = s-1
        chi = (strain-d["adavn_epsilon_0"])/d["adavn_epsilon_r"]
        f = stiffness*(d["adavn_E_e"]*strain+d["adavn_E_c"]*d["adavn_epsilon_r"]*np.logaddexp(0, chi))
        df = stiffness*(d["adavn_E_e"]+d["adavn_E_c"]/(1+np.exp(-np.clip(chi, -700, 700))))
        factor = d["h_wall"]*np.sqrt(np.pi*a0)
        return d["adavn_p_ref"]+factor/area*f, factor/area**2*(-f+.5*s*df)

    lo, hi = .1*a0, a0.copy()
    if np.any(law(lo)[0] > pressure):
        return float("inf")
    for _ in range(40):
        p, derivative = law(hi)
        expand = p < pressure
        if not np.any(expand):
            break
        if np.any(derivative[expand] <= 0):
            return float("inf")
        hi[expand] *= 1.1
    else:
        return float("inf")
    for _ in range(55):
        mid = (lo+hi)/2
        below = law(mid)[0] < pressure
        lo = np.where(below, mid, lo)
        hi = np.where(below, hi, mid)
    _, derivative = law((lo+hi)/2)
    if np.any(derivative <= 0):
        return float("inf")
    return float(np.sum(length/derivative))


def fit_compliance(data, arterial, terminal_compliance, target):
    pressure, desired = target["mean_pressure_Pa"], target["total_arterial_compliance_m3_Pa"]
    total = lambda k: wall_compliance(data, arterial, pressure, k)+terminal_compliance/k
    grid = np.geomspace(.1, 30., 45)
    values = [total(k) for k in grid]
    brackets = [(a, b) for a, b, ca, cb in zip(grid[:-1], grid[1:], values[:-1], values[1:])
                if (ca-desired)*(cb-desired) <= 0]
    if not brackets:
        raise ValueError("Cannot bracket positive total arterial compliance target")
    lo, hi = min(brackets, key=lambda pair: abs(np.log(np.sqrt(pair[0]*pair[1]))))
    flo = total(lo)-desired
    for _ in range(45):
        mid = (lo+hi)/2
        f = total(mid)-desired
        if (f > 0) == (flo > 0):
            lo, flo = mid, f
        else:
            hi = mid
    k = (lo+hi)/2
    fitted = total(k)
    if not np.isfinite(fitted) or abs(fitted/desired-1) > 1e-6:
        raise ValueError("Total compliance target was not attained")
    return k, dict(wall_before_m3_Pa=wall_compliance(data, arterial, pressure, 1.),
                   terminal_before_m3_Pa=terminal_compliance,
                   wall_after_m3_Pa=wall_compliance(data, arterial, pressure, k),
                   terminal_after_m3_Pa=terminal_compliance/k,
                   total_after_m3_Pa=fitted)


def steady_pressure(n, edges, resistance, reservoirs, injection, inflow):
    a, b = edges.T
    g = 1/resistance
    rows = np.concatenate((a, b, a, b, reservoirs[:, 0].astype(int)))
    cols = np.concatenate((a, b, b, a, reservoirs[:, 0].astype(int)))
    values = np.concatenate((g, g, -g, -g, 1/reservoirs[:, 1]))
    rhs = np.zeros(n)
    rhs[injection] += inflow
    np.add.at(rhs, reservoirs[:, 0].astype(int), reservoirs[:, 2]/reservoirs[:, 1])
    matrix = coo_matrix((values, (rows, cols)), shape=(n, n)).tocsr()
    p = spsolve(matrix, rhs)
    residual = np.max(np.abs(matrix@p-rhs))/max(abs(inflow), 1e-30)
    if not np.isfinite(p).all() or residual > 1e-7:
        raise ValueError(f"Invalid steady resistance fit, relative residual {residual}")
    return float(p[injection])


def resistance_model(directory, model, mesh, point, data, stiffness):
    bids = point["boundary_id"].astype(int)
    if model == "adan56":
        edges = np.concatenate([block.data for block in mesh.cells])
        resistance = 8*np.pi*.004*data["L"]/data["a_d"]**2
        terminals = np.flatnonzero((bids != 0) & (bids != 255))
        inlet = int(np.flatnonzero(bids == 0)[0])
        def evaluate(scale, inflow):
            ports = np.column_stack((terminals,
                point["R1"][terminals]*np.sqrt(stiffness)+point["R2"][terminals]*scale,
                point["P_out"][terminals]))
            return steady_pressure(len(mesh.points), edges, resistance, ports, inlet, inflow)
        return evaluate
    with (directory/"network/edges.csv").open() as stream:
        records = list(csv.DictReader(stream))
    edges = np.array([[int(row["node0"]), int(row["node1"])] for row in records])
    resistance = np.array([float(row["resistance_Pa_s_m3"]) for row in records])
    scale_mask = np.array([row["kind"] in ("proximal", "connection") for row in records])
    provenance = json.loads((directory/"network/provenance.json").read_text())
    drains = np.flatnonzero(np.isin(point["source_node_id"], provenance["central_drain_nodes"]))
    ports = np.column_stack((point["source_node_id"][drains], point["R2"][drains], point["P_out"][drains]))
    def evaluate(scale, inflow):
        values = resistance*np.where(scale_mask, scale, 1.)
        return steady_pressure(int(edges.max())+1, edges, values, ports,
                               provenance["inlet_node"], inflow)
    return evaluate


def rewrite_scalars(path, changes):
    """Keep geometry/topology/header bytes and untouched scalar arrays intact."""
    text = path.read_text()
    if "\nASCII\n" not in text:
        raise ValueError("Expected the original ASCII legacy VTK input")
    for name, values in changes.items():
        pattern = re.compile(r"(SCALARS\s+"+re.escape(name)+r"\s+[^\n]+\nLOOKUP_TABLE\s+[^\n]+\n)(.*?)(?=SCALARS |POINT_DATA |CELL_DATA |\Z)", re.S)
        found = list(pattern.finditer(text))
        if len(found) != 1 or len(found[0][2].split()) != len(values):
            raise ValueError(f"Unexpected VTK scalar array: {name}")
        if not np.isfinite(values).all():
            raise ValueError(f"Nonfinite VTK scalar array: {name}")
        text = pattern.sub(lambda m: m[1]+"".join(f"{v:.16e}\n" for v in values), text)
    path.write_text(text)


def scale_csv(path, column, scale, kinds=None):
    with path.open() as stream:
        reader = csv.DictReader(stream)
        fields, rows = reader.fieldnames, list(reader)
    for row in rows:
        if kinds is None or row["kind"] in kinds:
            row[column] = format(float(row[column])*scale, ".17g")
    with path.open("w") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def prepare_one(baseline, destination, model, case, target, issue):
    old = baseline/case/model
    receipt = json.loads((old/"provenance.json").read_text())
    if (receipt["sha256"] != target["source_sha256"] or receipt["case"] != case
            or receipt["model"] != model or receipt["ranks"] != 1):
        raise ValueError("Baseline MOX history differs from calibration targets")
    if digest(Path(receipt["executable"])) != receipt["executable_sha256"]:
        raise ValueError("The previously validated solver executable changed")
    if digest(old/"parameters.prm") != receipt["parameters_sha256"]:
        raise ValueError("Baseline numerical parameters changed")
    out = destination/case/model
    out.mkdir(parents=True, exist_ok=False)
    for name, checksum in receipt["inputs_sha256"].items():
        if digest(old/name) != checksum:
            raise ValueError(f"Baseline input changed: {name}")
        (out/name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(old/name, out/name)
    mesh_name = "network.vtk" if model == "adan56" else "adavn_full.vtk"
    vtk = out/"network"/mesh_name
    mesh = meshio.read(vtk)
    data = {name: np.concatenate(values).ravel() for name, values in mesh.cell_data.items()}
    point = {name: values.ravel() for name, values in mesh.point_data.items()}
    arterial = np.ones(len(data["a_d"]), dtype=bool) if model == "adan56" else data["source_vessel_type"] == 1
    if model == "adan56":
        terminal = (point["boundary_id"] != 0) & (point["boundary_id"] != 255)
    else:
        mapping = json.loads((out/"network/mapping.json").read_text())
        terminal_bids = {row[f"boundary{end}"] for row in mapping if row["vessel_type"] == 1
                         for end in (0, 1) if row[f"boundary{end}"] not in (0, 255)}
        terminal = np.isin(point["boundary_id"], list(terminal_bids))
    stiffness, compliance = fit_compliance(data, arterial, float(point["C"][terminal].sum()), target)
    evaluate = resistance_model(out, model, mesh, point, data, stiffness)
    q, desired = target["mean_QAV_m3_s"], target["mean_pressure_Pa"]
    scale = brentq(lambda s: evaluate(s, q)-desired, 1e-4, 100., xtol=1e-9)
    fitted = evaluate(scale, q)
    if abs(fitted-desired)/MMHG > 1e-5:
        raise ValueError("Steady mean-pressure target was not attained")
    changes = {}
    for name in ("E", "adavn_E_e", "adavn_E_c"):
        if name in data:
            values = data[name].copy()
            values[arterial] *= stiffness
            changes[name] = values
    for name in ("R1", "R2", "C"):
        values = point[name].copy()
        factor = 1/stiffness if name == "C" else (np.sqrt(stiffness) if model == "adan56" and name == "R1" else scale)
        values[terminal] *= factor
        changes[name] = values
    rewrite_scalars(vtk, changes)
    if model == "adavn_full":
        scale_csv(out/"network/connections.csv", "resistance", scale)
        scale_csv(out/"network/edges.csv", "resistance_Pa_s_m3", scale, {"proximal", "connection"})
    calibration = dict(issue=issue, case=case, model=model, targets=target,
                       stiffness_multiplier=stiffness, arterial_terminal_C_multiplier=1/stiffness,
                       peripheral_resistance_multiplier=scale,
                       arterial_terminal_R1_multiplier=np.sqrt(stiffness) if model == "adan56" else scale,
                       quasi_static_compliance=compliance,
                       reference_geometry_steady_pressure_before_mmHg=evaluate(1., q)/MMHG,
                       reference_geometry_steady_pressure_after_mmHg=fitted/MMHG,
                       method="Fit global peripheral resistance in the reference-geometry steady graph; fit sum(L*dA/dp)+terminal C at uniform MOX mean pressure. Scale arterial elastic moduli by k and terminal C by 1/k. These are reduced-model proxies, not a transient optimum.",
                       preserved="Original geometry/topology, inflow, pressure datums, venous walls/compliances/impedances, ADAVN 15/85 split and drain weights, numerical parameters and output cadence.",
                       limitations="Compliance uses uniform target pressure; the steady graph uses reference geometry. Original 0D parameters remain inferred. Transient fit, periodicity, numerical convergence and conservation must be assessed separately.",
                       baseline_directory=str(old), baseline_parameters_sha256=receipt["parameters_sha256"],
                       baseline_inputs_sha256=receipt["inputs_sha256"])
    (out/"calibration.json").write_text(json.dumps(calibration, indent=2)+"\n")
    if model == "adavn_full":
        p = out/"network/provenance.json"
        network = json.loads(p.read_text())
        network["calibration"] = dict(issue=issue, stiffness_multiplier=stiffness,
                                     arterial_C_multiplier=1/stiffness, arterial_R_multiplier=scale)
        network["sha256"] = {name: digest(out/"network"/name) for name in network["sha256"]}
        p.write_text(json.dumps(network, indent=2)+"\n")
    text = (old/"parameters.prm").read_text().replace(str(old), str(out))
    (out/"parameters.prm").write_text(text)
    receipt.update(parameters_sha256=digest(out/"parameters.prm"), calibration=calibration,
                   inputs_sha256={name: digest(out/name) for name in receipt["inputs_sha256"]})
    receipt["inputs_sha256"]["calibration.json"] = digest(out/"calibration.json")
    (out/"provenance.json").write_text(json.dumps(receipt, indent=2)+"\n")
    print(f"{case}/{model}: wall stiffness x{stiffness:.5g}, terminal C x{1/stiffness:.5g}, peripheral R x{scale:.5g}", flush=True)
    return calibration


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--baseline", type=Path, default=ROOT/"build/integration/heart_circulation")
    p.add_argument("--assets", type=Path, default=ROOT/"assets")
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--issue", default="https://github.com/dealii-X/dealii-X/issues/42")
    args = p.parse_args()
    if args.output.exists():
        p.error("Choose a fresh calibration output directory")
    args.output.mkdir(parents=True)
    results = []
    for case in CASES:
        target = targets(args.assets, case)
        for model in MODELS:
            results.append(prepare_one(args.baseline.resolve(), args.output.resolve(), model, case, target, args.issue))
    (args.output/"calibration_campaign.json").write_text(json.dumps(dict(issue=args.issue, cases=results), indent=2)+"\n")


if __name__ == "__main__":
    main()
