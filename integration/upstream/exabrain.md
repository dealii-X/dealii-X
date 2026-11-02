## Problem

The deal.II-X integration is compiling ExaBrain at
`9a4f3218defea30b4b585411ed9ddaf58d0b4d3b` against a current deal.II installation
(`9.8.0-rc1`, macOS ARM64). Configuration succeeds, but compilation stops at
`nonlinear-poro-viscoelasticity.cc:50`: the removed compatibility header
`deal.II/base/std_cxx11/shared_ptr.h` cannot be found.

## Requested changes

- Replace removed compatibility headers with their standard C++ equivalents
  and complete a clean build against the project's supported deal.II baseline.
- Make the parameter filename selectable from argv (currently main hard-codes
  `parameters.prm`), preserving the existing default.
- Confirm whether this public repository is the brain application intended for
  the multi-organ paper: its current entry point selects experimental tissue
  loading models. Please identify the vascularized-tissue model and minimal case.
- For that model, expose mapped vascular terminal pressure/flow histories with
  explicit units, boundary identifiers and time interpolation. This integration
  must follow the model's admissible boundary conditions; pressure and flow
  must not be blindly imposed simultaneously.

## Acceptance

Clean build plus a small documented numerical case; tabulated versus analytic
boundary-history comparison, invalid-data/coverage checks, and a documented
one-way coupling interface. Actual patient geometry and group data are separate
prerequisites. No validation of an organ-scale vascular model is inferred from
compiling the existing tissue experiment.
