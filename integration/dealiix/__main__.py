import argparse
import json
from pathlib import Path

from .contracts import Series, import_csv, write_inflow
from .pipeline import run_pipeline
from .sources import inventory, prepare


def main():
    parser = argparse.ArgumentParser(description="deal.II-X file-coupled workflows")
    commands = parser.add_subparsers(dest="command", required=True)
    audit = commands.add_parser("inventory")
    audit.add_argument("--refresh", action="store_true")
    audit.add_argument("--output", required=True)
    snapshot = commands.add_parser("prepare-sources")
    snapshot.add_argument("--manifest", required=True)
    snapshot.add_argument("--destination", required=True)
    snapshot.add_argument("--component", action="append", default=[])
    convert = commands.add_parser("import-csv")
    convert.add_argument("source")
    convert.add_argument("mapping")
    convert.add_argument("destination")
    check = commands.add_parser("validate")
    check.add_argument("manifest")
    inflow = commands.add_parser("inflow")
    inflow.add_argument("manifest")
    inflow.add_argument("channel")
    inflow.add_argument("destination")
    run = commands.add_parser("run")
    run.add_argument("pipeline")
    run.add_argument("directory")
    run.add_argument("--workers", type=int, default=1)
    args = parser.parse_args()
    if args.command == "inventory":
        Path(args.output).write_text(json.dumps(inventory(args.refresh), indent=2) + "\n")
    elif args.command == "prepare-sources":
        prepare(json.loads(Path(args.manifest).read_text()), args.destination, args.component)
    elif args.command == "import-csv":
        import_csv(args.source, json.loads(Path(args.mapping).read_text()), args.destination)
    elif args.command == "validate":
        Series(args.manifest)
    elif args.command == "inflow":
        write_inflow(args.manifest, args.channel, args.destination)
    elif args.command == "run":
        if not run_pipeline(args.pipeline, args.directory, args.workers):
            raise SystemExit(1)


if __name__ == "__main__":
    main()
