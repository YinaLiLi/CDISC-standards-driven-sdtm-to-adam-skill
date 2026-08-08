# Standards-Driven SDTM Preprocessing Engine

The preprocessing engine answers:

> Execute only preprocessing operations that were explicitly specified and approved.

It consumes SDTM datasets and approved preprocessing specifications. It never invents, infers, or silently adds preprocessing operations.

## Execution Gate

An operation may execute only when all of the following are true:

- `implementation_allowed = true`
- `source_preserving = true`
- `clinical_meaning_changed = false`
- `classification != UNSUPPORTED`

Unsupported, unsafe, or absent operations are rejected or skipped with execution records.

## Supported Version 1 Operations

- `deterministic_date_parsing`
- `deterministic_numeric_parsing`
- `missingness_quality_flag`
- `quality_flag_creation`
- `neutral_whitespace_normalization`
- `technical_datatype_normalization`

Only operations represented by approved preprocessing specifications are executable.

## Source Preservation

The engine produces processed copies. It never overwrites the original SDTM inputs.

Execution may add technical companion fields such as parsed values, normalized copies, or flags. The original source value remains retained.

## Execution Records

Every executed, rejected, or failed operation produces an execution record with:

- `execution_id`
- `operation_id`
- `dataset`
- `variable`
- `operation`
- `classification`
- `input_record_count`
- `output_record_count`
- `affected_record_count`
- `status`
- `validation_status`
- `warnings`
- `source_reference`

`source_reference` preserves traceability to:

1. Preprocessing execution
2. Preprocessing specification
3. Decision classification
4. Evidence references

## Fail-Safe Behavior

If an operation cannot be executed deterministically:

- Source values are retained.
- Technical parsed fields are left empty.
- Failure flags or warnings are recorded.
- Record counts are preserved.

## Boundary

Preprocessing Specification answers:

> What operations are allowed?

Preprocessing Engine answers:

> Execute approved source-preserving operations.

ADaM Derivation Specification answers:

> What analysis datasets and variables must be derived?

This layer does not implement ADaM derivation, statistical analysis, dashboards, final reports, or regulatory certification.
