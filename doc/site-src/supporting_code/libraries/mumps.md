# MUMPS

Parallel sparse direct solver used as a robust coarse or fallback solve
layer for hard linear systems, especially when iterative preconditioners
need a stronger global component.

[Homepage](https://mumps-solver.org/index.php?page=home) [Source access](https://mumps-solver.org/index.php?page=dwnld)

<div class="repo-placeholder">
Public upstream source is distributed from the official MUMPS website. A dedicated
project submodule is still pending in this repository.
</div>

- Role: massively parallel sparse direct factorization and solve.
- Highlights: multifrontal factorization, symmetric and unsymmetric systems, MPI scalability.
- Status in dealii-X: integrated as an external dependency rather than a published project repo.
