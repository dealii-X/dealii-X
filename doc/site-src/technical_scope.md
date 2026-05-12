# Technical scope

The technical directions below shape the software developments and
scientific themes of the project.

Key directions

- Algorithmic optimization: improve efficiency and scalability of
  numerical kernels with attention to memory, data locality and
  vectorization.
- Solvers and preconditioners: integrate and evaluate PSCToolkit and
  MUMPS as robust coarse/problem solvers for ill-conditioned cases.
- Accelerators and heterogeneity: adapt critical phases (assembly,
  preconditioner setup) for GPUs and hybrid architectures, including
  matrix-free and mixed-precision strategies.
- Multiscale and coupling: tooling for 3D/1D coupling, mixed-dimensional
  formulations and immersed methods for bio-physical problems.
- Validation and reproducibility: test workflows, datasets for ML, and
  benchmark suites to compare methods and optimizations.

These themes guide the development of the components listed in the
technical repositories section. See `project_overview.md` for a short summary.
