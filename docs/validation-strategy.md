# Validation Strategy

Version 1 validation is implemented by `standards_driven_sdtm_adam.validation.AdamValidationEngine`.

Validation runs after ADaM derivation and does not repair or regenerate outputs. It checks supplied source SDTM data, approved ADaM specifications, generated ADaM datasets, derivation execution records, preprocessing traceability where supplied, evidence references, and study decisions.

Validation categories are:

- `STRUCTURAL`
- `LOGICAL`
- `TRACEABILITY`

Validation statuses are:

- `PASS`
- `FAIL`
- `WARNING`
- `NOT_APPLICABLE`
- `NOT_EVALUATED`

The validation engine does not perform statistical analysis, machine learning, dashboard generation, Define-XML generation, or regulatory certification.
