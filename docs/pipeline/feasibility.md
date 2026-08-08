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
- Basic source-data availability needed for downstream derivation

It does not modify SDTM data.

## Status Values

Each objective receives exactly one status:

- `FEASIBLE`
- `PARTIALLY_FEASIBLE`
- `UNSUPPORTED`

Hard blockers prevent reasonable source-data support. Limitations constrain downstream interpretation but do not necessarily prevent the objective from being supported.

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

## Boundary

Feasibility Assessment answers:

> Can this data support the objective?

Future ADaM Specification answers:

> Which analysis-ready variables and datasets must be derived?

Statistical Analysis is out of scope for Version 1.

This layer does not implement preprocessing, ADaM derivation, statistical analysis, machine learning, dashboards, or report generation.
