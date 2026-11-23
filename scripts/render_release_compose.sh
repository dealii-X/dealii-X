#!/usr/bin/env bash
set -euo pipefail

base=$1
visualizer=$2
platform=$3
execution=$4

docker compose config --no-interpolate --no-normalize --no-path-resolution --format json |
  jq --arg base "$base" --arg visualizer "$visualizer" --arg platform "$platform" \
    --arg execution "$execution" '
      .services["prepare-examples"].image = $base |
      .services["coral-visualizer"].image = $visualizer |
      .services["dealiix-platform"].image = $platform |
      .services["coral-ssh-slurm"].image = $execution |
      del(.services["coral-ssh-slurm"].build)
    '
