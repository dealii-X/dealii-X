# Integration changelog

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
