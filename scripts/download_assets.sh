#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
export PYTHONPATH="$root/integration${PYTHONPATH:+:$PYTHONPATH}"
exec python3 -m dealiix.assets "$root/assets" "$@"
