from standards_driven_sdtm_adam.extraction.model import EvidenceRecord
from standards_driven_sdtm_adam.feasibility import FeasibilityAssessor
from standards_driven_sdtm_adam.preprocessing import PreprocessingSpecifier


def _sdtm_data():
    return {
        "DM": [{"USUBJID": " 01 "}],
        "AE": [{"USUBJID": "01", "AETERM": " Headache ", "AESTDTC": "2024-01-02"}],
        "LB": [{"USUBJID": "01", "LBTESTCD": "ALT", "LBORRES": " 70 ", "LBDTC": "2024-01-01"}],
        "DS": [{"USUBJID": "01", "DSDECOD": "COMPLETED", "DSSTDTC": "2024-02-01"}],
        "EX": [{"USUBJID": "01", "EXTRT": "Drug", "EXSTDTC": "2024-01-01"}],
        "SV": [{"USUBJID": "01", "SVSTDTC": "2024-01-01"}],
    }


def _feasibility(data=None):
    return FeasibilityAssessor().assess(
        ["Are abnormal laboratory values associated with adverse events?"],
        data or _sdtm_data(),
    )


def _evidence(evidence_id="adamig:1", quote="Date guidance may be consulted for DTC values."):
    return EvidenceRecord(
        evidence_id=evidence_id,
        standard_id="adamig",
        standard_title="ADaM Implementation Guide",
        version="1.3",
        evidence_type="GUIDANCE",
        section="Dates",
        page=12,
        short_quote=quote,
        source_local_path="adamig.txt",
        official_url=None,
        search_context="metadata_search:date, dtc",
        extraction_status="EXTRACTED",
    )


def _specs(requested_operations=(), evidence=()):
    return PreprocessingSpecifier().specify(
        _sdtm_data(),
        _feasibility(),
        evidence=evidence,
        requested_operations=requested_operations,
    ).operations


def test_standard_guided_date_handling_attaches_evidence():
    operations = _specs(evidence=(_evidence(),))
    date_specs = [spec for spec in operations if spec.operation == "deterministic_date_parsing"]

    assert date_specs
    assert all(spec.classification == "STANDARD_GUIDED" for spec in date_specs)
    assert all(spec.evidence_references == ("adamig:1",) for spec in date_specs)
    assert all(spec.source_preserving for spec in date_specs)
    assert all(not spec.clinical_meaning_changed for spec in date_specs)


def test_data_engineering_numeric_parsing_without_cdisc_claim():
    operations = _specs()
    numeric_specs = [spec for spec in operations if spec.operation == "deterministic_numeric_parsing"]

    assert len(numeric_specs) == 1
    assert numeric_specs[0].dataset == "LB"
    assert numeric_specs[0].variable == "LBORRES"
    assert numeric_specs[0].classification == "DATA_ENGINEERING"
    assert numeric_specs[0].evidence_references == ()


def test_neutral_whitespace_handling_is_source_preserving():
    operations = _specs()
    whitespace_specs = [spec for spec in operations if spec.operation == "neutral_whitespace_normalization"]

    assert whitespace_specs
    assert all(spec.classification == "DATA_ENGINEERING" for spec in whitespace_specs)
    assert all(spec.source_preserving for spec in whitespace_specs)
    assert all(spec.implementation_allowed for spec in whitespace_specs)


def test_prohibited_clinical_value_imputation_is_blocked():
    operations = _specs(requested_operations=("Impute missing clinical values in LBORRES",))
    blocked = [spec for spec in operations if spec.operation == "impute_clinical_value"]

    assert len(blocked) == 1
    assert blocked[0].classification == "UNSUPPORTED"
    assert not blocked[0].implementation_allowed
    assert blocked[0].clinical_meaning_changed


def test_prohibited_silent_record_deletion_is_blocked():
    operations = _specs(requested_operations=("Delete records from AE with missing AETERM",))
    blocked = [spec for spec in operations if spec.operation == "silent_record_deletion"]

    assert len(blocked) == 1
    assert blocked[0].classification == "UNSUPPORTED"
    assert not blocked[0].source_preserving
    assert not blocked[0].implementation_allowed


def test_prohibited_adam_variable_derivation_during_preprocessing_is_blocked():
    operations = _specs(requested_operations=("Create ADaM analysis variable TRTEMFL during preprocessing",))
    blocked = [spec for spec in operations if spec.operation == "adam_variable_derivation"]

    assert len(blocked) == 1
    assert blocked[0].classification == "UNSUPPORTED"
    assert blocked[0].variable == "TRTEMFL"
    assert not blocked[0].implementation_allowed


def test_missing_evidence_does_not_fabricate_standard_requirement():
    operations = _specs()
    date_specs = [spec for spec in operations if spec.operation == "deterministic_date_parsing"]

    assert date_specs
    assert all(spec.classification == "DATA_ENGINEERING" for spec in date_specs)
    assert all(spec.evidence_references == () for spec in date_specs)


def test_correct_decision_classification_for_examples_is_not_required():
    example = _evidence("ct:example", "Example: DTC date values may be shown for illustration.")
    operations = _specs(evidence=(example,))
    date_specs = [spec for spec in operations if spec.operation == "deterministic_date_parsing"]

    assert date_specs
    assert all(spec.classification == "STANDARD_GUIDED" for spec in date_specs)
    assert all(spec.classification != "STANDARD_REQUIRED" for spec in date_specs)


def test_source_preserving_behavior_for_allowed_operations():
    allowed = [spec for spec in _specs() if spec.implementation_allowed]

    assert allowed
    assert all(spec.source_preserving for spec in allowed)
    assert all(not spec.clinical_meaning_changed for spec in allowed)
    assert all("Verify no records are deleted." in spec.validation_plan for spec in allowed)
