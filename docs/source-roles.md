# Source Roles

Standards intake and source identity verification are Developer Standards Setup tasks. Runtime users load an already configured registry and do not perform role assignment, SHA256 checks, or document identity inspection during normal workflow.

## primary_standard

May participate in:

- Standards Discovery
- Evidence Extraction
- Citation
- Derivation and preprocessing specification
- Validation against official standards

## upstream_reference

May participate only where appropriate for upstream SDTM interpretation, source-preserving preprocessing, and upstream traceability.

`SDTM_v2.0.pdf` and `SDTMIG v3.4.pdf` are upstream references. They support interpretation of existing SDTM input datasets and SDTM domain/variable semantics. They do not participate as primary ADaM normative evidence, produce `STANDARD_REQUIRED` ADaM evidence, perform Raw-to-SDTM mapping, perform SDTM mapping, or perform SDTM conformance transformation.

## validation_reference

May participate in:

- Structural comparison
- Regression testing
- Implementation comparison
- Validation support
- Reference or traceability comparison where explicitly requested by validation workflows

Validation references must not:

- Participate in primary rule discovery
- Become the basis for `STANDARD_REQUIRED`
- Override a `primary_standard`
- Introduce mandatory derivation logic
- Be represented as official requirements merely because an example contains logic

If a validation reference conflicts with a primary standard, the primary standard wins.

## future_scope

Disabled entry for explicitly out-of-scope future work.

Future-scope standards must not participate in Version 1 runtime rule discovery, evidence extraction, evidence resolution, specification, derivation, validation, or reporting as supporting evidence.
