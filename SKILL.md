---
name: standards-driven-sdtm-to-adam
description: Canonical shared CDISC SDTM to ADaM Skill definition. Use for CDISC Feasibility Checker, CDISC SDTM to ADaM Transfer, or full CDISC SDTM to ADaM workflows when a user provides existing SDTM datasets and a concrete clinical or analysis objective, such as why subjects discontinue a trial, treatment-emergent adverse events, lab change from baseline, or exposure duration. Checks feasibility, builds explicit specifications, derives supported ADaM outputs, validates independently, and returns traceable reports. Agent-specific Codex and Claude Code adapters should delegate here instead of duplicating runtime instructions.
metadata:
  version: 1.2.2
---

# CDISC Standards-Driven SDTM-to-ADaM

## Overview

Version: 1.2.2

CDISC SDTM to ADaM is a CDISC standards-driven Skill for checking whether a concrete clinical or analysis objective is feasible from existing SDTM data, then deriving supported ADaM outputs only after the objective and derivation plan are confirmed.

## Usage Examples

After installing or reinstalling this Skill, tell the user it will be available on the next turn or in a new session, then show these usage examples:

```text
CDISC Feasibility Checker:
Use CDISC Feasibility Checker.
Objective: When and why do subjects discontinue the trial?
Available SDTM: DM, DS, SV, AE, EX, LB.

CDISC SDTM to ADaM Transfer:
Use CDISC SDTM to ADaM Transfer.
Objective: When and why do subjects discontinue the trial?
Use the confirmed feasibility result and derivation plan to derive the supported ADaM outputs, validate them, and generate the traceability report.

CDISC SDTM to ADaM:
Use CDISC SDTM to ADaM.
Objective: How do key lab values change from baseline over scheduled visits?
Available SDTM: DM, LB, SV, EX.
First check feasibility, then show the derivation plan. Wait for confirmation before running the transfer.
```

Objective means the concrete clinical or analysis question, not the dataset name. For example, use `When and why do subjects discontinue the trial?` instead of `Create ADSL`.

This root file is the canonical shared Skill definition. Keep agent-specific discovery metadata and invocation syntax in thin adapters:

- Codex adapter: `skills/cdisc-sdtm-to-adam/SKILL.md`
- Claude Code adapter: `.claude/skills/cdisc-sdtm-to-adam/SKILL.md`

Do not duplicate this runtime workflow in agent adapters unless an agent format technically requires it.

## Post-Install Output

After installing or reinstalling this Skill, output this usage guide to the user. If the installing agent summarizes instead of copying this block, preserve the same three modes and examples:

```text
CDISC SDTM to ADaM is installed.

Use one of these modes:

1. CDISC Feasibility Checker
   Checks whether a concrete clinical or analysis objective is feasible with the available SDTM data. It does not derive ADaM datasets.

   Example:
   Use CDISC Feasibility Checker.
   Objective: When and why do subjects discontinue the trial?
   Available SDTM: DM, DS, SV, AE, EX, LB.

2. CDISC SDTM to ADaM Transfer
   Runs the confirmed SDTM-to-ADaM transfer after feasibility and the derivation plan are approved.

   Example:
   Use CDISC SDTM to ADaM Transfer.
   Objective: When and why do subjects discontinue the trial?
   Use the confirmed feasibility result and derivation plan to derive the supported ADaM outputs, validate them, and generate the traceability report.

3. CDISC SDTM to ADaM
   Runs the guided full workflow: feasibility first, derivation plan, user confirmation, transfer, validation, and traceability report.

   Example:
   Use CDISC SDTM to ADaM.
   Objective: How do key lab values change from baseline over scheduled visits?
   Available SDTM: DM, LB, SV, EX.
   First check feasibility, then show the derivation plan. Wait for confirmation before running the transfer.

Objective means the concrete clinical or analysis question, not the dataset name. For example, use "When and why do subjects discontinue the trial?" instead of "Create ADSL."
```

## Runtime Boundary

Use this skill only for existing SDTM inputs. Version 1 supports:

- SDTM inputs: `DM`, `AE`, `LB`, `DS`, `EX`, `SV`
- ADaM outputs: `ADSL`, `ADAE`, `ADLB`, `ADTTE`

Do not add Raw-to-SDTM mapping, SDTM conformance transformation, statistical analysis, machine learning, dashboards, AI summaries, Define-XML generation, or regulatory certification unless a later task explicitly changes scope.

## User Objective

Treat the objective as the concrete clinical or analysis question the user wants to answer, not as the ADaM dataset name to produce.

Good objectives:

- When and why do subjects discontinue the trial?
- Which subjects experienced treatment-emergent adverse events, and how severe were they?
- How do key lab values change from baseline over scheduled visits?
- What is each subject's treatment exposure duration, and who discontinued treatment early?

Avoid treating these as user objectives:

- Derive ADSL.
- Create ADAE.
- Run the pipeline.

Map the user's objective to the supported SDTM inputs, required variables, feasible ADaM outputs, missing data, assumptions, and traceability needs.

## Invocation Modes

Support these user-facing modes:

| Mode | Use when | Required behavior |
|---|---|---|
| CDISC Feasibility Checker | The user asks whether a clinical or analysis objective is answerable from existing SDTM. | Inspect available SDTM domains and variables, return feasibility, missing inputs, blockers, limitations, required ADaM outputs, and next steps. Do not derive ADaM datasets. |
| CDISC SDTM to ADaM Transfer | The user has a confirmed objective and derivation plan and asks to execute the SDTM-to-ADaM transfer. | Derive supported ADaM outputs from approved specifications, run independent validation, resolve evidence, and produce traceability reports. |
| CDISC SDTM to ADaM | The user wants the complete guided workflow. | Run feasibility first, show the derivation plan, wait for user confirmation, then run transfer, validation, evidence resolution, and reporting. |

Default to the complete guided workflow when the user invokes `CDISC SDTM to ADaM` without choosing a mode.

Example prompts:

```text
Use CDISC Feasibility Checker.

Objective: When and why do subjects discontinue the trial?
Available SDTM: DM, DS, SV, AE, EX, LB.

Check whether this objective is feasible with the available SDTM data. Identify required domains, missing variables, assumptions, and the ADaM outputs needed.
```

```text
Use CDISC SDTM to ADaM.

Objective: How do key lab values change from baseline over scheduled visits?
Available SDTM: DM, LB, SV, EX.

First check feasibility, then show the derivation plan. Wait for confirmation before running the transfer.
```

```text
Use CDISC SDTM to ADaM Transfer.

Objective: When and why do subjects discontinue the trial?

Use the confirmed feasibility result and derivation plan to derive the supported ADaM outputs, validate them independently, and generate the traceability report.
```

## Runtime Workflow

Follow this governance flow:

```text
Search Standards
  -> Classify Decision
  -> Generate Specification
  -> Implementation
  -> Independent Validation
  -> Trace & Cite
```

Use the implemented v1 sequence:

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

Specification is required before implementation. Do not execute preprocessing or ADaM derivation without approved specifications.

## Runtime User Responsibilities

Runtime users provide:

- configured standards manifests
- existing SDTM datasets
- research objectives
- study decisions when required for study-specific derivations
- CDISC authentication when required for authorized standards acquisition

Runtime users do not perform standards intake, search CDISC for standards, choose versions, choose filenames, choose storage locations, recompute SHA256, confirm releases, or verify document identity during normal workflow.

## Developer Standards Setup

Developer Standards Setup is maintainer work:

- register local standards and references
- inspect source identity/version/release
- calculate SHA256 with the registry utility
- update manifest metadata
- keep licensed CDISC source files out of Git unless redistribution is explicitly allowed

Version and release metadata are descriptive. A newer legitimate official release is not automatically a mismatch. `MISMATCH` means wrong or unexpected document identity or an integrity issue.

## Source Roles

Use only these manifest roles:

- `primary_standard`
- `upstream_reference`
- `validation_reference`
- `future_scope`

`validation_reference` does not participate in primary rule discovery, cannot produce `STANDARD_REQUIRED` evidence, and may only support regression testing, structural comparison, implementation comparison, and validation support. `future_scope` is excluded from Version 1 runtime rule and evidence processing. Primary standards remain authoritative.

## Traceability And Reporting

Preserve provenance from source evidence to specification, execution, validation, evidence resolution, and reports where supported. Reports present existing outputs as deterministic dictionaries, JSON, and Markdown; they do not perform validation or evidence resolution.

## Resources

- `docs/standards/standards-index.md`: Version 1 standards scope notes.
