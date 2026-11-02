#!/usr/bin/env bash
#SBATCH --job-name=dealiix-stage
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=2
#SBATCH --time=00:10:00
set -euo pipefail
# Supply an image whose container MPI matches this cluster's implementation and
# PMI/PMIx. The launcher owns the ranks; no mpirun is launched inside the image.
: "${DEALIIX_SIF:?Set the absolute validated SIF image path}"
: "${DEALIIX_WORKDIR:?Set the absolute stage working directory}"
: "${DEALIIX_MPI_TYPE:?Set the site's tested Slurm MPI plugin, e.g. pmix}"
: "${DEALIIX_EXECUTABLE:?Set the absolute executable path inside the image}"
cd "$DEALIIX_WORKDIR"
srun --mpi="$DEALIIX_MPI_TYPE" apptainer exec \
  --bind "$DEALIIX_WORKDIR:$DEALIIX_WORKDIR" \
  --pwd "$DEALIIX_WORKDIR" "$DEALIIX_SIF" "$DEALIIX_EXECUTABLE" "$@"
