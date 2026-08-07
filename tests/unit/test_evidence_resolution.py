from pathlib import Path

from standards_driven_sdtm_adam.derivation.model import AdamVariableSpecification
from standards_driven_sdtm_adam.extraction.model import EvidenceRecord, RuleExtractionRun
from standards_driven_sdtm_adam.standards import StandardsRegistry
from standards_driven_sdtm_adam.traceability import (
    DecisionEvidenceRequest,
    EvidenceResolver,
)


def _write_manifest(
    standards_dir: Path,
    *,
    standard_id: str,
    title: str,
    version: str | None = "1.0",
    role: str = "primary_standard",
    release_date: str | None = "2026-03-27",
    original_filename: str | None = None,
    enabled: bool = True,
) -> None:
    version_value = "null" if version is None else f'"{version}"'
    release_date_value = "null" if release_date is None else f'"{release_date}"'
    original_filename_value = (
        "null" if original_filename is None else f'"{original_filename}"'
    )
    manifest = f"""schema_version: 1
standard:
  id: {standard_id}
  title: {title}
  role: {role}
  version: {version_value}
  release_date: {release_date_value}
  official_url: https://example.org/{standard_id}
  package_url: null
  local_path: null
  local_root: null
  original_filename: {original_filename_value}
  sha256: null
  sha256_status: NOT_APPLICABLE
  verification_status: UNVERIFIED
  indexed: false
  verified: false
  enabled: {str(enabled).lower()}
"""
    (standards_dir / f"{standard_id}.yaml").write_text(manifest, encoding="utf-8")


def _registry(tmp_path: Path, *manifest_kwargs: dict[str, object]) -> StandardsRegistry:
    standards_dir = tmp_path / "standards"
    standards_dir.mkdir()
    for kwargs in manifest_kwargs:
        _write_manifest(standards_dir, **kwargs)
    return StandardsRegistry.load(standards_dir, validate_integrity=False)


def _evidence(
    evidence_id: str,
    *,
    standard_id: str = "adamig",
    standard_title: str = "ADaM Implementation Guide",
    version: str | None = "1.3",
    evidence_type: str = "RULE",
    section: str | None = "ADSL",
    page: int | None = 12,
    short_quote: str | None = "ADSL must include one record per subject.",
    extraction_status: str = "EXTRACTED",
) -> EvidenceRecord:
    return EvidenceRecord(
        evidence_id=evidence_id,
        standard_id=standard_id,
        standard_title=standard_title,
        version=version,
        evidence_type=evidence_type,
        section=section,
        page=page,
        short_quote=short_quote,
        source_local_path=None,
        official_url=f"https://example.org/{standard_id}",
        search_context="metadata_search: adsl",
        extraction_status=extraction_status,
    )


def _run(*records: EvidenceRecord) -> RuleExtractionRun:
    return RuleExtractionRun(task_intent="Create ADSL", evidence=records)


def _variable_spec(
    *,
    specification_id: str = "ADSL.USUBJID",
    classification: str = "STANDARD_REQUIRED",
    evidence_references: tuple[str, ...] = ("adamig:1",),
) -> AdamVariableSpecification:
    return AdamVariableSpecification(
        specification_id=specification_id,
        dataset="ADSL",
        variable="USUBJID",
        label="Unique Subject Identifier",
        purpose="Identify subject records.",
        source_domains=("DM",),
        source_variables=("USUBJID",),
        derivation_logic="Copy from DM.USUBJID.",
        dependencies=(),
        classification=classification,
        evidence_references=evidence_references,
        user_defined_inputs=(),
        assumptions=(),
        validation_plan=(),
        implementation_allowed=True,
        unresolved_issues=(),
    )


def test_resolves_primary_standard_evidence_for_specification_item(tmp_path):
    registry = _registry(
        tmp_path,
        {
            "standard_id": "adamig",
            "title": "ADaM Implementation Guide",
            "version": "1.3",
            "role": "primary_standard",
            "release_date": "2024-11-29",
            "original_filename": "adamig-v1-3.pdf",
        },
    )

    result = EvidenceResolver(registry).resolve(
        [_variable_spec()],
        _run(_evidence("adamig:1")),
    )

    resolved = result.items[0]
    assert resolved.rule_specification_id == "ADSL.USUBJID"
    assert resolved.decision_classification == "STANDARD_REQUIRED"
    assert resolved.resolution_status == "RESOLVED"
    assert resolved.unresolved_evidence_references == ()
    citation = resolved.citations[0]
    assert citation.source_id == "adamig"
    assert citation.source_role == "primary_standard"
    assert citation.document_title == "ADaM Implementation Guide"
    assert citation.official_filename == "adamig-v1-3.pdf"
    assert citation.standard_version == "1.3"
    assert citation.standard_release_date == "2024-11-29"
    assert citation.page == 12
    assert citation.section == "ADSL"
    assert citation.decision_classification == "STANDARD_REQUIRED"
    assert citation.rule_specification_id == "ADSL.USUBJID"


def test_preserves_multiple_supporting_citations_in_deterministic_order(tmp_path):
    registry = _registry(
        tmp_path,
        {
            "standard_id": "adamig",
            "title": "ADaM Implementation Guide",
            "role": "primary_standard",
        },
        {
            "standard_id": "adam-model",
            "title": "ADaM Model",
            "role": "primary_standard",
        },
        {
            "standard_id": "sdtm-model",
            "title": "SDTM Model",
            "role": "upstream_reference",
        },
    )
    records = (
        _evidence("sdtm-model:1", standard_id="sdtm-model", evidence_type="CONTEXT"),
        _evidence("adamig:2", page=14),
        _evidence("adam-model:1", standard_id="adam-model", page=2),
    )

    result = EvidenceResolver(registry).resolve(
        [
            _variable_spec(
                evidence_references=("sdtm-model:1", "adamig:2", "adam-model:1")
            )
        ],
        _run(*records),
    )

    assert [citation.evidence_reference for citation in result.items[0].citations] == [
        "adam-model:1",
        "adamig:2",
        "sdtm-model:1",
    ]
    assert [citation.source_role for citation in result.items[0].citations] == [
        "primary_standard",
        "primary_standard",
        "upstream_reference",
    ]


def test_missing_evidence_is_explicit_and_does_not_fabricate_citation(tmp_path):
    registry = _registry(
        tmp_path,
        {
            "standard_id": "adamig",
            "title": "ADaM Implementation Guide",
            "role": "primary_standard",
        },
    )

    result = EvidenceResolver(registry).resolve(
        [_variable_spec(evidence_references=("adamig:missing",))],
        _run(_evidence("adamig:1")),
    )

    resolved = result.items[0]
    assert resolved.resolution_status == "NO_VALID_STANDARD_EVIDENCE"
    assert resolved.citations == ()
    assert resolved.unresolved_evidence_references == ("adamig:missing",)


def test_validation_reference_isolated_from_normative_decision_evidence(tmp_path):
    registry = _registry(
        tmp_path,
        {
            "standard_id": "adam-example",
            "title": "ADaM Example Package",
            "role": "validation_reference",
        },
    )

    result = EvidenceResolver(registry).resolve(
        [_variable_spec(evidence_references=("adam-example:1",))],
        _run(_evidence("adam-example:1", standard_id="adam-example")),
    )

    resolved = result.items[0]
    assert resolved.resolution_status == "NO_VALID_STANDARD_EVIDENCE"
    assert resolved.citations == ()
    assert resolved.excluded_evidence_references == ("adam-example:1",)


def test_validation_reference_allowed_only_as_validation_support(tmp_path):
    registry = _registry(
        tmp_path,
        {
            "standard_id": "adam-example",
            "title": "ADaM Example Package",
            "role": "validation_reference",
        },
    )
    request = DecisionEvidenceRequest(
        rule_specification_id="VALIDATE.ADSL",
        decision_classification="EXAMPLE_ADAPTED",
        evidence_references=("adam-example:1",),
        evidence_use="validation_support",
    )

    result = EvidenceResolver(registry).resolve(
        [request],
        _run(_evidence("adam-example:1", standard_id="adam-example")),
    )

    citation = result.items[0].citations[0]
    assert citation.source_role == "validation_reference"
    assert citation.citation_purpose == "validation_support"
    assert result.items[0].resolution_status == "RESOLVED"


def test_future_scope_evidence_is_excluded_from_runtime_resolution(tmp_path):
    registry = _registry(
        tmp_path,
        {
            "standard_id": "define-xml",
            "title": "Define-XML",
            "role": "future_scope",
            "enabled": False,
        },
    )

    result = EvidenceResolver(registry).resolve(
        [
            _variable_spec(
                specification_id="DEFINE.METADATA",
                evidence_references=("define-xml:1",),
            )
        ],
        _run(_evidence("define-xml:1", standard_id="define-xml")),
    )

    assert result.items[0].resolution_status == "NO_VALID_STANDARD_EVIDENCE"
    assert result.items[0].citations == ()
    assert result.items[0].excluded_evidence_references == ("define-xml:1",)


def test_non_standard_classification_is_preserved_without_forced_standard_citation(tmp_path):
    registry = _registry(
        tmp_path,
        {
            "standard_id": "adamig",
            "title": "ADaM Implementation Guide",
            "role": "primary_standard",
        },
    )
    request = DecisionEvidenceRequest(
        rule_specification_id="ADSL.STUDYFLAG",
        decision_classification="STUDY_SPECIFIC",
        evidence_references=("adamig:1",),
    )

    result = EvidenceResolver(registry).resolve(
        [request],
        _run(_evidence("adamig:1")),
    )

    resolved = result.items[0]
    assert resolved.decision_classification == "STUDY_SPECIFIC"
    assert resolved.resolution_status == "NON_STANDARD_DECISION"
    assert resolved.citations == ()
    assert resolved.unresolved_evidence_references == ()


def test_primary_standard_precedence_over_validation_reference(tmp_path):
    registry = _registry(
        tmp_path,
        {
            "standard_id": "adamig",
            "title": "ADaM Implementation Guide",
            "role": "primary_standard",
        },
        {
            "standard_id": "adam-example",
            "title": "ADaM Example Package",
            "role": "validation_reference",
        },
    )

    result = EvidenceResolver(registry).resolve(
        [
            _variable_spec(
                evidence_references=("adam-example:1", "adamig:1")
            )
        ],
        _run(
            _evidence("adam-example:1", standard_id="adam-example"),
            _evidence("adamig:1"),
        ),
    )

    assert [citation.source_id for citation in result.items[0].citations] == ["adamig"]
    assert result.items[0].excluded_evidence_references == ("adam-example:1",)
