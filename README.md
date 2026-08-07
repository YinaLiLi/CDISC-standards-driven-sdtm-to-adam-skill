# Standards-Driven SDTM-to-ADaM Pipeline

Version 1 is a small, standards-governed Python package and Codex Skill for deriving selected ADaM outputs from existing SDTM datasets. It keeps standards discovery, specification, implementation, validation, evidence resolution, and reporting as explicit stages so provenance is visible rather than inferred.

## Version 1 Scope

Supported SDTM inputs:

- `DM`
- `AE`
- `LB`
- `DS`
- `EX`
- `SV`

Supported ADaM outputs:

- `ADSL`
- `ADAE`
- `ADLB`
- `ADTTE`

Version 1 assumes SDTM data already exists. It does not perform Raw-to-SDTM mapping or SDTM conformance transformation.

## Out Of Scope

Version 1 does not provide:

- Raw -> SDTM
- SDTM mapping
- SDTM conformance transformation
- exploratory data analysis
- statistical analysis
- machine learning
- dashboards or interactive UI
- AI summaries
- Define-XML generation
- regulatory certification

## Architecture

Runtime follows the governance flow:

```text
Search Standards
  -> Classify Decision
  -> Generate Specification
  -> Implementation
  -> Independent Validation
  -> Trace & Cite
```

The concrete v1 sequence is:

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

Specification is never skipped. Preprocessing and ADaM derivation execute only approved specifications, and validation independently checks generated outputs and traceability.

## Quick Start

Install local test dependencies as needed, then run:

```powershell
python -m pytest
python -m compileall src tests
```

Minimal v1 pipeline usage:

```python
from standards_driven_sdtm_adam.pipeline import V1Pipeline

result = V1Pipeline().run(
    registry_dir="config/standards",
    task_intents=(
        "Create ADSL subject-level analysis dataset",
        "Derive treatment-emergent adverse event variables for ADAE",
        "Plan ADLB laboratory analysis",
        "Identify ADTTE time-to-event evidence",
    ),
    research_objectives=(
        "Evaluate adverse events, laboratory values, and time-to-event outcomes.",
    ),
    sdtm_datasets={
        "DM": ({"USUBJID": "01"},),
        "AE": ({"USUBJID": "01", "AESTDTC": "2024-01-03"},),
        "LB": ({"USUBJID": "01", "LBTESTCD": "ALT", "LBORRES": "70", "LBSTRESN": "70", "LBDTC": "2024-01-02"},),
        "DS": ({"USUBJID": "01", "DSDECOD": "COMPLETED", "DSSTDTC": "2024-02-01"},),
        "EX": ({"USUBJID": "01", "EXTRT": "A", "EXSTDTC": "2024-01-01", "EXENDTC": "2024-01-14"},),
        "SV": ({"USUBJID": "01", "SVSTDTC": "2024-01-02"},),
    },
)

print(result.report.to_dict())
print(result.markdown_report)
```

The pipeline facade is intentionally v1-scoped. It sequences existing components and exposes all intermediate results for auditability.

## Local Standards Requirement

Standards manifests live under `config/standards`. They describe local CDISC standards and reference files, but licensed CDISC source files themselves must remain local unless redistributability is explicitly confirmed.

Use portable local paths such as `${CDISC_HOME}` or repository-relative paths. Keep official filenames unchanged. Source roles belong in manifests, not directory names.

Runtime users load configured standards and do not need to recompute SHA256, confirm release metadata, or perform document identity verification.

## Generated Outputs And Reports

The runtime can produce:

- preprocessing specifications and execution records
- ADaM specifications for `ADSL`, `ADAE`, `ADLB`, and `ADTTE`
- derived ADaM dataset objects for approved v1 variables
- independent validation results
- resolved citation records
- deterministic report dictionaries, JSON, and Markdown

Reports present existing outputs. They do not perform validation, evidence resolution, analysis, or certification.

## Developer Standards Setup

Developer Standards Setup is separate from runtime usage. Maintainers may:

- register local standards
- inspect source identity/version/release
- compute SHA256 with `StandardsRegistry.calculate_sha256(...)`
- update manifests and metadata
- maintain validation-reference and future-scope entries

Version and release metadata are descriptive. A different legitimate official release is not automatically a `MISMATCH`; update descriptive metadata during setup. `MISMATCH` is reserved for wrong or unexpected document identity or integrity issues.

## Limitations

Version 1 uses concise text extraction and lightweight deterministic fixtures. It is suitable for validating architecture, traceability, and supported v1 derivations, not for exhaustive clinical review. Study-specific choices such as safety population, treatment-emergent windows, and time-to-event event/censoring rules must be supplied explicitly.

See also:

- [Architecture](docs/architecture.md)
- [Standards Registry](docs/standards-registry.md)
- [Source Roles](docs/source-roles.md)
- [Usage Examples](docs/usage-examples.md)
- [Evidence Resolution](docs/evidence-resolution.md)
- [Reporting](docs/reporting.md)
- [Release Notes](docs/release-notes-v1.0.0.md)
- [Changelog](CHANGELOG.md)
