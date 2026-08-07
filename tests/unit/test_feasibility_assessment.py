from standards_driven_sdtm_adam.feasibility import FeasibilityAssessor


def _complete_sdtm():
    return {
        "DM": [
            {"USUBJID": "01"},
            {"USUBJID": "02"},
            {"USUBJID": "03"},
        ],
        "AE": [
            {"USUBJID": "01", "AETERM": "Headache", "AESTDTC": "2024-01-03"},
            {"USUBJID": "02", "AETERM": "Nausea", "AESTDTC": "2024-01-04"},
        ],
        "LB": [
            {"USUBJID": "01", "LBTESTCD": "ALT", "LBORRES": "70", "LBDTC": "2024-01-02"},
            {"USUBJID": "02", "LBTESTCD": "AST", "LBORRES": "60", "LBDTC": "2024-01-02"},
        ],
        "EX": [
            {"USUBJID": "01", "EXTRT": "Drug", "EXSTDTC": "2024-01-01"},
            {"USUBJID": "02", "EXTRT": "Drug", "EXSTDTC": "2024-01-01"},
        ],
        "DS": [{"USUBJID": "01", "DSDECOD": "COMPLETED", "DSSTDTC": "2024-02-01"}],
        "SV": [{"USUBJID": "01", "SVSTDTC": "2024-01-01"}],
    }


def test_fully_feasible_objective():
    assessment = FeasibilityAssessor().assess(
        ["Are abnormal laboratory values associated with adverse events?"],
        _complete_sdtm(),
        evidence_references=("adamig:1",),
    )

    result = assessment.results[0]
    assert result.status == "FEASIBLE"
    assert result.required_domains == ("AE", "DM", "LB")
    assert result.missing_domains == ()
    assert result.blocking_issues == ()
    assert result.evidence_references == ("adamig:1",)


def test_partially_feasible_objective_due_to_missing_temporal_information():
    data = _complete_sdtm()
    data["LB"] = [
        {"USUBJID": "01", "LBTESTCD": "ALT", "LBORRES": "70", "LBDTC": ""},
        {"USUBJID": "02", "LBTESTCD": "AST", "LBORRES": "60", "LBDTC": ""},
    ]

    assessment = FeasibilityAssessor().assess(
        ["Are abnormal laboratory values associated with adverse events?"],
        data,
    )

    result = assessment.results[0]
    assert result.status == "PARTIALLY_FEASIBLE"
    assert result.blocking_issues == ()
    assert any("Temporal support is limited" in limitation for limitation in result.limitations)


def test_unsupported_objective_due_to_missing_domain():
    data = {"DM": [{"USUBJID": "01"}], "AE": [{"USUBJID": "01", "AETERM": "Headache"}]}

    assessment = FeasibilityAssessor().assess(
        ["Are abnormal laboratory values associated with adverse events?"],
        data,
    )

    result = assessment.results[0]
    assert result.status == "UNSUPPORTED"
    assert result.missing_domains == ("LB",)
    assert any("LB" in issue for issue in result.blocking_issues)


def test_unsupported_objective_due_to_insufficient_usable_records():
    data = {
        "DM": [{"USUBJID": "01"}],
        "AE": [],
    }

    assessment = FeasibilityAssessor().assess(
        ["Assess adverse events."],
        data,
    )

    result = assessment.results[0]
    assert result.status == "UNSUPPORTED"
    assert any("AE has no usable records" in issue for issue in result.blocking_issues)


def test_cross_domain_subject_overlap_blocker():
    data = {
        "DM": [{"USUBJID": "01"}],
        "AE": [{"USUBJID": "02", "AETERM": "Headache"}],
        "LB": [{"USUBJID": "03", "LBTESTCD": "ALT", "LBORRES": "70"}],
    }

    assessment = FeasibilityAssessor().assess(
        ["Are abnormal laboratory values associated with adverse events?"],
        data,
    )

    result = assessment.results[0]
    assert result.status == "UNSUPPORTED"
    assert result.subject_coverage["overlap_subject_count"] == 0
    assert any("overlapping USUBJID" in issue for issue in result.blocking_issues)


def test_missing_temporal_information_is_limitation_not_hard_blocker():
    data = {
        "DM": [{"USUBJID": "01"}],
        "AE": [{"USUBJID": "01", "AETERM": "Headache", "AESTDTC": ""}],
        "EX": [{"USUBJID": "01", "EXTRT": "Drug", "EXSTDTC": ""}],
    }

    assessment = FeasibilityAssessor().assess(
        ["Can adverse events be evaluated during treatment exposure?"],
        data,
    )

    result = assessment.results[0]
    assert result.status == "PARTIALLY_FEASIBLE"
    assert result.blocking_issues == ()
    assert result.date_coverage["temporal_required"]


def test_recommends_supported_research_objectives():
    assessment = FeasibilityAssessor().assess(
        ["Assess adverse events."],
        _complete_sdtm(),
    )

    recommended = assessment.supported_research_objectives
    assert 1 <= len(recommended) <= 5
    assert all(objective.objective_text for objective in recommended)
    assert all("Top 5 Analyses" not in objective.objective_text for objective in recommended)
    assert any("adverse event" in objective.objective_text.lower() for objective in recommended)


def test_results_do_not_recommend_statistical_analysis_behavior():
    assessment = FeasibilityAssessor().assess(
        ["Are abnormal laboratory values associated with adverse events?"],
        _complete_sdtm(),
    )

    serialized = repr(assessment).lower()
    forbidden = ("hypothesis", "regression", "model", "machine learning", "dashboard", "p-value")
    assert not any(term in serialized for term in forbidden)
