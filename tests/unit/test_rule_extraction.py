from pathlib import Path

from standards_driven_sdtm_adam.extraction import RuleExtractionEngine


def _write_manifest(
    standards_dir: Path,
    *,
    standard_id: str,
    title: str,
    version: str | None,
    local_path: str | None,
    scope_category: str = "primary",
    enabled: bool = True,
    official_url: str | None = "https://example.org/standard",
) -> None:
    version_value = "null" if version is None else f'"{version}"'
    local_path_value = "null" if local_path is None else local_path
    official_url_value = "null" if official_url is None else official_url
    manifest = f"""schema_version: 1
standard:
  id: {standard_id}
  title: {title}
  version: {version_value}
  scope_category: {scope_category}
  official_url: {official_url_value}
  local_path: {local_path_value}
  sha256: null
  indexed: false
  verified: false
  enabled: {str(enabled).lower()}
"""
    (standards_dir / f"{standard_id}.yaml").write_text(manifest, encoding="utf-8")


def _write_standard(standards_dir: Path, relative_path: str, content: str) -> None:
    path = standards_dir / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _engine(tmp_path: Path) -> tuple[RuleExtractionEngine, Path]:
    standards_dir = tmp_path / "standards"
    standards_dir.mkdir()
    return RuleExtractionEngine.from_registry_dir(standards_dir), standards_dir


def test_extracts_adsl_evidence_from_local_registered_standards(tmp_path):
    _, standards_dir = _engine(tmp_path)
    _write_manifest(
        standards_dir,
        standard_id="adamig",
        title="ADaM Implementation Guide",
        version="1.3",
        local_path="docs/adamig.txt",
    )
    _write_standard(
        standards_dir,
        "docs/adamig.txt",
        """# ADSL Subject-Level Analysis Dataset
[page 5]
ADSL guidance should describe subject-level analysis dataset concepts and population flags.
""",
    )

    run = RuleExtractionEngine.from_registry_dir(standards_dir).extract(
        "Create ADSL subject-level analysis dataset"
    )

    assert len(run.evidence) == 1
    record = run.evidence[0]
    assert record.standard_id == "adamig"
    assert record.evidence_type == "GUIDANCE"
    assert record.section == "ADSL Subject-Level Analysis Dataset"
    assert record.page == 5
    assert "ADSL guidance" in record.short_quote
    assert record.extraction_status == "EXTRACTED"


def test_extracts_adae_adverse_event_evidence_from_multiple_standards(tmp_path):
    _, standards_dir = _engine(tmp_path)
    _write_manifest(
        standards_dir,
        standard_id="adamig",
        title="ADaM Implementation Guide",
        version="1.3",
        local_path="docs/adamig.txt",
    )
    _write_manifest(
        standards_dir,
        standard_id="adam-occds",
        title="ADaM OCCDS Implementation Guide",
        version="1.1",
        local_path="docs/occds.txt",
    )
    _write_manifest(
        standards_dir,
        standard_id="adam-ct",
        title="ADaM Controlled Terminology",
        version=None,
        local_path="docs/ct.txt",
    )
    _write_standard(
        standards_dir,
        "docs/adamig.txt",
        """# ADAE Context
ADAE context discusses adverse events in an analysis dataset.
""",
    )
    _write_standard(
        standards_dir,
        "docs/occds.txt",
        """# Adverse Events
[page 12]
Treatment-emergent adverse event guidance should be reviewed for ADAE development.
""",
    )
    _write_standard(
        standards_dir,
        "docs/ct.txt",
        """# Terminology
Example: adverse event terminology values may be shown for illustration.
""",
    )

    run = RuleExtractionEngine.from_registry_dir(standards_dir).extract(
        "Derive treatment-emergent adverse event variables for ADAE"
    )

    assert {record.standard_id for record in run.evidence} == {
        "adam-ct",
        "adam-occds",
        "adamig",
    }
    example_records = [
        record for record in run.evidence if record.standard_id == "adam-ct"
    ]
    assert example_records[0].evidence_type == "EXAMPLE"
    assert example_records[0].evidence_type != "RULE"


def test_extracts_adlb_laboratory_analysis_evidence(tmp_path):
    _, standards_dir = _engine(tmp_path)
    _write_manifest(
        standards_dir,
        standard_id="adam-model",
        title="ADaM Model",
        version="2.1",
        local_path="docs/adam-model.txt",
    )
    _write_standard(
        standards_dir,
        "docs/adam-model.txt",
        """# Laboratory Analysis
The ADLB laboratory analysis context may include baseline and analysis value concepts.
""",
    )

    run = RuleExtractionEngine.from_registry_dir(standards_dir).extract(
        "Plan ADLB laboratory analysis"
    )

    assert len(run.evidence) == 1
    assert run.evidence[0].standard_id == "adam-model"
    assert run.evidence[0].evidence_type == "GUIDANCE"


def test_extracts_adtte_time_to_event_evidence(tmp_path):
    _, standards_dir = _engine(tmp_path)
    _write_manifest(
        standards_dir,
        standard_id="adam-bds-tte",
        title="ADaM BDS Time-to-Event Guide",
        version="1.0",
        local_path="docs/tte.txt",
    )
    _write_standard(
        standards_dir,
        "docs/tte.txt",
        """# Time-to-Event
[page 20]
A time-to-event definition is defined as an analysis concept involving event or censoring information.
""",
    )

    run = RuleExtractionEngine.from_registry_dir(standards_dir).extract(
        "Identify evidence for ADTTE time-to-event output"
    )

    assert len(run.evidence) == 1
    assert run.evidence[0].standard_id == "adam-bds-tte"
    assert run.evidence[0].evidence_type == "DEFINITION"
    assert run.evidence[0].page == 20


def test_extracts_treatment_emergent_concept_without_dataset_token(tmp_path):
    _, standards_dir = _engine(tmp_path)
    _write_manifest(
        standards_dir,
        standard_id="adam-occds",
        title="ADaM OCCDS Implementation Guide",
        version="1.1",
        local_path="docs/occds.txt",
    )
    _write_standard(
        standards_dir,
        "docs/occds.txt",
        """# Treatment-Emergent Concepts
Treatment-emergent guidance may be relevant to adverse event analysis.
""",
    )

    run = RuleExtractionEngine.from_registry_dir(standards_dir).extract(
        "Find treatment-emergent concepts"
    )

    assert len(run.evidence) == 1
    assert run.evidence[0].standard_id == "adam-occds"


def test_extracts_sdtm_preprocessing_evidence_as_upstream_reference(tmp_path):
    _, standards_dir = _engine(tmp_path)
    _write_manifest(
        standards_dir,
        standard_id="sdtm-model",
        title="Study Data Tabulation Model",
        version=None,
        scope_category="upstream_reference",
        local_path="docs/sdtm.txt",
    )
    _write_standard(
        standards_dir,
        "docs/sdtm.txt",
        """# SDTM Source Data
SDTM source-preserving preprocessing context may be consulted as upstream reference only.
""",
    )

    run = RuleExtractionEngine.from_registry_dir(standards_dir).extract(
        "Evaluate source-preserving SDTM preprocessing concepts"
    )

    assert len(run.evidence) == 1
    assert run.evidence[0].standard_id == "sdtm-model"
    assert run.evidence[0].evidence_type == "GUIDANCE"


def test_missing_local_standard_does_not_fabricate_citation(tmp_path):
    _, standards_dir = _engine(tmp_path)
    _write_manifest(
        standards_dir,
        standard_id="adamig",
        title="ADaM Implementation Guide",
        version="1.3",
        local_path="docs/missing.txt",
    )

    run = RuleExtractionEngine.from_registry_dir(standards_dir).extract(
        "Create ADSL subject-level analysis dataset"
    )

    assert len(run.evidence) == 1
    record = run.evidence[0]
    assert record.extraction_status == "STANDARD_FILE_UNAVAILABLE"
    assert record.short_quote is None
    assert record.section is None
    assert record.page is None


def test_no_relevant_evidence_does_not_fabricate_citation(tmp_path):
    _, standards_dir = _engine(tmp_path)
    _write_manifest(
        standards_dir,
        standard_id="adamig",
        title="ADaM Implementation Guide",
        version="1.3",
        local_path="docs/adamig.txt",
    )
    _write_standard(
        standards_dir,
        "docs/adamig.txt",
        """# Unrelated Topic
This paragraph discusses a topic unrelated to the requested dataset.
""",
    )

    run = RuleExtractionEngine.from_registry_dir(standards_dir).extract(
        "Create ADSL subject-level analysis dataset"
    )

    assert run.evidence == ()
    assert run.no_relevant_evidence


def test_future_scope_request_does_not_extract_define_xml(tmp_path):
    _, standards_dir = _engine(tmp_path)
    _write_manifest(
        standards_dir,
        standard_id="define-xml",
        title="Define-XML",
        version=None,
        scope_category="future_scope",
        enabled=False,
        local_path="docs/define.txt",
    )
    _write_standard(
        standards_dir,
        "docs/define.txt",
        """# Define-XML
Define-XML metadata content is outside Version 1 scope.
""",
    )

    run = RuleExtractionEngine.from_registry_dir(standards_dir).extract(
        "Prepare Define-XML metadata package"
    )

    assert run.evidence == ()
    assert run.no_relevant_evidence


def test_text_extraction_failure_does_not_fabricate_quote(tmp_path):
    _, standards_dir = _engine(tmp_path)
    _write_manifest(
        standards_dir,
        standard_id="adamig",
        title="ADaM Implementation Guide",
        version="1.3",
        local_path="docs/adamig.docx",
    )
    _write_standard(standards_dir, "docs/adamig.docx", "ADSL content")

    run = RuleExtractionEngine.from_registry_dir(standards_dir).extract(
        "Create ADSL subject-level analysis dataset"
    )

    assert len(run.evidence) == 1
    assert run.evidence[0].extraction_status == "TEXT_EXTRACTION_FAILED"
    assert run.evidence[0].short_quote is None
