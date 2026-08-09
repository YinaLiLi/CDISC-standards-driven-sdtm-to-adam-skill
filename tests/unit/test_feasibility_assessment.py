from standards_driven_sdtm_adam.feasibility import FeasibilityAssessor


def _complete_sdtm():
    subjects = [f"{i:02d}" for i in range(1, 7)]
    return {
        "DM": [{"USUBJID": subject} for subject in subjects],
        "AE": [
            {"USUBJID": subject, "AETERM": "Headache", "AESTDTC": f"2024-01-{i + 2:02d}"}
            for i, subject in enumerate(subjects, start=1)
        ],
        "LB": [
            {
                "USUBJID": subject,
                "LBTESTCD": "ALT",
                "LBORRES": "70",
                "LBNRIND": "HIGH",
                "LBDTC": f"2024-01-{i + 1:02d}",
            }
            for i, subject in enumerate(subjects, start=1)
        ],
        "EX": [
            {"USUBJID": subject, "EXTRT": "Drug", "EXSTDTC": "2024-01-01"}
            for subject in subjects
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
        {
            "USUBJID": f"{i:02d}",
            "LBTESTCD": "ALT",
            "LBORRES": "70",
            "LBNRIND": "HIGH",
            "LBDTC": "",
        }
        for i in range(1, 7)
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
    subjects = [f"{i:02d}" for i in range(1, 7)]
    data = {
        "DM": [{"USUBJID": subject} for subject in subjects],
        "AE": [{"USUBJID": subject, "AETERM": "Headache", "AESTDTC": ""} for subject in subjects],
        "EX": [{"USUBJID": subject, "EXTRT": "Drug", "EXSTDTC": ""} for subject in subjects],
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


def test_sparse_adverse_event_burden_is_unsupported():
    data = {
        "DM": [{"USUBJID": f"{i:02d}"} for i in range(1, 7)],
        "AE": [
            {"USUBJID": "01", "AETERM": "Headache"},
            {"USUBJID": "02", "AETERM": "Nausea"},
            {"USUBJID": "03", "AETERM": "Fatigue"},
        ],
    }

    assessment = FeasibilityAssessor().assess(
        ["Assess adverse event burden."],
        data,
    )

    result = assessment.results[0]
    assert result.status == "UNSUPPORTED"
    assert any("AE has only 3 usable records" in issue for issue in result.blocking_issues)
    assert any("AE has only 3 subjects" in issue for issue in result.blocking_issues)


def test_lab_abnormality_objective_requires_abnormality_source():
    data = _complete_sdtm()
    data["LB"] = [
        {
            "USUBJID": f"{i:02d}",
            "LBTESTCD": "ALT",
            "LBORRES": "70",
            "LBDTC": f"2024-01-{i + 1:02d}",
        }
        for i in range(1, 7)
    ]

    assessment = FeasibilityAssessor().assess(
        ["Are abnormal laboratory values preceding adverse events?"],
        data,
    )

    result = assessment.results[0]
    assert result.status == "UNSUPPORTED"
    assert any("abnormality indicator" in issue for issue in result.blocking_issues)


def test_lab_change_from_baseline_requires_enough_baseline_pairs():
    data = {
        "DM": [{"USUBJID": f"{i:02d}"} for i in range(1, 7)],
        "LB": [
            {"USUBJID": "01", "LBTESTCD": "ALT", "LBORRES": "50", "LBBLFL": "Y", "LBDTC": "2024-01-01"},
            {"USUBJID": "01", "LBTESTCD": "ALT", "LBORRES": "70", "LBBLFL": "", "LBDTC": "2024-01-08"},
            {"USUBJID": "02", "LBTESTCD": "ALT", "LBORRES": "45", "LBBLFL": "Y", "LBDTC": "2024-01-01"},
            {"USUBJID": "02", "LBTESTCD": "ALT", "LBORRES": "68", "LBBLFL": "", "LBDTC": "2024-01-08"},
        ],
    }

    assessment = FeasibilityAssessor().assess(
        ["How do key laboratory values change from baseline?"],
        data,
    )

    result = assessment.results[0]
    assert result.status == "UNSUPPORTED"
    assert any("baseline-flagged records" in issue for issue in result.blocking_issues)


def test_predictive_ml_objective_is_unsupported_with_sparse_outcomes():
    data = {
        "DM": [{"USUBJID": f"{i:02d}"} for i in range(1, 31)],
        "AE": [
            {"USUBJID": "01", "AETERM": "Hospitalization", "AESER": "Y"},
            {"USUBJID": "02", "AETERM": "Hospitalization", "AESER": "Y"},
            {"USUBJID": "03", "AETERM": "Hospitalization", "AESER": "Y"},
        ],
        "LB": [
            {"USUBJID": f"{i:02d}", "LBTESTCD": "ALT", "LBORRES": "70"}
            for i in range(1, 31)
        ],
    }

    assessment = FeasibilityAssessor().assess(
        ["Can we build a predictive machine learning model for serious adverse event risk?"],
        data,
    )

    result = assessment.results[0]
    assert result.status == "UNSUPPORTED"
    assert any("outside Version 1 feasibility scope" in issue for issue in result.blocking_issues)
    assert any("only 3 outcome-positive subjects" in issue for issue in result.blocking_issues)


def test_sparse_domains_are_not_recommended_as_supported_objectives():
    data = {
        "DM": [{"USUBJID": f"{i:02d}"} for i in range(1, 7)],
        "AE": [{"USUBJID": "01", "AETERM": "Headache"}],
        "LB": [{"USUBJID": "01", "LBTESTCD": "ALT", "LBORRES": "70"}],
    }

    assessment = FeasibilityAssessor().assess(
        ["Assess adverse events."],
        data,
    )

    recommended = assessment.supported_research_objectives
    assert all("adverse event" not in item.objective_text.lower() for item in recommended)
    assert all("laboratory" not in item.objective_text.lower() for item in recommended)
