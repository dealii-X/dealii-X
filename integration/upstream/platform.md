## Problem

The deal.II-X multi-organ workflow chains independent Coral plugins and executable
stages. At `36580d3`, every Coral stage inherits one global plugin, and pipeline
edges specify ordering only. Stage directories are separate, so dependent runs
cannot consume named validated artifacts from their producers.

## Proposed change

- Optional per-stage Coral executable/plugin overrides with global settings as
  backwards-compatible defaults; environment and image provenance per stage.
- Named output artifacts and input bindings to a producer stage/output.
- Validate DAG and artifact references before submission; materialize files
  after producer success, validate presence/type/checksum before consumer start.
- Preserve existing ordering-only edges and old pipeline import/export.
- Use the same contract locally and in Slurm scripts; queued remote jobs must
  materialize their inputs at execution time, not at initial submission.
- Record stage parameters, source revisions, image identifiers and input/output
  checksums in the run directory.
- Add editor fields for backend selection and artifact bindings.

## Acceptance

- A pipeline runs two different plugins and transfers a time-series bundle.
- Existing pipelines still inherit global defaults and run unchanged.
- Missing/incompatible artifacts fail the consumer; producer failure prevents
  all descendants, while independent branches can complete.
- Test local and remote behavior, import/export, quoting and path confinement.
- Validate generated registry signatures against the actual installed plugins.
