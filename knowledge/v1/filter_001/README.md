# FILTER-001 SDTM-to-ADaM Transfer Relevance Filter

FILTER-001 was applied to all canonical reconstructed candidate rules. The pass classifies every candidate as `KEEP_RELEVANT`, `REMOVE_NON_RELEVANT`, or `REVIEW_AMBIGUOUS`. `REVIEW_AMBIGUOUS` candidates remain in the canonical rule catalog.

## Counts

- Before: 2534
- KEEP_RELEVANT: 1409
- REMOVE_NON_RELEVANT: 1071
- REVIEW_AMBIGUOUS: 54
- After: 1463

## KEEP_RELEVANT Reasons

- `adam_output`: 1
- `baseline_treatment_datetime`: 2
- `dataset_structure_name_label_grain_keys`: 1071
- `event_or_censor_logic`: 1
- `mapping_derivation_calculation`: 1
- `sdtm_source_or_adam_output`: 2
- `traceability_origin_lineage`: 115
- `variable_requirement_or_applicability`: 216

## REMOVE_NON_RELEVANT Reasons

- `document_noise_header_footer_page_date`: 31
- `legal_patent_license_disclaimer`: 4
- `publication_management`: 3
- `semantic_duplicate_requirement`: 1033

## REVIEW_AMBIGUOUS Reasons

- `example_may_contain_derivation_logic`: 51
- `example_only_atomic_requirement`: 3

## Shards

| Shard | Before | KEEP | REMOVE | AMBIGUOUS | After |
|---|---:|---:|---:|---:|---:|
| adam-bds-tte.json | 39 | 6 | 32 | 1 | 7 |
| adam-common-statistical-analysis-examples.json | 36 | 0 | 1 | 35 | 35 |
| adam-conformance-rules.json | 1963 | 930 | 1033 | 0 | 930 |
| adam-ct.json | 3 | 3 | 0 | 0 | 3 |
| adam-important-considerations.json | 1 | 1 | 0 | 0 | 1 |
| adam-model.json | 11 | 10 | 1 | 0 | 10 |
| adam-msg.json | 2 | 2 | 0 | 0 | 2 |
| adam-occds.json | 32 | 32 | 0 | 0 | 32 |
| adam-traceability-examples.json | 17 | 0 | 1 | 16 | 16 |
| adamig.json | 45 | 44 | 0 | 1 | 45 |
| sdtm-model.json | 98 | 98 | 0 | 0 | 98 |
| sdtmig.json | 287 | 283 | 3 | 1 | 284 |
