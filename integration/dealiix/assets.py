"""Fetch checksum-pinned external assets and transcribe the unchanged XLSX legend."""
import argparse
import hashlib
import html
import json
from pathlib import Path
import posixpath
import shutil
import tempfile
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

from .sources import sha256

NS = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def checksums_match(path, item):
    return sha256(path) == item["sha256"] and (
        "sha1" not in item or hashlib.sha1(Path(path).read_bytes()).hexdigest() == item["sha1"])


def legend_markdown(source, destination):
    """Read cell values without rewriting the workbook or guessing column names."""
    source = Path(source)
    lines = ["# Four-chamber electromechanics legend", "",
             f"Source: `{source.name}`. SHA-256: `{sha256(source)}`.", "",
             "Values and descriptions transcribed from the workbook without renaming quantities.", ""]
    with zipfile.ZipFile(source) as archive:
        strings = []
        if "xl/sharedStrings.xml" in archive.namelist():
            strings = ["".join(t.text or "" for t in item.findall(".//s:t", NS))
                       for item in ET.fromstring(archive.read("xl/sharedStrings.xml"))]
        relations = {r.get("Id"): r.get("Target") for r in
                     ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))}
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        for sheet in workbook.findall("s:sheets/s:sheet", NS):
            relation = sheet.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
            target = relations[relation]
            member = target.lstrip("/") if target.startswith("/") else posixpath.normpath("xl/" + target)
            rows = []
            for row in ET.fromstring(archive.read(member)).findall(".//s:sheetData/s:row", NS):
                values = {}
                for cell in row.findall("s:c", NS):
                    if cell.find("s:f", NS) is not None:
                        raise ValueError("Formula in legend: review its meaning before transcribing")
                    column = 0
                    for letter in cell.get("r").rstrip("0123456789"):
                        column = column * 26 + ord(letter) - ord("A") + 1
                    value = cell.find("s:v", NS)
                    text = value.text or "" if value is not None else ""
                    if cell.get("t") == "s": text = strings[int(text)]
                    if cell.get("t") == "inlineStr":
                        text = "".join(t.text or "" for t in cell.findall(".//s:t", NS))
                    values[column] = text
                if any(values.values()): rows.append(values)
            if not rows: continue
            width = max(max(row) for row in rows)
            def render(row):
                return "| " + " | ".join(html.escape(row.get(i, "")).replace("\\", "\\\\")
                    .replace("|", "&#124;").replace("\n", "<br>") for i in range(1, width + 1)) + " |"
            lines += ["## " + sheet.get("name"), "", render(rows[0]),
                      "| " + " | ".join(["---"] * width) + " |", *map(render, rows[1:]), ""]
    Path(destination).write_text("\n".join(lines), encoding="utf-8")


def fetch(url, destination):
    request = urllib.request.Request(url, headers={"User-Agent": "dealii-X-assets"})
    with urllib.request.urlopen(request, timeout=60) as response, open(destination, "wb") as output:
        shutil.copyfileobj(response, output)


def download_assets(root, base_url, fetcher=fetch):
    """Refresh release metadata, verify all bytes, then update unmodified managed files."""
    from .contracts import relative_file
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    receipt_path = root / ".download-manifest.json"
    previous = json.loads(receipt_path.read_text()) if receipt_path.exists() else {"files": []}
    old_hashes = {item["name"]: item["sha256"] for item in previous["files"]}
    with tempfile.TemporaryDirectory(prefix=".download-", dir=root) as work:
        work = Path(work)
        metadata = work / "assets-manifest.json"
        fetcher(base_url.rstrip("/") + "/assets-manifest.json", metadata)
        manifest = json.loads(metadata.read_text())
        if manifest.get("version") != 1 or manifest.get("archive", {}).get("name") != "assets.zip":
            raise ValueError("Unsupported release asset manifest")
        files = manifest["files"]
        names = [item["name"] for item in files]
        if not files or len(names) != len(set(names)):
            raise ValueError("Release manifest needs unique files")
        for item in files:
            name = item["name"]
            if "\\" in name or any(part.startswith(".") for part in Path(name).parts):
                raise ValueError("Invalid release asset path")
            target = relative_file(root, name)
            # Check the lexical path too: even an internal symlink is not a managed file.
            lexical = root / name
            if lexical.is_symlink() or any(p.is_symlink() for p in lexical.parents if p != root and p.is_relative_to(root)):
                raise ValueError(f"Refusing asset symlink: {name}")
            if target.exists():
                current = sha256(target)
                if current not in (item["sha256"], old_hashes.get(name)):
                    raise ValueError(f"Local asset changed; preserved: {name}. Move it aside before downloading.")
        # Metadata is refreshed on every call; a cached matching release needs no ZIP download.
        changed = [item for item in files if not relative_file(root, item["name"]).exists()
                   or not checksums_match(relative_file(root, item["name"]), item)]
        if changed:
            archive = work / "assets.zip"
            fetcher(base_url.rstrip("/") + "/assets.zip", archive)
            if not checksums_match(archive, manifest["archive"]):
                raise ValueError("Release ZIP checksum mismatch; local assets preserved")
            with zipfile.ZipFile(archive) as bundle:
                if len(bundle.namelist()) != len(names) or set(bundle.namelist()) != set(names):
                    raise ValueError("ZIP members differ from the release manifest")
                for item in files:
                    info = bundle.getinfo(item["name"])
                    if info.file_size != item["bytes"] or info.is_dir():
                        raise ValueError("ZIP member size/type mismatch")
                    extracted = relative_file(work / "unpacked", item["name"])
                    extracted.parent.mkdir(parents=True, exist_ok=True)
                    with bundle.open(info) as source, extracted.open("wb") as output:
                        shutil.copyfileobj(source, output)
                    if not checksums_match(extracted, item):
                        raise ValueError("Release file checksum mismatch; local assets preserved")
            for item in changed:
                target = relative_file(root, item["name"])
                target.parent.mkdir(parents=True, exist_ok=True)
                relative_file(work / "unpacked", item["name"]).replace(target)
        # Removed release members and unrelated local files are deliberately retained.
        receipt = work / "receipt.json"
        receipt.write_text(json.dumps({**manifest, "release_url": base_url}, indent=2) + "\n")
        receipt.replace(receipt_path)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory")
    args = parser.parse_args()
    config = json.loads((Path(__file__).resolve().parents[1] / "assets.json").read_text())
    manifest = download_assets(args.directory, config["release_url"])
    print(f"Verified {len(manifest['files'])} release files in {args.directory}")


if __name__ == "__main__": main()
