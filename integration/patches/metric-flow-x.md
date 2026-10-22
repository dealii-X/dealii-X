# MetricFlowX merged-stack replay

Baseline: upstream `main` at `2afa9060f7657363f19a6983dc63dc217a071200`.
Feature stack: merged PR #23 at `a808b423bd5e4599d472855a4ff887336de27579`.

On 2026-10-22, PR #22 targets `codex/fix-zero-capacitance-rcr` and PR #23
targets `codex/terminal-rcr-csv`. Their merged feature stack is not an ancestor
of current main. Conversely, main's PRs #16–#21 are not all present in the stack.
Taking the feature tip alone would restore incorrect ADAN56 reference areas,
old/deleted release asset names and missing component tolerances/sonic diagnostics.

`metric-flow-x.patch` now records the complete feature-stack replay on main,
including its vendored rapidcsv implementation/license and native regressions.
It supersedes the initial header-only integration implementation. Merge conflicts
in README retain both sets of documentation; source conflicts retain both runtime
validations, both output features and main's area/radius diagnostics. The optional
taper fields use PR #22's single-reader `has_cell_data` handling, without restoring
the older catch-all fallback. All remaining main changes are kept.

The patch applies cleanly to the exact main baseline and reconstructs the tested
combined source tree. It introduces no new scientific boundary law or solver
algorithm beyond those upstream changes. The build driver records its checksum.

Validation: native ARM64 Release build; seven focused CTests; actual analytic/CSV
nonzero inlet and terminal pressure/flow comparisons at one and two MPI ranks;
short MOX/ADAN56 case with all 31 terminal bundles. The full eight-second and
physiological studies remain open. Main and stack require consolidation before
the patch can be removed: [central issue #40](https://github.com/dealii-X/dealii-X/issues/40).
