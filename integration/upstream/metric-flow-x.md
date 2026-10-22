## Status on 2026-10-22

The following is the original request and historical reproduction. The feature
port and small MPI defect are now resolved in upstream PR #23; central issues
#17/#18 are closed. PRs #22/#23 were merged into stack branches, not main.
The global PR preserves current main plus a recorded replay of that reviewed
stack. Consolidation/patch retirement is central issue #40. Full ADAN56/physical
validation remains #33/#32; original historical measurements do not establish
validation of the subsequently corrected ADAN56 geometry.

## Original problem

The deal.II-X one-way workflow must drive the 1D circulation with a measured or
simulated aortic flow history from the MOX 3D–0D heart model, and supply actual
terminal values to downstream organs. At `d080dcc`, the inlet uses only a parsed
expression and CSV probes sample vessel midpoints. Midpoint probes cannot be
used as terminal boundary data.

## Proposed change

- Optional `Inflow CSV file` parameter accepting SI `time_s,flow_m3_s` columns.
- Piecewise linear interpolation; reject non-finite data, fewer than two rows,
  non-increasing times and extrapolation. Preserve the analytic inlet when no
  CSV is configured. Validate coverage before starting the solver.
- Explicit optional `Inflow CSV period` (seconds), requiring one complete cycle
  with matching endpoint values. No inferred repetition.
- Export boundary trace pressure and flow (not cell midpoint values), with
  boundary/vessel identifiers, SI units and documented outward-flow convention.
  Exactly one MPI owner writes each terminal file.
- Prescribe aortic flow only; cardiac pressure remains a comparison signal.

## Acceptance

- Analytic and tabulated representations of the same linear waveform agree.
- Test exact knots, interpolated values, invalid data, time coverage, explicit
  periodicity and unchanged legacy parameters.
- Check actual terminal values and unique file ownership at one and multiple
  MPI ranks; compare physical outputs within solver tolerance.

Implementation and evidence are being tracked in the deal.II-X integration
repository. MOX data are an external prerequisite; synthetic fixtures establish
software behavior only.

## Local implementation evidence (2026-10-19)

An isolated implementation at the pinned revision builds and runs against the
installed macOS ARM64 deal.II 9.8.0-rc1 / SUNDIALS 6.7.0 toolchain. The serial
HLL_HDG triangular-wave case (0–0.01 s; peak 1e-8 m3/s; absolute IDA tolerance
1e-12) reproduces the prescribed outward inlet flow to 6.9e-21 m3/s. Actual
terminal traces and mass-balance diagnostics are exported.

Two-rank validation exposed an independent numerical gate: with eight initial
line cells and the same source waveform, both the CSV input and the equivalent
analytic expression `1e-8 - 2e-6*abs(t-0.005)` produce essentially zero inlet flow,
while the same eight-cell mesh at one rank reproduces the waveform. The CSV and
analytic two-rank traces agree with each other. This is not counted as a CSV
interpolation regression or a successful MPI numerical validation; investigate
the native parallel constraints/IDA path before freezing a release.

A separate one-cell/two-rank crash is tracked at
https://github.com/dealii/dealii/issues/20306 (empty-rank NVector minimum).


### ADAN56 integration follow-up

The user selected the tracked ADAN56 tutorial (77 computational vessel segments, 31 RCR terminals). The external MOX legend identifies `QAV` as aortic-valve flow in mL/s and `pressure_AA` as ascending-aorta pressure in Pa. The adapter feeds `QAV * 1e-6` into boundary 0, retains pressure only for comparison, and removes the former Fourier waveform from the generated parameter file. No systemic 0D flow is substituted for valve flow. The raw dataset remains external.

A serial unrefined ADAN56 smoke run over 0–0.002 s reaches the final time and exports all 31 terminals. IDA emits two recoverable mxstep reports; this is diagnostic evidence, not a validated full cardiac cycle. Full 8 s, refinement/conservation studies, the pressure datum, the valve forward-sign convention, and compatibility of ADAN56 RCRs with the original MOX 0D closure still need validation.
