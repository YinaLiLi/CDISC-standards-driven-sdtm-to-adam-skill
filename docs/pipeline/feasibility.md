# Feasibility Assessment

The Feasibility Assessment layer answers:

> Can this data support the objective?

It inspects available SDTM source data and returns one feasibility status for each research objective.

## Inputs

- Research plan or research objectives
- Existing SDTM datasets
- Standards discovery and evidence extraction references when applicable

Version 1 supported SDTM domains:

- `DM`
- `AE`
- `LB`
- `DS`
- `EX`
- `SV`

## Assessment Scope

The assessor may inspect:

- Domain availability
- Variable availability
- Subject counts
- Record counts
- `USUBJID` overlap across required domains
- Relevant date coverage
- Missingness relevant to the objective
- Objective-specific sufficiency signals such as outcome-positive subjects, abnormality evidence, and baseline flags
- Basic source-data availability needed for downstream derivation

It does not modify SDTM data.

## Status Values

Each objective receives exactly one status:

- `FEASIBLE`
- `PARTIALLY_FEASIBLE`
- `UNSUPPORTED`

Hard blockers prevent reasonable source-data support. Limitations constrain downstream interpretation but do not necessarily prevent the objective from being supported.

Sparse data can be a hard blocker even when required domains and variables exist. Version 1 requires at least five usable records and five subjects for each non-DM domain required by an objective, and at least five overlapping subjects for cross-domain objectives. Objectives that require laboratory abnormality assessment need either `LB.LBNRIND` or laboratory reference range variables. Objectives that require laboratory change from baseline need enough `LB.LBBLFL == "Y"` baseline subjects and post-baseline records for those subjects.

Predictive objectives are returned as `UNSUPPORTED` when the provided data do not satisfy the requested analysis need. When an apparent outcome can be counted, sparse outcome-positive subject counts are reported as blockers rather than converted into descriptive or rule-based support.

Monitoring-risk or risk-stratification objectives are treated as exploratory rule-based profile objectives when the required source domains are sufficient. They are `PARTIALLY_FEASIBLE`, not fully supported, until the user provides an explicit rule for combining adverse event, laboratory, exposure, and discontinuation signals.

## Output Fields

Each result includes:

- `objective_id`
- `objective_text`
- `status`
- `required_domains`
- `available_domains`
- `missing_domains`
- `required_variables`
- `missing_variables`
- `subject_coverage`
- `date_coverage`
- `blocking_issues`
- `limitations`
- `evidence_references`

## Supported Research Objectives

After evaluating user-provided objectives, the assessor returns up to five `Supported Research Objectives` that are genuinely supported by the available data.

Ranking is based on source-data support signals such as domain availability, subject overlap, record availability, and temporal coverage. It does not recommend statistical models, hypothesis tests, machine learning, dashboards, or reports.

Sparse domains are not listed as supported research objectives merely because one record overlaps with `DM`.

## Boundary

Feasibility Assessment answers:

> Can this data support the objective?

Future ADaM Specification answers:

> Which analysis-ready variables and datasets must be derived?

Statistical Analysis is out of scope for Version 1.

This layer does not implement preprocessing, ADaM derivation, statistical analysis, machine learning, dashboards, or report generation.
