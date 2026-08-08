# Standards Discovery Engine

The Standards Discovery Engine answers one question:

> Which registered standards should be consulted?

It does not answer:

> What does the standard require?

That requirement belongs to Rule Extraction.

## Inputs

Discovery accepts a task or development intent as plain text. The engine uses registered standards metadata and deterministic keyword matching only.

Discovery considers:

- Task type
- Dataset or domain token
- Requested output
- Source role
- Standard metadata

## Source-Role Isolation

Primary rule discovery may use:

- `primary_standard`
- eligible `upstream_reference` sources when the task specifically requires upstream SDTM/source-preserving preprocessing context

Primary rule discovery excludes:

- `validation_reference`
- `future_scope`

Validation references are reserved for validation/reference workflows. They must not leak into standards evidence retrieval and must not become the basis for mandatory CDISC rules.

## Version 1 Discovery Rules

Dataset-specific metadata routing:

- `ADSL`: common ADaM standards
- `ADAE`: ADaMIG, ADaM OCCDS IG, ADaM Controlled Terminology, ADaM Conformance Rules
- `ADLB`: ADaM Model, ADaMIG, ADaM Controlled Terminology, ADaM Conformance Rules
- `ADTTE`: ADaMIG, ADaM BDS Time-to-Event Guide, ADaM Controlled Terminology, ADaM Conformance Rules

SDTM preprocessing intent returns SDTM upstream references only. This does not imply Raw-to-SDTM mapping, SDTM conformance transformation, or SDTM certification support.

## Boundaries

The discovery engine must not:

- Parse PDFs
- Search PDF contents
- Build embeddings
- Build semantic indexes
- Extract rules
- Infer section numbers
- Infer page numbers
- Quote standards text
- Infer specific CDISC requirements
- Use validation/reference examples as primary standards
- Hallucinate standards not registered in the manifest registry
