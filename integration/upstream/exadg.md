## Confirmed integration blockers on alveolar-model

Candidate: `temuer/exadg`, branch `alveolar-model`,
`0fc5c8aa8dc096db153ece05215b497ec9db94d0`.

1. Native ARM64 build against deal.II 9.8.0-rc1 stops in
   `include/exadg/structure/spatial_discretization/operators/continuum_mechanics.h`:
   `fast_approx_exp` calls SIMD `floor` and `type_cast` for
   `VectorizedArray<float,4>` / `VectorizedArray<double,2>`, but available fallback
   overloads only support width 1. Provide tested portable lane-wise fallbacks or
   explicitly restrict supported architectures. ARM64 is a development check;
   the primary release target remains Linux amd64.
2. `applications/structure/alveolar/input.json` refers to `alveolar.e`, which is
   not supplied in that case directory. Identify a redistributable minimal mesh
   and the exact application variant to reproduce the group's alveolar case.
3. Define a tabulated respiratory load interface for the selected variant.
   `HydrostaticPressureNBC` currently receives a scalar pressure and applies its
   built-in time factor. Require explicit pressure units/reference, bounded
   temporal interpolation and no implicit repetition of cycles.

Acceptance: build on Linux amd64; run the small group case; compare tabulated and
analytic respiratory histories; export displacement/strain with reference mesh,
time and coordinate-frame metadata for future microscale coupling.

Direct issue creation is unavailable: GitHub reports `has_issues=false` for
`temuer/exadg`. This text is retained for the fork maintainers and tracked in the
deal.II-X integration tracker; repository settings have not been changed.
