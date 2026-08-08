# Standards Reference Index

Version 1 primary ADaM standards are registered through `config/standards` manifests. Runtime discovery uses manifest metadata and source roles, then rule extraction reads locally available configured files.

## Primary Standards

- ADaM Model
- Important Considerations When Using ADaM
- ADaM Implementation Guide
- ADaM OCCDS Implementation Guide
- ADaM BDS Time-to-Event Guide
- ADaM Metadata Submission Guidelines
- ADaM Controlled Terminology
- ADaM Conformance Rules

## Upstream References

- SDTM Model
- SDTM Implementation Guide

These are upstream references for source-preserving SDTM interpretation only. They do not add Raw-to-SDTM mapping or SDTM conformance transformation support.

`SDTM_v2.0.pdf` and `SDTMIG v3.4.pdf` support interpretation of existing SDTM input datasets, SDTM domain/variable semantics, source-preserving preprocessing decisions, and upstream traceability where appropriate. They do not participate as primary ADaM normative evidence and cannot produce `STANDARD_REQUIRED` ADaM evidence.

## Validation References

Examples and reference packages may support regression testing, structural comparison, implementation comparison, and validation support. They do not participate in primary rule discovery and cannot produce `STANDARD_REQUIRED` evidence.

## Future Scope

Define-XML and SDRG entries are disabled future-scope entries and do not participate in Version 1 runtime rule or evidence processing.
