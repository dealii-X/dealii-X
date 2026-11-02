## Reproduction

A source-only checkout of PSCToolkit `883a4280465d5705c205f46fa662bd342f752d35`
with its recorded `psblas3-ext` gitlink fails immediately at
`psblas3-ext/configure` with:

```
configure: error: cannot find required auxiliary files: compile
```

The parent PSBLAS checkout contains a tracked zero-byte `compile` placeholder.
Creating another empty placeholder gets past the existence check but does not
supply the compiler wrapper Autoconf expects.

Please include a genuine GNU Automake `compile` helper in distributed sources,
or make the documented bootstrap install required auxiliary files and state its
Autoconf/Automake prerequisites. The deal.II-X build temporarily supplies the
official helper from pinned GNU Automake v1.16.5 with its license and checksum.

Acceptance: configure/build/install PSBLAS-EXT from a clean recursive checkout
after installing the matching PSBLAS release, for CPU and CUDA profiles. Also
ensure required empty output directories are created by the build.
