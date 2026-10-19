import csv
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from dealiix.contracts import Series, copy_series, import_csv, relative_file, write_inflow
from dealiix.pipeline import run_pipeline, validate
from dealiix.stage import execute


class Workflows(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.source = self.root / "heart.csv"
        self.source.write_text("ms,mls,mmHg\n0,0,80\n500,2,100\n1000,0,80\n")
        self.mapping = {"time_column": "ms", "time_unit": "ms", "anatomy": "aorta",
                        "provenance": {"synthetic": True}, "channels": [
                            {"name": "Q", "column": "mls", "quantity": "flow", "unit": "ml/s",
                             "positive_direction": "heart-to-aorta"},
                            {"name": "P", "column": "mmHg", "quantity": "pressure", "unit": "mmHg",
                             "reference": "gauge-to-atmosphere"}]}

    def tearDown(self):
        self.temporary.cleanup()

    def bundle(self, **updates):
        return import_csv(self.source, {**self.mapping, **updates}, self.root / "bundle")

    def test_si_and_interpolation(self):
        series = Series(self.bundle())
        self.assertAlmostEqual(series.at(.25, "Q"), 1e-6)
        self.assertAlmostEqual(series.at(.5, "P"), 13332.2387415)
        self.assertEqual(series.at(1, "Q"), 0)

    def test_extrapolation_rejected(self):
        series = Series(self.bundle())
        for time in [-.1, 1.1, float("nan")]:
            with self.assertRaises(ValueError): series.at(time, "Q")

    def test_explicit_period(self):
        series = Series(self.bundle(period_s=1))
        self.assertAlmostEqual(series.at(1.25, "Q"), series.at(.25, "Q"))
        self.assertAlmostEqual(series.at(-.25, "Q"), series.at(.75, "Q"))

    def test_bad_period(self):
        with self.assertRaises(ValueError): self.bundle(period_s=2)

    def test_unclosed_period(self):
        self.source.write_text("ms,mls,mmHg\n0,0,80\n1000,2,80\n")
        with self.assertRaises(ValueError): self.bundle(period_s=1)

    def test_bad_rows(self):
        for data in ["0,0,80\n0,1,90", "0,0,80\n500,nan,90", "0,0,80"]:
            with self.subTest(data=data), tempfile.TemporaryDirectory() as out:
                self.source.write_text("ms,mls,mmHg\n" + data + "\n")
                with self.assertRaises(ValueError): import_csv(self.source, self.mapping, Path(out) / "bundle")

    def test_pressure_reference_required(self):
        del self.mapping["channels"][1]["reference"]
        with self.assertRaises(ValueError): self.bundle()

    def test_checksum(self):
        path = self.bundle()
        (path.parent / "data.csv").write_text("changed")
        with self.assertRaisesRegex(ValueError, "checksum"): Series(path)

    def test_bundle_copy_and_native_input(self):
        path = self.bundle()
        copied = copy_series(path, self.root / "copy")
        self.assertEqual(Series(copied).rows, Series(path).rows)
        write_inflow(copied, "Q", self.root / "inflow.csv")
        with (self.root / "inflow.csv").open() as stream:
            rows = list(csv.reader(stream))
        self.assertEqual(rows[0], ["time_s", "flow_m3_s"])
        with self.assertRaises(ValueError): write_inflow(copied, "P", self.root / "wrong.csv")

    def test_path_confinement(self):
        for name in ["../secret", "/secret"]:
            with self.assertRaises(ValueError): relative_file(self.root, name)
        (self.root / "escape").symlink_to(self.root.parent)
        with self.assertRaises(ValueError): relative_file(self.root, "escape/secret")

    def pipeline(self, fail=False):
        document = {"version": 1, "stages": [
            {"id": "producer", "command": [sys.executable, "-c", "import pathlib; pathlib.Path('data.txt').write_text('value')"],
             "outputs": {"data": {"path": "data.txt", "kind": "file"}}},
            {"id": "consumer", "inputs": {"data": {"stage": "producer", "output": "data", "kind": "file"}},
             "command": [sys.executable, "-c", "import pathlib,sys; assert pathlib.Path(sys.argv[1]).read_text()=='value'", "{input_data}"]},
            {"id": "independent", "command": [sys.executable, "-c", "pass"]}]}
        if fail: document["stages"][0]["command"] = [sys.executable, "-c", "raise SystemExit(9)"]
        return document

    def test_artifact_dependency_and_provenance(self):
        path = self.root / "pipeline.json"
        path.write_text(json.dumps(self.pipeline()))
        self.assertTrue(run_pipeline(path, self.root / "run", workers=2))
        record = json.loads((self.root / "run/provenance.json").read_text())
        self.assertEqual(record["stages"]["consumer"]["status"], "COMPLETED")
        self.assertIn("sha256", record["stages"]["consumer"]["inputs"]["data"])

    def test_failure_cascade_keeps_independent_branch(self):
        path = self.root / "pipeline.json"
        path.write_text(json.dumps(self.pipeline(fail=True)))
        self.assertFalse(run_pipeline(path, self.root / "run", workers=2))
        record = json.loads((self.root / "run/provenance.json").read_text())["stages"]
        self.assertEqual(record["consumer"]["status"], "CANCELLED")
        self.assertEqual(record["independent"]["status"], "COMPLETED")

    def test_missing_output_fails_producer(self):
        pipeline = self.pipeline()
        pipeline["stages"][0]["outputs"]["data"]["path"] = "absent"
        path = self.root / "pipeline.json"
        path.write_text(json.dumps(pipeline))
        self.assertFalse(run_pipeline(path, self.root / "run"))

    def test_cycle_rejected_before_directory_creation(self):
        document = self.pipeline()
        document["stages"][0]["after"] = ["consumer"]
        with self.assertRaises(ValueError): validate(document)

    def test_stage_wrapper_materializes_after_success(self):
        producer = self.root / "stage-producer"
        producer.mkdir()
        (producer / "out.txt").write_text("hello")
        from dealiix.pipeline import artifact_record
        artifact = {"kind": "file", "path": "out.txt"}
        (producer / "provenance.json").write_text(json.dumps({"status": "COMPLETED", "outputs": {"data": artifact_record(producer, artifact)}}))
        stage = self.root / "stage-consumer"
        stage.mkdir()
        spec = {"pipelineDirectory": str(self.root), "stageDirectory": str(stage),
                "inputs": {"data": {"producerDirectory": producer.name, "output": "data", "artifact": artifact, "destination": "inputs/data.txt"}}}
        path = stage / "spec.json"
        path.write_text(json.dumps(spec))
        execute(path, [sys.executable, "-c", "from pathlib import Path; assert Path('inputs/data.txt').read_text()=='hello'"])
        self.assertEqual(json.loads((stage / "provenance.json").read_text())["status"], "COMPLETED")


if __name__ == "__main__": unittest.main()
