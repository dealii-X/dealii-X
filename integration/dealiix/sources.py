"""Audit sources and prepare isolated snapshots; never update a user's checkout."""
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
CATALOG = [
    ("dealii", "libraries/dealii", "https://github.com/dealii/dealii.git", "master", ["MPI", "p4est", "PETSc", "Trilinos", "SUNDIALS"]),
    ("lifex", "applications/heart/lifex", "https://gitlab.com/lifex/lifex-public.git", "main", ["dealii"]),
    ("metric-flow-x", "applications/circulation/metric-flow-x", "https://github.com/luca-heltai/metric-flow-x.git", "main", ["dealii", "SUNDIALS", "PETSc"]),
    ("immersx", "applications/liver/immersx", "https://github.com/luca-heltai/immersx.git", "master", ["dealii", "coral"]),
    ("exabrain", "applications/brain/ExaBrain", "https://github.com/BRAINIACS-Group/ExaBrain.git", "main", ["dealii", "Trilinos/Sacado"]),
    ("exadg", "applications/lungs/exadg", "https://github.com/temuer/exadg.git", "alveolar-model", ["dealii", "p4est"]),
    ("4c", "applications/lungs/4C", "https://github.com/4C-multiphysics/4C.git", "main", ["Trilinos/Thyra/Shards/Intrepid2/Zoltan2/Stratimikos/Teko/NOX", "CLN", "NetCDF"]),
    ("psctoolkit", "libraries/psctoolkit", "https://github.com/psctoolkit/psctoolkit.git", "master", ["MPI", "BLAS", "Fortran"]),
    ("polydeal", "tools/polygonal", "https://github.com/fdrmrc/Polydeal.git", "main", ["dealii"]),
    ("platform", "tools/dealiiX-platform", "https://github.com/2listic/dealiiX-platform.git", "main", ["Node.js", "Electron", "coral", "visualizer", "remote-server"]),
    ("coral", "tools/dealiiX-platform/coral", "https://github.com/2listic/coral.git", "HEAD", []),
    ("visualizer", "tools/dealiiX-platform/coral-visualizer", "https://github.com/2listic/coral-visualizer.git", "HEAD", []),
    ("remote-server", "tools/dealiiX-platform/coral-remote-server", "https://github.com/2listic/coral-remote-server.git", "HEAD", []),
]


def git(*args, cwd=None):
    return subprocess.check_output(["git", *args], cwd=cwd, text=True, stderr=subprocess.PIPE, timeout=90).strip()


def inventory(refresh=False):
    def inspect(row):
        name, path, url, branch, dependencies = row
        initialized = (ROOT / path / ".git").exists()
        if initialized:
            checkout_sha = git("rev-parse", "HEAD", cwd=ROOT / path)
        else:
            parent, child = Path(path).parent, Path(path).name
            checkout_sha = git("ls-tree", "HEAD", child, cwd=ROOT / parent).split()[2]
        entry = dict(name=name, path=path, url=url, branch=branch, dependencies=dependencies,
                     checkout_sha=checkout_sha, initialized=initialized,
                     validation="not-run", data_status="group-case-required")
        entry["working_tree_dirty"] = initialized and bool(git("status", "--porcelain", cwd=ROOT / path))
        if initialized:
            entry["checkout_nested_gitlinks"] = {
                line.split("\t", 1)[1]: line.split()[2]
                for line in git("ls-tree", "-r", "HEAD", cwd=ROOT / path).splitlines()
                if line.startswith("160000 ")}
        try:
            ref = "HEAD" if branch == "HEAD" else "refs/heads/" + branch
            entry["candidate_sha"] = (git("ls-remote", url, ref).split()[0]
                                      if refresh else entry["checkout_sha"])
            entry["candidate_origin"] = "remote-query" if refresh else "local-checkout"
        except (subprocess.SubprocessError, IndexError) as error:
            entry["candidate_sha"] = None
            entry["query_error"] = str(error)
        return entry
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        return {"version": 1, "policy": "validate-before-updating-gitlinks",
                "components": list(pool.map(inspect, CATALOG))}


def prepare(manifest, destination, names):
    """Checkout exactly the selected candidate, including nested gitlinks."""
    destination = Path(destination).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    for entry in manifest["components"]:
        if names and entry["name"] not in names:
            continue
        sha = entry.get("candidate_sha")
        if not sha or len(sha) != 40:
            raise ValueError(f"No pinned candidate for {entry['name']}")
        target = destination / entry["name"]
        if target.exists():
            if git("rev-parse", "HEAD", cwd=target) != sha:
                raise ValueError(f"Refusing to replace existing snapshot: {target}")
            continue
        # A fresh clone reconstructs 4C independently of its damaged index.
        subprocess.run(["git", "init", str(target)], check=True, stdout=subprocess.DEVNULL)
        subprocess.run(["git", "-C", str(target), "remote", "add", "origin", entry["url"]], check=True)
        subprocess.run(["git", "-C", str(target), "fetch", "--depth=1", "origin", sha], check=True)
        environment = {**os.environ, "GIT_LFS_SKIP_SMUDGE": "1"}
        no_lfs = ["-c", "filter.lfs.process=", "-c", "filter.lfs.smudge=", "-c", "filter.lfs.required=false"]
        subprocess.run(["git", *no_lfs, "-C", str(target), "checkout", "--detach", sha], check=True, env=environment)
        subprocess.run(["git", *no_lfs, "-C", str(target), "-c", "url.https://github.com/.insteadOf=git@github.com:",
                        "submodule", "update", "--init", "--recursive", "--depth=1"], check=True, env=environment)


def sha256(path):
    with open(path, "rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()
