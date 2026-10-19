"""Build pinned isolated sources and retain a machine-readable validation record."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess

from .sources import git, sha256

OPTIONS = {
    "dealii": ["-DDEAL_II_ALLOW_AUTODETECTION=ON", "-DDEAL_II_COMPONENT_EXAMPLES=OFF",
               "-DDEAL_II_WITH_MPI=ON", "-DDEAL_II_WITH_P4EST=ON", "-DDEAL_II_WITH_PETSC=ON",
               "-DDEAL_II_WITH_SUNDIALS=ON", "-DDEAL_II_WITH_TRILINOS=ON"],
    "coral": ["-DCORAL_BUILD_BACKEND_DEALII=ON", "-DCORAL_BUILD_TESTS=ON", "-DCORAL_BUILD_SHARED_CORE=ON"],
    "immersx": ["-DENABLE_COUPLED_PROBLEMS=OFF", "-DENABLE_GOOGLE_TESTING=OFF",
                "-DENABLE_DEAL_II_APP_TESTING=OFF", "-DIMMERSX_BUILD_CORAL_PLUGINS=ON"],
    "4c": ["-DFOUR_C_TRILINOS_ROOT=/opt/4C-dependencies", "-DFOUR_C_WITH_DEAL_II=OFF",
           "-DFOUR_C_WITH_GOOGLETEST=OFF", "-DFOUR_C_ENABLE_DOCUMENTATION=OFF",
           "-DFOUR_C_ENABLE_PYTHON_BINDINGS=OFF", "-DFOUR_C_ENABLE_WARNINGS_AS_ERRORS=OFF"],
}


def build(args):
    manifest = json.loads(Path(args.manifest).read_text())
    entry = next(e for e in manifest["components"] if e["name"] == args.component)
    source = Path(args.source_root).resolve() / args.component
    if git("rev-parse", "HEAD", cwd=source) != entry["candidate_sha"]:
        raise ValueError("Source revision differs from manifest")
    build_dir = Path(args.build_root).resolve() / args.component
    prefix = Path(args.prefix_root).resolve() / args.component
    build_dir.mkdir(parents=True, exist_ok=True)
    result = {"component": args.component, "sha": entry["candidate_sha"],
              "patches": {}, "commands": [], "status": "RUNNING",
              "manifest_sha256": sha256(args.manifest), "build_driver_sha256": sha256(__file__)}

    def run(command, cwd=build_dir):
        result["commands"].append(command)
        subprocess.run(command, cwd=cwd, check=True)

    try:
        patch_path = Path(__file__).resolve().parents[1] / "patches" / (args.component + ".patch")
        if patch_path.exists():
            result["patches"][patch_path.name] = sha256(patch_path)
            check = subprocess.run(["git", "apply", "--reverse", "--check", str(patch_path)], cwd=source,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if check.returncode:
                run(["git", "apply", "--check", str(patch_path)], source)
                run(["git", "apply", str(patch_path)], source)
        if args.component == "platform":
            run(["npm", "ci", "--ignore-scripts"], source)
            run(["npm", "run", "check:electron"], source)
            run(["npm", "run", "check"], source)
            run(["npm", "test"], source)
            run(["npm", "run", "build"], source)
            prefix.mkdir(parents=True, exist_ok=True)
            for name in ("dist", "dist-electron", "package.json", "package-lock.json"):
                item = source / name
                if item.is_dir(): shutil.copytree(item, prefix / name, dirs_exist_ok=True)
                elif item.exists(): shutil.copyfile(item, prefix / name)
        elif args.component == "psctoolkit":
            run(["bash", str(Path(__file__).resolve().parents[1] / "containers/build-psctoolkit.sh"),
                 str(source), str(prefix), str(args.jobs), args.gpu])
        else:
            command = ["cmake", "-S", str(source), "-B", str(build_dir),
                       "-DCMAKE_BUILD_TYPE=Release", "-DCMAKE_INSTALL_PREFIX=" + str(prefix),
                       "-DCMAKE_INSTALL_LIBDIR=lib",
                       "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON",
                       "-DCMAKE_BUILD_RPATH_USE_ORIGIN=ON", "-DCMAKE_INSTALL_RPATH_USE_LINK_PATH=ON"]
            if args.dealii_dir: command.append("-DDEAL_II_DIR=" + args.dealii_dir)
            if args.coral_dir: command.append("-Dcoral_DIR=" + args.coral_dir)
            command.extend(OPTIONS.get(args.component, []))
            command.extend(args.cmake_arg)
            run(command)
            compile_commands = build_dir / "compile_commands.json"
            if compile_commands.exists() and any(flag in compile_commands.read_text()
                                                for flag in ("-march=native", "-mtune=native")):
                raise ValueError("Native CPU flags are forbidden in distributable builds")
            command = ["cmake", "--build", str(build_dir), "--parallel", str(args.jobs)]
            if args.target: command.extend(["--target", args.target])
            run(command)
            if (build_dir / "cmake_install.cmake").exists() and args.component not in ("exabrain", "polydeal"):
                run(["cmake", "--install", str(build_dir)])
            # Preserve actual native executables/libraries even in upstreams with
            # no install rules. ET_REL object files and compiler probes are excluded.
            for item in build_dir.rglob("*"):
                if not item.is_file() or "CMakeFiles" in item.parts or item.suffix == ".o": continue
                with item.open("rb") as stream: header = stream.read(18)
                if header[:4] == b"\x7fELF" and int.from_bytes(header[16:18], "little") in (2, 3):
                    destination = prefix / "native" / item.relative_to(build_dir)
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, destination)
        result["status"] = "BUILT"
        result["numerical_validation"] = "not-run"
    except Exception as error:
        result.update(status="FAILED", error=str(error))
        raise
    finally:
        (build_dir / "build-record.json").write_text(json.dumps(result, indent=2) + "\n")
        if result["status"] == "BUILT":
            shutil.copyfile(build_dir / "build-record.json", prefix / "build-record.json")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("component")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--build-root", required=True)
    parser.add_argument("--prefix-root", required=True)
    parser.add_argument("--dealii-dir")
    parser.add_argument("--coral-dir")
    parser.add_argument("--target")
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--gpu", choices=["cpu", "cuda"], default="cpu")
    parser.add_argument("--cmake-arg", action="append", default=[])
    build(parser.parse_args())


if __name__ == "__main__": main()
