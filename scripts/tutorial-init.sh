#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
state="$root/.dealiix-tutorial"
ssh_dir="$state/ssh"
install -d -m 700 "$ssh_dir"
mkdir -p "$state/shared-data" "$state/platform-userdata"

if [[ ! -f "$ssh_dir/id_ed25519" ]]; then
  ssh-keygen -q -t ed25519 -N '' -f "$ssh_dir/id_ed25519" -C dealiix-tutorial
fi
if [[ ! -s "$ssh_dir/id_ed25519.pub" ]]; then
  ssh-keygen -y -f "$ssh_dir/id_ed25519" > "$ssh_dir/id_ed25519.pub"
fi
chmod 600 "$ssh_dir/id_ed25519"
chmod 644 "$ssh_dir/id_ed25519.pub"

printf 'Tutorial data and SSH key initialized. Follow the Compose startup commands in doc/tutorial-containers.md.\n'
