"""Versioned SI time-series bundles, with explicit pressure and flow conventions."""
import bisect
import csv
import json
import math
from pathlib import Path
import shutil

from .sources import sha256

UNITS = {"time": {"s": 1., "ms": .001},
         "pressure": {"Pa": 1., "kPa": 1000., "mmHg": 133.322387415, "dyn/cm2": .1},
         "flow": {"m3/s": 1., "ml/s": 1e-6, "cm3/s": 1e-6, "l/min": 1e-3 / 60.}}
SI = {"pressure": "Pa", "flow": "m3/s"}


def finite(value):
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("Non-finite time-series value")
    return value


def relative_file(root, name):
    path = Path(name)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError(f"Expected a confined relative path: {name}")
    root = Path(root).resolve()
    result = (root / path).resolve()
    if not result.is_relative_to(root):
        raise ValueError(f"Path escapes bundle: {name}")
    return result


class Series:
    def __init__(self, manifest_path):
        self.path = Path(manifest_path).resolve()
        self.metadata = json.loads(self.path.read_text())
        m = self.metadata
        if m.get("version") != 1 or m.get("kind") != "timeseries":
            raise ValueError("Expected version 1 timeseries manifest")
        if not m.get("anatomy") or not m.get("provenance"):
            raise ValueError("Anatomy and provenance are required")
        channels = m["channels"]
        if not channels or len({c["name"] for c in channels}) != len(channels):
            raise ValueError("Channels must be nonempty and uniquely named")
        for channel in channels:
            if channel["quantity"] not in SI or channel["unit"] != SI[channel["quantity"]]:
                raise ValueError("Canonical channels must use supported SI units")
            if channel["quantity"] == "pressure" and not channel.get("reference"):
                raise ValueError("Pressure reference is required")
            if channel["quantity"] == "flow" and not channel.get("positive_direction"):
                raise ValueError("Flow orientation is required")
        if m.get("time_unit") != "s":
            raise ValueError("Canonical time unit must be s")
        data = relative_file(self.path.parent, m["data"])
        if sha256(data) != m["sha256"]:
            raise ValueError("Time-series checksum mismatch")
        with data.open(newline="") as source:
            reader = csv.DictReader(source)
            if reader.fieldnames != ["time_s", *[c["name"] for c in channels]]:
                raise ValueError("CSV header does not match manifest")
            self.rows = [[finite(row[name]) for name in reader.fieldnames] for row in reader]
        if len(self.rows) < 2 or any(a[0] >= b[0] for a, b in zip(self.rows, self.rows[1:])):
            raise ValueError("Need at least two strictly increasing sample times")
        self.times = [row[0] for row in self.rows]
        self.period = m.get("period_s")
        if self.period is not None:
            self.period = finite(self.period)
            if self.period <= 0 or not math.isclose(self.times[-1] - self.times[0], self.period, rel_tol=1e-10):
                raise ValueError("Periodic bundle must contain one complete period")
            if any(not math.isclose(a, b, rel_tol=1e-8, abs_tol=1e-14)
                   for a, b in zip(self.rows[0][1:], self.rows[-1][1:])):
                raise ValueError("Periodic endpoints must agree")

    def at(self, time, name):
        time = finite(time)
        index = [c["name"] for c in self.metadata["channels"]].index(name) + 1
        if self.period is not None and not self.times[0] <= time <= self.times[-1]:
            time = self.times[0] + (time - self.times[0]) % self.period
        if not self.times[0] <= time <= self.times[-1]:
            raise ValueError(f"Extrapolation forbidden at t={time}")
        right = min(max(bisect.bisect_right(self.times, time), 1), len(self.times) - 1)
        a, b = self.rows[right - 1], self.rows[right]
        return a[index] + (b[index] - a[index]) * ((time - a[0]) / (b[0] - a[0]))


def import_csv(source_path, config, destination):
    """Convert explicitly mapped source columns and units; never guess MOX headers."""
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    channels = config["channels"]
    canonical = []
    for channel in channels:
        item = {key: value for key, value in channel.items() if key not in ("column", "scale", "offset")}
        item["unit"] = SI[channel["quantity"]]
        canonical.append(item)
    with open(source_path, newline="") as source, (destination / "data.csv").open("w", newline="") as output:
        reader = csv.DictReader(source, delimiter=config.get("delimiter", ","))
        writer = csv.writer(output)
        writer.writerow(["time_s", *[c["name"] for c in channels]])
        for row in reader:
            time = finite(row[config["time_column"]]) * UNITS["time"][config["time_unit"]]
            values = [finite(row[c["column"]]) * UNITS[c["quantity"]][c["unit"]] * finite(c.get("scale", 1))
                      + finite(c.get("offset", 0)) for c in channels]
            writer.writerow([time, *values])
    metadata = {"version": 1, "kind": "timeseries", "time_unit": "s", "data": "data.csv",
                "sha256": sha256(destination / "data.csv"), "channels": canonical,
                "anatomy": config["anatomy"], "geometry": config.get("geometry"),
                "provenance": {**config["provenance"], "source_sha256": sha256(source_path)}}
    if "period_s" in config:
        metadata["period_s"] = config["period_s"]
    manifest = destination / "manifest.json"
    manifest.write_text(json.dumps(metadata, indent=2) + "\n")
    Series(manifest)
    return manifest


def copy_series(source, destination):
    series = Series(source)
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    data = relative_file(series.path.parent, series.metadata["data"])
    target = relative_file(destination, series.metadata["data"])
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(data, target)
    shutil.copyfile(series.path, destination / "manifest.json")
    return destination / "manifest.json"


def write_inflow(manifest, channel, destination):
    series = Series(manifest)
    metadata = next(c for c in series.metadata["channels"] if c["name"] == channel)
    if metadata["quantity"] != "flow":
        raise ValueError("MetricFlowX inlet requires a flow channel")
    with open(destination, "w", newline="") as output:
        writer = csv.writer(output)
        writer.writerow(["time_s", "flow_m3_s"])
        for time in series.times:
            writer.writerow([time, series.at(time, channel)])
