# ADaM Derivation Engine

## Boundary

ADaM Derivation Specification answers: "What should be derived?"

ADaM Derivation Engine answers: "Execute approved specifications."

Validation Engine answers: "Independently validate resulting ADaM datasets, derivation logic, and traceability."

This engine does not perform statistical analysis, machine learning, dashboards, final reports, Define-XML generation, or regulatory submission certification.

## Version 1 Supported Outputs

- ADSL
- ADAE
- ADLB
- ADTTE

## Execution Rules

The engine executes only variable specifications where:

- `implementation_allowed = true`
- all dependencies have completed successfully
- required study/user decisions are resolved
- required source domains and variables are available
- a Version 1 executor is registered for the specified ADaM variable

If any requirement is not satisfied, the variable is not derived. The engine records a blocked or failed execution status, warnings, unresolved study-decision references, and provenance.

## Source Safety

The engine creates new ADaM dataset objects. It never mutates source SDTM or preprocessing outputs.

It does not add helpful variables that were not represented by approved derivation specifications.

## Traceability

Each variable execution records:

- `execution_id`
- `specification_id`
- `dataset`
- `variable`
- `classification`
- `source_domains`
- `source_variables`
- `dependency_executions`
- `input_record_count`
- `output_record_count`
- `derived_value_count`
- `status`
- `validation_status`
- `warnings`
- `evidence_references`
- `study_decision_references`

Traceability follows:

```text
ADaM value
  -> Variable Specification
  -> Source SDTM record(s)/variable(s)
  -> Decision Classification
  -> Evidence / Study Decision
```

## Version 1 Dataset Behavior

ADSL is generated at one record per subject and supports approved core subject, treatment, and population variables.

ADAE is generated from AE records and may use completed ADSL dependencies. Treatment-emergent logic executes only when the required treatment-emergent definition is resolved.

ADLB is generated from LB records and preserves source traceability for laboratory analysis variables. Baseline and analysis-window logic are not inferred.

ADTTE is generated only when explicit event and censoring rules are provided. Censoring strategy is never inferred.

## Structural Checks

The engine includes execution-time structural checks such as:

- ADSL uniqueness by `USUBJID`
- required key and source-variable availability
- expected record grain for supported datasets
- dependency completion checks

These checks are not a substitute for the independent Validation Engine.
