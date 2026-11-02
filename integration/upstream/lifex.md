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
