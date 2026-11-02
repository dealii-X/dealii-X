"""Collect the complete ELF dependency closure of installed 4C artifacts."""
from pathlib import Path
import re
import shutil
import subprocess
import sys

prefix, destination = map(Path, sys.argv[1:])
destination.mkdir(parents=True, exist_ok=True)
for item in prefix.rglob("*"):
    if not item.is_file(): continue
    with item.open("rb") as stream:
        if stream.read(4) != b"\x7fELF": continue
    result = subprocess.run(["ldd", str(item)], capture_output=True, text=True)
    if "not found" in result.stdout: raise RuntimeError(result.stdout)
    for name in re.findall(r"(?:=>\s+)?(/[^\s()]+)", result.stdout):
        source = Path(name)
        target = destination / source.name
        if target.exists() and target.read_bytes() != source.read_bytes():
            raise RuntimeError(f"Conflicting runtime library: {target}")
        shutil.copy2(source, target)
