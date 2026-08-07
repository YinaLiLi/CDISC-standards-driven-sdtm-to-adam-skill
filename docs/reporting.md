# Reporting

Milestone 12 adds a thin presentation layer for existing v1 pipeline outputs.

## Responsibility

Reporting consumes supplied objects from earlier milestones:

- preprocessing specifications
- ADaM derivation specifications
- independent validation results
- Milestone 11 evidence resolution results

The reporting layer builds a stable report representation and renders it for readers. It does not perform standards discovery, rule extraction, decision classification, derivation, validation, or evidence resolution.

## Output Formats

The public reporting API supports:

- deterministic dictionary output through `PipelineReport.to_dict()` or `render_dict(...)`
- deterministic JSON through `render_json(...)`
- deterministic Markdown through `render_markdown(...)`

No HTML, PDF, Excel, dashboard, or interactive UI output is included in v1.

## Report Coverage

The v1 report includes:

- preprocessing/specification summary
- ADaM derivation/specification summary for ADSL, ADAE, ADLB, and ADTTE
- validation status, counts, warnings, and failures from M10 validation results
- traceability and evidence summary from M11 resolution results
- unresolved and excluded evidence references

Normative citations and validation/supporting citations remain distinguishable through the M11 `citation_purpose` and `source_role` fields.

## Status

Overall report status is derived from supplied validation results only:

- `FAIL` when any validation result has status `FAIL`
- `PASS_WITH_WARNINGS` when warnings exist and failures do not
- `PASS` otherwise

These statuses are operational report statuses only. They do not imply CDISC certification, submission approval, or any regulatory conclusion.

## Public API

The public API is exposed from `standards_driven_sdtm_adam.reporting`:

- `ReportBuilder`
- `PipelineReport`
- `render_dict`
- `render_json`
- `render_markdown`
