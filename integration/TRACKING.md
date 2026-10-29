# Integration follow-up tracker

Implementation PR: [#39](https://github.com/dealii-X/dealii-X/pull/39). Meta-issue: [#16](https://github.com/dealii-X/dealii-X/issues/16).

All coordination issues live in this repository. Status checked on 2026-10-22.

| Status | Task | Target code | Local patch/workaround |
| --- | --- | --- | --- |
| completed | [MetricFlowX: port CSV inlet and terminal-trace patches upstream](https://github.com/dealii-X/dealii-X/issues/17) | luca-heltai/metric-flow-x | — |
| completed | [MetricFlowX: fix multi-rank inlet constraint/IDA discrepancy](https://github.com/dealii-X/dealii-X/issues/18) | luca-heltai/metric-flow-x | — |
| completed | [deal.II: resolve empty-rank SUNDIALS NVector minimum failure](https://github.com/dealii-X/dealii-X/issues/19) | dealii/dealii | — |
| open | [dealiiX-platform: port per-stage profiles and named artifacts upstream](https://github.com/dealii-X/dealii-X/issues/20) | 2listic/dealiiX-platform | integration/patches/platform.patch |
| completed | [Polydeal: upstream explicit quadrature includes and verify examples](https://github.com/dealii-X/dealii-X/issues/21) | fdrmrc/Polydeal | — |
| open | [4C: upstream positive oxygen inversion and Sacado derivative fix](https://github.com/dealii-X/dealii-X/issues/22) | 4C-multiphysics/4C | integration/patches/4c.patch |
| open | [ExaBrain: modernize deal.II APIs and port portable compiler flags upstream](https://github.com/dealii-X/dealii-X/issues/23) | BRAINIACS-Group/ExaBrain | integration/patches/exabrain.patch |
| open | [lifeX: resolve deal.II compatibility and identify the complete MOX model](https://github.com/dealii-X/dealii-X/issues/24) | gitlab.com/lifex/lifex-public | — |
| open | [ExaDG: resolve alveolar-branch SIMD portability and verify Linux build](https://github.com/dealii-X/dealii-X/issues/25) | temuer/exadg:alveolar-model | — |
| open | [ExaDG: provide alveolar mesh and tabulated respiratory forcing interface](https://github.com/dealii-X/dealii-X/issues/26) | temuer/exadg:alveolar-model | — |
| open | [PSBLAS-EXT: upstream missing Autoconf helper/bootstrap fix](https://github.com/dealii-X/dealii-X/issues/27) | sfilippone/psblas3-ext | integration/vendor/compile and integration/containers/build-psctoolkit.sh |
| open | [PSCToolkit: validate complete CPU and separate CUDA builds](https://github.com/dealii-X/dealii-X/issues/28) | psctoolkit/psctoolkit and nested components | — |
| open | [ImmersX/liver: implement physiological terminal-to-organ coupling case](https://github.com/dealii-X/dealii-X/issues/29) | luca-heltai/immersx | — |
| open | [ExaBrain: select vascularized brain case and map ADAN56 terminals](https://github.com/dealii-X/dealii-X/issues/30) | BRAINIACS-Group/ExaBrain | — |
| open | [4C: build complete pinned sources and validate pulmonary exchange case](https://github.com/dealii-X/dealii-X/issues/31) | 4C-multiphysics/4C | — |
| open | [Heart/MOX: confirm valve sign, pressure datum and ADAN56 RCR compatibility](https://github.com/dealii-X/dealii-X/issues/32) | MOX model / MetricFlowX scientific interface | — |
| open | [ADAN56: complete 8-second, refinement and conservation validation](https://github.com/dealii-X/dealii-X/issues/33) | luca-heltai/metric-flow-x / integration | — |
| open | [Sources/deal.II: validate common Linux baseline and freeze gitlinks](https://github.com/dealii-X/dealii-X/issues/34) | All application/library repositories | — |
| open | [Coral/platform: run the physiological chain through installed plugins and GUI](https://github.com/dealii-X/dealii-X/issues/35) | Coral / 2listic/dealiiX-platform / integration | — |
| open | [Containers: validate modular/full CPU images and usable platform runtime](https://github.com/dealii-X/dealii-X/issues/36) | dealii-X distribution / platform nested services | — |
| open | [HPC: validate Apptainer/Slurm MPI and multi-node execution](https://github.com/dealii-X/dealii-X/issues/37) | dealii-X deployment / target cluster | — |
| open | [Assets/provenance: retain retrievable scientific snapshots as assets evolve](https://github.com/dealii-X/dealii-X/issues/38) | dealii-X dataset release and workflow provenance | — |
| completed | [MetricFlowX: consolidate merged PR stack into main and retire integration replay patch](https://github.com/dealii-X/dealii-X/issues/40) | luca-heltai/metric-flow-x | — |

MetricFlowX PR #28 consolidates #22/#23 into main `77cc1d7239ef015a1dcf73cb408a0cfb3ece9fe2` while preserving the earlier SI dataset, ADAN56 area and tolerance fixes. The global PR now uses this commit directly; the MetricFlowX integration patch has been removed. #17, #18 and #40 are complete.

Further audit: #19 is resolved by deal.II PR #20307 (candidate `8122d681`); #21 by Polydeal PR #161 (pin `1120f5de`, no patch). Legacy setup #2 and MUMPS modernization #7 are complete; aggregate #15 is superseded by #24–#26. Complete source/distribution verification remains #34/#36.

## Upstream review on 2026-10-27

See [the 18-repository audit](UPSTREAM_AUDIT_2026-10-27.md) and its JSON snapshot. Current branch tips are observed revisions, not replacements for validated pins. MetricFlowX output adapters and 4C patch retirement require follow-up before new upstream code is used.

Open scientific decision: [#41 — full ADAVN or reduced ADAN56?](https://github.com/dealii-X/dealii-X/issues/41). No network choice is changed by the audit.
