#!/usr/bin/env bash
set -euo pipefail
source_dir=$1
prefix=$2
jobs=$3
profile=$4
helper_dir=$(cd "$(dirname "$0")/../vendor" && pwd)
mkdir -p "$prefix"
cd "$source_dir/psblas3"
./configure --prefix="$prefix" --with-ipk=4 --with-lpk=4
make -j "$jobs"
make install
if [[ $profile == cuda ]]; then
  cmake -S "$source_dir/spgpu/src" -B "$source_dir/spgpu-build" \
    -DCMAKE_INSTALL_PREFIX="$prefix" -DCMAKE_POLICY_VERSION_MINIMUM=3.5
  cmake --build "$source_dir/spgpu-build" --parallel "$jobs"
  # Upstream has no common install target across versions.
  mkdir -p "$prefix/lib" "$prefix/include"
  cp "$source_dir"/spgpu/lib/* "$prefix/lib/"
  cp "$source_dir"/spgpu/src/core/*.h "$prefix/include/"
fi
cd "$source_dir/psblas3-ext"
# The recorded extension gitlink omits this standard Autoconf helper; the pinned
# PSBLAS parent only has an empty placeholder. Supply the upstream GNU helper.
if [[ ! -s compile ]]; then cp "$helper_dir/compile" compile; chmod +x compile; fi
mkdir -p include modules lib
if [[ $profile == cuda ]]; then
  ./configure --prefix="$prefix" --with-psblas="$prefix" --with-spgpu="$prefix"
else
  ./configure --prefix="$prefix" --with-psblas="$prefix"
fi
make -j "$jobs"
make install
cd "$source_dir/amg4psblas"
./configure --prefix="$prefix" --with-psblas="$prefix"
make -j "$jobs"
make install
cmake -S "$source_dir/sundials" -B "$source_dir/sundials-build" \
  -DCMAKE_INSTALL_PREFIX="$prefix" -DENABLE_MPI=ON -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
  -DENABLE_PSCTOOLKIT=ON -DPSCTOOLKIT_DIR="$prefix" -DMPI_ENABLE=ON
cmake --build "$source_dir/sundials-build" --parallel "$jobs"
cmake --install "$source_dir/sundials-build"
