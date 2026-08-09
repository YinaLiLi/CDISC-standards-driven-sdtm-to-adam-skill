# Changelog

## 1.2.1 - Post-Install Usage Output

### Changed

- Added canonical post-install usage output to `SKILL.md` so installation flows can display the supported modes and example prompts after install.
- Updated Codex and Claude Code adapters to point installers to the canonical post-install output instead of relying only on README guidance.

## 1.2.0 - Skill Invocation Guidance

### Changed

- Reframed the user objective as a concrete clinical or analysis question rather than an ADaM dataset name.
- Added user-facing modes for `CDISC Feasibility Checker`, `CDISC SDTM to ADaM Transfer`, and the complete `CDISC SDTM to ADaM` guided workflow.
- Updated Codex and Claude Code Skill adapter metadata and examples to use CDISC-prefixed invocation names.
- Added post-install quick-start examples that show feasibility-first usage before transfer.

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
