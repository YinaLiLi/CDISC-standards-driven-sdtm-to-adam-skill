from decimal import Decimal

from standards_driven_sdtm_adam.preprocessing import (
    PreprocessingExecutionEngine,
    PreprocessingOperationSpec,
    PreprocessingSpecification,
)


def _spec(
    operation,
    *,
    operation_id=None,
    dataset="LB",
    variable="LBORRES",
    classification="DATA_ENGINEERING",
    implementation_allowed=True,
    source_preserving=True,
    clinical_meaning_changed=False,
    evidence_references=("adamig:1",),
):
    return PreprocessingOperationSpec(
        operation_id=operation_id or f"SPEC-{operation}",
        dataset=dataset,
        variable=variable,
        operation=operation,
        purpose="test operation",
        classification=classification,
        evidence_references=evidence_references,
        source_preserving=source_preserving,
        clinical_meaning_changed=clinical_meaning_changed,
        implementation_allowed=implementation_allowed,
        validation_plan=("Verify source value is retained unchanged.",),
        notes=(),
    )


def _data():
    return {
        "AE": [
            {"USUBJID": "01", "AETERM": " Headache ", "AESTDTC": "2024-01-02"},
            {"USUBJID": "02", "AETERM": "Nausea", "AESTDTC": "not-a-date"},
        ],
        "LB": [
            {"USUBJID": "01", "LBTESTCD": "ALT", "LBORRES": " 70 ", "LBDTC": "2024-01-01"},
            {"USUBJID": "02", "LBTESTCD": "AST", "LBORRES": "abc", "LBDTC": ""},
        ],
    }


def _execute(specs, data=None, requested_operation_ids=None):
    return PreprocessingExecutionEngine().execute(
        data or _data(),
        PreprocessingSpecification(tuple(specs)),
        requested_operation_ids=requested_operation_ids,
    )


def test_approved_date_parsing_retains_original_and_adds_technical_fields():
    result = _execute([
        _spec("deterministic_date_parsing", dataset="AE", variable="AESTDTC"),
    ])

    ae = result.processed_datasets["AE"]
    assert ae[0]["AESTDTC"] == "2024-01-02"
    assert ae[0]["__AESTDTC_PARSED"] == "2024-01-02"
    assert ae[1]["AESTDTC"] == "not-a-date"
    assert ae[1]["__AESTDTC_PARSED"] is None
    assert ae[1]["__AESTDTC_PARSE_STATUS"] == "UNPARSABLE"
    record = result.execution_records[0]
    assert record.status == "EXECUTED"
    assert record.affected_record_count == 1
    assert record.input_record_count == record.output_record_count == 2
    assert record.validation_status == "PASSED_WITH_WARNINGS"


def test_approved_numeric_parsing_retains_original_and_flags_failures():
    result = _execute([
        _spec("deterministic_numeric_parsing", dataset="LB", variable="LBORRES"),
    ])

    lb = result.processed_datasets["LB"]
    assert lb[0]["LBORRES"] == " 70 "
    assert lb[0]["__LBORRES_NUM"] == Decimal("70")
    assert lb[1]["LBORRES"] == "abc"
    assert lb[1]["__LBORRES_NUM"] is None
    assert lb[1]["__LBORRES_NUM_PARSE_STATUS"] == "UNPARSABLE"
    assert result.execution_records[0].affected_record_count == 1


def test_whitespace_normalization_adds_normalized_copy_only():
    result = _execute([
        _spec("neutral_whitespace_normalization", dataset="AE", variable="AETERM"),
    ])

    ae = result.processed_datasets["AE"]
    assert ae[0]["AETERM"] == " Headache "
    assert ae[0]["__AETERM_NORM"] == "Headache"
    assert ae[0]["__AETERM_NORM_STATUS"] == "NORMALIZED"
    assert ae[1]["AETERM"] == "Nausea"
    assert ae[1]["__AETERM_NORM_STATUS"] == "UNCHANGED"


def test_missingness_flags_are_created_without_deleting_records():
    result = _execute([
        _spec("missingness_quality_flag", dataset="LB", variable=None),
    ])

    lb = result.processed_datasets["LB"]
    assert len(lb) == 2
    assert lb[1]["__SOURCE_MISSINGNESS_FLAG"] is True
    assert "LBDTC" in lb[1]["__SOURCE_MISSING_VARIABLES"]
    record = result.execution_records[0]
    assert record.input_record_count == record.output_record_count == 2


def test_quality_flag_creation_uses_same_safe_flag_behavior():
    result = _execute([
        _spec("quality_flag_creation", dataset="LB", variable=None),
    ])

    assert result.processed_datasets["LB"][1]["__SOURCE_MISSINGNESS_FLAG"] is True
    assert result.execution_records[0].status == "EXECUTED"


def test_rejects_unsupported_operation_spec():
    result = _execute([
        _spec(
            "impute_clinical_value",
            classification="UNSUPPORTED",
            implementation_allowed=False,
            source_preserving=False,
            clinical_meaning_changed=True,
        ),
    ])

    record = result.execution_records[0]
    assert record.status == "REJECTED"
    assert record.validation_status == "NOT_RUN"
    assert "__LBORRES_NUM" not in result.processed_datasets["LB"][0]


def test_unapproved_operation_id_is_rejected_and_not_inferred():
    result = _execute(
        [_spec("deterministic_numeric_parsing", operation_id="APPROVED-1")],
        requested_operation_ids=("MISSING-OP",),
    )

    assert len(result.execution_records) == 1
    assert result.execution_records[0].operation_id == "MISSING-OP"
    assert result.execution_records[0].status == "REJECTED"
    assert "__LBORRES_NUM" not in result.processed_datasets["LB"][0]


def test_preserves_original_input_data():
    source = _data()
    before = repr(source)
    result = _execute([
        _spec("neutral_whitespace_normalization", dataset="AE", variable="AETERM"),
    ], data=source)

    assert repr(source) == before
    assert "__AETERM_NORM" not in source["AE"][0]
    assert "__AETERM_NORM" in result.processed_datasets["AE"][0]


def test_record_count_preservation_across_multiple_operations():
    result = _execute([
        _spec("deterministic_date_parsing", dataset="AE", variable="AESTDTC"),
        _spec("deterministic_numeric_parsing", dataset="LB", variable="LBORRES"),
        _spec("neutral_whitespace_normalization", dataset="AE", variable="AETERM"),
    ])

    for record in result.execution_records:
        assert record.input_record_count == record.output_record_count
        assert record.validation_status in {"PASSED", "PASSED_WITH_WARNINGS"}


def test_execution_traceability_links_to_spec_classification_and_evidence():
    spec = _spec(
        "deterministic_date_parsing",
        dataset="AE",
        variable="AESTDTC",
        classification="STANDARD_GUIDED",
        evidence_references=("adamig:date",),
    )
    result = _execute([spec])
    record = result.execution_records[0]

    assert record.operation_id == spec.operation_id
    assert record.classification == "STANDARD_GUIDED"
    assert record.source_reference["operation_id"] == spec.operation_id
    assert record.source_reference["classification"] == "STANDARD_GUIDED"
    assert record.source_reference["evidence_references"] == ("adamig:date",)
