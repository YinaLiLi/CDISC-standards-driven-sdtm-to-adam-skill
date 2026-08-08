# Standards Manifests

This directory registers CDISC standards and reference materials. Each `*.yaml` file follows the manifest schema and contains registration metadata only.

Manifest files must not contain PDF parsing rules, search indexes, derivation logic, validation rule extraction, or dataset processing code.

Required source metadata:

- `id`
- `title`
- `role`
- `version`
- `release_date`
- `official_url`
- `local_path`
- `original_filename`
- `sha256`
- `sha256_status`
- `verification_status`
- `indexed`
- `verified`
- `enabled`

Package references may also use:

- `package_url`
- `local_root`
- `members`

Use `null` for intentionally pending values, but keep the field present. Do not require both `version` and `release_date`; ADaM Controlled Terminology uses `release_date: "2026-07-11"` and no fabricated version number.

`verification_status` is Developer Standards Setup metadata, not a runtime gate. Runtime may use available configured sources even if status is `UNVERIFIED`.

Allowed `verification_status` values:

- `VERIFIED`
- `PARTIALLY_VERIFIED`
- `UNVERIFIED`
- `MISMATCH`
- `MISSING`
- `NOT_APPLICABLE`

Never mark a source `VERIFIED` from filename alone. Do not mark a source `MISMATCH` solely because a version or release date differs from an older manifest value; update descriptive metadata when the local file is a newer official release of the same source.

Allowed `role` values:

- `primary_standard`: official standards eligible for standards discovery, evidence extraction, citation, specification, and validation against official standards.
- `upstream_reference`: upstream SDTM references used only for appropriate SDTM source interpretation, SDTM domain/variable semantics, source-preserving preprocessing, and upstream traceability.
- `validation_reference`: examples or reference packages used only by validation/reference workflows.
- `future_scope`: disabled entries that are not supported in the current version.

`validation_reference` materials must not participate in primary rule discovery, produce `STANDARD_REQUIRED` evidence, override a primary standard, or introduce mandatory derivation logic.

`future_scope` materials must not participate in Version 1 runtime rule or evidence processing.

`SDTM_v2.0.pdf` and `SDTMIG v3.4.pdf` are upstream references only. They do not participate as primary ADaM normative evidence, produce `STANDARD_REQUIRED` ADaM evidence, perform Raw-to-SDTM mapping, perform SDTM mapping, or perform SDTM conformance transformation.

Local paths must be portable and must not require machine-specific absolute paths. Prefer `${CDISC_HOME}` or repository-relative paths. CDISC source files are referenced by manifest IDs and original filenames; do not rename, flatten, or normalize source filenames.

The simple local convention is to keep official standards under a local `standards/` folder and example or comparison packages under a local `examples/` folder, both ignored from Git when they contain licensed source files. Source roles belong in manifests rather than directory names.
