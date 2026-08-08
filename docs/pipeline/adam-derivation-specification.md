# ADaM Derivation Specification

## Boundary

ADaM Derivation Specification answers: "What should be derived and why?"

It creates dataset-level and variable-level specifications for supported ADaM outputs. It does not create ADaM datasets, calculate values, run statistical analysis, validate finished datasets, generate Define-XML, or claim submission approval.

Adjacent layers remain separate:

- ADaM Derivation Engine: execute approved derivation specifications.
- Validation Engine: check resulting datasets and traceability.
- Reporting: communicate results after derivation and validation.

## Version 1 Supported Outputs

- ADSL
- ADAE
- ADLB
- ADTTE

## Inputs

The specification layer may use:

- Approved research scope and feasibility results.
- Existing and preprocessed SDTM source data.
- Standards Discovery results.
- Extracted CDISC evidence.
- Explicit user-defined or study-specific decisions.

## Variable Specification Contract

Every ADaM variable specification records:

- `specification_id`
- `dataset`
- `variable`
- `label`
- `purpose`
- `source_domains`
- `source_variables`
- `derivation_logic`
- `dependencies`
- `classification`
- `evidence_references`
- `user_defined_inputs`
- `assumptions`
- `validation_plan`
- `implementation_allowed`
- `unresolved_issues`

## Decision Classifications

- `STANDARD_REQUIRED`
- `STANDARD_GUIDED`
- `STUDY_SPECIFIC`
- `USER_DEFINED`
- `DATA_ENGINEERING`
- `EXAMPLE_ADAPTED`
- `UNSUPPORTED`

Study-specific logic is never invented. Population definitions, treatment analysis windows, baseline definitions, censoring rules, treatment-emergent windows, and similar study decisions must be provided explicitly before implementation is allowed.

CDISC examples may inform a specification only when the variable is classified as `EXAMPLE_ADAPTED`; examples are not treated as mandatory CDISC rules.

## Traceability

Traceability is maintained in this chain:

```text
ADaM Variable
  -> Derivation Specification
  -> Source SDTM Variables
  -> Decision Classification
  -> CDISC Evidence / Study Decision
```

Dependency relationships are represented directly in variable specifications. For example, `ADAE.TRTEMFL` depends on ADSL treatment dates, ADAE analysis start date, and a study-defined treatment-emergent window.

## Unresolved Study Decisions

Missing study decisions are represented with structured records containing:

- `decision_id`
- `question`
- `affected_datasets`
- `affected_variables`
- `required_before_implementation`
- `status`

If a required decision or evidence source is missing, affected variables set `implementation_allowed = false` and record the unresolved issue.
