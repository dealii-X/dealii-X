#!/bin/bash
set -e

export NODE_ADDR=127.0.0.1
echo "$NODE_ADDR slurmnode1" >> /etc/hosts

# Generate a tutorial key in the shared bind mount when the user did not run
# tutorial-init.sh. The platform container mounts the same directory read-only.
mkdir -p /tutorial-ssh
chmod 700 /tutorial-ssh
if [ ! -s /tutorial-ssh/id_ed25519 ]; then
  ssh-keygen -q -t ed25519 -N '' -f /tutorial-ssh/id_ed25519 -C dealiix-tutorial
fi
chmod 600 /tutorial-ssh/id_ed25519
chmod 644 /tutorial-ssh/id_ed25519.pub
cp /tutorial-ssh/id_ed25519.pub /root/.ssh/authorized_keys
chmod 600 /root/.ssh/authorized_keys

# Keep host identities and Slurm authentication keys local to the container.
ssh-keygen -A
if [ ! -s /etc/munge/munge.key ]; then
  (umask 077; head -c 1024 /dev/urandom > /etc/munge/munge.key)
  chown munge:munge /etc/munge/munge.key
fi

service munge start
service mariadb start
service slurmdbd start
service slurmctld start
slurmd -N slurmnode1
service ssh start

if [ "$#" -gt 0 ]; then
  exec "$@"
fi

exec tail -f /dev/null
