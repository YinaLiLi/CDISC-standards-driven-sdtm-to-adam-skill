# Version 1.0.0 Release Notes

## Summary

Version 1.0.0 provides a standards-driven SDTM-to-ADaM workflow for existing SDTM datasets. It keeps standards evidence, specifications, implementation, validation, citation, and reporting as separate auditable stages.

## Implemented Milestones

- Project architecture and repository scaffold.
- Standards manifest registry.
- Standards discovery.
- Rule extraction.
- Feasibility assessment.
- Source-preserving preprocessing specification.
- Approved preprocessing execution.
- ADaM derivation specification.
- Approved ADaM derivation execution.
- Independent ADaM validation.
- Developer Standards Setup utilities for manifest finalization and local source identity metadata.
- Evidence resolution and citation.
- Deterministic reports.
- End-to-end v1 pipeline validation.
- Documentation alignment.

## Supported Workflow

```text
Standards Discovery
  -> Rule Extraction
  -> Feasibility Assessment
  -> Preprocessing Specification
  -> Preprocessing
  -> ADaM Specification
  -> ADaM Derivation
  -> Independent Validation
  -> Evidence Resolution
  -> Reporting
```

Specification is required before implementation.

## Supported Scope

Inputs:

- `DM`
- `AE`
- `LB`
- `DS`
- `EX`
- `SV`

Outputs:

- `ADSL`
- `ADAE`
- `ADLB`
- `ADTTE`

## Architectural Decisions

- Runtime usage is separate from Developer Standards Setup.
- Source roles are manifest metadata, not directory semantics.
- `validation_reference` materials do not participate in primary rule discovery and cannot produce `STANDARD_REQUIRED` evidence.
- `future_scope` entries are excluded from Version 1 runtime rule and evidence processing.
- Reports present existing results; they do not validate or resolve evidence.
- The `V1Pipeline` facade is a v1 orchestration and validation aid, not a generic workflow engine.

## Limitations

Version 1 excludes Raw-to-SDTM mapping, SDTM mapping, SDTM conformance transformation, exploratory data analysis, statistical analysis, machine learning, dashboards, AI summaries, Define-XML generation, and regulatory certification.

## Future Roadmap

Future work should be scoped explicitly before implementation. Potential directions include broader standards coverage, richer evidence indexing, additional supported ADaM variables, and release packaging improvements.
