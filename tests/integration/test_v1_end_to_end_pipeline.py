import json
from dataclasses import replace
from pathlib import Path

from standards_driven_sdtm_adam.standards import DownloadReceipt
from standards_driven_sdtm_adam.derivation import AdamVariableSpecification
from standards_driven_sdtm_adam.pipeline import V1Pipeline
from standards_driven_sdtm_adam.traceability import DecisionEvidenceRequest


TASK_INTENTS = (
    "Create ADSL subject-level analysis dataset",
    "Derive treatment-emergent adverse event variables for ADAE",
    "Plan ADLB laboratory analysis value outputs",
    "Identify ADTTE time-to-event censoring evidence",
    "Evaluate source-preserving SDTM preprocessing date concepts",
)

OBJECTIVES = (
    "Evaluate adverse events, laboratory values, and time-to-event outcomes.",
)


def _write_manifest(
    standards_dir: Path,
    *,
    standard_id: str,
    title: str,
    role: str,
    local_path: str,
    enabled: bool = True,
    version: str | None = "1.0",
) -> None:
    version_value = "null" if version is None else f'"{version}"'
    manifest = f"""schema_version: 1
standard:
  id: {standard_id}
  title: {title}
  role: {role}
  version: {version_value}
  release_date: "2024-11-29"
  official_url: https://example.org/{standard_id}
  package_url: null
  local_path: {local_path}
  local_root: null
  original_filename: {standard_id}.txt
  sha256: null
  sha256_status: NOT_APPLICABLE
  verification_status: UNVERIFIED
  indexed: false
  verified: false
  enabled: {str(enabled).lower()}
"""
    (standards_dir / f"{standard_id}.yaml").write_text(manifest, encoding="utf-8")


def _write_standard(standards_dir: Path, relative_path: str, content: str) -> None:
    path = standards_dir / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _registry_dir(tmp_path: Path) -> Path:
    standards_dir = tmp_path / "standards"
    standards_dir.mkdir()
    manifests = (
        ("adamig", "ADaM Implementation Guide", "primary_standard", "docs/adamig.txt"),
        ("adam-occds", "ADaM OCCDS Implementation Guide", "primary_standard", "docs/occds.txt"),
        ("adam-model", "ADaM Model", "primary_standard", "docs/adam-model.txt"),
        ("adam-bds-tte", "ADaM BDS Time-to-Event Guide", "primary_standard", "docs/tte.txt"),
        ("adam-ct", "ADaM Controlled Terminology", "primary_standard", "docs/ct.txt"),
        ("adam-conformance-rules", "ADaM Conformance Rules", "primary_standard", "docs/rules.txt"),
        ("sdtm-model", "Study Data Tabulation Model", "upstream_reference", "docs/sdtm.txt"),
        ("sdtmig", "SDTM Implementation Guide", "upstream_reference", "docs/sdtmig.txt"),
        ("adam-traceability-examples", "ADaM Traceability Examples", "validation_reference", "docs/examples.txt"),
        ("define-xml", "Define-XML", "future_scope", "docs/define.txt"),
    )
    for standard_id, title, role, path in manifests:
        _write_manifest(
            standards_dir,
            standard_id=standard_id,
            title=title,
            role=role,
            local_path=path,
            enabled=role != "future_scope",
        )

    _write_standard(
        standards_dir,
        "docs/adamig.txt",
        "# ADSL\n[page 11]\nADSL must support subject-level analysis with one record per subject.\n",
    )
    _write_standard(
        standards_dir,
        "docs/occds.txt",
        "# ADAE\n[page 21]\nTreatment-emergent adverse event guidance should support TRTEMFL decisions.\n",
    )
    _write_standard(
        standards_dir,
        "docs/adam-model.txt",
        "# ADLB\n[page 31]\nADLB analysis value AVAL guidance should preserve laboratory analysis values.\n",
    )
    _write_standard(
        standards_dir,
        "docs/tte.txt",
        "# ADTTE\n[page 41]\nADTTE time-to-event guidance should document event and censoring concepts.\n",
    )
    _write_standard(
        standards_dir,
        "docs/ct.txt",
        "# Terminology\nADaM controlled terminology context may support analysis dataset review.\n",
    )
    _write_standard(
        standards_dir,
        "docs/rules.txt",
        "# Conformance\nADaM conformance context may support independent validation planning.\n",
    )
    _write_standard(
        standards_dir,
        "docs/sdtm.txt",
        "# SDTM\nSource-preserving SDTM preprocessing date guidance may support deterministic date handling.\n",
    )
    _write_standard(
        standards_dir,
        "docs/sdtmig.txt",
        "# SDTMIG\nSDTMIG source data context may be consulted as upstream reference only.\n",
    )
    _write_standard(
        standards_dir,
        "docs/examples.txt",
        "# Examples\nValidation reference examples are comparison evidence only.\n",
    )
    _write_standard(
        standards_dir,
        "docs/define.txt",
        "# Define-XML\nDefine-XML metadata content is future scope in Version 1.\n",
    )
    return standards_dir


def _sdtm_data():
    return {
        "DM": (
            {"STUDYID": "S1", "USUBJID": "01", "AGE": "64", "SEX": "F"},
            {"STUDYID": "S1", "USUBJID": "02", "AGE": "59", "SEX": "M"},
        ),
        "AE": (
            {"USUBJID": "01", "AESEQ": "1", "AETERM": "Headache", "AESTDTC": "2024-01-03"},
            {"USUBJID": "02", "AESEQ": "1", "AETERM": "Nausea", "AESTDTC": "2024-02-20"},
        ),
        "LB": (
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
        ),
        "DS": (
            {"USUBJID": "01", "DSDECOD": "DEATH", "DSSTDTC": "2024-02-01"},
            {"USUBJID": "02", "DSDECOD": "COMPLETED", "DSSTDTC": "2024-03-01"},
        ),
        "EX": (
            {"USUBJID": "01", "EXTRT": "A", "EXSTDTC": "2024-01-01", "EXENDTC": "2024-01-14"},
            {"USUBJID": "02", "EXTRT": "A", "EXSTDTC": "2024-01-03", "EXENDTC": "2024-01-17"},
        ),
        "SV": (
            {"USUBJID": "01", "SVSTDTC": "2024-01-02"},
            {"USUBJID": "02", "SVSTDTC": "2024-01-04"},
        ),
    }


def _study_decisions():
    from standards_driven_sdtm_adam.derivation import StudyDecision

    return (
        StudyDecision(
            decision_id="DECISION-SAFETY-POPULATION",
            question="What is the Safety Population?",
            affected_datasets=("ADSL",),
            affected_variables=("ADSL.SAFFL",),
            required_before_implementation=True,
            status="PROVIDED",
            value="Safety population includes all exposed subjects.",
        ),
        StudyDecision(
            decision_id="DECISION-TREATMENT-EMERGENT-WINDOW",
            question="What is the treatment-emergent window?",
            affected_datasets=("ADAE",),
            affected_variables=("ADAE.TRTEMFL",),
            required_before_implementation=True,
            status="PROVIDED",
            value="treatment_emergent_window=start through end plus 30 days",
        ),
        StudyDecision(
            decision_id="DECISION-TTE-EVENT-CENSOR",
            question="What are event and censoring rules?",
            affected_datasets=("ADTTE",),
            affected_variables=("ADTTE.ADT", "ADTTE.CNSR", "ADTTE.AVAL"),
            required_before_implementation=True,
            status="PROVIDED",
            value="origin=EX.EXSTDTC; event_terms=DEATH; censor_terms=COMPLETED; time_scale=days",
        ),
    )


def _run(tmp_path: Path, **overrides):
    registry_dir = overrides.pop("registry_dir", None) or _registry_dir(tmp_path)
    args = {
        "registry_dir": registry_dir,
        "task_intents": TASK_INTENTS,
        "research_objectives": OBJECTIVES,
        "sdtm_datasets": _sdtm_data(),
        "study_decisions": _study_decisions(),
    }
    args.update(overrides)
    return V1Pipeline().run(**args)


def test_v1_pipeline_happy_path_flows_through_all_runtime_boundaries(tmp_path):
    result = _run(tmp_path)

    assert {run.task_intent for run in result.discovery_runs} == set(TASK_INTENTS)
    assert {"adamig", "adam-occds", "adam-model", "adam-bds-tte"}.issubset(
        {record.standard_id for record in result.rule_extraction.evidence}
    )
    assert result.feasibility.results
    assert result.preprocessing_specification.operations
    assert result.preprocessing_execution.execution_records
    assert {spec.dataset for spec in result.adam_specification.dataset_specs} == {
        "ADSL",
        "ADAE",
        "ADLB",
        "ADTTE",
    }
    assert {"ADSL", "ADAE", "ADLB", "ADTTE"}.issubset(
        set(result.adam_execution.datasets)
    )
    assert result.validation.status == "PASS"
    assert result.evidence_resolution.items
    assert result.report.overall_status == "PASS"
    assert "Traceability and Evidence Summary" in result.markdown_report
    assert json.loads(result.json_report)["overall_status"] == "PASS"


def test_v1_pipeline_preserves_traceability_from_evidence_to_report(tmp_path):
    result = _run(tmp_path)

    usubjid = next(
        spec
        for spec in result.adam_specification.variable_specs
        if spec.dataset == "ADSL" and spec.variable == "USUBJID"
    )
    execution = next(
        record
        for record in result.adam_execution.execution_records
        if record.specification_id == usubjid.specification_id
    )
    validation = [
        item
        for item in result.validation.validation_results
        if item.specification_reference == usubjid.specification_id
    ]
    resolved = next(
        item
        for item in result.evidence_resolution.items
        if item.rule_specification_id == usubjid.specification_id
    )

    assert usubjid.evidence_references
    assert execution.evidence_references == usubjid.evidence_references
    assert validation
    assert resolved.citations
    assert resolved.citations[0].evidence_reference in usubjid.evidence_references
    assert resolved.citations[0].source_role == "primary_standard"
    assert usubjid.specification_id in result.markdown_report


def test_v1_pipeline_outputs_are_deterministic_for_identical_inputs(tmp_path):
    registry_dir = _registry_dir(tmp_path)
    first = _run(tmp_path, registry_dir=registry_dir)
    second = _run(tmp_path, registry_dir=registry_dir)

    assert first.adam_specification == second.adam_specification
    assert first.adam_execution == second.adam_execution
    assert first.validation == second.validation
    assert first.evidence_resolution == second.evidence_resolution
    assert first.report.to_dict() == second.report.to_dict()
    assert first.markdown_report == second.markdown_report
    assert first.json_report == second.json_report


def test_source_role_isolation_is_preserved_at_integration_level(tmp_path):
    registry_dir = _registry_dir(tmp_path)
    result = _run(
        tmp_path,
        registry_dir=registry_dir,
        task_intents=TASK_INTENTS + ("Prepare Define-XML metadata package",),
        evidence_resolution_requests=(
            DecisionEvidenceRequest(
                rule_specification_id="DEFINE.METADATA",
                decision_classification="STANDARD_REQUIRED",
                evidence_references=("define-xml:1",),
            ),
            DecisionEvidenceRequest(
                rule_specification_id="ADSL.EXAMPLE",
                decision_classification="STANDARD_REQUIRED",
                evidence_references=("adam-traceability-examples:1",),
            ),
        ),
    )

    discovered_ids = {
        item.standard_id
        for run in result.discovery_runs
        for item in run.results
    }
    future_ids = {
        item.standard_id
        for run in result.discovery_runs
        for item in run.excluded_future_scope
    }
    assert "adam-traceability-examples" not in discovered_ids
    assert "define-xml" not in discovered_ids
    assert "define-xml" in future_ids
    assert "adam-traceability-examples" not in {
        citation.source_id
        for item in result.evidence_resolution.items
        for citation in item.citations
        if citation.citation_purpose == "normative"
    }
    assert any(
        item.rule_specification_id == "DEFINE.METADATA"
        and item.resolution_status == "NO_VALID_STANDARD_EVIDENCE"
        for item in result.evidence_resolution.items
    )


def test_missing_required_source_propagates_to_validation_and_report_failure(tmp_path):
    sdtm = _sdtm_data()
    sdtm["LB"] = tuple(
        {key: value for key, value in record.items() if key != "LBSTRESN"}
        for record in sdtm["LB"]
    )

    result = _run(tmp_path, sdtm_datasets=sdtm)

    aval_execution = next(
        record
        for record in result.adam_execution.execution_records
        if record.dataset == "ADLB" and record.variable == "AVAL"
    )
    assert aval_execution.status == "BLOCKED"
    assert result.validation.status == "FAIL"
    assert result.report.overall_status == "FAIL"
    assert "Validation Failures" in result.markdown_report


def test_unsupported_derivation_requirement_is_specified_but_not_executed(tmp_path):
    result = _run(tmp_path, requested_variables=("ADLB.BASE",))

    base_spec = next(
        spec
        for spec in result.adam_specification.variable_specs
        if spec.dataset == "ADLB" and spec.variable == "BASE"
    )
    base_execution = next(
        record
        for record in result.adam_execution.execution_records
        if record.dataset == "ADLB" and record.variable == "BASE"
    )
    assert base_spec.classification == "UNSUPPORTED"
    assert not base_spec.implementation_allowed
    assert base_execution.status == "BLOCKED"
    assert "BASE" not in result.adam_execution.datasets.get("ADLB", ({},))[0]


def test_unresolved_required_evidence_is_reported_without_fabricated_citation(tmp_path):
    result = _run(
        tmp_path,
        evidence_resolution_requests=(
            DecisionEvidenceRequest(
                rule_specification_id="ADSL.MISSING-EVIDENCE",
                decision_classification="STANDARD_REQUIRED",
                evidence_references=("adamig:missing",),
            ),
        ),
    )

    missing = next(
        item
        for item in result.evidence_resolution.items
        if item.rule_specification_id == "ADSL.MISSING-EVIDENCE"
    )
    assert missing.resolution_status == "NO_VALID_STANDARD_EVIDENCE"
    assert missing.citations == ()
    assert missing.unresolved_evidence_references == ("adamig:missing",)
    assert "adamig:missing" in result.markdown_report


def test_v1_pipeline_proceeds_after_successful_standards_acquisition(tmp_path):
    registry_dir = _registry_dir(tmp_path)
    missing_source = registry_dir / "docs" / "adamig.txt"
    missing_source.unlink()

    class AuthorizedFixtureDownloader:
        def download(self, manifest, destination: Path) -> DownloadReceipt:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(
                "# ADSL\n[page 11]\nADSL must support subject-level analysis with one record per subject.\n",
                encoding="utf-8",
            )
            return DownloadReceipt(path=destination, authorized=True, message="fixture download")

    result = _run(
        tmp_path,
        registry_dir=registry_dir,
        standards_acquisition_downloader=AuthorizedFixtureDownloader(),
    )

    assert result.report.overall_status == "PASS"
    assert missing_source.exists()


def test_invalid_derivation_dependency_blocks_dependent_variable_in_integration(tmp_path):
    result = _run(
        tmp_path,
        adam_specification_transform=lambda spec: replace(
            spec,
            variable_specs=spec.variable_specs
            + (
                AdamVariableSpecification(
                    specification_id="ADAM-SPEC-ADAE-DEPENDENTX",
                    dataset="ADAE",
                    variable="DEPENDENTX",
                    label="Invalid Dependency Test",
                    purpose="Exercise dependency failure integration.",
                    source_domains=("AE",),
                    source_variables=("AE.AESTDTC",),
                    derivation_logic="Blocked because dependency is invalid.",
                    dependencies=("ADSL.DOESNOTEXIST",),
                    classification="DATA_ENGINEERING",
                    evidence_references=(),
                    user_defined_inputs=(),
                    assumptions=(),
                    validation_plan=("Confirm blocked dependency is not executed.",),
                    implementation_allowed=True,
                    unresolved_issues=(),
                ),
            ),
        ),
    )

    dependent = next(
        record
        for record in result.adam_execution.execution_records
        if record.variable == "DEPENDENTX"
    )
    assert dependent.status == "BLOCKED"
    assert "Dependency ADSL.DOESNOTEXIST did not complete successfully." in dependent.warnings
