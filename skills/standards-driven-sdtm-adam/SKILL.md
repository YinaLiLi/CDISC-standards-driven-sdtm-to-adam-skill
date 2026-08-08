---
name: standards-driven-sdtm-adam
description: Use for Version 1 standards-driven workflows that derive supported ADaM outputs from existing SDTM datasets using configured CDISC standards, explicit specifications, independent validation, traceability, and deterministic reports.
---

# Standards-Driven SDTM-to-ADaM Pipeline

## Runtime Boundary

Use this skill only for existing SDTM inputs. Version 1 supports:

- SDTM inputs: `DM`, `AE`, `LB`, `DS`, `EX`, `SV`
- ADaM outputs: `ADSL`, `ADAE`, `ADLB`, `ADTTE`

Do not add Raw-to-SDTM mapping, SDTM conformance transformation, statistical analysis, machine learning, dashboards, AI summaries, Define-XML generation, or regulatory certification unless a later task explicitly changes scope.

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

- `references/standards-index.md`: Version 1 standards scope notes.
