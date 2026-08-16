# Standards-Driven SDTM-to-ADaM Pipeline Report

Overall status: `PASS`

## Preprocessing Operations

| Target | Operation | Basis |
| --- | --- | --- |
| AE.AESTDTC | Parse source date text into a machine-readable representation while preserving the original SDTM value. | ADaM Basic Data Structure for Time-to-Event Analyses page 8; ADaM Basic Data Structure for Time-to-Event Analyses page 10; ADaM Basic Data Structure for Time-to-Event Analyses page 6; ADaM Basic Data Structure for Time-to-Event Analyses page 29 |
| AE.AETERM | Normalize leading, trailing, or repeated technical whitespace for stable joins and checks while preserving clinical meaning. | Technical source-preserving operation |
| AE.USUBJID | Normalize leading, trailing, or repeated technical whitespace for stable joins and checks while preserving clinical meaning. | Technical source-preserving operation |
| DM.USUBJID | Normalize leading, trailing, or repeated technical whitespace for stable joins and checks while preserving clinical meaning. | Technical source-preserving operation |
| DS.DSSTDTC | Parse source date text into a machine-readable representation while preserving the original SDTM value. | ADaM Basic Data Structure for Time-to-Event Analyses page 8; ADaM Basic Data Structure for Time-to-Event Analyses page 10; ADaM Basic Data Structure for Time-to-Event Analyses page 6; ADaM Basic Data Structure for Time-to-Event Analyses page 29 |
| DS.DSDECOD | Normalize leading, trailing, or repeated technical whitespace for stable joins and checks while preserving clinical meaning. | Technical source-preserving operation |
| DS.USUBJID | Normalize leading, trailing, or repeated technical whitespace for stable joins and checks while preserving clinical meaning. | Technical source-preserving operation |
| EX.EXSTDTC | Parse source date text into a machine-readable representation while preserving the original SDTM value. | ADaM Basic Data Structure for Time-to-Event Analyses page 8; ADaM Basic Data Structure for Time-to-Event Analyses page 10; ADaM Basic Data Structure for Time-to-Event Analyses page 6; ADaM Basic Data Structure for Time-to-Event Analyses page 29 |
| EX.EXTRT | Normalize leading, trailing, or repeated technical whitespace for stable joins and checks while preserving clinical meaning. | Technical source-preserving operation |
| EX.USUBJID | Normalize leading, trailing, or repeated technical whitespace for stable joins and checks while preserving clinical meaning. | Technical source-preserving operation |
| LB.LBDTC | Parse source date text into a machine-readable representation while preserving the original SDTM value. | ADaM Basic Data Structure for Time-to-Event Analyses page 8; ADaM Basic Data Structure for Time-to-Event Analyses page 10; ADaM Basic Data Structure for Time-to-Event Analyses page 6; ADaM Basic Data Structure for Time-to-Event Analyses page 29 |
| LB.LBORRES | Parse numeric-looking source values into technical numeric form for downstream checks without changing the source value. | Technical source-preserving operation |
| LB.LBSTRESN | Parse numeric-looking source values into technical numeric form for downstream checks without changing the source value. | Technical source-preserving operation |
| LB.LBORRES | Normalize leading, trailing, or repeated technical whitespace for stable joins and checks while preserving clinical meaning. | Technical source-preserving operation |
| LB.LBTESTCD | Normalize leading, trailing, or repeated technical whitespace for stable joins and checks while preserving clinical meaning. | Technical source-preserving operation |
| LB.USUBJID | Normalize leading, trailing, or repeated technical whitespace for stable joins and checks while preserving clinical meaning. | Technical source-preserving operation |
| SV.SVSTDTC | Parse source date text into a machine-readable representation while preserving the original SDTM value. | ADaM Basic Data Structure for Time-to-Event Analyses page 8; ADaM Basic Data Structure for Time-to-Event Analyses page 10; ADaM Basic Data Structure for Time-to-Event Analyses page 6; ADaM Basic Data Structure for Time-to-Event Analyses page 29 |
| SV.USUBJID | Normalize leading, trailing, or repeated technical whitespace for stable joins and checks while preserving clinical meaning. | Technical source-preserving operation |

## ADaM Derivation Operations

| Target | Operation | Basis |
| --- | --- | --- |
| ADAE.ASTDT | Specify deterministic date parsing from AE.AESTDTC; do not impute partial or missing dates. | Technical derivation from source data |
| ADAE.TRTEMFL | Treatment-emergent AEs start on or after first exposure through 30 days after last exposure. | Study decision |
| ADLB.AVAL | Use LB.LBSTRESN when available, with LB.LBORRES retained as source traceability. | No valid standard evidence resolved |
| ADLB.AVISIT | Adapt example visit timing logic only as a documented specification; do not treat example text as a CDISC requirement. | Study decision |
| ADLB.PARAMCD | Specify parameter code from LB.LBTESTCD where supported by the source laboratory record. | No valid standard evidence resolved |
| ADSL.SAFFL | Safety Population includes subjects with at least one EX record. | Study decision |
| ADSL.TRTEDT | Specify last treatment exposure date from EX.EXENDTC; do not execute derivation here. | No valid standard evidence resolved |
| ADSL.TRTSDT | Specify first treatment exposure date from EX.EXSTDTC; do not execute derivation here. | No valid standard evidence resolved |
| ADSL.USUBJID | Carry DM.USUBJID into ADSL as the subject identifier. | ADaM Basic Data Structure for Time-to-Event Analyses page 6; ADaM Basic Data Structure for Time-to-Event Analyses page 7 |
| ADTTE.ADT | Specify event or censoring date from source events according to documented study rules. | Study decision |
| ADTTE.AVAL | Calculate duration only after STARTDT, ADT, event rules, censoring rules, and time scale are specified. | Study decision |
| ADTTE.CNSR | Classify event versus censoring using the documented study-specific event and censoring rules. | Study decision |
| ADTTE.STARTDT | Specify time-to-event origin from treatment start date or another explicitly documented study origin. | Study decision |
