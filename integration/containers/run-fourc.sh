#!/usr/bin/env bash
set -euo pipefail
runtime=${DEALIIX_FOURC_RUNTIME:-/opt/fourc-runtime}
loader=$(find "$runtime" -maxdepth 1 -name 'ld-linux-*.so*' -print -quit)
[[ -n $loader ]] || { echo 'Missing isolated 4C dynamic loader' >&2; exit 1; }
exec "$loader" --library-path "$runtime:/opt/dealiix/4c/lib" /opt/dealiix/4c/bin/4C "$@"
