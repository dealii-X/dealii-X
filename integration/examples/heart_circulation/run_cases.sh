#!/usr/bin/env bash
set -euo pipefail
directory=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
for condition in normal_pressure severe_hypertension; do
  for model in adavn_full adan56; do
    "${PYTHON:-python3}" "$directory/workflow.py" "$model" --case "$condition" "$@"
  done
done
