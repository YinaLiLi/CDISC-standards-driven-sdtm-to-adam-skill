from standards_driven_sdtm_adam.derivation import (
    AdamDerivationSpecifier,
    StudyDecision,
)
from standards_driven_sdtm_adam.extraction.model import EvidenceRecord
from standards_driven_sdtm_adam.feasibility import FeasibilityAssessor


def _sdtm_data(include_ds=True):
    data = {
        "DM": [
            {
                "STUDYID": "S1",
                "USUBJID": "01",
                "SUBJID": "01",
                "SITEID": "100",
                "AGE": "64",
                "SEX": "F",
                "RACE": "WHITE",
                "ARM": "Drug A",
                "ACTARM": "Drug A",
            }
        ],
        "EX": [{"USUBJID": "01", "EXSTDTC": "2024-01-01", "EXENDTC": "2024-01-14"}],
        "AE": [{"USUBJID": "01", "AETERM": "Headache", "AESTDTC": "2024-01-03"}],
        "LB": [
            {
                "USUBJID": "01",
                "LBTESTCD": "ALT",
                "LBTEST": "Alanine Aminotransferase",
                "LBORRES": "70",
                "LBSTRESN": "70",
                "LBSTRESU": "U/L",
                "LBDTC": "2024-01-02",
            }
        ],
    }
    if include_ds:
        data["DS"] = [{"USUBJID": "01", "DSDECOD": "DEATH", "DSSTDTC": "2024-02-01"}]
    return data


def _feasibility(data=None):
    return FeasibilityAssessor().assess(
        ["Evaluate adverse events, laboratory values, and time-to-event outcomes."],
        data or _sdtm_data(),
    )


def _evidence(
    evidence_id,
    quote,
    *,
    evidence_type="GUIDANCE",
    standard_id="adamig",
    section="General",
):
    return EvidenceRecord(
        evidence_id=evidence_id,
        standard_id=standard_id,
        standard_title="ADaM Implementation Guide",
        version="1.3",
        evidence_type=evidence_type,
        section=section,
        page=1,
        short_quote=quote,
        source_local_path="adamig.txt",
        official_url=None,
        search_context=quote,
        extraction_status="EXTRACTED",
    )


def _specification(data=None, evidence=(), study_decisions=(), requested_variables=()):
    return AdamDerivationSpecifier().specify(
        data or _sdtm_data(),
        _feasibility(data),
        evidence=evidence,
        study_decisions=study_decisions,
        requested_variables=requested_variables,
    )


def _variable(specification, dataset, variable):
    matches = [
        spec
        for spec in specification.variable_specs
        if spec.dataset == dataset and spec.variable == variable
    ]
    assert len(matches) == 1
    return matches[0]


def test_standard_supported_adsl_subject_identifier_specification():
    specification = _specification(
        evidence=(
            _evidence(
                "adam-model:adsl",
                "ADSL is the subject-level analysis dataset with one record per subject.",
                evidence_type="DEFINITION",
                standard_id="adam-model",
            ),
        )
    )

    adsl = _variable(specification, "ADSL", "USUBJID")

    assert adsl.classification == "STANDARD_REQUIRED"
    assert adsl.source_domains == ("DM",)
    assert adsl.source_variables == ("DM.USUBJID",)
    assert adsl.evidence_references == ("adam-model:adsl",)
    assert adsl.implementation_allowed
    assert "Confirm one ADSL record per subject." in adsl.validation_plan


def test_adae_treatment_emergent_flag_requires_study_specific_window():
    specification = _specification(
        evidence=(
            _evidence(
                "adam-occds:trtemfl",
                "Treatment-emergent analysis flags may be derived for occurrence data.",
                standard_id="adam-occds-ig",
            ),
        )
    )

    trtemfl = _variable(specification, "ADAE", "TRTEMFL")

    assert trtemfl.classification == "STUDY_SPECIFIC"
    assert trtemfl.dependencies == ("ADSL.TRTSDT", "ADSL.TRTEDT", "ADAE.ASTDT")
    assert "AE.AESTDTC" in trtemfl.source_variables
    assert not trtemfl.implementation_allowed
    assert trtemfl.user_defined_inputs == ("treatment_emergent_window",)
    assert specification.unresolved_decisions[0].decision_id == "DECISION-TREATMENT-EMERGENT-WINDOW"
    assert specification.unresolved_decisions[0].required_before_implementation


def test_adlb_analysis_value_specification_uses_laboratory_source_data():
    specification = _specification(
        evidence=(
            _evidence(
                "adamig:aval",
                "Analysis value variables are populated from relevant source measurements.",
            ),
        )
    )

    aval = _variable(specification, "ADLB", "AVAL")

    assert aval.classification == "STANDARD_GUIDED"
    assert aval.source_domains == ("LB",)
    assert aval.source_variables == ("LB.LBSTRESN", "LB.LBORRES")
    assert aval.dependencies == ()
    assert aval.implementation_allowed


def test_adtte_requires_event_and_censor_logic_before_implementation():
    specification = _specification(
        evidence=(
            _evidence(
                "tte-guide:adtte",
                "Time-to-event analysis datasets include event and censoring information.",
                standard_id="adam-bds-tte",
            ),
        )
    )

    cnsr = _variable(specification, "ADTTE", "CNSR")

    assert cnsr.classification == "STUDY_SPECIFIC"
    assert cnsr.source_domains == ("DS",)
    assert cnsr.source_variables == ("DS.DSDECOD", "DS.DSSTDTC")
    assert cnsr.user_defined_inputs == ("event_definition", "censoring_rules")
    assert not cnsr.implementation_allowed


def test_unsupported_derivation_due_to_missing_evidence_is_blocked():
    specification = _specification(requested_variables=("ADSL.CUSTOMX",))

    custom = _variable(specification, "ADSL", "CUSTOMX")

    assert custom.classification == "UNSUPPORTED"
    assert custom.evidence_references == ()
    assert not custom.implementation_allowed
    assert custom.unresolved_issues == (
        "No extracted CDISC evidence or explicit study decision supports ADSL.CUSTOMX.",
    )


def test_missing_user_defined_study_decision_is_structured():
    specification = _specification()

    decisions = {decision.decision_id: decision for decision in specification.unresolved_decisions}

    assert "DECISION-SAFETY-POPULATION" in decisions
    assert decisions["DECISION-SAFETY-POPULATION"].question == "What is the study-defined Safety Population?"
    assert decisions["DECISION-SAFETY-POPULATION"].affected_variables == ("ADSL.SAFFL",)
    assert decisions["DECISION-SAFETY-POPULATION"].status == "MISSING"


def test_provided_user_decision_allows_user_defined_population_flag_specification():
    specification = _specification(
        study_decisions=(
            StudyDecision(
                decision_id="DECISION-SAFETY-POPULATION",
                question="What is the study-defined Safety Population?",
                affected_datasets=("ADSL",),
                affected_variables=("ADSL.SAFFL",),
                required_before_implementation=True,
                status="PROVIDED",
                value="Subjects who received at least one dose of study treatment.",
            ),
        )
    )

    saffl = _variable(specification, "ADSL", "SAFFL")

    assert saffl.classification == "USER_DEFINED"
    assert saffl.user_defined_inputs == ("DECISION-SAFETY-POPULATION",)
    assert saffl.implementation_allowed
    assert saffl.unresolved_issues == ()


def test_example_adapted_logic_is_not_treated_as_required():
    specification = _specification(
        evidence=(
            _evidence(
                "adamig:example-avisit",
                "Example: AVISIT may be populated from visit timing for illustrative purposes.",
                evidence_type="EXAMPLE",
            ),
        )
    )

    avisit = _variable(specification, "ADLB", "AVISIT")

    assert avisit.classification == "EXAMPLE_ADAPTED"
    assert avisit.evidence_references == ("adamig:example-avisit",)
    assert avisit.classification != "STANDARD_REQUIRED"


def test_traceability_to_sdtm_source_variables_and_decision_classification():
    specification = _specification()

    trace = specification.traceability["ADAE.ASTDT"]

    assert trace["derivation_specification_id"] == "ADAM-SPEC-ADAE-ASTDT"
    assert trace["source_sdtm_variables"] == ("AE.AESTDTC",)
    assert trace["decision_classification"] == "DATA_ENGINEERING"
    assert trace["study_decisions"] == ()


def test_dependency_handling_for_adtte_analysis_duration():
    specification = _specification()

    aval = _variable(specification, "ADTTE", "AVAL")

    assert aval.dependencies == ("ADTTE.STARTDT", "ADTTE.ADT")
    assert "DS.DSSTDTC" in aval.source_variables
    assert not aval.implementation_allowed


def test_implementation_allowed_becomes_false_when_required_source_data_is_missing():
    specification = _specification(data=_sdtm_data(include_ds=False))

    adt = _variable(specification, "ADTTE", "ADT")

    assert adt.classification == "UNSUPPORTED"
    assert not adt.implementation_allowed
    assert adt.unresolved_issues == ("Required source variables are missing: DS.DSSTDTC.",)
