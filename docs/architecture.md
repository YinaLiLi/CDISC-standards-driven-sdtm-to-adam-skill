# Architecture

The project has two separate flows: Developer Standards Setup and Runtime Skill Workflow.

## Developer / Maintainer Flow

Developer Standards Setup is used by the skill developer or maintainer to prepare a local standards environment:

```text
Download or provide local standards
  -> Register standards
  -> Inspect identity/version/release
  -> Compute SHA256
  -> Update manifest
  -> Prepare local standards environment
```

Setup utilities may:

- register local CDISC standards and references
- inspect source identity
- detect version or release metadata
- compute SHA256
- verify local source availability
- populate or update manifest metadata
- prepare standards for local development and testing

Milestone 10.5 and Milestone 10.6 are Developer Standards Setup work. They are not runtime workflow steps and are not required from normal skill users.

Version and release date are descriptive metadata. They are not hard runtime compatibility gates. If a developer replaces a local standard with a newer official release, Developer Standards Setup should detect the observed metadata, update the manifest, and recompute SHA256.

`MISMATCH` is reserved for cases where the local file is actually a different standard or reference. A version or release-date difference alone should be handled by updating descriptive manifest metadata, not by blocking runtime use.

## Runtime User Flow

Runtime Skill Workflow is used by normal skill users:

```text
Configure standards directory
  -> Load registry
  -> Standards Discovery
  -> Evidence Extraction
  -> Feasibility
  -> Preprocessing Specification
  -> Preprocessing Execution
  -> ADaM Derivation Specification
  -> ADaM Derivation
  -> Independent Validation
  -> Evidence Resolution and Citation
  -> Reporting
```

At runtime, configured registry entries are usable when available. Runtime does not require users to perform standards intake, manual SHA256 verification, release/version confirmation, source identity verification, or developer manifest maintenance.

Runtime must not repeatedly inspect document identity/version, recompute SHA256 on every run, or require developer verification status before normal usage unless the source is genuinely unavailable or invalid.

The high-level decision flow is:

```text
Search Standards
  -> Classify Decision
  -> Generate Specification
  -> Implementation
  -> Independent Validation
  -> Trace & Cite
```

Specification is never skipped. See `docs/decision-classifications.md` for the exact Version 1 classification set.

## Source Roles

The source roles are:

- `primary_standard`
- `upstream_reference`
- `validation_reference`
- `future_scope`

Runtime rule discovery must exclude `validation_reference` and `future_scope`. Validation references may support validation/reference workflows but must not produce mandatory standards evidence or override a primary standard.

## Local Source Safety

Do not rename CDISC files. Do not commit licensed CDISC source files unless redistributability is explicitly confirmed. Use portable path configuration such as `${CDISC_HOME}` or repository-relative paths. Keep machine-specific absolute paths out of committed configuration.

## Module Boundaries

Milestone 2 introduces the standards registry under `src/standards_driven_sdtm_adam/standards`. It loads and validates manifest schema and local availability. Runtime loading does not perform repeated source identity inspection or SHA256 recomputation.

Milestone 3 introduces standards discovery under `src/standards_driven_sdtm_adam/discovery`. It identifies which registered runtime-eligible standards should be consulted.

Milestone 4 introduces rule extraction under `src/standards_driven_sdtm_adam/extraction`. It reads discovered local standards and returns traceable evidence records.

Milestone 5 introduces feasibility assessment under `src/standards_driven_sdtm_adam/feasibility`.

Milestone 6 introduces preprocessing specifications under `src/standards_driven_sdtm_adam/preprocessing`.

Milestone 7 adds approved preprocessing execution.

Milestone 8 introduces ADaM derivation specifications.

Milestone 9 adds approved ADaM derivation execution.

Milestone 10 introduces independent validation under `src/standards_driven_sdtm_adam/validation`.

Milestone 10.5 finalizes standards intake and manifests as Developer Standards Setup.

Milestone 10.6 verifies local source identity as Developer Standards Setup.

Milestone 11 introduces evidence resolution and citation under `src/standards_driven_sdtm_adam/traceability`. It resolves existing evidence references from specification, derivation, and validation-facing decisions into deterministic citation records. It preserves source role boundaries and does not render reports.

Milestone 12 introduces reports under `src/standards_driven_sdtm_adam/reporting`. It presents existing pipeline outputs, independent validation results, and Milestone 11 evidence resolution results as deterministic machine-readable dictionaries, JSON, and Markdown. It does not run standards discovery, rule extraction, classification, derivation, validation, or evidence resolution.

Milestone 13 validates the complete Version 1 flow end to end. The minimal `V1Pipeline` facade in `src/standards_driven_sdtm_adam/pipeline.py` sequences existing milestone components and exposes every intermediate stage output for auditability. It is not a generic workflow engine and does not add transformation, validation, evidence resolution, or reporting logic beyond calling the existing milestone modules.

## Boundary Terms

- Execution Engine: "Build the approved output."
- Validation Engine: "Independently verify the output."
- Evidence Resolution and Citation Engine: "Resolve supporting evidence into deterministic citation records."
- Report Engine: "Present supplied pipeline, validation, traceability, and citation outputs for readers."
- V1 Pipeline Facade: "Run the Version 1 milestone sequence and expose stage outputs for integration validation."
- Developer Standards Setup: "Prepare and verify local standards inputs for development."
- Runtime Skill Workflow: "Use configured standards to perform discovery, evidence extraction, specification, execution, and validation."
