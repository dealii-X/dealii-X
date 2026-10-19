# Integration follow-up tracker

Implementation PR: [#39](https://github.com/dealii-X/dealii-X/pull/39).

Meta-issue: [16](https://github.com/dealii-X/dealii-X/issues/16). All component tasks and upstream ports are coordinated in this repository.

| Task | Target code | Local patch/workaround |
| --- | --- | --- |
| [MetricFlowX: port CSV inlet and terminal-trace patches upstream](https://github.com/dealii-X/dealii-X/issues/17) | luca-heltai/metric-flow-x | integration/patches/metric-flow-x.patch |
| [MetricFlowX: fix multi-rank inlet constraint/IDA discrepancy](https://github.com/dealii-X/dealii-X/issues/18) | luca-heltai/metric-flow-x | — |
| [deal.II: resolve empty-rank SUNDIALS NVector minimum failure](https://github.com/dealii-X/dealii-X/issues/19) | dealii/dealii | — |
| [dealiiX-platform: port per-stage profiles and named artifacts upstream](https://github.com/dealii-X/dealii-X/issues/20) | 2listic/dealiiX-platform | integration/patches/platform.patch |
| [Polydeal: upstream explicit quadrature includes and verify examples](https://github.com/dealii-X/dealii-X/issues/21) | fdrmrc/Polydeal | integration/patches/polydeal.patch |
| [4C: upstream positive oxygen inversion and Sacado derivative fix](https://github.com/dealii-X/dealii-X/issues/22) | 4C-multiphysics/4C | integration/patches/4c.patch |
| [ExaBrain: modernize deal.II APIs and port portable compiler flags upstream](https://github.com/dealii-X/dealii-X/issues/23) | BRAINIACS-Group/ExaBrain | integration/patches/exabrain.patch |
| [lifeX: resolve deal.II compatibility and identify the complete MOX model](https://github.com/dealii-X/dealii-X/issues/24) | gitlab.com/lifex/lifex-public | — |
| [ExaDG: resolve alveolar-branch SIMD portability and verify Linux build](https://github.com/dealii-X/dealii-X/issues/25) | temuer/exadg:alveolar-model | — |
| [ExaDG: provide alveolar mesh and tabulated respiratory forcing interface](https://github.com/dealii-X/dealii-X/issues/26) | temuer/exadg:alveolar-model | — |
| [PSBLAS-EXT: upstream missing Autoconf helper/bootstrap fix](https://github.com/dealii-X/dealii-X/issues/27) | sfilippone/psblas3-ext | integration/vendor/compile and integration/containers/build-psctoolkit.sh |
| [PSCToolkit: validate complete CPU and separate CUDA builds](https://github.com/dealii-X/dealii-X/issues/28) | psctoolkit/psctoolkit and nested components | — |
| [ImmersX/liver: implement physiological terminal-to-organ coupling case](https://github.com/dealii-X/dealii-X/issues/29) | luca-heltai/immersx | — |
| [ExaBrain: select vascularized brain case and map ADAN56 terminals](https://github.com/dealii-X/dealii-X/issues/30) | BRAINIACS-Group/ExaBrain | — |
| [4C: build complete pinned sources and validate pulmonary exchange case](https://github.com/dealii-X/dealii-X/issues/31) | 4C-multiphysics/4C | — |
| [Heart/MOX: confirm valve sign, pressure datum and ADAN56 RCR compatibility](https://github.com/dealii-X/dealii-X/issues/32) | MOX model / MetricFlowX scientific interface | — |
| [ADAN56: complete 8-second, refinement and conservation validation](https://github.com/dealii-X/dealii-X/issues/33) | luca-heltai/metric-flow-x / integration | — |
| [Sources/deal.II: validate common Linux baseline and freeze gitlinks](https://github.com/dealii-X/dealii-X/issues/34) | All application/library repositories | — |
| [Coral/platform: run the physiological chain through installed plugins and GUI](https://github.com/dealii-X/dealii-X/issues/35) | Coral / 2listic/dealiiX-platform / integration | — |
| [Containers: validate modular/full CPU images and usable platform runtime](https://github.com/dealii-X/dealii-X/issues/36) | dealii-X distribution / platform nested services | — |
| [HPC: validate Apptainer/Slurm MPI and multi-node execution](https://github.com/dealii-X/dealii-X/issues/37) | dealii-X deployment / target cluster | — |
| [Assets/provenance: retain retrievable scientific snapshots as assets evolve](https://github.com/dealii-X/dealii-X/issues/38) | dealii-X dataset release and workflow provenance | — |

Source patches are temporary integration implementations. Close their porting tasks only after reviewed upstream changes are validated and the matching pins/patches are updated.
