# Standards-Driven SDTM-to-ADaM Pipeline

Reusable Codex Skill and Python pipeline for deriving selected ADaM datasets from existing SDTM inputs. It uses configured standards, generated specifications, independent validation, traceable evidence, and deterministic reporting to keep each derivation auditable.

## Supported Scope

| Input SDTM | Output ADaM |
| --- | --- |
| `DM` | `ADSL` |
| `AE` | `ADAE` |
| `LB` | `ADLB` |
| `DS` | `ADTTE` |
| `EX` | `ADTTE` |
| `SV` | `ADTTE` |

Existing SDTM is required. Raw -> SDTM mapping and SDTM conformance transformation are outside this Skill.
Exploratory analysis, statistical analysis, machine learning, dashboards, AI summaries, Define-XML generation, and regulatory certification are outside Version 1 scope.

## How It Works

```text
Standards Discovery
  -> Rule Extraction
  -> Feasibility Assessment
  -> Specification
  -> Implementation
  -> Independent Validation
  -> Evidence Resolution
  -> Reporting
```

Specification is always generated before implementation.

## Standards

CDISC source documents are not bundled with this Skill because some standards are subject to licensing and access restrictions. On first use, the Skill checks required local standards.

When required CDISC standards are missing, the Skill opens the official CDISC sign-in flow. After the user signs in with their cdiscID, the Skill automatically locates, downloads, validates, and stores the required standards. If automated access is unavailable, the Skill identifies the exact official CDISC source and expected document so the user does not need to search for it manually.

Programmatic first-run preflight:

```python
from standards_driven_sdtm_adam.standards import first_user_preflight, manual_setup_lines

result = first_user_preflight(
    "config/standards",
    task_intents=("Create ADSL subject-level analysis dataset",),
)
if result.manual_setup_required:
    print("\n".join(manual_setup_lines(result)))
```

Manual setup remains available when a source is not retrievable through the supported authorization flow. In that case, the Skill identifies the exact official source and expected filename.

Version 1 uses these primary ADaM standards:

- ADaM Model
- Important Considerations When Using ADaM
- ADaM Implementation Guide
- ADaM OCCDS Implementation Guide
- ADaM BDS Time-to-Event Guide
- ADaM Metadata Submission Guidelines
- ADaM Controlled Terminology
- ADaM Conformance Rules

Version 1 also uses these upstream references:

- SDTM Model
- SDTM Implementation Guide

See [Standards Registry](docs/standards-registry.md) for registry details.

## Quick Start

Install and run the test suite:

```powershell
python -m pip install -e ".[test]"
python -m pytest
```

Minimal pipeline usage:

```python
from standards_driven_sdtm_adam.pipeline import V1Pipeline

pipeline = V1Pipeline()
result = pipeline.run(
    registry_dir="config/standards",
    task_intents=(...),
    research_objectives=(...),
    sdtm_datasets={...},
)

print(result.markdown_report)
```

See [Usage Examples](docs/usage-examples.md) for a complete runnable example.

## Outputs

- ADaM datasets and specifications
- independent validation results
- traceable evidence and citations
- deterministic Markdown and JSON reports

## Documentation

- [Architecture](docs/architecture.md)
- [Standards Registry](docs/standards-registry.md)
- [Source Roles](docs/source-roles.md)
- [Usage Examples](docs/usage-examples.md)
- [Evidence Resolution](docs/evidence-resolution.md)
- [Reporting](docs/reporting.md)

Release history: [Release Notes](docs/release-notes-v1.0.0.md) and [CHANGELOG](CHANGELOG.md).
