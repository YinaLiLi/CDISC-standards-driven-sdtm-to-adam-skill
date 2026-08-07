from dataclasses import replace
from copy import deepcopy

from standards_driven_sdtm_adam.derivation import (
    AdamDerivationEngine,
    AdamDerivationExecutionRecord,
    AdamDerivationSpecification,
    AdamDerivationSpecifier,
    AdamValidationEngine,
    AdamVariableSpecification,
    StudyDecision,
)
from standards_driven_sdtm_adam.extraction.model import EvidenceRecord
from standards_driven_sdtm_adam.feasibility import FeasibilityAssessor
from standards_driven_sdtm_adam.preprocessing.model import (
    PreprocessingOperationSpec,
    PreprocessingSpecification,
)
from standards_driven_sdtm_adam.preprocessing.execution import PreprocessingExecutionRecord


def _sdtm_data():
    return {
        "DM": [
            {"STUDYID": "S1", "USUBJID": "01", "AGE": "64", "SEX": "F"},
            {"STUDYID": "S1", "USUBJID": "02", "AGE": "59", "SEX": "M"},
        ],
        "EX": [
            {"USUBJID": "01", "EXSTDTC": "2024-01-01", "EXENDTC": "2024-01-14"},
            {"USUBJID": "02", "EXSTDTC": "2024-01-03", "EXENDTC": "2024-01-17"},
        ],
        "AE": [
            {"USUBJID": "01", "AESEQ": "1", "AETERM": "Headache", "AESTDTC": "2024-01-03"},
            {"USUBJID": "02", "AESEQ": "1", "AETERM": "Nausea", "AESTDTC": "2024-02-20"},
        ],
        "LB": [
            {"USUBJID": "01", "LBSEQ": "1", "LBTESTCD": "ALT", "LBORRES": "70", "LBSTRESN": "70"},
            {"USUBJID": "02", "LBSEQ": "1", "LBTESTCD": "ALT", "LBORRES": "42", "LBSTRESN": "42"},
        ],
        "DS": [
            {"USUBJID": "01", "DSDECOD": "DEATH", "DSSTDTC": "2024-02-01"},
            {"USUBJID": "02", "DSDECOD": "COMPLETED", "DSSTDTC": "2024-03-01"},
        ],
    }


def _feasibility(data=None):
    return FeasibilityAssessor().assess(
        ["Evaluate adverse events, laboratory values, and time-to-event outcomes."],
        data or _sdtm_data(),
    )


def _decision(decision_id, value):
    return StudyDecision(
        decision_id=decision_id,
        question=f"Resolved {decision_id}",
        affected_datasets=(),
        affected_variables=(),
        required_before_implementation=True,
        status="PROVIDED",
        value=value,
    )


def _evidence(evidence_id):
    return EvidenceRecord(
        evidence_id=evidence_id,
        standard_id="adamig",
        standard_title="ADaM Implementation Guide",
        version="1.3",
        evidence_type="GUIDANCE",
        section="Validation",
        page=1,
        short_quote="Relevant ADaM validation evidence.",
        source_local_path="adamig.txt",
        official_url=None,
        search_context="validation",
        extraction_status="EXTRACTED",
    )


def _specification(data=None, study_decisions=(), variables=()):
    full = AdamDerivationSpecifier().specify(
        data or _sdtm_data(),
        _feasibility(data),
        study_decisions=study_decisions,
    )
    if not variables:
        return full
    return replace(
        full,
        variable_specs=tuple(
            spec
            for spec in full.variable_specs
            if f"{spec.dataset}.{spec.variable}" in variables
        ),
    )


def _var_spec(dataset, variable, **overrides):
    defaults = {
        "specification_id": f"ADAM-SPEC-{dataset}-{variable}",
        "dataset": dataset,
        "variable": variable,
        "label": variable,
        "purpose": f"Derive {dataset}.{variable}.",
        "source_domains": (),
        "source_variables": (),
        "derivation_logic": "Approved validation test derivation.",
        "dependencies": (),
        "classification": "DATA_ENGINEERING",
        "evidence_references": (),
        "user_defined_inputs": (),
        "assumptions": (),
        "validation_plan": ("Independently validate output.",),
        "implementation_allowed": True,
        "unresolved_issues": (),
    }
    defaults.update(overrides)
    return AdamVariableSpecification(**defaults)


def _custom_specification(specs):
    return AdamDerivationSpecification(
        dataset_specs=(),
        variable_specs=tuple(specs),
        unresolved_decisions=(),
        traceability={},
    )


def _execute(specification, decisions=()):
    return AdamDerivationEngine().execute(_sdtm_data(), specification, study_decisions=decisions)


def _validate(specification, execution, **overrides):
    args = {
        "source_sdtm_datasets": _sdtm_data(),
        "adam_specification": specification,
        "adam_datasets": execution.datasets,
        "derivation_execution_records": execution.execution_records,
        "study_decisions": (),
        "evidence": (),
    }
    args.update(overrides)
    return AdamValidationEngine().validate(**args)


def _check(result, check_id, dataset=None, variable=None):
    matches = [
        validation
        for validation in result.validation_results
        if validation.check_id == check_id
        and (dataset is None or validation.dataset == dataset)
        and (variable is None or validation.variable == variable)
    ]
    assert len(matches) == 1
    return matches[0]


def test_valid_adsl_structure_passes():
    spec = _specification(variables=("ADSL.USUBJID", "ADSL.TRTSDT"))
    execution = _execute(spec)

    result = _validate(spec, execution)

    assert _check(result, "STRUCTURE-ADSL-USUBJID-GRAIN", "ADSL").status == "PASS"
    assert _check(result, "STRUCTURE-REQUIRED-USUBJID", "ADSL").status == "PASS"


def test_duplicate_adsl_subject_fails():
    spec = _specification(variables=("ADSL.USUBJID",))
    execution = _execute(spec)
    adam = dict(execution.datasets)
    adam["ADSL"] = execution.datasets["ADSL"] + ({"USUBJID": "01"},)

    result = _validate(spec, execution, adam_datasets=adam)

    check = _check(result, "STRUCTURE-ADSL-USUBJID-GRAIN", "ADSL")
    assert check.status == "FAIL"
    assert check.severity == "ERROR"


def test_valid_adae_dependency_logic_passes():
    decision = _decision("DECISION-TREATMENT-EMERGENT-WINDOW", "window=end plus 30 days")
    spec = _specification(
        study_decisions=(decision,),
        variables=("ADSL.TRTSDT", "ADSL.TRTEDT", "ADAE.ASTDT", "ADAE.TRTEMFL"),
    )
    execution = _execute(spec, decisions=(decision,))

    result = _validate(spec, execution, study_decisions=(decision,))

    assert _check(result, "LOGIC-ADAE-TRTEMFL", "ADAE", "TRTEMFL").status == "PASS"


def test_incorrect_treatment_emergent_flag_is_detected():
    decision = _decision("DECISION-TREATMENT-EMERGENT-WINDOW", "window=end plus 30 days")
    spec = _specification(
        study_decisions=(decision,),
        variables=("ADSL.TRTSDT", "ADSL.TRTEDT", "ADAE.ASTDT", "ADAE.TRTEMFL"),
    )
    execution = _execute(spec, decisions=(decision,))
    adam = dict(execution.datasets)
    adae = [dict(record) for record in execution.datasets["ADAE"]]
    adae[1]["TRTEMFL"] = "Y"
    adam["ADAE"] = tuple(adae)

    result = _validate(spec, execution, adam_datasets=adam, study_decisions=(decision,))

    assert _check(result, "LOGIC-ADAE-TRTEMFL", "ADAE", "TRTEMFL").status == "FAIL"


def test_valid_adlb_derivation_passes():
    spec = _specification(variables=("ADLB.PARAMCD", "ADLB.AVAL"))
    execution = _execute(spec)

    result = _validate(spec, execution)

    assert _check(result, "LOGIC-ADLB-AVAL", "ADLB", "AVAL").status == "PASS"


def test_incorrect_baseline_dependent_value_is_detected():
    spec = _custom_specification(
        (
            _var_spec(
                "ADLB",
                "BASE",
                source_domains=("LB",),
                source_variables=("LB.LBSTRESN",),
                classification="STUDY_SPECIFIC",
                user_defined_inputs=("baseline_definition",),
                implementation_allowed=False,
            ),
        )
    )
    execution = _execute(spec)
    adam = {"ADLB": ({"BASE": 70.0}, {"BASE": 42.0})}

    result = _validate(spec, execution, adam_datasets=adam)

    assert _check(result, "LOGIC-BLOCKED-VARIABLE-NOT-POPULATED", "ADLB", "BASE").status == "FAIL"


def test_valid_adtte_event_censor_logic_passes():
    decision = _decision(
        "DECISION-TTE-EVENT-CENSOR",
        "origin=EX.EXSTDTC; event_terms=DEATH; censor_terms=COMPLETED; time_scale=days",
    )
    specs = (
        _var_spec("ADTTE", "STARTDT", source_domains=("EX",), source_variables=("EX.EXSTDTC",)),
        _var_spec("ADTTE", "ADT", source_domains=("DS",), source_variables=("DS.DSSTDTC",), user_defined_inputs=("event_definition", "censoring_rules")),
        _var_spec("ADTTE", "CNSR", source_domains=("DS",), source_variables=("DS.DSDECOD", "DS.DSSTDTC"), user_defined_inputs=("event_definition", "censoring_rules")),
        _var_spec("ADTTE", "AVAL", source_domains=("DS", "EX"), source_variables=("DS.DSSTDTC", "EX.EXSTDTC"), dependencies=("ADTTE.STARTDT", "ADTTE.ADT")),
    )
    spec = _custom_specification(specs)
    execution = _execute(spec, decisions=(decision,))

    result = _validate(spec, execution, study_decisions=(decision,))

    assert _check(result, "LOGIC-ADTTE-CNSR", "ADTTE", "CNSR").status == "PASS"


def test_incorrect_adtte_event_censor_value_is_detected():
    decision = _decision(
        "DECISION-TTE-EVENT-CENSOR",
        "origin=EX.EXSTDTC; event_terms=DEATH; censor_terms=COMPLETED; time_scale=days",
    )
    specs = (
        _var_spec("ADTTE", "STARTDT", source_domains=("EX",), source_variables=("EX.EXSTDTC",)),
        _var_spec("ADTTE", "ADT", source_domains=("DS",), source_variables=("DS.DSSTDTC",), user_defined_inputs=("event_definition", "censoring_rules")),
        _var_spec("ADTTE", "CNSR", source_domains=("DS",), source_variables=("DS.DSDECOD", "DS.DSSTDTC"), user_defined_inputs=("event_definition", "censoring_rules")),
    )
    spec = _custom_specification(specs)
    execution = _execute(spec, decisions=(decision,))
    adam = dict(execution.datasets)
    adtte = [dict(record) for record in execution.datasets["ADTTE"]]
    adtte[0]["CNSR"] = 1
    adam["ADTTE"] = tuple(adtte)

    result = _validate(spec, execution, adam_datasets=adam, study_decisions=(decision,))

    assert _check(result, "LOGIC-ADTTE-CNSR", "ADTTE", "CNSR").status == "FAIL"


def test_missing_specification_reference_fails_traceability():
    spec = _specification(variables=("ADSL.USUBJID",))
    execution = _execute(spec)
    adam = {"ADSL": ({"USUBJID": "01", "UNSPEC": "X"}, {"USUBJID": "02", "UNSPEC": "Y"})}

    result = _validate(spec, execution, adam_datasets=adam)

    assert _check(result, "TRACE-SPEC-REFERENCE", "ADSL", "UNSPEC").status == "FAIL"


def test_missing_evidence_reference_fails_when_classification_depends_on_evidence():
    spec = _custom_specification(
        (
            _var_spec(
                "ADLB",
                "AVAL",
                source_domains=("LB",),
                source_variables=("LB.LBSTRESN",),
                classification="STANDARD_GUIDED",
                evidence_references=("adamig:aval",),
            ),
        )
    )
    execution = _execute(spec)

    result = _validate(spec, execution, evidence=())

    assert _check(result, "TRACE-EVIDENCE-REFERENCE", "ADLB", "AVAL").status == "FAIL"


def test_missing_source_reference_fails_traceability():
    source = _sdtm_data()
    for record in source["LB"]:
        record.pop("LBSTRESN")
    spec = _custom_specification(
        (_var_spec("ADLB", "AVAL", source_domains=("LB",), source_variables=("LB.LBSTRESN",)),)
    )
    execution = _execute(spec)

    result = _validate(spec, execution, source_sdtm_datasets=source)

    assert _check(result, "TRACE-SOURCE-REFERENCE", "ADLB", "AVAL").status == "FAIL"


def test_orphan_execution_record_fails_traceability():
    spec = _specification(variables=("ADSL.USUBJID",))
    execution = _execute(spec)
    orphan = replace(
        execution.execution_records[0],
        execution_id="EXEC-ORPHAN",
        specification_id="ADAM-SPEC-ADLB-ORPHAN",
        dataset="ADLB",
        variable="ORPHAN",
    )

    result = _validate(
        spec,
        execution,
        derivation_execution_records=execution.execution_records + (orphan,),
    )

    assert _check(result, "TRACE-ORPHAN-EXECUTION", "ADLB", "ORPHAN").status == "FAIL"


def test_blocked_variable_incorrectly_populated_fails():
    spec = _specification(variables=("ADAE.TRTEMFL",))
    execution = _execute(spec)
    adam = {"ADAE": ({"TRTEMFL": "Y"}, {"TRTEMFL": "N"})}

    result = _validate(spec, execution, adam_datasets=adam)

    assert _check(result, "LOGIC-BLOCKED-VARIABLE-NOT-POPULATED", "ADAE", "TRTEMFL").status == "FAIL"


def test_preprocessing_traceability_validation_passes():
    prep_spec = PreprocessingOperationSpec(
        operation_id="PREP-LB-deterministic_numeric_parsing-LBORRES",
        dataset="LB",
        variable="LBORRES",
        operation="deterministic_numeric_parsing",
        purpose="Parse numeric source value.",
        classification="DATA_ENGINEERING",
        evidence_references=(),
        source_preserving=True,
        clinical_meaning_changed=False,
        implementation_allowed=True,
        validation_plan=("Verify source value is retained unchanged.",),
        notes=(),
    )
    prep_execution = PreprocessingExecutionRecord(
        execution_id="EXEC-001",
        operation_id=prep_spec.operation_id,
        dataset="LB",
        variable="LBORRES",
        operation="deterministic_numeric_parsing",
        classification="DATA_ENGINEERING",
        input_record_count=2,
        output_record_count=2,
        affected_record_count=2,
        status="EXECUTED",
        validation_status="PASSED",
        warnings=(),
        source_reference={"operation_id": prep_spec.operation_id},
    )
    spec = _specification(variables=("ADLB.AVAL",))
    execution = _execute(spec)

    result = _validate(
        spec,
        execution,
        preprocessing_specification=PreprocessingSpecification((prep_spec,)),
        preprocessed_datasets=_sdtm_data(),
        preprocessing_execution_records=(prep_execution,),
    )

    assert _check(result, "TRACE-PREPROCESSING-EXECUTION", "LB", "LBORRES").status == "PASS"


def test_not_evaluated_for_unresolved_study_logic():
    spec = _specification(variables=("ADTTE.CNSR",))
    execution = _execute(spec)

    result = _validate(spec, execution)

    check = _check(result, "LOGIC-ADTTE-CNSR", "ADTTE", "CNSR")
    assert check.status == "NOT_EVALUATED"
    assert check.severity == "INFO"


def test_validation_does_not_mutate_inputs():
    spec = _specification(variables=("ADLB.PARAMCD", "ADLB.AVAL"))
    execution = _execute(spec)
    source = _sdtm_data()
    adam = dict(execution.datasets)
    source_before = deepcopy(source)
    adam_before = deepcopy(adam)

    _validate(spec, execution, source_sdtm_datasets=source, adam_datasets=adam)

    assert source == source_before
    assert adam == adam_before
