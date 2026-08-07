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

Standards are registered through `config/standards`. Local licensed CDISC source files are not committed, portable paths such as `${CDISC_HOME}` are supported, and official filenames are preserved.

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
