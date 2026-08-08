# Evidence Resolution and Citation Engine

The evidence resolution layer resolves evidence references into citation records for downstream reporting.

## Responsibility

The resolver accepts decisions and specification items that already contain:

- a stable rule or specification identifier
- a decision classification
- evidence reference ids produced by rule extraction

It joins those references to `RuleExtractionRun` records and registry manifest metadata, then returns deterministic citation records. It does not search standards, classify decisions, generate specifications, execute derivations, validate outputs, or render reports.

## Source Roles

Runtime citation resolution preserves the existing source-role boundaries:

- `primary_standard` may provide normative citations for `STANDARD_REQUIRED` and `STANDARD_GUIDED` decisions.
- `upstream_reference` may provide upstream contextual citations.
- `validation_reference` is excluded from normative decision evidence and may appear only when the request is explicitly for validation support.
- `future_scope` is excluded from runtime evidence resolution.

Primary standards take precedence over validation references because validation references cannot become primary rule evidence.

## Missing Evidence

The resolver does not fabricate provenance. If a referenced evidence id is absent, points to an unknown standard, has no extractable evidence, or is disallowed by source role, the output records that condition through unresolved or excluded evidence references.

Non-standard classifications keep their semantics. `STUDY_SPECIFIC`, `USER_DEFINED`, `DATA_ENGINEERING`, `EXAMPLE_ADAPTED`, and `UNSUPPORTED` decisions are not forced into normative standard citations.

## Public API

The public API is exposed from `standards_driven_sdtm_adam.traceability`:

- `EvidenceResolver`
- `DecisionEvidenceRequest`
- `CitationRecord`
- `ResolvedEvidenceItem`
- `EvidenceResolutionResult`

Reporting should consume these citation records rather than re-resolving standard evidence.
