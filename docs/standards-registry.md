# Standards Registry

The standards registry records configured CDISC standards and reference materials. It supports both Developer Standards Setup and Runtime Skill Workflow, but these are separate uses.

## Runtime Use

Runtime loads configured manifests, resolves local availability, and provides metadata to discovery and extraction. Runtime does not require users to perform identity verification, SHA256 recomputation, release/version confirmation, standards intake, or manifest maintenance.

Configured entries are usable when the registered source is available. Missing or unreadable sources still fail safely.

## Developer Standards Setup

Developer Standards Setup may inspect local source content, compute SHA256, check release/version metadata, and update manifests. These checks are explicit setup utilities, not normal runtime work.

If a developer replaces a local standard with a newer official release, setup should update descriptive manifest metadata and recompute SHA256. A version/release difference alone is not a runtime compatibility failure.

`MISMATCH` is reserved for cases where the local file is actually a different standard or reference than the manifest describes.

## Manifest Shape

```yaml
schema_version: 1
standard:
  id: adamig
  title: ADaM Implementation Guide
  role: primary_standard
  version: "1.3"
  release_date: null
  official_url: https://www.cdisc.org/system/files/members/standard/foundational/ADaMIG_v1.3.pdf
  package_url: null
  local_path: ../../docs/standards/ADaM/standards/ADaMIG_v1.3.pdf
  local_root: null
  original_filename: ADaMIG_v1.3.pdf
  sha256: <64-character digest>
  sha256_status: PRESENT
  verification_status: VERIFIED
  indexed: false
  verified: true
  enabled: true
```

## Source Roles

- `primary_standard`: eligible for runtime Standards Discovery, Evidence Extraction, Citation, Specification, and validation against official standards.
- `upstream_reference`: eligible only where appropriate for upstream SDTM interpretation and source-preserving preprocessing.
- `validation_reference`: eligible for validation/reference workflows only.
- `future_scope`: disabled entry for out-of-scope future work.

Validation references must not participate in primary rule discovery, produce `STANDARD_REQUIRED` evidence, override primary standards, or introduce mandatory derivation logic.

## Verification Status

Verification status is setup metadata:

- `VERIFIED`: the local file explicitly supports the declared identity and version or release.
- `PARTIALLY_VERIFIED`: identity is verified but version/release cannot be conclusively confirmed, or the reverse.
- `UNVERIFIED`: the source does not expose enough reliable information to confirm identity or version.
- `MISMATCH`: observed source information indicates a different standard/reference.

Runtime does not require `VERIFIED` status before normal use.

## Repository Safety

Do not copy licensed CDISC source files into Git-managed source directories for redistribution. Local paths must be portable. Machine-specific absolute paths belong only in ignored local configuration.
