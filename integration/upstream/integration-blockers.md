# Integration blockers requiring group or upstream action

## exadg

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


## lifex

## Current deal.II compatibility and cardiac workflow availability

lifeˣ candidate: `7e0421580bb32a5e0e3ec088ca313264c61222a2` (public main).
Native environment: macOS ARM64, deal.II 9.8.0-rc1, CMake 3.31.12.

Configuration succeeds after explicitly selecting the installed Expat headers
(`EXPAT_INCLUDE_DIR`): CMake had otherwise mixed a Mono 2.2.5 header with the
Spack Expat 2.8.2 library. This dependency discovery issue is local environment
configuration, not a lifeˣ source defect.

Compilation then fails in `source/core/geometry/mesh_handler.hpp`: four explicit
`std::vector<ReferenceCell>` declarations do not support deal.II's dimensioned
`ReferenceCell<dim>`, and the dependent `get_nodal_type_quadrature` call needs
review. Consider deducing the container type with `const auto &` while retaining
compatibility with older supported deal.II versions.

Please verify supported deal.II versions and provide a small public application
case. Separately confirm availability/build instructions for the MOX four-chamber
3D–0D model: compiling lifeˣ's public fluid/mesh utilities does not establish that
the full cardiac simulation is included. Initial multi-organ coupling will use
the supplied MOX CSV histories as an external input.

GitLab issue submission currently requires authentication; the browser reached
the sign-in/security-verification page. No credentials or repository settings
were changed. Keep this body for direct submission once access is available.


Related issues: MetricFlowX https://github.com/luca-heltai/metric-flow-x/issues/10; platform https://github.com/2listic/dealiiX-platform/issues/240; ExaBrain https://github.com/BRAINIACS-Group/ExaBrain/issues/3; Polydeal https://github.com/fdrmrc/Polydeal/issues/160; deal.II https://github.com/dealii/dealii/issues/20306.
