# Independent ADaM Validation Engine

## Boundary

Execution Engine answers: "Build the approved output."

Validation Engine answers: "Independently verify the output."

The validation engine is logically separate from preprocessing and derivation execution. It does not rely solely on execution-time `validation_status` fields, does not modify datasets, does not repair failed data, does not create new derivation logic, and does not convert warnings into silent passes.

This is not a regulatory certification tool and does not claim CDISC or regulatory submission certification.

## Inputs

The validation engine may inspect:

- Source SDTM datasets
- Preprocessed dataset copies
- Preprocessing specifications and execution records
- ADaM derivation specifications
- Generated ADSL, ADAE, ADLB, and ADTTE datasets
- Derivation execution records
- Standards evidence
- Study/user decisions

## Validation Categories

Validation results are grouped into:

- `STRUCTURAL`
- `LOGICAL`
- `TRACEABILITY`

Each result records:

- `validation_id`
- `category`
- `dataset`
- `variable`
- `check_id`
- `description`
- `status`
- `severity`
- `expected`
- `observed`
- `specification_reference`
- `evidence_references`
- `execution_references`
- `source_references`
- `message`

Supported statuses include `PASS`, `FAIL`, `WARNING`, `NOT_APPLICABLE`, and `NOT_EVALUATED`.

Supported severities include `ERROR`, `WARNING`, and `INFO`.

## Structural Validation

Structural checks cover dataset grain and expected keys, including:

- ADSL one record per `USUBJID`
- required subject linkage
- occurrence-level record expectations for ADAE
- analysis-record expectations for ADLB
- event-level expectations for ADTTE
- unexpected datasets
- unspecified variables where prohibited by approved specifications

## Logical Validation

Logical checks independently evaluate deterministic derivations where the approved specification and study decisions make that possible.

Examples include:

- ADLB `AVAL` agreement with laboratory source values
- ADAE `TRTEMFL` agreement with resolved treatment-emergent rules
- ADTTE `CNSR` agreement with explicit event/censor logic
- blocked variables are not silently populated

If study logic is unresolved, the engine returns `NOT_EVALUATED` rather than guessing.

## Traceability Validation

Traceability checks verify that generated outputs can be followed through:

```text
ADaM Output
  -> Execution Record
  -> Derivation Specification
  -> Source SDTM Variable / Record
  -> Decision Classification
  -> Evidence or Study/User Decision
```

The engine also validates preprocessing traceability:

```text
Processed Field
  -> Preprocessing Execution
  -> Preprocessing Specification
  -> Classification
  -> Evidence / Engineering Convention
```

Checks include missing specification references, missing source references, missing evidence references, orphan execution records, and preprocessing execution records without matching specifications.
