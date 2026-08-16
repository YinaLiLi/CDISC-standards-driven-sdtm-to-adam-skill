import json

from standards_driven_sdtm_adam.derivation.model import (
    AdamDatasetSpecification,
    AdamDerivationSpecification,
    AdamVariableSpecification,
)
from standards_driven_sdtm_adam.preprocessing.model import (
    PreprocessingOperationSpec,
    PreprocessingSpecification,
)
from standards_driven_sdtm_adam.reporting import ReportBuilder, render_markdown
from standards_driven_sdtm_adam.traceability import (
    CitationRecord,
    EvidenceResolutionResult,
    ResolvedEvidenceItem,
)
from standards_driven_sdtm_adam.validation.model import (
    AdamValidationResult,
    ValidationResult,
)


def _preprocessing_spec() -> PreprocessingSpecification:
    return PreprocessingSpecification(
        operations=(
            PreprocessingOperationSpec(
                operation_id="PREP-AE-DATE",
                dataset="AE",
                variable="AESTDTC",
                operation="deterministic_date_parsing",
                purpose="Prepare AE dates for downstream derivation.",
                classification="STANDARD_GUIDED",
                evidence_references=("adamig:2",),
                source_preserving=True,
                clinical_meaning_changed=False,
                implementation_allowed=True,
                validation_plan=("Record count preserved.",),
                notes=("Use parsed copy field only.",),
            ),
            PreprocessingOperationSpec(
                operation_id="PREP-DM-ID",
                dataset="DM",
                variable="USUBJID",
                operation="neutral_whitespace_normalization",
                purpose="Normalize technical whitespace.",
                classification="DATA_ENGINEERING",
                evidence_references=(),
                source_preserving=True,
                clinical_meaning_changed=False,
                implementation_allowed=True,
                validation_plan=("Record count preserved.",),
                notes=(),
            ),
        )
    )


def _dataset_spec(dataset: str) -> AdamDatasetSpecification:
    return AdamDatasetSpecification(
        dataset=dataset,
        purpose=f"{dataset} purpose",
        structure="one record per subject" if dataset == "ADSL" else "BDS/OCCDS",
        source_domains=("DM",) if dataset == "ADSL" else ("AE", "LB", "DS"),
        supported_variables=(f"{dataset}VAR",),
        evidence_references=(f"{dataset.lower()}:1",),
        unresolved_decisions=(),
        implementation_allowed=True,
    )


def _variable_spec(
    specification_id: str,
    dataset: str,
    variable: str,
    classification: str = "STANDARD_GUIDED",
) -> AdamVariableSpecification:
    return AdamVariableSpecification(
        specification_id=specification_id,
        dataset=dataset,
        variable=variable,
        label=f"{variable} Label",
        purpose=f"Derive {variable}.",
        source_domains=("DM",) if dataset == "ADSL" else ("AE", "LB", "DS"),
        source_variables=(variable,),
        derivation_logic=f"Derive {dataset}.{variable}.",
        dependencies=(),
        classification=classification,
        evidence_references=(f"{specification_id.lower()}:1",),
        user_defined_inputs=(),
        assumptions=(),
        validation_plan=("Validate traceability.",),
        implementation_allowed=True,
        unresolved_issues=(),
    )


def _derivation_spec() -> AdamDerivationSpecification:
    return AdamDerivationSpecification(
        dataset_specs=tuple(
            _dataset_spec(dataset) for dataset in ("ADLB", "ADAE", "ADTTE", "ADSL")
        ),
        variable_specs=(
            _variable_spec("ADLB.AVAL", "ADLB", "AVAL"),
            _variable_spec("ADAE.TRTEMFL", "ADAE", "TRTEMFL"),
            _variable_spec("ADTTE.AVAL", "ADTTE", "AVAL"),
            _variable_spec("ADSL.USUBJID", "ADSL", "USUBJID", "STANDARD_REQUIRED"),
        ),
        unresolved_decisions=(),
        traceability={},
    )


def _validation_result() -> AdamValidationResult:
    return AdamValidationResult(
        status="FAIL",
        validation_results=(
            ValidationResult(
                validation_id="VAL-002",
                category="TRACEABILITY",
                dataset="ADAE",
                variable="TRTEMFL",
                check_id="TRACE-001",
                description="Evidence reference is present.",
                status="FAIL",
                severity="ERROR",
                expected=True,
                observed=False,
                specification_reference="ADAE.TRTEMFL",
                evidence_references=("adamig:missing",),
                execution_references=("EXEC-002",),
                source_references=("AE",),
                message="Missing evidence reference.",
            ),
            ValidationResult(
                validation_id="VAL-001",
                category="STRUCTURAL",
                dataset="ADSL",
                variable=None,
                check_id="STRUCT-001",
                description="Dataset exists.",
                status="PASS",
                severity="INFO",
                expected=True,
                observed=True,
                specification_reference="ADSL",
                evidence_references=(),
                execution_references=("EXEC-001",),
                source_references=("DM",),
                message="Dataset exists.",
            ),
        ),
    )


def _citation(
    *,
    citation_id: str,
    source_role: str,
    purpose: str,
    evidence_reference: str,
    rule_specification_id: str = "ADSL.USUBJID",
) -> CitationRecord:
    return CitationRecord(
        citation_id=citation_id,
        rule_specification_id=rule_specification_id,
        decision_classification="STANDARD_REQUIRED",
        citation_purpose=purpose,
        evidence_reference=evidence_reference,
        source_id="adamig" if source_role == "primary_standard" else "adam-example",
        source_role=source_role,
        document_title="ADaM Implementation Guide"
        if source_role == "primary_standard"
        else "ADaM Example Package",
        official_filename="adamig.pdf",
        standard_version="1.3",
        standard_release_date="2024-11-29",
        page=12,
        section="ADSL",
        table=None,
        row=None,
        evidence_type="RULE",
        evidence_text="ADSL must include one record per subject.",
        extraction_status="EXTRACTED",
        official_url="https://example.org/adamig",
    )


def _evidence_resolution() -> EvidenceResolutionResult:
    return EvidenceResolutionResult(
        items=(
            ResolvedEvidenceItem(
                rule_specification_id="PREP-AE-DATE",
                decision_classification="STANDARD_GUIDED",
                evidence_use="decision_support",
                resolution_status="RESOLVED",
                citations=(
                    _citation(
                        citation_id="CIT-PREP",
                        source_role="primary_standard",
                        purpose="normative",
                        evidence_reference="adamig:2",
                        rule_specification_id="PREP-AE-DATE",
                    ),
                ),
                unresolved_evidence_references=(),
                excluded_evidence_references=(),
            ),
            ResolvedEvidenceItem(
                rule_specification_id="ADSL.USUBJID",
                decision_classification="STANDARD_REQUIRED",
                evidence_use="decision_support",
                resolution_status="RESOLVED",
                citations=(
                    _citation(
                        citation_id="CIT-NORM",
                        source_role="primary_standard",
                        purpose="normative",
                        evidence_reference="adamig:1",
                    ),
                    _citation(
                        citation_id="CIT-VAL",
                        source_role="validation_reference",
                        purpose="validation_support",
                        evidence_reference="adam-example:1",
                    ),
                ),
                unresolved_evidence_references=(),
                excluded_evidence_references=(),
            ),
            ResolvedEvidenceItem(
                rule_specification_id="ADAE.TRTEMFL",
                decision_classification="STANDARD_GUIDED",
                evidence_use="decision_support",
                resolution_status="NO_VALID_STANDARD_EVIDENCE",
                citations=(),
                unresolved_evidence_references=("adamig:missing",),
                excluded_evidence_references=("adam-example:2",),
            ),
        )
    )


def _report():
    return ReportBuilder().build(
        preprocessing_specification=_preprocessing_spec(),
        adam_derivation_specification=_derivation_spec(),
        validation_result=_validation_result(),
        evidence_resolution_result=_evidence_resolution(),
    )


def test_builds_basic_report_from_existing_outputs():
    report = _report()

    assert report.title == "Standards-Driven SDTM-to-ADaM Pipeline Report"
    assert report.overall_status == "FAIL"
    assert report.preprocessing_summary["operation_count"] == 2
    assert report.adam_summary["dataset_count"] == 4
    assert report.preprocessing_summary["operations"][0]["basis"] == (
        "ADaM Implementation Guide page 12, section ADSL"
    )
    assert report.preprocessing_summary["operations"][1]["basis"] == (
        "Technical source-preserving operation"
    )
    assert report.adam_summary["variables"][0]["basis"] == (
        "No valid standard evidence resolved"
    )


def test_machine_readable_output_is_json_serializable_and_stable():
    payload = _report().to_dict()

    assert "validation" not in payload
    assert "traceability" not in payload
    assert "evidence" not in payload
    assert "operation_id" not in json.dumps(payload, sort_keys=True)
    assert "specification_id" not in json.dumps(payload, sort_keys=True)
    assert "evidence_references" not in json.dumps(payload, sort_keys=True)
    assert payload["metadata"]["supported_adam_datasets"] == [
        "ADAE",
        "ADLB",
        "ADSL",
        "ADTTE",
    ]
    assert payload["adam"]["datasets"][0]["dataset"] == "ADAE"
    assert payload["preprocessing"]["operations"][0]["basis"]
    assert payload["adam"]["variables"][0]["basis"]
    encoded = json.dumps(payload, sort_keys=True)
    assert json.loads(encoded) == payload


def test_markdown_rendering_is_human_readable_and_deterministic():
    markdown = render_markdown(_report())

    assert markdown == render_markdown(_report())
    assert markdown.startswith("# Standards-Driven SDTM-to-ADaM Pipeline Report")
    assert "## Preprocessing Operations" in markdown
    assert "## ADaM Derivation Operations" in markdown
    assert "| Target | Operation | Basis |" in markdown
    assert "## Validation Summary" not in markdown
    assert "## Traceability and Evidence Summary" not in markdown
    assert "VAL-002" not in markdown
    assert "ADAE.TRTEMFL" in markdown
    assert "No valid standard evidence resolved" in markdown
    assert "ADaM Implementation Guide page 12, section ADSL" in markdown


def test_deterministic_ordering_for_datasets_variables_and_traceability():
    payload = _report().to_dict()

    assert [item["dataset"] for item in payload["adam"]["datasets"]] == [
        "ADAE",
        "ADLB",
        "ADSL",
        "ADTTE",
    ]
    assert [item["target"] for item in payload["adam"]["variables"]] == [
        "ADAE.TRTEMFL",
        "ADLB.AVAL",
        "ADSL.USUBJID",
        "ADTTE.AVAL",
    ]
    assert payload["adam"]["variables"][1]["basis"] == "No valid standard evidence resolved"


def test_separates_normative_and_validation_supporting_evidence():
    traceability = _report().traceability_summary

    assert traceability["normative_citation_count"] == 2
    assert traceability["validation_support_citation_count"] == 1
    citations = traceability["items"][1]["citations"]
    assert citations[0]["citation_purpose"] == "normative"
    assert citations[1]["citation_purpose"] == "validation_support"


def test_displays_unresolved_and_excluded_evidence_references():
    item = _report().traceability_summary["items"][0]

    assert item["unresolved_evidence_references"] == ["adamig:missing"]
    assert item["excluded_evidence_references"] == ["adam-example:2"]
    markdown = render_markdown(_report())
    assert "Unresolved: adamig:missing" not in markdown
    assert "Excluded: adam-example:2" not in markdown


def test_validation_summary_includes_counts_and_failure_details():
    validation = _report().validation_summary

    assert validation["status"] == "FAIL"
    assert validation["counts_by_severity"] == {"ERROR": 1, "INFO": 1}
    assert validation["failures"][0]["validation_id"] == "VAL-002"
    assert validation["failures"][0]["message"] == "Missing evidence reference."


def test_reporting_consumes_m11_result_without_evidence_resolution_inputs():
    report = ReportBuilder().build(
        preprocessing_specification=None,
        adam_derivation_specification=None,
        validation_result=None,
        evidence_resolution_result=_evidence_resolution(),
    )

    assert report.overall_status == "NOT_EVALUATED"
    assert report.traceability_summary["item_count"] == 3
    assert report.traceability_summary["items"][1]["citations"][0][
        "evidence_reference"
    ] == "adamig:1"


def test_report_generation_covers_v1_adam_outputs():
    datasets = {
        item["dataset"] for item in _report().to_dict()["adam"]["datasets"]
    }

    assert datasets == {"ADSL", "ADAE", "ADLB", "ADTTE"}
