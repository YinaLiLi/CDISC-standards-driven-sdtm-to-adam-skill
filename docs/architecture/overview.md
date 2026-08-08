# Architecture

The package has two separate operating modes: the runtime Skill workflow and maintainer standards setup.

## Runtime Workflow

Runtime users provide existing SDTM datasets, research objectives, study decisions when needed, and CDISC authentication when required for authorized standards acquisition.

```text
Standards Discovery
  -> Rule Extraction
  -> Feasibility Assessment
  -> Preprocessing Specification
  -> Preprocessing Execution
  -> ADaM Derivation Specification
  -> ADaM Derivation
  -> Independent Validation
  -> Evidence Resolution
  -> Reporting
```

Specification is never skipped. Runtime loading uses configured manifests and available local sources; it does not require users to perform standards intake, source identity verification, release confirmation, SHA256 recomputation, or manifest maintenance.

When required CDISC sources are missing, first-run acquisition uses one browser-authenticated CDISC session, stores validated files in the configured local cache, and reuses that cache on subsequent runs.

## Source Roles

The manifest source roles are:

- `primary_standard`
- `upstream_reference`
- `validation_reference`
- `future_scope`

Primary ADaM standards are authoritative for ADaM derivation rules. `validation_reference` entries are excluded from primary discovery and cannot produce `STANDARD_REQUIRED` evidence. `future_scope` entries are excluded from Version 1 runtime rule and evidence processing.

`SDTM_v2.0.pdf` and `SDTMIG v3.4.pdf` are `upstream_reference` sources. They support interpretation of existing SDTM domain and variable semantics, source-preserving preprocessing decisions, and upstream traceability where appropriate. They do not participate as primary ADaM normative evidence, perform Raw-to-SDTM mapping, perform SDTM mapping, perform SDTM conformance transformation, or produce `STANDARD_REQUIRED` ADaM evidence.

## Module Boundaries

- `standards`: manifest loading, local availability checks, authorized first-run acquisition, and source validation.
- `discovery`: runtime selection of eligible standards for a requested task.
- `extraction`: evidence extraction from discovered local standards.
- `feasibility`: objective support checks against provided SDTM datasets.
- `preprocessing`: source-preserving preprocessing specifications and approved execution.
- `derivation`: ADaM derivation specifications and approved execution for supported outputs.
- `validation`: independent structural, logical, and traceability validation.
- `traceability`: deterministic evidence and citation resolution.
- `reporting`: deterministic dictionary, JSON, and Markdown reports from supplied outputs.
- `pipeline`: the Version 1 facade that sequences the implemented workflow and exposes intermediate results for auditability.

## Local Source Safety

CDISC source files are not redistributed in this repository. Do not commit downloaded standards, examples, packages, browser state, credentials, or local run artifacts. Keep local paths portable and avoid machine-specific absolute paths in committed configuration.
