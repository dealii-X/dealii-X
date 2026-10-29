# Integration changelog

## 2026-10-29 — Completed cases and local MOX comparison figures

- All four BDF-2 runs completed their supplied histories (8 s normal,
  11.636 s severe), followed by the native per-case output checks and plots.
- Added combined local comparisons of MOX, full ADAVN and ADAN56, using the
  correct final beat for each case. Distinguish predicted aortic pressure
  from supplied cardiac PV reference data and retain the MOX circulation
  panel layout with explicit reference/prediction labels.
- Full ADAVN systemic venous return sums only its three mapped central drains.
  Added reproducible figure exports, compact plotted-data CSVs, source/output
  hashes and pressure summaries; generated images remain outside Git/dataset.
- Recomputed pressure errors agree with the completed-run reports. Inlet-flow
  reproduction passes the existing acceptance check, while pressure agreement,
  especially in the severe case, still requires model/closure calibration.
  No model parameters were fitted or simulations rerun for these figures.

## 2026-10-29 — Return local cases to BDF maximum order 2

- The normal eight-rank ADAVN case failed at 1.34308 s with IDA error -4;
  this was nonlinear convergence failure, not exhaustion of the step budget.
  The last accepted steps had already dropped from order 3 to 2 and then 1.
- On the same local source and identical inputs, controlled one-rank replays
  to 1.6 s completed for maximum BDF orders 2 and 5 (244 / 980 accepted steps
  with Newton coefficient 0.1 and 100 iterations). Both Newton configurations
  passed with BDF maximum 2. Higher order alone is therefore not proved to be
  the cause of the eight-rank failure; MPI distribution remains another factor.
- Applied the user's requested BDF maximum 2 to all cases, retaining IDA-only
  0.01 s output and the 1,000,000-step work limit. ADAN56's BDF-2 startup passed
  with the original 0.02 s internal-step cap, removing its temporary tiny cap.
- Archived the failed normal and interrupted severe BDF-5 outputs, including
  their exact parameters and provenance. Restarted all four local cases with
  one process each; full trajectories remain in progress and unvalidated.

## 2026-10-29 — Local macOS MPI execution

- Built the pinned MetricFlowX Release solver with PETSc and the installed
  MPICH/MUMPS toolchain. Added native macOS launching without Linux CPU-affinity
  calls and configurable rank counts: 8 for full ADAVN, 1 for ADAN56 locally.
- Applied the requested maximum BDF order 5 and 1,000,000 maximum IDA internal
  steps between outputs. Removed the separate `Output time interval` setting;
  IDA output cadence is 0.01 s, while the complete source inflow remains at
  its original 0.001 s sampling. Output interval is configurable at preparation.
- Preserved interrupted/failed attempts in local archives. The initial BDF-5
  startup failed with IDA corrector convergence error -4 (not the step-work
  limit). Newton now uses coefficient 0.1 and at most 100 iterations; ADAN56
  also caps internal steps at 0.0001 s. Its 0–1 s serial startup check passed
  with finite fields and positive sampled area. Full runs remain unvalidated.
- Restarted the four-case background queue with full ADAVN first; native
  integration is underway. Queue state and per-case failures remain visible
  in local JSON/log files, and independent cases continue after a failure.

## 2026-10-29 — MOX normal-pressure and severe-hypertension inputs

- Added the unchanged `electromechanics_SH_severe.csv` to the external assets
  collection. All five received PNGs remain local references and are excluded
  from the dataset archive. Added tracked
  `integration/mox-datasets.json` with SHA-1/SHA-256, file sizes and explicit cases;
  release packaging now also emits SHA-1 and SHA-256 checksum lists.
- Recorded MOX's periods: 0.8 s for 10 normal beats and 0.8/1.1 s for 16 severe
  beats. Preserve the full 8 s / 11.636 s histories; the severe final source
  sample is 0.0003636 s short of the nominal end and is never extrapolated.
- Added reproducible preparation/launch/analysis for ADAVN full and ADAN56 for
  both cases, with isolated output directories and a preparation-only default.
  Retained the existing networks and one-way QAV coupling. The four-chamber
  blue/red PV reference uses each case's final beat and the actual MOX chamber
  pressures/volumes; computed 1D inlet pressure remains a separate comparison.
- Pinned only MetricFlowX to upstream main
  `9e013df07eeaa585bd140bbd629bfbf4d9a5bee4`; other component pins are preserved.
  Adapted the existing ADAN56 organ-DAG exporter to consolidated native terminal
  CSVs required by this pin.
- Prepared all four cases using the existing verified anatomical ADAVN network
  and the pinned ADAN56 mesh. Verified fresh asset extraction, both checksums,
  supplied periods/coverage, negative-flow preservation and four-panel plotting.
  Python checks and documentation build are recorded in the task validation.
  No physiological solve, MPI launch or Slurm submission was performed.

## 2026-10-19 — Reproducible multi-organ environment

### 1. Read-only baseline

- Read the agreed implementation plan and repository `AGENTS.md`.
- Inspected the root index, all ten submodule revisions, build files and Coral
  pipeline scheduling. Preserved pre-existing staged changes, untracked files,
  the 4C index with staged deletions, and modified nested PSCToolkit repositories.
- Confirmed Docker Engine 29.8.0 is available on this Apple Silicon workstation.
  Existing deal.II 9.8.0 Docker candidates are ARM64; they are not evidence of
  Linux amd64 or cluster compatibility.
- Confirmed that current platform edges express ordering only and all Coral
  stages inherit one global plugin. The nested Coral repositories are not
  initialized in the platform checkout.
- Read the existing 4C build scripts and installed Coral SDK documentation.
  Existing local results are not counted as validation of updated sources.
- Queried ExaDG remotes without changing refs: upstream `master` is
  `b368388ec9d2032d06b38729ae8f3a0fff3ff283`; the scientific fork's
  `alveolar-model` is `0fc5c8aa8dc096db153ece05215b497ec9db94d0`.
  An SSH query could not create its multiplexing socket in the sandbox; the
  equivalent public HTTPS queries succeeded.

### 2. Implementation and verification log

Entries below distinguish implemented behavior, checks actually performed and
external prerequisites. No image publication or scientific validation is implied
by the presence of a recipe.

### 3. Source inventory and isolated implementation

- Added `integration/sources.json`, querying all ten canonical remotes over
  HTTPS. Candidate SHAs and original checkout SHAs are distinct; candidates are
  explicitly marked `not-run`. ExaBrain, PSCToolkit, MetricFlowX and the platform
  already match their selected branch tips. No original gitlink was advanced.
- Added source preparation tooling: exact detached candidate checkouts in a
  separate build directory, recursive nested gitlinks and no LFS data download.
- Created isolated local clones of MetricFlowX and the platform under
  `build/integration/`; original application sources and indices are unchanged.
- Added the versioned SI CSV/JSON contract, explicit source-column mappings,
  checksums, bounded interpolation, optional closed periodic histories, and
  anatomy/pressure/flow metadata.
- Added the command-line DAG runner with per-stage environments, named artifacts,
  producer-success dependencies, isolated input copies, provenance and MPI guards.
- Implemented MetricFlowX tabulated inflow and boundary-trace SI CSV export in
  its isolated clone. Configured and built the actual `blood_flow` executable
  against the local deal.II installation (Release). Runtime checks follow below.

### 4. Requested upstream issues

- Opened [MetricFlowX #10](https://github.com/luca-heltai/metric-flow-x/issues/10):
  tabulated cardiac inflow and actual terminal boundary exports.
- Opened [dealiiX-platform #240](https://github.com/2listic/dealiiX-platform/issues/240):
  per-stage backends and named artifacts, including execution-time materialization
  in Slurm. Exact issue bodies are retained in `integration/upstream/`.

### 5. Native builds and upstream compatibility checks

- Prepared fresh HTTPS snapshots of lifeˣ, ImmersX, ExaBrain, the ExaDG alveolar
  branch, PSCToolkit (including five nested components), Polydeal, 4C and Coral.
  Added explicit Coral/visualizer/server candidates to the inventory.
- Initial lifeˣ source checkout failed because a global Git LFS filter required
  an unavailable `git-lfs` executable. Updated the source preparer to disable
  smudge/process filters explicitly for source-only snapshots; a fresh isolated
  destination then succeeded. No partial checkout was overwritten.
- Built current ImmersX's library and native `poisson` application. Its target is
  `immersx_lib`, not the historical `immersx`; the build was retried with the
  actual `poisson` target after inspecting generated targets.
- Polydeal initially failed on missing `QGauss` declarations. Added an explicit
  `quadrature_lib.h` include in the isolated snapshot; the library builds and
  existing `polydeal/agg_handler_bbox_test.release` passes (10.78 s).
  Retained the fix as `integration/patches/polydeal.patch` and opened
  [Polydeal #160](https://github.com/fdrmrc/Polydeal/issues/160).
- ExaBrain configures, but compilation fails on removed `std_cxx11` headers.
  A local include-only probe exposes further obsolete `DataOut<dim,DH>` APIs.
  No incomplete ExaBrain port is shipped as a validated patch. Opened
  [ExaBrain #3](https://github.com/BRAINIACS-Group/ExaBrain/issues/3).
- lifeˣ initially found Mono Expat headers with the Spack library. Explicitly
  setting `EXPAT_INCLUDE_DIR` resolves configuration; compilation then reveals
  incompatibility with dimensioned `ReferenceCell` in the installed deal.II.
- ExaDG configures and compiles most of its library, then fails in the alveolar
  branch's SIMD exponential helpers on ARM64. Its minimal alveolar mesh is also
  missing from the application directory. Linux amd64 remains unverified.
- GitHub reports `has_issues=false` for `temuer/exadg`; GitLab's lifeˣ issue page
  requires sign-in/security verification. Preserved both issue bodies and opened
  [central tracker #15](https://github.com/dealii-X/dealii-X/issues/15). Neither
  repository settings nor authentication configuration were changed.

### 6. CSV runtime checks and numerical limits

- Built and ran standalone C++ interpolation checks, including CRLF, exact
  endpoints, interpolation, periodic extension and duplicate-time rejection.
- MetricFlowX runs at one MPI rank and writes SI boundary-trace pressure and
  outward flow; tight-tolerance HLL_HDG inlet traces reproduce the prescribed
  triangular waveform. Default tolerances are too loose for this tiny signal.
- The one-coarse-cell/two-rank case fails in SUNDIALS `NVector min_element` on
  an empty rank. Opened [deal.II #20306](https://github.com/dealii/dealii/issues/20306)
  with the stack and source diagnosis. Verified installed SUNDIALS is 6.7.0 and
  corrected the issue's initial version description.
- An eight-coarse-cell case executes to completion at two ranks, but quantitative
  inlet checks reveal a discrepancy; the same eight-cell mesh at one rank
  reproduces the prescribed inlet. MPI numerical equivalence is **not passed**.
  Added a global terminal-ID uniqueness guard while investigating ownership.
- Implemented and executed the CLI chain using the real 1D binary; its last
  stage validates prepared terminal data. It is not a physiological organ run.

### 7. Coral and platform implementation

- Built and installed pinned Coral `6764d0b`; all 54 core CTests pass.
- Built ten installed workflow plugins exposing prepare/validate/run/export/
  diagnostics and actual native subprocess execution. Corrected registration
  argument labels against Coral's return-value contract; all ten installed
  registries now load successfully. Workflow plugins reject replicated MPI
  invocation; requests own their solver launch.
- Added optional per-stage backend/environment/provenance and named artifacts
  to the isolated platform. Artifact dependencies imply ordering; existing
  pipelines retain global defaults. The same Python execution-time wrapper
  materializes verified inputs locally and inside Slurm jobs.
- Added advanced editor fields and retained import/export compatibility.
- Frontend and Electron type checks pass with zero diagnostics; 58 focused
  platform tests pass. Initial checks using a symlink to another checkout's
  dependencies failed because Vite attempted to write there; replaced that
  symlink with a local copy. Other checkouts were preserved.
- Platform and MetricFlowX changes are distributed as reviewed patches applied
  only to exact pinned snapshots by the build driver; original submodule work
  has not been overwritten.

### 8. Containers and HPC infrastructure

- Added a source/patch-verifying build driver, modular Docker targets and a
  complete CPU target assembled from their compiled artifacts. Added PSCToolkit
  CPU/CUDA recipes, separate 4C runtime dependencies, Compose services and an
  Apptainer/Slurm profile with explicit site MPI prerequisites.
- Resolved registry digests for Python, Node, deal.II, 4C dependencies and CUDA;
  recorded them in `integration/containers/images.json`.
- Built `dealiix/contracts:integration-v1` for Linux amd64, including all 15
  Python contract/DAG tests. Ran its CLI successfully. Docker's first build was
  blocked writing Buildx activity under `~/.docker`; setting `BUILDX_CONFIG` to
  the ignored build directory resolved it without changing user configuration.
- Full CPU, CUDA, visualizer and cluster images are not reported as validated
  merely because recipes exist. Source compatibility and external datasets must
  pass before a complete release is tagged or published.

### 9. Native verification and source changes

- Built and installed the current Coral SDK and ten external plugins; all
  registries load, 54 core CTests pass, and a real installed heart graph runs.
- Completed all 189 platform tests, frontend/Electron type checks and production
  build. Applied the verified platform and MetricFlowX patches to their original
  clean source snapshots, preserving pre-existing root index entries.
- Advanced only the validated ImmersX and Polydeal checkouts to their recorded
  candidates. Polydeal retains the explicit quadrature-header patch. Native
  ImmersX Poisson receives a scalar derived from a real 1D terminal, writes VTK,
  and completes the four-stage transfer test. This is not a physiological liver model.
- Quantified the small serial CSV inlet error (6.90e-21 m3/s). The native
  multi-rank discrepancy also occurs with analytic inflow; it remains a release
  gate. Empty-rank SUNDIALS failure is tracked separately.
- ExaBrain fails removed shared-pointer/DataOut APIs; lifeX fails the dimensioned
  ReferenceCell transition; alveolar ExaDG fails ARM64 SIMD fallbacks. These
  candidates remain unvalidated. Corrected the ExaBrain portability patch hunk.
- Tested the current 4C oxygen inversion header against the retained positive
  root patch: the unpatched inverse returns a negative pressure for a positive
  concentration; patched native pressure and Sacado-derivative cases pass.
  This uses existing dependency/configuration artifacts, not a full new 4C build.
- PSBLAS and PSBLAS-EXT compile/install in the isolated PSCToolkit snapshot.
  Supplied a checksum-pinned genuine GNU Automake compile helper for the missing
  auxiliary file. AMG4PSBLAS currently stops on a missing native OpenMP C++ header;
  the complete CPU toolkit and CUDA profile are not yet validated.
- Opened upstream issues: MetricFlowX #10, platform #240, deal.II #20306,
  ExaBrain #3, Polydeal #160, 4C #2354 and PSBLAS-EXT #1. ExaDG fork issues are
  disabled and GitLab lifeX requires authentication; retained their drafts and
  recorded both prerequisites in dealii-X issue #15.

### 10. External MOX assets and legend

- Inspected the supplied CSV and workbook without changing their bytes.
  Added `/assets/` to .gitignore, covering original data and derived files.
- Added `scripts/download_assets.sh` with checksum-verified cached assets,
  explicit authorized HTTPS URL environment variables, and automatic Markdown
  transcription. Download locations were not supplied and are not invented.
- Generated `assets/4_chambers_electromechanics_legend.md`: all 139 data rows
  and 420 nonempty workbook cells verified against the source. Preserved original
  identifiers, units and descriptions, including legend/CSV naming differences.
  No asset file is added to Git.
- Added the explicit MOX column mapping: QAV in mL/s becomes Q in m3/s;
  pressure_AA remains P in Pa. Imported all 8001 samples over 0–8 s.
  Pressure datum, valve forward-sign confirmation and original 0D closure
  compatibility remain recorded scientific prerequisites.

### 11. ADAN56 cardiac coupling

- Selected the tracked ADAN56 tutorial as requested: 77 computational segments,
  inlet 0 and 31 RCR terminals. Validated the VTK topology independently.
- Added an ADAN56 adapter and reproducible pipeline generator. The generated
  parameters replace the Fourier waveform at inlet 0 with the converted QAV CSV;
  QARSYS is not used as aortic-valve flow. Pressure is a comparison observable.
  Original vessel data, RCRs, time origin and negative valve samples are retained.
- Prepared the default 0–8 s/five-refinement configuration. No automatic periodic
  extension, extrapolation or phase shift is introduced.
- Executed a serial, unrefined 0–0.002 s native smoke test. All 31 terminals
  export canonical bundles, final-time coverage passes, and the outward inlet
  equals minus the prescribed flow within 6.21e-25 m3/s (tolerance 1e-12).
  Recorded two recovered IDA internal step-limit reports. Full-duration,
  refinement, mass balance and physiological comparisons remain unvalidated.
- Updated MetricFlowX issue #10 with the ADAN56 interface and diagnostic evidence.
  Documented exact asset preparation and ADAN56 pipeline commands.

### 12. Final verification of the integration work

- Re-ran all 15 Python workflow tests and rebuilt the Linux amd64 contracts image
  successfully. Docker Compose configuration validates.
- Re-ran the ADAN56 adapter with its final-time, inlet-flow and terminal-export
  gates enabled; all gates pass for the short serial configuration. Prevented
  running the orchestration adapter once per MPI rank.
- Added `integration/validation.json` separating software checks, native numerical
  evidence and scientific prerequisites; complete-release validation remains false.
- Ran `./scripts/build_doc.sh`: the documentation site builds successfully.
  Preserved the pre-existing local repository-layout page during auto-generation.
- Confirmed all assets are ignored and original CSV/XLSX checksums are unchanged.
  The script cannot download missing originals until authorized source URLs are
  provided; existing assets verify and regenerate the legend successfully.

### 13. Updateable GitHub assets release

- Following the user's publication instruction, created the remote `assets` tag
  and release in `dealii-X/dealii-X`, anchored to existing source commit
  `75250231d62e50d5b83c2f247531bbb072d956d6`. Existing local index/source work
  remains untouched.
- Packaged CSV, original XLSX and generated Markdown into `assets.zip` (6,690,807
  bytes). Initial ZIP SHA-256:
  `62ca9c34b410d0ed637b56c003c3945a591ef679393431cc4bec6909ce54d9f0`.
  Uploaded `assets-manifest.json` with byte sizes and SHA-256 checksums.
- Replaced the provisional per-file URL configuration with the release URL.
  The downloader always refreshes the published inventory and accepts new or
  updated files without hardcoded dataset checksums in the source tree.
- Added reproducible packaging for future additions/updates; documented uploading
  the matching ZIP first and manifest last. Hidden local receipt/work files are
  excluded; assets stay outside Git.
- Added five regression tests for fresh downloads, upstream updates/additions,
  cache refresh, local-edit preservation, corrupt downloads, path confinement,
  retained removed files and reproducible packaging. All 20 Python tests pass.
- Downloaded the published release through `scripts/download_assets.sh` in an
  isolated empty checkout layout and compared all three files byte-for-byte with
  the originals. Verified the normal cached invocation and the remote tag SHA.
- Rebuilt the Linux amd64 contracts image with all 20 tests and ran
  `./scripts/build_doc.sh` successfully. The generated receipt and downloaded
  data remain ignored by Git.

### 14. Reviewable PR and centralized follow-up

- Followed the clarified instruction to create all new component issues here,
  in `dealii-X/dealii-X`; no additional issues were created in project repositories.
- Opened meta-tracker #16 and 22 concrete follow-ups (#17–#38), including every
  retained ad-hoc port (MetricFlowX, platform, Polydeal, 4C, ExaBrain and the
  PSBLAS-EXT helper), MPI defects, scientific inputs/cases, validation and deployment.
  Existing external issues remain references rather than the central task list.
- Added `integration/TRACKING.md` and machine-readable `tracking.json`, and linked
  the central tracker from validation evidence and workflow documentation.
- Prepared the PR in an isolated checkout on `codex/integrated-workflows`, using
  an explicit file allowlist and gitlinks. Preserved the original checkout's
  staged entries, 4C deletions, dirty nested modules and unrelated local documents.
- Audited the exact staged file set: explicitly included the build driver and
  PSCToolkit recipe, which the machine's global `build*` ignore rule otherwise
  omitted. Added focused exceptions and unified-patch whitespace attributes;
  required empty diff-context prefixes are preserved byte-for-byte.
- Opened PR #39 with concise feature coverage, local validation evidence and a
  grouped checklist linked to the 22 central follow-ups. Linked it bidirectionally
  with meta-issue #16 and the tracked component index.
- Verified the isolated PR checkout's 20 Python tests, Linux amd64 contracts image,
  documentation build and staged diff checks; no external assets or unrelated
  local documents are included. Original root index checksum remains unchanged.

## 2026-10-22

### 15. Synchronize MetricFlowX merged PRs and central tracker

- Inspected upstream merged PRs #8, #16, #17, #18, #20, #21, #22 and #23, their
  actual targets and source ancestry. PRs #22/#23 merge into stack branches;
  current main is `2afa9060f7657363f19a6983dc63dc217a071200`, while the feature
  stack tip is `a808b423bd5e4599d472855a4ff887336de27579`. Neither contains the other.
- Advanced PR #39's MetricFlowX gitlink/source baseline to current main. Retained
  main's corrected ADAN56 areas, SI asset names/provenance, RCR zero-capacitance
  fix, PETSc backend/install changes and SI component tolerances/sonic diagnostics.
- Replaced the old ad-hoc header-only patch with a reproducible replay of the
  reviewed #22/#23 stack on main. Recorded source/patch provenance and retained
  upstream rapidcsv licensing and native regressions. Resolved merge overlaps
  by retaining both runtime checks and output features, plus diagnostic checks
  with the single VTK reader. Verified clean-main patch replay byte-for-byte.
  This temporary patch remains necessary until upstream main consolidates the stack.
- Adapted both CLI demos to explicitly enable upstream's optional terminal CSV
  export, and added a regression for the ADAN56 opt-in. Removed the obsolete
  header-only parser probe; upstream now supplies a compiled parser regression.
- Native ARM64 Release build succeeds. Seven focused native CTests pass. The
  upstream analytic/CSV integration comparison now passes at one and two MPI ranks,
  with nonzero inlet and matching pressure/flow histories. Two ADAN56-area and
  two dataset-path tests confirm main's corrected assets/naming are preserved.
- Re-ran the CLI native transfer demo and corrected-geometry MOX/ADAN56 short
  smoke: all 31 terminal bundles export, and the inlet error remains below 1e-12
  m3/s. Two recovered IDA step-limit reports remain. Full 8-second, convergence,
  conservation and physiological checks are still open; native compiler reports
  existing unused-variable warnings rather than a warning-free build.
- Closed central feature/MPI issues #17/#18 with evidence; updated #16, #33 and
  #34. Opened central #40 specifically for upstream stack consolidation and patch
  retirement, without creating or modifying issues in project repositories.
  Synchronized machine-readable validation, tracker, workflow docs and PR summary.
- Preserved original dirty/staged application checkouts; all edits and native
  probes use isolated integration directories.
- Revalidated the final integration with 21 Python tests, the Linux amd64
  contracts image and `./scripts/build_doc.sh`; all pass. The original local
  application work and unrelated generated documentation page remain preserved.

### 16. Use consolidated upstream MetricFlowX main directly

- Verified the user's upstream merge: PR #28 consolidates #22/#23 into main
  `77cc1d7239ef015a1dcf73cb408a0cfb3ece9fe2`, including the earlier main fixes.
  Confirmed ancestry and inspected the differences from the tested combined tree.
- Updated PR #39's gitlink/source manifest to this exact upstream revision.
  Removed `integration/patches/metric-flow-x.patch` and its temporary replay note;
  no local MetricFlowX source patch is now needed.
- Rebuilt native ARM64 Release from a clean upstream checkout; reran analytic/CSV
  comparisons at one/two ranks and the seven focused native CTests. ADAN56 area
  and dataset-name regressions also pass. The short real MOX/ADAN56 pipeline
  exports 31 terminal bundles and passes its inlet gate; its two recovered IDA
  step-limit reports remain a separate numerical-validation task.
- Updated the PR summary, source/validation metadata, component tracker and
  central issues to mark upstream consolidation/patch retirement complete.
  The complete-release, eight-second and physiological gates remain open.
- Re-ran 21 Python integration tests, the Linux amd64 contracts image and the
  documentation build. Original dirty application checkouts remain untouched.

### 17. Audit and close resolved or superseded central issues

- Audited all open central issues against their acceptance criteria and current
  upstream merge/CI evidence. Closed setup #2 and MUMPS modernization #7 as
  completed; verified upstream MUMPS vector/options and BLR regression coverage.
- Closed aggregate #15 as superseded, with explicit links retaining its unresolved
  requirements in #24–#26. Component data, build, numerical and release tasks
  with outstanding acceptance gates remain open.
- Closed #19 after confirming deal.II PR #20307 merged with the empty-rank
  regression and MPI CI. Advanced the source candidate to its merge commit
  `8122d681995b6baf254bcab3c943e9b0ef4c5870`; full common-distribution build/freeze
  remains #34, so the deal.II gitlink is not declared validated or advanced.
- Closed #21 after confirming Polydeal PR #161 and upstream Linux Debug/Release
  CI. Built its clean merge revision `1120f5dec15368fbacdcdb10100043dd170cecf1`
  locally and passed `polydeal/agg_handler_bbox_test.release`. Updated the PR's
  Polydeal pin/gitlink and removed the obsolete quadrature include patch.
- Synchronized the component index, validation record, central meta-tracker and
  PR follow-up checklist; preserved the original dirty application checkouts.
- Verification after the audit: all 21 Python integration tests pass, the clean
  Polydeal bbox regression passes, and `./scripts/build_doc.sh` succeeds.

## 2026-10-27

### 18. Review all upstream repositories and open the network-scope question

- Read-only audit of all 13 integration components plus PSCToolkit's five nested
  repositories: verified configured branch tips, compared recorded pins/gitlinks,
  reviewed relevant merged/open PRs and inspected changed source/data contracts.
  Recorded the complete snapshot and component follow-ups in
  `integration/upstream-audit-2026-10-27.json` and its Markdown report.
- Updated meta-issue #16 with all 18 repository results and the distinction
  between new upstream capabilities and previously tested integration evidence.
  Source manifest pins, gitlinks, local application work and datasets are unchanged;
  this audit does not claim new builds or scientific validation of current heads.
- Flagged MetricFlowX's incompatible terminal-output change (#65/#67): the
  current adapters need the consolidated CSV setting and boundary-ID splitting.
  Recorded consistent initialization/IDA guards, full arterial ADAN import,
  ADAVN wall laws/native viscoelastic initialization, hepatic import and OCI
  tooling as upstream progress requiring integration-specific verification.
- Recorded ImmersX's vessel-wall/MMS and moving-Dirichlet improvements, ExaDG's
  new alveolar_hex variant/mesh prerequisite, 4C's merged oxygen/FAD fix #2360,
  the platform's still-stacked #239/#226 changes, and PSBLAS-EXT's open fix #2.
  No central task is closed merely because upstream code or import tooling exists.
- Opened central question #41: full ADAVN or reduced ADAN56 for the current
  model? Distinguished the available complete arterial import from the entire
  arterial–venous/closed-loop model, and requested an explicit scientific scope,
  interface/closure assumptions and controlled comparison before deciding.
- Synchronized the tracked issue index and added the audit reference without
  relabeling historical software/numerical checks as current-head validation.
- Verified the 18-entry audit has complete SHA observations and no failed remote
  queries. Re-ran the 21 Python integration tests and `./scripts/build_doc.sh`;
  both pass. These checks cover the tracked integration/report, not new upstream
  solver builds, full-network transients or physiological validation.
