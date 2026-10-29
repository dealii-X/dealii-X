## Reproduction

Configuring Polydeal at `d0468cc4e07380898c0df65d692c05a5a22a3110` against
deal.II `9.8.0-rc1` (macOS ARM64) succeeds, but building the `polydeal` library
fails because `QGauss` is undeclared in `include/utils.h` (lines 409, 1155, 1191)
and `source/agglomeration_handler.cc` (line 356).

## Proposed change

Include `deal.II/base/quadrature_lib.h` explicitly where the quadrature types are
used. The current code relies on transitive includes that no longer provide
`QGauss`. Verify the standalone library, representative examples and regression
tests against the supported deal.II baseline. Avoid native-CPU-only compilation
flags in distributable builds.

This was found while preparing the pinned deal.II-X software distribution.
