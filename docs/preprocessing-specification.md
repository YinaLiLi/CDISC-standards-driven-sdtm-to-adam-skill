# Standards-Driven SDTM Preprocessing Specification

The preprocessing specification layer answers:

> What source-preserving preprocessing operations are justified before ADaM derivation?

It does not execute preprocessing.

## Inputs

- Existing SDTM datasets
- Feasibility results
- Standards Discovery results where applicable
- Extracted CDISC evidence where applicable

Version 1 supports the following SDTM domains:

- `DM`
- `AE`
- `LB`
- `DS`
- `EX`
- `SV`

## Decision Classifications

Every proposed operation must be classified as one of:

- `STANDARD_REQUIRED`
- `STANDARD_GUIDED`
- `STUDY_SPECIFIC`
- `USER_DEFINED`
- `DATA_ENGINEERING`
- `EXAMPLE_ADAPTED`
- `UNSUPPORTED`

No preprocessing operation is silently treated as a CDISC requirement.

If official CDISC evidence exists, the operation references extracted evidence IDs. If no official rule exists, the operation is explicitly classified as a non-standard decision such as `DATA_ENGINEERING`, `STUDY_SPECIFIC`, or `USER_DEFINED`.

## Operation Specification

Each operation contains:

- `operation_id`
- `dataset`
- `variable`
- `operation`
- `purpose`
- `classification`
- `evidence_references`
- `source_preserving`
- `clinical_meaning_changed`
- `implementation_allowed`
- `validation_plan`
- `notes`

## Allowed Specification Examples

Potentially allowed operations include:

- Deterministic date parsing
- Deterministic numeric parsing
- Missingness flags
- Quality flags
- Neutral string normalization
- Technical datatype normalization

These operations must still be classified and justified.

## Prohibited In Preprocessing

The specification layer must not authorize:

- Clinical value imputation
- Changes to clinical meaning
- Medical terminology recoding unless explicitly justified in a later authorized layer
- Silent record deletion
- ADaM analysis variable creation
- SDTM compliance transformation
- Raw-to-SDTM mapping

If an operation would alter clinical meaning, `implementation_allowed` is `false` unless a future explicit study-defined transformation layer authorizes it.

## Boundary

Preprocessing Specification answers:

> What transformations are justified?

Preprocessing Engine answers:

> Execute only approved specifications.

ADaM Derivation answers:

> Create analysis-ready variables and datasets.

This milestone does not execute preprocessing, derive ADaM datasets, run statistical analysis, or generate final reports.
