import csv
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from dealiix import mox
from dealiix.adan56 import split_terminal_traces


class MoxHistories(unittest.TestCase):
    def test_macos_launch_uses_native_mpi_without_linux_affinity(self):
        path = Path(__file__).parents[1] / "examples/heart_circulation/workflow.py"
        spec = importlib.util.spec_from_file_location("heart_workflow_mac", path)
        workflow = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(workflow)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            binary = root / "solver"
            binary.write_text("unused test executable")
            parameters = root / "parameters.prm"
            parameters.write_text("synthetic parameters")
            (root / "provenance.json").write_text(json.dumps(dict(
                case="normal_pressure", model="adan56", ranks=4,
                executable=str(binary), executable_sha256=workflow.digest(binary),
                parameters_sha256=workflow.digest(parameters), inputs_sha256={})))
            with patch.object(workflow.sys, "platform", "darwin"), patch.object(
                workflow.sys, "argv", [str(path), "adan56", "--stage", "run",
                                      "--allow-local", "--output", str(root),
                                      "--launcher", "native-mpiexec"]
            ), patch.object(workflow, "run") as launch, patch.object(
                workflow.tempfile, "mkdtemp", return_value=str(root / "mpi")
            ), patch.object(workflow.os, "sched_getaffinity", create=True,
                            side_effect=AssertionError("Linux-only API")):
                workflow.main()
            self.assertEqual(launch.call_args.args[0],
                             ["native-mpiexec", "-n", "4", binary, parameters])
            runtime = json.loads((root / "runtime.json").read_text())
            self.assertEqual(runtime["platform"], "darwin")
            self.assertEqual(runtime["ranks"], 4)

    def test_consolidated_boundary_export_preserves_identity_and_flow_sign(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "terminals.csv"
            source.write_text("time_s,boundary_id,pressure_Pa,flow_m3_s\n"
                              "0,0,10000,-0.0001\n0,1,9000,0.0001\n"
                              "1,0,11000,-0.0002\n1,1,10000,0.0002\n")
            split_terminal_traces(source, root / "out", [0, 1])
            with (root / "out/terminal_0.csv").open() as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual([row["boundary_id"] for row in rows], ["0", "0"])
            self.assertEqual([float(row["flow_m3_s"]) for row in rows], [-1e-4, -2e-4])
            with self.assertRaisesRegex(ValueError, "Incomplete"):
                split_terminal_traces(source, root / "missing", [0, 1, 2])

    def test_periods_and_final_beat_from_mox_specification(self):
        normal = mox.cycle_window({"time": np.arange(8001) / 1000}, "normal_pressure")
        severe = mox.cycle_window({"time": np.arange(11637) / 1000}, "severe_hypertension")
        self.assertEqual(normal["start_s"], 7.2)
        self.assertEqual(normal["end_s"], 8.)
        self.assertAlmostEqual(severe["start_s"], 120 / 11)
        self.assertEqual(severe["end_s"], 11.636)
        self.assertAlmostEqual(severe["missing_tail_s"], 128 / 11 - 11.636)
        self.assertAlmostEqual(normal["period_s"] / severe["period_s"], 1.1)

    def test_reject_missing_final_beat(self):
        with self.assertRaisesRegex(ValueError, "duration"):
            mox.cycle_window({"time": np.arange(8001) / 1000}, "severe_hypertension")

    def test_last_cycle_never_extrapolates(self):
        data = {"time": np.arange(11637) / 1000}
        window = mox.cycle_window(data, "severe_hypertension")
        times = mox.cycle_samples(data, window)
        self.assertEqual(times[0], window["start_s"])
        self.assertEqual(times[-1], 11.636)
        self.assertTrue(np.all(np.diff(times) > 0))

    def test_si_conversion_keeps_negative_valve_flow_and_chamber_pressure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = root / "synthetic.csv"
            fields = ["time", "QAV", "pressure_AA", "pARSYS"]
            fields += [name for chamber, _ in mox.CHAMBERS
                       for name in (f"volume_{chamber}", f"pressure_{chamber}")]
            with raw.open("w") as stream:
                writer = csv.writer(stream)
                writer.writerow(fields)
                for time, flow in [(0, -1), (7.2, 2), (8., -1)]:
                    writer.writerow([time, flow, 13332.2, 100] + [90, 666.61] * 4)
            with patch.object(mox, "verified_file", return_value=raw), patch.object(
                mox, "cycle_window", return_value={"start_s": 7.2, "end_s": 8.}
            ), patch.object(mox, "catalog", return_value={**mox.catalog(), "files": {raw.name: {}}}):
                mox.cardiac_inputs(root, "normal_pressure", root)
            inflow = np.genfromtxt(root / "inflow.csv", delimiter=",", names=True)
            heart = np.genfromtxt(root / "heart_reference.csv", delimiter=",", names=True)
            self.assertEqual(inflow["flow_m3_s"][0], -1e-6)
            self.assertEqual(heart["pressure_RA_Pa"][0], 666.61)
            self.assertEqual(heart["pressure_Pa"][0], 13332.2)

    def test_modified_dataset_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            name = "electromechanics_SH_severe.csv"
            (Path(directory) / name).write_text("modified input")
            with self.assertRaisesRegex(ValueError, "checksum"):
                mox.verified_file(directory, name)

    def test_native_final_time_comes_from_selected_history(self):
        path = Path(__file__).parents[1] / "examples/heart_circulation/workflow.py"
        spec = importlib.util.spec_from_file_location("heart_workflow", path)
        workflow = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(workflow)
        from argparse import Namespace
        for model in ("adavn_full", "adan56"):
            for end in (8., 11.636):
                text = workflow.parameters(Namespace(model=model, refinements=3, output_interval=.01), Path("/run"), end)
                self.assertIn(f"set Final time = {end:g}\n", text)
                self.assertIn("set Inflow CSV period = 0", text)
                self.assertIn("set Maximum order of BDF = 5", text)
                self.assertIn("set Maximum number of nonlinear iterations = 100", text)
                self.assertIn("set Nonlinear convergence coefficient = 0.1", text)
                self.assertIn("set Maximum step size = " + ("0.0001" if model == "adan56" else "0.02"), text)
                self.assertIn("set Maximum IDA internal steps per output = 1000000", text)
                self.assertIn("set Time interval between each output = 0.01", text)
                self.assertNotIn("set Output time interval", text)
                self.assertNotIn("@", text)


if __name__ == "__main__":
    unittest.main()
