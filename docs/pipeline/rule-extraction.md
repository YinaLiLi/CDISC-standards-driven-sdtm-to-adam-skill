# Rule Extraction Engine

The Rule Extraction Engine answers:

> What relevant official CDISC guidance exists for this task?

It uses the Standards Discovery Engine to decide which registered standards may be consulted, then reads only applicable local standard documents that are enabled and available locally.

## Boundary

Standards Discovery answers:

> Which standards should be consulted?

Rule Extraction answers:

> What relevant evidence do those standards contain?

Specification and decision layers answer:

> How should that evidence be interpreted and implemented?

## Inputs

- Task or development intent
- Standards registry directory
- Registered local standards returned by discovery

The engine does not use web search as a substitute for missing local standards.

## Local Text Extraction

Supported local extraction paths:

- Plain text and Markdown files
- PDF files when `pypdf` is available

Plain text and Markdown extraction recognizes:

- Markdown headings and `Section ...` headings as verified section labels
- Explicit `[page n]` markers as verified page labels

PDF extraction uses the PDF page index as verified page metadata. It does not infer section numbers.

## Evidence Records

Each evidence record includes:

- `evidence_id`
- `standard_id`
- `standard_title`
- `version`
- `evidence_type`
- `section`
- `page`
- `short_quote`
- `source_local_path`
- `official_url`
- `search_context`
- `extraction_status`

Evidence types:

- `RULE`
- `GUIDANCE`
- `DEFINITION`
- `EXAMPLE`
- `CONTEXT`

Examples are classified as `EXAMPLE` and must not be represented as mandatory requirements.

Extraction statuses:

- `EXTRACTED`
- `AMBIGUOUS_EVIDENCE`
- `STANDARD_FILE_UNAVAILABLE`
- `TEXT_EXTRACTION_FAILED`

## Provenance Rules

The engine must never fabricate:

- Section labels
- Page numbers
- Quotes
- Rule language

If a section, page, or quote is unavailable, the field remains `null`.

Quotes are short traceability excerpts, not copied sections.

## Out Of Scope

Rule extraction does not implement:

- ADaM variable derivation
- SDTM preprocessing execution
- Feasibility assessment
- Report generation
- Machine learning
- Dashboards
- Define-XML
- Regulatory submission certification
- Decision classification such as `STANDARD_REQUIRED`, `STANDARD_GUIDED`, `STUDY_SPECIFIC`, or `DATA_ENGINEERING`
