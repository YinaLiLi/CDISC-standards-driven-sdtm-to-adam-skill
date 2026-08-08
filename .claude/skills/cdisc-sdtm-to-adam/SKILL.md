---
name: cdisc-sdtm-to-adam
description: CDISC SDTM to ADaM workflow skill for deriving supported ADaM datasets from existing SDTM using configured CDISC standards, feasibility assessment, explicit derivation plans, independent validation, traceability, and deterministic reporting. Use when the user asks to create ADSL, ADAE, ADLB, or ADTTE from existing SDTM datasets, asks whether an ADaM objective is feasible, or asks for a standards-driven SDTM-to-ADaM derivation workflow in this repository.
---

# CDISC SDTM to ADaM

This is the Claude Code version of the CDISC Standards-Driven SDTM-to-ADaM Skill.

Invoke directly in Claude Code with:

```text
/cdisc-sdtm-to-adam
```

Or ask naturally, for example:

```text
Use the CDISC SDTM to ADaM skill.

I have attached my SDTM datasets.

Goal:
Create ADSL and ADAE.

Check feasibility first. If the objective is supported,
build the derivation plan, derive the datasets,
run independent validation, and return the traceability report.
```

## Runtime Boundary

Use this skill only for existing SDTM inputs. Version 1 supports:

- SDTM inputs: `DM`, `AE`, `LB`, `DS`, `EX`, `SV`
- ADaM outputs: `ADSL`, `ADAE`, `ADLB`, `ADTTE`

Do not add Raw-to-SDTM mapping, SDTM conformance transformation, statistical analysis, machine learning, dashboards, AI summaries, Define-XML generation, or regulatory certification unless the user explicitly changes scope.

## Operating Workflow

Follow this order:

1. Confirm the user provided existing SDTM datasets and an ADaM objective.
2. Identify the requested ADaM outputs and required SDTM domains.
3. Use configured CDISC standards and available local source files as evidence.
4. Run or describe a feasibility check before any derivation.
5. If feasible, build the derivation plan before execution.
6. Derive the supported ADaM outputs.
7. Run independent validation separate from derivation.
8. Return traceability, citations, validation results, and deterministic reports.

If feasibility fails, do not proceed to derivation. Explain what is missing or unsupported, then ask the user to refine the objective or provide additional data.

## Feasibility Check

Answer this question before planning or deriving:

```text
Can the requested ADaM objective be supported by the available SDTM datasets and configured CDISC standards?
```

Check:

- Whether the requested output is one of `ADSL`, `ADAE`, `ADLB`, or `ADTTE`.
- Whether required SDTM domains are present.
- Whether required source variables can be identified.
- Whether configured standards evidence is locally available.
- Whether study-specific decisions are needed before derivation.

## Build Derivation Plan

Use "Build Derivation Plan" as the user-facing term. Internally, this corresponds to explicit preprocessing and ADaM specifications.

The plan must define:

- source datasets and variables
- derivation rules
- transformations
- assumptions and required study decisions
- supporting standards evidence
- validation checks

Do not execute preprocessing or ADaM derivation before a plan/specification exists.

## Standards And Evidence

Licensed CDISC source documents are not bundled in GitHub. Use configured standards manifests and local authorized source files. If a required local standard is missing, report it as unavailable instead of inventing evidence.

Primary ADaM standards:

- ADaM Model
- ADaM Implementation Guide
- ADaM OCCDS Implementation Guide
- ADaM BDS Time-to-Event Guide
- Important Considerations When Using ADaM
- ADaM Metadata Submission Guidelines
- ADaM Controlled Terminology
- ADaM Conformance Rules

Upstream SDTM references:

- SDTM Model
- SDTM Implementation Guide

Validation references may support regression, structural comparison, implementation comparison, and validation support. They do not replace primary ADaM evidence.

## Repository Pointers

Use these files when more detail is needed:

- `README.md` for user-facing product positioning and workflow.
- `skills/standards-driven-sdtm-adam/SKILL.md` for the Codex Skill runtime boundary.
- `skills/standards-driven-sdtm-adam/references/standards-index.md` for standards scope.
- `docs/architecture.md` for architecture.
- `docs/usage-examples.md` for Python usage examples.
- `docs/evidence-resolution.md` for evidence behavior.
- `docs/reporting.md` for report behavior.

## Response Shape

When helping a user derive ADaM from SDTM, respond in this structure:

1. Feasibility result: supported, unsupported, or needs more information.
2. Required SDTM inputs and any missing data.
3. Derivation plan summary.
4. Validation approach.
5. Traceability and report outputs.
6. Next action: derive, request missing inputs, or refine objective.

Keep Python API details secondary unless the user asks for implementation or developer usage.
