# Reproducible multi-organ workflows

The integration code lives in `integration/`. It connects completed simulations
through files and keeps each numerical solver in a separate process. The first
scientific target is cardiac CSV data → systemic 1D circulation → brain/liver.
The ExaDG alveolar and 4C pulmonary models are separate respiratory branches.
Tissue/cell models are a later extension.

Remaining work and upstream ports are tracked centrally in
the [integration meta-issue](https://github.com/dealii-X/dealii-X/issues/16).
The component index in `integration/TRACKING.md` maps each retained patch and
follow-up to its issue here. Implementation review: [PR #39](https://github.com/dealii-X/dealii-X/pull/39).

## Current evidence and limits

The CPU distribution is under development. **There is no validated complete
multi-organ release yet.** The local source checkouts and pre-existing index
changes are preserved. Candidate updates and patches are prepared in isolated
build directories. The inventory distinguishes current gitlinks from candidates;
an upstream branch tip is not automatically a validated revision.

The implemented infrastructure includes an SI data contract, CLI DAG execution,
ten coarse Coral plugins, per-stage platform backend overrides, named artifacts,
Docker build targets, Compose services and an Apptainer/Slurm template.

Verified locally:

- 20 Python contract, workflow and release-asset tests;
- installed Coral core and plugin registries;
- frontend/Electron type checks, 189 platform tests and the production build;
- native MetricFlowX compilation and a serial tabulated-inflow case;
- current ImmersX library and Poisson application compilation;
- Polydeal compilation with the retained include patch and an existing test.
- external MOX CSV import and a serial ADAN56 smoke run with all 31 terminal exports.

ExaBrain and lifeˣ require source compatibility work. The alveolar ExaDG branch
fails its ARM64 SIMD build; Linux amd64 is not inferred from that result.
MetricFlowX's multi-rank quantitative inlet comparison remains an open gate.
MOX histories are now available as external assets. Organ cases, the alveolar
mesh, GPU hardware and a target cluster remain external prerequisites.
A synthetic input or a successful build is not validation
of the paper's physiological model. See root `CHANGELOG.md` for the complete log.

## Inventory and isolated snapshots

From the repository root:

```bash
export PYTHONPATH="$PWD/integration"
python3 -m dealiix inventory --refresh --output build/integration/new-inventory.json
python3 -m dealiix prepare-sources \
  --manifest integration/sources.json \
  --destination build/integration/candidates
```

Inventory refresh writes a **new** file for review. It does not advance gitlinks,
alter the approved source manifest, or select a release. Source preparation checks
out exact candidate SHAs, recursively initializes their recorded gitlinks, and
leaves LFS assets as pointers until datasets are explicitly supplied. It refuses
to replace an existing snapshot at another revision.

ExaDG's scientific source is `temuer/exadg:alveolar-model`. ImmersX's canonical
repository is `luca-heltai/immersx`. PSCToolkit's nested revisions must be tested
as a compatible set; do not update each nested branch blindly.

Retained patches are applied by the build driver to exact snapshots. The patch
checksum and full command list are written to `build-record.json`. A `BUILT`
record explicitly leaves numerical validation `not-run`.

## Time-series contract

A bundle consists of `manifest.json` and a relative CSV file. Version 1 uses
seconds, pascals and cubic metres per second. The manifest identifies anatomy,
channels, pressure reference, positive flow direction, data checksum and source
provenance. Geometry is optional when no spatial mapping is needed.

```json
{
  "version": 1,
  "kind": "timeseries",
  "time_unit": "s",
  "data": "data.csv",
  "sha256": "<actual file checksum>",
  "anatomy": "aortic-root",
  "channels": [
    {"name": "Q", "quantity": "flow", "unit": "m3/s",
     "positive_direction": "heart-to-aorta"}
  ],
  "provenance": {"source": "<dataset identifier>"}
}
```

The CSV header for this example is `time_s,Q`. Data must be finite with at least
two strictly increasing times. Interpolation is linear; extrapolation fails.
`period_s` enables repetition only for one complete cycle with agreeing endpoint
values. Pressure offsets and flow sign changes must be explicit in the importer
mapping; offsets are in the resulting SI units.

`integration/examples/heart-mapping.json` demonstrates explicit input-column and
unit mapping. It is a synthetic software fixture, not a proposed MOX CSV schema.

```bash
python3 -m dealiix import-csv \
  integration/examples/heart.csv integration/examples/heart-mapping.json \
  build/integration/heart-bundle
python3 -m dealiix validate build/integration/heart-bundle/manifest.json
python3 -m dealiix inflow build/integration/heart-bundle/manifest.json Q \
  build/integration/inflow.csv
```

For the MOX data, obtain the column definitions, aortic/pulmonary/venous section
identifiers, units, orientations, pressure datum, time interval, cycle length and
0D closure configuration. Prescribe aortic flow in MetricFlowX; retain cardiac
pressure for comparison. No pressure/flow pair is imposed indiscriminately.

## MOX heart data and ADAN56

ADAN56 is the selected systemic network: 56 anatomical arteries represented by
77 computational segments, inlet boundary 0 and terminal boundaries 1–31.
The tracked tutorial's mesh, vessel properties and terminal RCR parameters are
retained. The generated case replaces its Fourier inflow with the measured
aortic-valve waveform. The small synthetic circulation demonstrator below remains
a software regression fixture.

The supplied workbook identifies `QAV` as aortic-valve flow in mL/s, `QARSYS`
as systemic 0D arterial flow, and `pressure_AA` as ascending-aorta pressure in Pa.
`integration/examples/mox-heart-mapping.json` selects **QAV**, multiplied by
`1e-6`, for inlet 0. It preserves small negative valve flows. The inlet trace is
exported with the outward normal convention, so it must equal **minus** the
prescribed inlet waveform. `pressure_AA` is retained only as a comparison
observable. Its pressure datum and the valve forward-sign convention still
require confirmation by the group. No new pressure offset is invented.

The external dataset has 8001 samples over 0–8 s. Times are unchanged, with
linear interpolation, no extrapolation and no periodic repetition. The legend
does not establish a cardiac period or compatibility between the MOX 0D closure
and ADAN56's original RCRs. Those checks remain scientific prerequisites.

All originals and the generated Markdown legend are ignored under `/assets/`.
They are distributed in the [assets release](https://github.com/dealii-X/dealii-X/releases/tag/assets).
`./scripts/download_assets.sh` refreshes `assets-manifest.json` from that release
on every invocation, downloads `assets.zip` when needed, and verifies the archive
and every member before installing any files. The release URL is configured in
`integration/assets.json`; data checksums and inventory come from the release,
allowing additions and updates without changing the script.

The receipt `assets/.download-manifest.json` records the downloaded inventory and
checksums. Unmodified previously downloaded files can be updated. Locally changed
files cause a clear error before replacement; move those files aside and rerun
to fetch the published versions. Unrelated local files and files removed from the
release are retained. The first archive includes the original CSV/XLSX and the
139-row Markdown legend, transcribed without renaming workbook quantities.

```bash
./scripts/download_assets.sh
export PYTHONPATH="$PWD/integration"
python3 integration/examples/make_adan56_pipeline.py \
  --binary /absolute/path/to/blood_flow \
  --source "$PWD/applications/circulation/metric-flow-x" \
  --output build/integration/adan56.json
python3 -m dealiix run build/integration/adan56.json build/integration/adan56-run
```

The default case covers 0–8 s and retains five refinement levels. For the
explicitly coarse smoke configuration, pass `--final-time .002 --refinements 0`
when generating the pipeline. A new run directory is required each time.
Every successful run exports 31 named terminal bundles and `coupling.json`,
including mesh/template/input/binary checksums, IDA diagnostics and a quantitative
inlet-flow check. Terminal identifiers are preserved; mappings to organ boundaries
are still required before connecting physiological organ cases.

The local 0–0.002 s smoke run reached the final time and matched the prescribed
inlet to `6.21e-25 m3/s`. IDA reported two recovered internal step-limit events.
This establishes data placement and export, not an eight-second numerical
validation, conservation/convergence study, or agreement with the paper.

### Updating the external asset collection

Put revised or additional files in `assets/`, then package and inspect the result:

```bash
PYTHONPATH=integration python3 -m dealiix.asset_release \
  assets build/integration/assets-release
cat build/integration/assets-release/assets-manifest.json
```

The packager includes all non-hidden files recursively, rejects symlinks,
regenerates the known XLSX legend's Markdown table, and produces a reproducible
ZIP plus checksums outside `assets/`. Inspect the manifest before publishing.
Upload the ZIP first and the manifest last to the existing release:

```bash
gh release upload assets build/integration/assets-release/assets.zip \
  --repo dealii-X/dealii-X --clobber
gh release upload assets build/integration/assets-release/assets-manifest.json \
  --repo dealii-X/dealii-X --clobber
./scripts/download_assets.sh
```

The `assets` tag identifies this maintained collection. Record data checksums
with scientific runs, because release files may change. New CSV schemas or units
also require reviewing the scientific column mapping before executing solvers.

Brain/liver adapters also require terminal-to-boundary mappings and admissible
boundary conditions. Hepatic arterial, portal and venous conditions are distinct.
Pulmonary vascular and respiratory inputs must be identified separately from the
systemic branches. Displacement/strain exports for future microscale coupling
must carry a reference mesh and coordinate frame; no generic field interpolation
is currently claimed.

## Build and run the native circulation demonstrator

For an installed compatible deal.II, use the actual configuration directory:

```bash
python3 -m dealiix.build metric-flow-x \
  --manifest integration/sources.json --source-root build/integration/candidates \
  --build-root build/integration/builds --prefix-root build/integration/install \
  --dealii-dir /path/to/dealii/lib/cmake/deal.II --target blood_flow

python3 integration/examples/make_native_pipeline.py \
  --binary build/integration/install/metric-flow-x/bin/blood_flow \
  --source build/integration/candidates/metric-flow-x \
  --output build/integration/native-pipeline.json
python3 -m dealiix run build/integration/native-pipeline.json \
  build/integration/native-run --workers 2
```

Use a fresh output directory for each run. The synthetic chain executes the real
1D solver and exports actual terminal traces. Its final stage validates prepared
boundary data; **it does not execute an organ model**. The cardiac pressure column
is not prescribed at the inlet.

The native patch adds `Inflow CSV file` (`time_s,flow_m3_s`) and optional
`Inflow CSV period`. Empty CSV configuration preserves the analytical inlet.
`terminal_<boundary-id>.csv` exports SI pressure and outward flow from the actual
boundary traces, with boundary and vessel IDs. IDs must be globally unique.
Mid-vessel diagnostic CSVs retain their original format and units.

Check the numerical inlet condition, including its outward sign:

```bash
python3 integration/tests/verify_inlet.py \
  build/integration/native-run/stage-heart/heart/manifest.json \
  build/integration/native-run/stage-circulation/output/terminal_0.csv
```

The tiny fixture uses tight IDA tolerances and HLL_HDG. The one-cell/two-rank
setup encounters an empty-rank SUNDIALS defect. A larger distributed mesh avoids
that crash, but quantitative serial/MPI equivalence still requires resolution.
The diagnostic script fails if the prescribed inlet is not reproduced.

## CLI stages and artifact handoff

CLI pipelines have `version: 1` and a `stages` array. Each stage supplies an argv
`command`, optional `after`, named `inputs` and `outputs`, and an optional
`profile` with environment/image provenance. Commands never pass through a shell.

```json
{
  "id": "brain",
  "inputs": {
    "artery": {"stage": "circulation", "output": "brain-terminal",
               "channels": ["P"], "anatomy": "brain-inlet"}
  },
  "command": ["/opt/bin/brain-adapter", "{input_artery}"],
  "outputs": {"result": {"kind": "file", "path": "result.vtu"}}
}
```

This illustrates the interface; a brain adapter is not supplied by that example.
Bindings imply dependencies. After producer success the runner verifies and
copies inputs into the consumer directory; it checks bundle integrity, channels,
optional anatomy and requested time coverage. Missing outputs fail their producer.
Failure cancels descendants while independent branches may finish. Every run
records commands, input/output checksums, profiles and outcomes. A new run never
silently resumes or overwrites an old run directory.

`mpi` requests specify `launcher`, `ranks` and optional argv `args`. The runner
rejects nested MPI launches when invoked within an existing rank environment.

## Installed Coral plugins

Build Coral's installed shared SDK first, then:

```bash
cmake -S integration/coral -B build/integration/plugins \
  -DCMAKE_PREFIX_PATH=/path/to/coral/install \
  -DCMAKE_INSTALL_PREFIX="$PWD/build/integration/install"
cmake --build build/integration/plugins --parallel 4
cmake --install build/integration/plugins
```

The ten `libdealiix_<component>` plugins register
`dealiix::<component>::prepare`, `validate`, `run`, `export` and `diagnostics`.
Each operation takes a JSON request filename and returns it for chaining. The
request specifies `version`, `component`, `case_directory`, native argv and
explicit input/output mappings. Relative case/input paths are relative to the
stage working directory. Generic diagnostics check artifact integrity; a native
`diagnostics_command` can add model-specific criteria.

The plugins launch real native applications; they do not implement replacement
organ physics. Application-specific scientific cases are still required.
Existing fine-grained ImmersX/deal.II backends can be used independently.

Workflow plugins run serially. Set MPI in the solver request rather than
replicating subprocess-launching plugin nodes across ranks. Host and plugins
must use the same shared Coral SDK/configuration. `DEALIIX_PYTHON` selects the
Python executable; its environment must include the integration package.

Generate a complete CSV-import Coral graph with
`integration/examples/make_coral_heart.py <new-directory>`, then run `graph.json`
from that directory with `libdealiix_heart`. Registry keys are obtained from the
installed plugin, not inferred from compiler-specific function signatures.

## Platform integration

`integration/patches/platform.patch` targets the pinned platform checkout and
adds optional stage fields while preserving existing global defaults:

```json
{
  "profile": {"coralPluginPath": "/plugins/libdealiix_immersx.so",
              "pythonPath": "/usr/bin/python3",
              "environment": {"PYTHONPATH": "/opt/dealiix-integration"}},
  "inputs": {"inlet": {"stage": "p0", "output": "waveform",
                       "destination": "inputs/inlet", "channels": ["Q"]}},
  "outputs": {"result": {"path": "case/result.vtu", "kind": "file"}}
}
```

The advanced stage editor accepts these three objects. For a time-series input,
`destination` names a bundle directory; the manifest becomes
`inputs/inlet/manifest.json`. For a plain file it names the copied file.
Generated graph/parameter paths should be plain stage-relative paths, not
pre-submission uploads of files that do not exist yet.

The execution wrapper runs **after** parents succeed, locally or inside a queued
Slurm job. It verifies the producer's provenance, copies inputs and validates
outputs before reporting success. The Python package must be installed on the
execution target. Legacy pipelines without these fields require no wrapper.

## Containers and HPC

The checked-in Dockerfile provides `contracts`, `toolchain`, individual component,
`platform`, `four-c` and `complete` targets. Modular and complete targets consume
the same built artifacts. 4C's library closure is isolated and launched through
`integration/containers/run-fourc.sh`. Sources and dependencies use recorded
revisions/digests; release readiness still requires all numerical gates.

```bash
docker buildx build --platform linux/amd64 --target contracts \
  -f integration/containers/Dockerfile -t dealiix/contracts:integration-v1 --load .
docker buildx build --platform linux/amd64 \
  --build-context sources=build/integration/candidates --target complete \
  -f integration/containers/Dockerfile -t dealiix/complete:integration-v1 --load .
```

The first command is verified; the complete target is a development recipe with
known source compatibility blockers. Tags shown are local development names.
No existing published release tag is overwritten, and no image is published by
these commands. Additional upstream service package locks must be frozen and
validated before declaring the full release reproducible.

`integration/compose.yaml` supplies the contract runner, optional compute service
and visualizer. Prepare a writable work directory and set `DEALIIX_UID`,
`DEALIIX_GID` and an absolute `DEALIIX_WORKDIR` matching its owner. The optional
server is in `compose.server.yaml`, which requires an explicit server secret.
Visualizer/server builds use their isolated pinned source snapshots.

CUDA has a separate Dockerfile based on the CPU PSCToolkit image. It requires
Linux NVIDIA hardware and a matching container runtime for numerical tests.
No GPU validation is claimed on this Apple Silicon host.

Build an Apptainer SIF using `integration/hpc/dealiix.def` and an explicit OCI
digest via `--build-arg image=...`. Fill the cluster profile and use
`integration/hpc/run-stage.slurm` only after checking host/container MPI and
PMI/PMIx compatibility. The Slurm launcher starts ranks outside the image.
Require single-rank, single-node multi-rank and actual two-node checks before
marking a cluster profile validated. Docker Compose is used for workstation
services; Slurm manages cluster jobs.

## Upstream tracking

- [MetricFlowX #10](https://github.com/luca-heltai/metric-flow-x/issues/10)
- [Platform #240](https://github.com/2listic/dealiiX-platform/issues/240)
- [deal.II #20306](https://github.com/dealii/dealii/issues/20306)
- [ExaBrain #3](https://github.com/BRAINIACS-Group/ExaBrain/issues/3)
- [Polydeal #160](https://github.com/fdrmrc/Polydeal/issues/160)
- [Central integration tracker #15](https://github.com/dealii-X/dealii-X/issues/15)

Direct ExaDG issue submission is disabled on the scientific fork. lifeˣ's direct
GitLab issue requires authentication. Exact draft bodies are retained under
`integration/upstream/` and referenced by the central tracker.
