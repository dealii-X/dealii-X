## Reproduction on current main

At 4C `16cff11a8ed481f362a73e4332193d234f3dbcd6`, call the native templated
`FourC::PoroPressureBased::get_oxy_partial_pressure_from_concentration` from
`4C_porofluid_pressure_based_elast_scatra_utils.hpp` with:

```cpp
double pressure = 0.;
get_oxy_partial_pressure_from_concentration(
  pressure, 0.26, 0.25, 3.6, 3.0, 0.00021);
```

Compiling a probe against the current candidate's header returns approximately
**-10.0334**, despite positive concentration and physical parameters. The probe
uses an existing local 4C build for generated configuration/dependency flags and
linking; it is not a claim of a fresh full current-main build.

## Cause and proposal

For nonnegative pressure the forward Hill relation is strictly increasing.
The unconstrained polynomial Newton inversion can select an unphysical negative
root. This also blocks the deal.II-X coarse porous-lung gas-exchange case.

Bracket the unique nonnegative root of the original forward relation, then
retain the correct implicit Sacado derivatives at that root. Preserve the
constitutive law and physical coefficients. Explicitly reject invalid states.

## Acceptance

Test native double and Sacado values/derivatives against the forward relation
over pressures 0, 1, 3.6, 10, 20, 100 and 1000, including concentration 0.26 and
invalid input. Re-run existing reference tests and a small coupled lung case.
The deal.II-X integration retains a candidate patch and a native-function
regression; neither establishes quantitative agreement with a published lung
model on its own.
