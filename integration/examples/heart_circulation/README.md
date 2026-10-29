# MOX heart → ADAVN full / ADAN56

Prepare and run either supplied MOX history with either circulation model.
The default stage is **prepare** and never invokes MPI, the solver or Slurm.

| Case | Source CSV | Period | Supplied beats | Solve interval | Last beat for comparison |
| --- | --- | --- | --- | --- | --- |
| `normal_pressure` | `electromechanics.csv` | 0.8 s | 10 | 0–8 s | 7.2–8 s |
| `severe_hypertension` | `electromechanics_SH_severe.csv` | 0.8/1.1 ≈ 0.7272727 s | 16 | 0–11.636 s | 10.9090909–11.636 s |

MOX confirmed a 10% heart-rate increase in the severe case. Its final sample
is 0.0003636 s before the nominal sixteenth beat ends. This sampling truncation
is recorded in provenance; no extrapolation, period rounding to 0.73 s,
repetition or phase alignment is applied. The last beat is selected from the
supplied beat count, including this short final sampling gap.

The one-way coupling prescribes **QAV × 1e-6 m³/s** at boundary 0, including
small negative flows. `pressure_AA` is a comparison signal, never a simultaneous
pressure boundary condition. No arbitrary hypertension multiplier is applied
to the network resistances. ADAVN retains its arterial/venous wall laws,
1,679 peripheral links and fixed central venous reservoirs; ADAN56 retains its
31 RCR outlets. These closures can yield different pressures from the MOX 0D
circulation. A pressure match or new chamber PV prediction requires additional
physiological calibration or feedback coupling and is not imposed by these scripts.

## Source and dependencies

MetricFlowX is pinned to `9e013df07eeaa585bd140bbd629bfbf4d9a5bee4`, including
the merged full ADAVN, hp RCR and graph partitioning implementations.
On the Linux compute machine, from the integration repository root:

```bash
git submodule update --init applications/circulation/metric-flow-x
python3 -m venv build/integration/heart-venv
build/integration/heart-venv/bin/pip install -r integration/examples/heart_circulation/requirements.txt
export PYTHON="$PWD/build/integration/heart-venv/bin/python"
export METRIC_FLOW_SOURCE="$PWD/applications/circulation/metric-flow-x"
# DEAL_II_DIR must identify a Linux deal.II build with PETSc, METIS,
# SUNDIALS and working parallel MUMPS support.
cmake -S "$METRIC_FLOW_SOURCE" -B build/integration/metric-flow-mox \
  -DCMAKE_BUILD_TYPE=Release -DDEAL_II_DIR="$DEAL_II_DIR"
cmake --build build/integration/metric-flow-mox --target blood_flow -j 8
export BLOOD_FLOW_EXECUTABLE="$PWD/build/integration/metric-flow-mox/blood_flow"
export MPIEXEC=/absolute/path/to/matching/OpenMPI/mpiexec
./scripts/download_assets.sh
```

Use the MPI launcher of the solver's dependency toolchain. The scripts use
OpenMPI and Linux CPU-affinity APIs. Source, Python, executable and output paths
must be shared by the compute nodes. Preparation itself also works on macOS.
An executable can be supplied during preparation or bound at run time.

## Prepare without simulation

```bash
# Existing authorized cache containing both arterial and venous atlases:
export ADAVN_SOURCE_CACHE=/absolute/path/to/adan_source_cache
integration/examples/heart_circulation/run_cases.sh --stage prepare --assets "$PWD/assets"
```

Alternatively reuse a prepared, checksum-verified anatomical network:

```bash
integration/examples/heart_circulation/run_cases.sh --stage prepare \
  --assets "$PWD/assets" --adavn-network /absolute/path/to/adavn_full/network
```

Without either cache, the original upstream download guard requires
`ADAVN_ATLAS_PERMISSION=1` for anatomical geometry. Explicit `--geometry metric`
selects synthetic metric coordinates instead. The full anatomical network has
4,041 arterial and 361 venous source segments and 8,804 cells. ADAN56 has
77 segments, with three refinements by default (616 cells); use `--refinements`
for a separate spatial study. Atlas-derived files remain outside Git and the
MOX dataset release.

Four fresh directories are created under:

```text
build/integration/heart_circulation/normal_pressure/adavn_full/
build/integration/heart_circulation/normal_pressure/adan56/
build/integration/heart_circulation/severe_hypertension/adavn_full/
build/integration/heart_circulation/severe_hypertension/adan56/
```

Each contains `parameters.prm`, `inflow.csv`, all four chambers in
`heart_reference.csv`, the network, and `provenance.json` with source commit,
input hashes, periods, beat count and analysis window. Existing solver output
causes an error. To prepare one case, use `run_adan56.sh` or `run_adavn_full.sh`
with `--case normal_pressure` or `--case severe_hypertension`.
Use `--output /absolute/fresh/directory` for an individual alternate run.

## Launch when ready

After preparation on the compute machine with the paths above:

```bash
# Submits four jobs; default partition gpu, 32 ranks ADAVN / 4 ranks ADAN56.
integration/examples/heart_circulation/run_cases.sh --stage run --submit
```

Each Slurm job executes the solver and then plots its results. Change the
partition with `--partition NAME`. Each rank uses one physical core and one
computational thread, with recorded CPU affinity and node-local MPI temporary
files. One MPI launch is used per case. To launch one prepared case:

```bash
integration/examples/heart_circulation/run_adavn_full.sh \
  --case severe_hypertension --stage run --submit
```

For a standalone Linux machine with enough physical cores, replace `--submit`
with `--allow-local`, then call the same command with `--stage plot`.
Preparation and execution on different machines require re-preparation with
machine-local absolute paths, because parameter files record absolute I/O paths.

## Figures and numerical output

`mox_reference/PV_loops_comparisons.png` (also PDF and SVG) reproduces the
received figure's four-panel order: right atrium, left atrium, right ventricle,
left ventricle; baseline blue, severe red; volume in mL and pressure in mmHg.
It uses **MOX chamber pressure** `pressure_RA/LA/RV/LV`, divided by the
source conversion 133.322 Pa/mmHg, and matching `volume_RA/LA/RV/LV`.
It never substitutes aortic pressure for ventricular pressure. Original CSV files
remain unchanged in the external dataset. The five received PNGs remain local
comparison/documentation references and are not uploaded in the dataset.
`PV_last_beat_<case>.csv` and `PV_comparison.json` expose the plotted values,
windows, source hashes and extrema. These figures are **MOX input references**,
not outputs predicted by the one-way 1D model. They can be generated alone:

```bash
PYTHONPATH=integration "$PYTHON" -m dealiix.mox --assets assets \
  --output build/integration/heart_circulation/mox_reference
```

After an actual solve, `pressure_loops.png/.pdf/.svg` shows computed inlet
pressure versus MOX ascending-aortic pressure, pressure–flow loops, and aortic
pressure against the MOX LV volume. `last_cycle.csv` and `comparison.json`
report pressure error, QAV reproduction, previous-beat pressure drift and
integrated mass defect. Native VTU/PVTU/PVD, terminal/probe CSVs, flow-regime
and mass diagnostics, solver log and IDA statistics remain available. The final
VTK is selected by its recorded physical time, including a final output that
does not lie on the regular 0.005 s cadence. Sampled fields must be finite and
area positive; prescribed inlet flow must agree within 0.1% of peak flow.

Both cases retain the original solver settings: steady-network initialization,
relative tolerance 1e-5, area absolute tolerance 1e-6 of reference area,
velocity 1e-6 m/s, capacitor pressure 0.01 Pa; 1,000-fold loose tolerances until
4 s, tightened through 4.8 s; BDF order at most 2 and maximum step 0.02 s.
All last-beat comparisons use final tolerances. Mesh/time convergence and
physiological calibration remain separate validation work.
