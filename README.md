# CDISC Standards-Driven SDTM-to-ADaM

Reusable Skill for deriving supported ADaM datasets from existing SDTM using CDISC standards, feasibility checks, explicit specifications, independent validation, and traceable evidence.

This repository packages **CDISC SDTM to ADaM** as one canonical Skill with Codex and Claude Code adapters.

- Canonical Skill: [SKILL.md](SKILL.md)
- Codex adapter: [skills/standards-driven-sdtm-adam/](skills/standards-driven-sdtm-adam/)
- Claude Code adapter: [.claude/skills/cdisc-sdtm-to-adam/](.claude/skills/cdisc-sdtm-to-adam/)

## Workflow

![CDISC SDTM to ADaM workflow](docs/assets/readme-workflow.png)

| Stage | What it means |
|---|---|
| Feasibility Check | Confirm the requested ADaM can be supported by available SDTM and standards. |
| Build Derivation Plan | Define source variables, derivation rules, transformations, and supporting evidence before execution. |
| Independent Validation | Validate the derived result separately from derivation. |
| Trace & Report | Link decisions back to evidence and produce the final report. |

## What The Skill Does

Provide existing SDTM datasets and the ADaM objective. The Skill checks feasibility first, builds an explicit derivation plan when supported, derives the ADaM outputs, validates them independently, and returns traceability with deterministic reports.

## Supported Scope

| Existing SDTM input | Supported ADaM output |
|---|---|
| `DM` | `ADSL` |
| `AE` | `ADAE` |
| `LB` | `ADLB` |
| `DS`, `EX`, `SV` | `ADTTE` |

Existing SDTM is required. Raw -> SDTM mapping, SDTM conformance transformation, statistical analysis, machine learning, dashboards, AI summaries, Define-XML generation, and regulatory certification are outside Version 1 scope.

## Workflow / Pipeline

The implemented Version 1 flow is:

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

Specification is required before implementation. Unsupported objectives should be refined or supplied with missing data before derivation.

## Quick Start

### Codex

The Codex Skill is displayed as **CDISC SDTM to ADaM**.

```text
Use the "CDISC SDTM to ADaM" skill.

I have attached my SDTM datasets.

Goal:
Create ADSL and ADAE.

Check feasibility first. If the objective is supported,
build the derivation plan, derive the datasets,
run independent validation, and return the traceability report.
```

### Claude Code

Invoke the Claude Code adapter with:

```text
/cdisc-sdtm-to-adam
```

Then provide the same SDTM datasets and ADaM objective.

## Outputs

| Output | Description |
|---|---|
| ADaM datasets | Supported `ADSL`, `ADAE`, `ADLB`, and `ADTTE` outputs. |
| Specifications | Explicit preprocessing and derivation plans generated before implementation. |
| Validation results | Independent checks of structure, logic, and traceability. |
| Evidence and citations | Links from decisions and derivations back to available standards evidence. |
| Reports | Deterministic Markdown and JSON summaries. |

## Standards / Evidence Model

Licensed CDISC source documents are not bundled in GitHub. Runtime discovery uses configured standards manifests and locally available authorized source files. If a required local file is missing, the runtime records that standard as unavailable rather than inventing evidence.

| Group | Sources | Purpose |
|---|---|---|
| Primary ADaM | ADaM Model, ADaM Implementation Guide, OCCDS Implementation Guide, BDS Time-to-Event Guide, Important Considerations, Metadata Submission Guidelines, Controlled Terminology, Conformance Rules | ADaM derivation rules, terminology, validation, and conformance evidence. |
| Upstream SDTM | SDTM Model, SDTM Implementation Guide | Interpretation of existing SDTM structure and variable semantics. |
| Validation references | ADaM Examples, ADaM MSG Example Submission, ADaM Traceability Examples | Regression support, structural comparison, implementation comparison, and validation support. |

Runtime users do not perform standards intake, choose standards versions, select filenames, calculate checksums, or verify document identity. Those are maintainer responsibilities.

## Architecture

The Python implementation behind the Skill lives in `src/standards_driven_sdtm_adam/`. See [Architecture Overview](docs/architecture/overview.md) for module boundaries and runtime flow.

## Documentation

Start with the [documentation index](docs/README.md).

| Topic | Link |
|---|---|
| Architecture | [docs/architecture/overview.md](docs/architecture/overview.md) |
| Standards setup | [docs/standards/standards-registry.md](docs/standards/standards-registry.md) |
| Usage examples | [docs/guides/usage-examples.md](docs/guides/usage-examples.md) |
| Evidence resolution | [docs/pipeline/evidence-resolution.md](docs/pipeline/evidence-resolution.md) |
| Reporting | [docs/pipeline/reporting.md](docs/pipeline/reporting.md) |
| Release history | [docs/release/v1.0.0.md](docs/release/v1.0.0.md) and [CHANGELOG](CHANGELOG.md) |

## Development

Developers can install the Python package locally to run or test the Version 1 pipeline:

```powershell
python -m pip install -e .
```

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

See [Usage Examples](docs/guides/usage-examples.md) for a complete runnable example.

## License

See [LICENSE](LICENSE).
