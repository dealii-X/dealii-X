#!/usr/bin/env python3
"""Bind this new rank to one allocated physical core before starting the solver."""
import json
import os
from pathlib import Path
import socket
import sys

rank = int(os.environ["OMPI_COMM_WORLD_LOCAL_RANK"])
cpus = [int(cpu) for cpu in os.environ["DEALIIX_RANK_CPUS"].split(",")]
os.sched_setaffinity(0, {cpus[rank]})
binding = dict(rank=rank, host=socket.gethostname(),
               allowed_os_cpus=sorted(os.sched_getaffinity(0)))
target = Path(os.environ["DEALIIX_BINDING_DIR"]) / f"rank_{rank:02d}.json"
target.write_text(json.dumps(binding, indent=2) + "\n")
os.execv(sys.argv[1], sys.argv[1:])
