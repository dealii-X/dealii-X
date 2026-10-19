"""Package the current external assets for the updateable GitHub assets release."""
import argparse
import json
from pathlib import Path
import zipfile

from .assets import legend_markdown
from .sources import sha256


def package_assets(directory, destination):
    root = Path(directory).resolve()
    destination = Path(destination).resolve()
    if destination.is_relative_to(root):
        raise ValueError("Package outside the assets directory")
    legend = root / "4_chambers_electromechanics_legend.xlsx"
    if legend.exists(): legend_markdown(legend, legend.with_suffix(".md"))
    paths = sorted(p for p in root.rglob("*") if not any(x.startswith(".") for x in p.relative_to(root).parts))
    if any(p.is_symlink() for p in paths): raise ValueError("Asset symlinks are not supported")
    paths = [p for p in paths if p.is_file()]
    if not paths: raise ValueError("No assets to package")
    destination.mkdir(parents=True, exist_ok=True)
    archive = destination / "assets.zip"
    files = [{"name": p.relative_to(root).as_posix(), "sha256": sha256(p), "bytes": p.stat().st_size}
             for p in paths]
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for path, item in zip(paths, files):
            info = zipfile.ZipInfo(item["name"], date_time=(1980, 1, 1, 0, 0, 0))
            info.external_attr = 0o100644 << 16
            bundle.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    manifest = {"version": 1, "archive": {"name": "assets.zip", "sha256": sha256(archive),
                                          "bytes": archive.stat().st_size}, "files": files}
    (destination / "assets-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory")
    parser.add_argument("destination")
    args = parser.parse_args()
    manifest = package_assets(args.directory, args.destination)
    print(f"Packaged {len(manifest['files'])} files; ZIP SHA-256 {manifest['archive']['sha256']}")


if __name__ == "__main__": main()
