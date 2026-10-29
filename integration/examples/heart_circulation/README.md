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
  -DCMAKE_BUILD_TYPE=Release -DMETRIC_FLOW_X_BACKEND=PETSc -DDEAL_II_DIR="$DEAL_II_DIR"
cmake --build build/integration/metric-flow-mox --target blood_flow -j 8
export BLOOD_FLOW_EXECUTABLE="$PWD/build/integration/metric-flow-mox/blood_flow"
export MPIEXEC=/absolute/path/to/matching/OpenMPI/mpiexec
./scripts/download_assets.sh
```

Use the MPI launcher of the solver's dependency toolchain. Linux Slurm runs use
OpenMPI and Linux CPU-affinity APIs; local macOS runs also support native
MPICH/Hydra, with process placement managed by macOS and MPI. Source, Python,
executable and output paths must be shared by the compute nodes when using Slurm.
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

For a standalone Linux machine or Mac, replace `--submit` with `--allow-local`,
then call the same command with `--stage plot`. During preparation, `--ranks N`
sets the MPI process count. Defaults are 32 for full ADAVN on Linux, 8 on macOS
(or fewer if fewer CPUs are available), and 4 for ADAN56 on Linux / 1 on macOS. One computational
thread is used per rank. On macOS the matching launcher can be
`/Applications/deal.II.app/Contents/Resources/Libraries/bin/mpiexec`.
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
does not lie on the regular 0.01 s cadence. Sampled fields must be finite and
area positive; prescribed inlet flow must agree within 0.1% of peak flow.

Both cases use steady-network initialization,
relative tolerance 1e-5, area absolute tolerance 1e-6 of reference area,
velocity 1e-6 m/s, capacitor pressure 0.01 Pa; 1,000-fold loose tolerances until
4 s, tightened through 4.8 s; BDF order at most 2 and maximum internal
step 0.02 s for both networks. Newton uses a convergence coefficient of 0.1
and at most 100 nonlinear iterations. `Maximum IDA internal steps per output`
is 1,000,000.

The maximum BDF order was returned to 2 after the local eight-rank normal ADAVN
case failed with IDA corrector-convergence error -4 at 1.34308 s. The last
accepted step was already order 1, after earlier order reductions. Serial
controlled replays of the same current source and inputs reached 1.6 s with
both maximum orders 2 and 5, requiring 244 versus 980 accepted steps with the
same Newton controls. Therefore higher order alone is not established as the
cause of the parallel failure. The BDF-2 replay also passed with the legacy
Newton controls. ADAN56 passed a 0–1 s BDF-2 check with its original 0.02 s
internal-step cap, so the temporary BDF-5 cap of 0.0001 s was removed.
These are bounded startup checks, not full physiological validation. The local
retry campaign uses `--ranks 1` for both networks; interrupted BDF-5 outputs
remain archived beside the restarted cases.

Only IDA's `Time interval between each output` controls output cadence: 0.01 s
by default, configurable during preparation with `--output-interval`. The
separate `Output time interval` parameter is omitted (its default is zero).
This gives 801 normal-case snapshots and 1,165 severe-case snapshots, about
half the former 0.005 s cadence. The original 0.001 s input CSV is preserved
for forcing; output sampling does not coarsen the inflow used by IDA.
All last-beat comparisons use final tolerances. Mesh/time convergence and
physiological calibration remain separate validation work.


## Compare completed results with the MOX figures

After all four cases finish, generate the combined plots locally:

```bash
"$PYTHON" integration/examples/heart_circulation/compare_mox.py \
  --assets "$PWD/assets" \
  --results "$PWD/build/integration/heart_circulation" \
  --output "$PWD/build/integration/mox_comparison"
```

The script verifies the MOX input hashes, prepared parameter hashes, full native
inlet coverage and pressure RMSE against the per-case reports. It writes PNG,
vector PDF/SVG, compact last-beat CSVs, `pressure_summary.csv` and
`comparison_report.json`. No solver is launched and no figure is uploaded to
the dataset release.

`systemic_comparison` overlays MOX, full ADAVN and ADAN56 aortic pressure and
inlet flow. `aortic_pressure_LV_volume` distinguishes the supplied ventricular
PV reference from aortic pressure against the shared MOX ventricular volume.
`venous_return_comparison` uses the full ADAVN sum of IVC, SVC and coronary-sinus
central-drain flows, with IDs derived from network provenance and mapping;
internal peripheral links are never summed as external venous return.

The two `circulation_<case>` figures retain the supplied MOX four-panel layout.
Only the systemic-flow panel includes 1D predictions; cardiac and pulmonary
panels remain explicitly labelled MOX references. `mox_reference/` contains the
four-chamber baseline/severe PV comparison reconstructed from the unchanged
cardiac CSVs. Analysis uses the nominal last-beat windows recorded in provenance,
without pressure offsets, fitted phase shifts, inflow clipping or calibration.
ADAN56 has no venous network and neither 1D model predicts new cardiac PV loops.
