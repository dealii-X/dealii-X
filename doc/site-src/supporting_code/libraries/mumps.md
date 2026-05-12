# MUMPS

Parallel sparse direct solver used as a robust coarse or fallback solve
layer for hard linear systems, especially when iterative preconditioners
need a stronger global component.

[Homepage](https://mumps-solver.org/index.php?page=home) [Source access](https://mumps-solver.org/index.php?page=dwnld)

<div class="repo-placeholder">
Public upstream source is distributed from the official MUMPS website. The MUMPS-related integration in dealii-X is currently internalized within the current deal.II codebase as a `SparseDirectMUMPS` class within the `deal.II` library, allowing users that link against MUMPS to use it as a direct solver or preconditioner without needing to interact with a separate repository.
</div>

- Role: massively parallel sparse direct factorization and solve.
- Highlights: multifrontal factorization, symmetric and unsymmetric systems, MPI scalability.
- Status in dealii-X: integrated as an external dependency rather than a published project repo.
