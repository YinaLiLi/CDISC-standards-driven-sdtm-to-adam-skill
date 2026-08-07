from dataclasses import replace

from standards_driven_sdtm_adam.derivation import (
    AdamDerivationEngine,
    AdamDerivationSpecification,
    AdamDerivationSpecifier,
    AdamVariableSpecification,
    StudyDecision,
)
from standards_driven_sdtm_adam.feasibility import FeasibilityAssessor


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
            {
                "USUBJID": "01",
                "LBSEQ": "1",
                "LBTESTCD": "ALT",
                "LBORRES": "70",
                "LBSTRESN": "70",
                "LBDTC": "2024-01-02",
            },
            {
                "USUBJID": "02",
                "LBSEQ": "1",
                "LBTESTCD": "ALT",
                "LBORRES": "42",
                "LBSTRESN": "42",
                "LBDTC": "2024-01-04",
            },
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


def _specification(data=None, study_decisions=(), variables=()):
    full = AdamDerivationSpecifier().specify(
        data or _sdtm_data(),
        _feasibility(data),
        study_decisions=study_decisions,
    )
    if not variables:
        return full
    selected = tuple(
        spec
        for spec in full.variable_specs
        if f"{spec.dataset}.{spec.variable}" in variables
    )
    return replace(full, variable_specs=selected)


def _custom_specification(specs):
    return AdamDerivationSpecification(
        dataset_specs=(),
        variable_specs=tuple(specs),
        unresolved_decisions=(),
        traceability={},
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
        "derivation_logic": "Approved test derivation.",
        "dependencies": (),
        "classification": "DATA_ENGINEERING",
        "evidence_references": (),
        "user_defined_inputs": (),
        "assumptions": (),
        "validation_plan": ("Check execution traceability.",),
        "implementation_allowed": True,
        "unresolved_issues": (),
    }
    defaults.update(overrides)
    return AdamVariableSpecification(**defaults)


def _execution(result, dataset, variable):
    matches = [
        record
        for record in result.execution_records
        if record.dataset == dataset and record.variable == variable
    ]
    assert len(matches) == 1
    return matches[0]


def test_successful_adsl_derivation_creates_new_dataset_without_mutating_sdtm():
    source = _sdtm_data()
    original_first_dm = dict(source["DM"][0])
    specification = _specification(
        source,
        variables=("ADSL.USUBJID", "ADSL.TRTSDT", "ADSL.TRTEDT"),
    )

    result = AdamDerivationEngine().execute(source, specification)

    assert result.datasets["ADSL"] == (
        {"USUBJID": "01", "TRTSDT": "2024-01-01", "TRTEDT": "2024-01-14"},
        {"USUBJID": "02", "TRTSDT": "2024-01-03", "TRTEDT": "2024-01-17"},
    )
    assert source["DM"][0] == original_first_dm
    assert _execution(result, "ADSL", "TRTSDT").status == "DERIVED"


def test_adsl_one_record_per_subject_is_enforced():
    source = _sdtm_data()
    source["DM"].append({"STUDYID": "S1", "USUBJID": "01", "AGE": "65", "SEX": "F"})
    specification = _specification(source, variables=("ADSL.USUBJID",))

    result = AdamDerivationEngine().execute(source, specification)

    assert len(result.datasets["ADSL"]) == 2
    assert _execution(result, "ADSL", "USUBJID").validation_status == "PASSED_WITH_WARNINGS"
    assert "ADSL input DM contained duplicate USUBJID values; output was de-duplicated." in result.warnings


def test_adae_derivation_uses_adsl_dependency():
    decision = _decision(
        "DECISION-TREATMENT-EMERGENT-WINDOW",
        "treatment_emergent_window=start through end plus 30 days",
    )
    specification = _specification(
        study_decisions=(decision,),
        variables=("ADSL.TRTSDT", "ADSL.TRTEDT", "ADAE.ASTDT", "ADAE.TRTEMFL"),
    )

    result = AdamDerivationEngine().execute(_sdtm_data(), specification, study_decisions=(decision,))

    assert result.datasets["ADAE"] == (
        {"ASTDT": "2024-01-03", "TRTEMFL": "Y"},
        {"ASTDT": "2024-02-20", "TRTEMFL": "N"},
    )
    trtemfl = _execution(result, "ADAE", "TRTEMFL")
    assert trtemfl.dependency_executions == (
        "EXEC-ADAM-SPEC-ADSL-TRTSDT",
        "EXEC-ADAM-SPEC-ADSL-TRTEDT",
        "EXEC-ADAM-SPEC-ADAE-ASTDT",
    )


def test_trtemfl_is_blocked_when_treatment_emergent_definition_is_unresolved():
    specification = _specification(variables=("ADAE.TRTEMFL",))

    result = AdamDerivationEngine().execute(_sdtm_data(), specification)

    trtemfl = _execution(result, "ADAE", "TRTEMFL")
    assert trtemfl.status == "BLOCKED"
    assert trtemfl.study_decision_references == ("treatment_emergent_window",)
    assert "Specification is not approved for implementation." in trtemfl.warnings
    assert "ADAE" not in result.datasets


def test_successful_adlb_derivation_preserves_source_laboratory_values():
    specification = _specification(variables=("ADLB.PARAMCD", "ADLB.AVAL"))

    result = AdamDerivationEngine().execute(_sdtm_data(), specification)

    assert result.datasets["ADLB"] == (
        {"PARAMCD": "ALT", "AVAL": 70.0},
        {"PARAMCD": "ALT", "AVAL": 42.0},
    )
    aval = _execution(result, "ADLB", "AVAL")
    assert aval.derived_value_count == 2
    assert aval.source_variables == ("LB.LBSTRESN", "LB.LBORRES")


def test_adlb_baseline_logic_is_blocked_when_baseline_definition_is_unresolved():
    baseline_spec = _var_spec(
        "ADLB",
        "BASE",
        source_domains=("LB",),
        source_variables=("LB.LBSTRESN",),
        classification="STUDY_SPECIFIC",
        user_defined_inputs=("baseline_definition",),
        implementation_allowed=False,
        unresolved_issues=("Baseline definition has not been provided.",),
    )

    result = AdamDerivationEngine().execute(_sdtm_data(), _custom_specification((baseline_spec,)))

    base = _execution(result, "ADLB", "BASE")
    assert base.status == "BLOCKED"
    assert base.study_decision_references == ("baseline_definition",)
    assert "ADLB" not in result.datasets


def test_successful_adtte_derivation_with_explicit_event_and_censor_rules():
    decision = _decision(
        "DECISION-TTE-EVENT-CENSOR",
        "origin=EX.EXSTDTC; event_terms=DEATH; censor_terms=COMPLETED; time_scale=days",
    )
    specs = (
        _var_spec("ADTTE", "STARTDT", source_domains=("EX",), source_variables=("EX.EXSTDTC",)),
        _var_spec(
            "ADTTE",
            "ADT",
            source_domains=("DS",),
            source_variables=("DS.DSSTDTC",),
            classification="STUDY_SPECIFIC",
            user_defined_inputs=("event_definition", "censoring_rules"),
        ),
        _var_spec(
            "ADTTE",
            "CNSR",
            source_domains=("DS",),
            source_variables=("DS.DSDECOD", "DS.DSSTDTC"),
            classification="STUDY_SPECIFIC",
            user_defined_inputs=("event_definition", "censoring_rules"),
        ),
        _var_spec(
            "ADTTE",
            "AVAL",
            source_domains=("DS", "EX"),
            source_variables=("DS.DSSTDTC", "EX.EXSTDTC"),
            dependencies=("ADTTE.STARTDT", "ADTTE.ADT"),
            classification="STUDY_SPECIFIC",
            user_defined_inputs=("event_definition", "censoring_rules"),
        ),
    )

    result = AdamDerivationEngine().execute(
        _sdtm_data(),
        _custom_specification(specs),
        study_decisions=(decision,),
    )

    assert result.datasets["ADTTE"] == (
        {"STARTDT": "2024-01-01", "ADT": "2024-02-01", "CNSR": 0, "AVAL": 31},
        {"STARTDT": "2024-01-03", "ADT": "2024-03-01", "CNSR": 1, "AVAL": 58},
    )
    assert _execution(result, "ADTTE", "AVAL").status == "DERIVED"


def test_adtte_is_blocked_when_censoring_logic_is_unresolved():
    specification = _specification(variables=("ADTTE.CNSR",))

    result = AdamDerivationEngine().execute(_sdtm_data(), specification)

    cnsr = _execution(result, "ADTTE", "CNSR")
    assert cnsr.status == "BLOCKED"
    assert cnsr.study_decision_references == ("event_definition", "censoring_rules")
    assert "ADTTE" not in result.datasets


def test_missing_source_variable_handling_blocks_only_affected_variable():
    source = _sdtm_data()
    del source["LB"][0]["LBSTRESN"]
    del source["LB"][1]["LBSTRESN"]
    specification = _specification(source, variables=("ADLB.PARAMCD", "ADLB.AVAL"))

    result = AdamDerivationEngine().execute(source, specification)

    assert result.datasets["ADLB"] == ({"PARAMCD": "ALT"}, {"PARAMCD": "ALT"})
    aval = _execution(result, "ADLB", "AVAL")
    assert aval.status == "BLOCKED"
    assert "Required source variable is missing: LB.LBSTRESN." in aval.warnings


def test_failed_dependency_blocks_dependent_variable():
    specs = (
        _var_spec(
            "ADSL",
            "TRTSDT",
            source_domains=("EX",),
            source_variables=("EX.MISSINGDTC",),
        ),
        _var_spec(
            "ADAE",
            "TRTEMFL",
            source_domains=("AE", "EX"),
            source_variables=("AE.AESTDTC", "EX.EXSTDTC"),
            dependencies=("ADSL.TRTSDT",),
            classification="STUDY_SPECIFIC",
        ),
    )

    result = AdamDerivationEngine().execute(_sdtm_data(), _custom_specification(specs))

    assert _execution(result, "ADSL", "TRTSDT").status == "BLOCKED"
    trtemfl = _execution(result, "ADAE", "TRTEMFL")
    assert trtemfl.status == "BLOCKED"
    assert "Dependency ADSL.TRTSDT did not complete successfully." in trtemfl.warnings


def test_unapproved_specification_is_rejected():
    spec = _var_spec("ADSL", "CUSTOMX", implementation_allowed=False)

    result = AdamDerivationEngine().execute(_sdtm_data(), _custom_specification((spec,)))

    custom = _execution(result, "ADSL", "CUSTOMX")
    assert custom.status == "BLOCKED"
    assert "Specification is not approved for implementation." in custom.warnings
    assert result.datasets == {}


def test_execution_traceability_records_required_fields():
    specification = _specification(variables=("ADLB.AVAL",))

    result = AdamDerivationEngine().execute(_sdtm_data(), specification)

    aval = _execution(result, "ADLB", "AVAL")
    assert aval.execution_id == "EXEC-ADAM-SPEC-ADLB-AVAL"
    assert aval.specification_id == "ADAM-SPEC-ADLB-AVAL"
    assert aval.input_record_count == 2
    assert aval.output_record_count == 2
    assert aval.validation_status == "PASSED"
    assert aval.classification == "STANDARD_GUIDED"


def test_no_unspecified_variable_creation():
    specification = _specification(variables=("ADLB.AVAL",))

    result = AdamDerivationEngine().execute(_sdtm_data(), specification)

    assert tuple(result.datasets["ADLB"][0]) == ("AVAL",)
