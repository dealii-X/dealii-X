#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
SITE_SRC="$ROOT_DIR/doc/site-src"
OUT_DIR="$ROOT_DIR/build/docs/site"

VENV="$ROOT_DIR/.venv_docs"
if [ ! -d "$VENV" ]; then
	python3 -m venv "$VENV"
fi
source "$VENV/bin/activate"
python3 -m pip install --upgrade pip
python3 -m pip install -r "$ROOT_DIR/doc/requirements.txt"

mkdir -p "$OUT_DIR"

# Auto-generate repository layout page
python3 "$ROOT_DIR/tools/generate_repo_layout.py"

# Build Sphinx site into a standalone directory
sphinx-build -b html "$SITE_SRC" "$OUT_DIR"

deactivate || true

echo "Site built to $OUT_DIR"

