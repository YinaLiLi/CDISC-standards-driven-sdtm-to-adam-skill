# Changelog

## 1.0.0 - Version 1 Release

### Added

- Standards registry and manifest loading for configured CDISC standards and reference materials.
- Standards discovery and local rule extraction.
- Feasibility assessment for supported SDTM source data.
- Source-preserving preprocessing specification and approved preprocessing execution.
- ADaM derivation specification and approved derivation execution for `ADSL`, `ADAE`, `ADLB`, and `ADTTE`.
- Independent validation for generated ADaM outputs and traceability.
- Evidence resolution and deterministic citation records.
- Deterministic report dictionary, JSON, and Markdown rendering.
- Version 1 pipeline facade for end-to-end validation and auditability.
- Documentation for runtime use, Developer Standards Setup, source roles, decision classifications, traceability, and reporting.

### Supported Scope

- SDTM inputs: `DM`, `AE`, `LB`, `DS`, `EX`, `SV`
- ADaM outputs: `ADSL`, `ADAE`, `ADLB`, `ADTTE`

### Limitations

Version 1 does not include Raw-to-SDTM mapping, SDTM conformance transformation, exploratory data analysis, statistical analysis, machine learning, dashboards, AI summaries, Define-XML generation, or regulatory certification.
