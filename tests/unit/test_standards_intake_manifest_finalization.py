from pathlib import Path

from standards_driven_sdtm_adam.discovery import StandardsDiscoveryEngine
from standards_driven_sdtm_adam.extraction import RuleExtractionEngine
from standards_driven_sdtm_adam.standards import StandardsRegistry


REGISTRY_DIR = Path("config") / "standards"


def _write_manifest(
    standards_dir: Path,
    *,
    source_id: str,
    title: str,
    role: str,
    local_path: str,
    version: str | None = "1.0",
    release_date: str | None = None,
    enabled: bool = True,
    sha256: str | None = None,
    verification_status: str = "UNVERIFIED",
) -> None:
    version_value = "null" if version is None else f'"{version}"'
    release_value = "null" if release_date is None else f'"{release_date}"'
    sha_value = "null" if sha256 is None else f'"{sha256}"'
    manifest = f"""schema_version: 1
standard:
  id: {source_id}
  title: {title}
  role: {role}
  version: {version_value}
  release_date: {release_value}
  official_url: https://example.org/{source_id}
  local_path: {local_path}
  original_filename: {Path(local_path).name}
  sha256: {sha_value}
  verification_status: {verification_status}
  indexed: false
  verified: false
  enabled: {str(enabled).lower()}
"""
    (standards_dir / f"{source_id}.yaml").write_text(manifest, encoding="utf-8")


def _write_source(standards_dir: Path, relative_path: str, content: str) -> None:
    path = standards_dir / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_controlled_terminology_uses_observed_release_date_without_fabricated_version():
    registry = StandardsRegistry.load(REGISTRY_DIR, validate_integrity=False)

    manifest = registry.get("adam-ct")

    assert manifest.title == "ADaM Controlled Terminology"
    assert manifest.role == "primary_standard"
    assert manifest.version is None
    assert manifest.release_date == "2026-03-27"
    assert manifest.original_filename == "ADaM Terminology.xls"


def test_package_metadata_supports_msg_example_submission_package():
    registry = StandardsRegistry.load(REGISTRY_DIR, validate_integrity=False)

    manifest = registry.get("adam-msg-example-submission")

    assert manifest.role == "validation_reference"
    assert manifest.verification_status == "PARTIALLY_VERIFIED"
    assert manifest.package_url == "https://www.cdisc.org/system/files/members/standard/foundational/ADaM-MSG-Example-Submission-Package_1.zip"
    assert manifest.package_version == "1.0"
    assert manifest.local_root == "../../docs/standards/ADaM/examples/ADaM_MSG_Example_Submission"
    assert "datasets/adsl.xpt" in manifest.members
    assert "programs/adsl-sas.txt" in manifest.members
    assert registry.missing_package_members(manifest) == ()


def test_original_filenames_are_preserved_for_primary_standards():
    registry = StandardsRegistry.load(REGISTRY_DIR, validate_integrity=False)

    filenames = {manifest.id: manifest.original_filename for manifest in registry.all()}

    assert filenames["adam-model"] == "analysis_data_model_v2.1.pdf"
    assert filenames["adam-important-considerations"] == "Important Considerations When Using ADaM v2.1.pdf"
    assert filenames["adam-occds"] == "ADaM_OCCDS_Implementation_Guide v1.1.pdf"
    assert filenames["adam-conformance-rules"] == "ADaM Conformance Rules v5.0.xlsx"


def test_primary_standard_has_sha256_and_file_available_status():
    registry = StandardsRegistry.load(REGISTRY_DIR, validate_integrity=False)
    manifest = registry.get("adamig")

    assert manifest.sha256 is not None
    assert manifest.sha256_status == "PRESENT"
    assert manifest.verification_status == "VERIFIED"
    assert registry.resolve_local_path(manifest).exists()
    assert registry.local_file_status(manifest) == "AVAILABLE"


def test_controlled_terminology_mismatch_is_not_converted_to_verified():
    registry = StandardsRegistry.load(REGISTRY_DIR, validate_integrity=False)
    manifest = registry.get("adam-ct")

    assert manifest.release_date == "2026-03-27"
    assert manifest.verification_status == "VERIFIED"
    assert manifest.verified


def test_conformance_rules_are_partially_verified_from_workbook_content():
    registry = StandardsRegistry.load(REGISTRY_DIR, validate_integrity=False)
    manifest = registry.get("adam-conformance-rules")

    assert manifest.version == "5.0"
    assert manifest.verification_status == "PARTIALLY_VERIFIED"


def test_validation_reference_cannot_enter_primary_rule_discovery(tmp_path):
    standards_dir = tmp_path / "standards"
    standards_dir.mkdir()
    _write_manifest(
        standards_dir,
        source_id="adam-reference-example",
        title="ADaM Reference Example",
        role="validation_reference",
        local_path="docs/example.txt",
    )
    _write_source(
        standards_dir,
        "docs/example.txt",
        "ADSL example text says values must appear in a demonstration dataset.",
    )

    run = StandardsDiscoveryEngine.from_registry_dir(standards_dir).discover("Create ADSL")

    assert run.results == ()
    assert run.no_applicable_standard


def test_validation_reference_cannot_produce_standard_required_evidence(tmp_path):
    standards_dir = tmp_path / "standards"
    standards_dir.mkdir()
    _write_manifest(
        standards_dir,
        source_id="adam-reference-example",
        title="ADaM Reference Example",
        role="validation_reference",
        local_path="docs/example.txt",
    )
    _write_source(
        standards_dir,
        "docs/example.txt",
        "# ADSL\nADSL example text says values must be populated for this example.",
    )

    run = RuleExtractionEngine.from_registry_dir(standards_dir).extract("Create ADSL")

    assert run.evidence == ()
    assert run.no_relevant_evidence


def test_primary_standard_remains_eligible_for_discovery_and_evidence(tmp_path):
    standards_dir = tmp_path / "standards"
    standards_dir.mkdir()
    _write_manifest(
        standards_dir,
        source_id="adamig",
        title="ADaM Implementation Guide",
        role="primary_standard",
        version="1.3",
        local_path="docs/adamig.txt",
    )
    _write_source(
        standards_dir,
        "docs/adamig.txt",
        "# ADSL\nADSL guidance should be consulted for subject-level analysis.",
    )

    discovery = StandardsDiscoveryEngine.from_registry_dir(standards_dir).discover("Create ADSL")
    extraction = RuleExtractionEngine.from_registry_dir(standards_dir).extract("Create ADSL")

    assert [result.standard_id for result in discovery.results] == ["adamig"]
    assert [record.standard_id for record in extraction.evidence] == ["adamig"]


def test_upstream_reference_is_used_only_for_eligible_upstream_context(tmp_path):
    standards_dir = tmp_path / "standards"
    standards_dir.mkdir()
    _write_manifest(
        standards_dir,
        source_id="sdtm",
        title="Study Data Tabulation Model",
        role="upstream_reference",
        version=None,
        local_path="docs/sdtm.txt",
    )
    _write_source(
        standards_dir,
        "docs/sdtm.txt",
        "# SDTM\nSDTM source-preserving preprocessing context.",
    )

    adam_run = StandardsDiscoveryEngine.from_registry_dir(standards_dir).discover("Create ADSL")
    upstream_run = StandardsDiscoveryEngine.from_registry_dir(standards_dir).discover(
        "Evaluate source-preserving SDTM preprocessing"
    )

    assert adam_run.results == ()
    assert [result.standard_id for result in upstream_run.results] == ["sdtm"]


def test_runtime_load_does_not_require_sha256_recomputation(tmp_path):
    standards_dir = tmp_path / "standards"
    standards_dir.mkdir()
    _write_manifest(
        standards_dir,
        source_id="adamig",
        title="ADaM Implementation Guide",
        role="primary_standard",
        version="1.3",
        local_path="docs/adamig.txt",
        sha256="0" * 64,
        verification_status="UNVERIFIED",
    )
    _write_source(standards_dir, "docs/adamig.txt", "# ADSL\nADSL guidance should be consulted.")

    registry = StandardsRegistry.load(standards_dir)

    assert registry.get("adamig").verification_status == "UNVERIFIED"
    assert registry.local_file_status(registry.get("adamig")) == "AVAILABLE"


def test_runtime_can_use_available_standard_without_developer_verification(tmp_path):
    standards_dir = tmp_path / "standards"
    standards_dir.mkdir()
    _write_manifest(
        standards_dir,
        source_id="adamig",
        title="ADaM Implementation Guide",
        role="primary_standard",
        version="1.3",
        local_path="docs/adamig.txt",
        verification_status="UNVERIFIED",
    )
    _write_source(standards_dir, "docs/adamig.txt", "# ADSL\nADSL guidance should be consulted.")

    discovery = StandardsDiscoveryEngine.from_registry_dir(standards_dir).discover("Create ADSL")
    extraction = RuleExtractionEngine.from_registry_dir(standards_dir).extract("Create ADSL")

    assert [result.standard_id for result in discovery.results] == ["adamig"]
    assert [record.standard_id for record in extraction.evidence] == ["adamig"]


def test_unavailable_runtime_source_still_fails_safely(tmp_path):
    standards_dir = tmp_path / "standards"
    standards_dir.mkdir()
    _write_manifest(
        standards_dir,
        source_id="adamig",
        title="ADaM Implementation Guide",
        role="primary_standard",
        version="1.3",
        local_path="docs/missing.txt",
        verification_status="UNVERIFIED",
    )

    run = RuleExtractionEngine.from_registry_dir(standards_dir).extract("Create ADSL")

    assert run.evidence[0].extraction_status == "STANDARD_FILE_UNAVAILABLE"


def test_developer_setup_can_explicitly_calculate_sha256(tmp_path):
    standards_dir = tmp_path / "standards"
    standards_dir.mkdir()
    _write_manifest(
        standards_dir,
        source_id="adamig",
        title="ADaM Implementation Guide",
        role="primary_standard",
        version="1.3",
        local_path="docs/adamig.txt",
    )
    _write_source(standards_dir, "docs/adamig.txt", "ADSL guidance")
    registry = StandardsRegistry.load(standards_dir)
    manifest = registry.get("adamig")

    digest = registry.calculate_sha256(manifest)

    assert len(digest) == 64
    assert registry.sha256_status(manifest) == "MISSING"


def test_developer_setup_can_explicitly_detect_sha256_mismatch(tmp_path):
    standards_dir = tmp_path / "standards"
    standards_dir.mkdir()
    _write_manifest(
        standards_dir,
        source_id="adamig",
        title="ADaM Implementation Guide",
        role="primary_standard",
        version="1.3",
        local_path="docs/adamig.txt",
        sha256="0" * 64,
    )
    _write_source(standards_dir, "docs/adamig.txt", "ADSL guidance")
    registry = StandardsRegistry.load(standards_dir)

    assert registry.sha256_status(registry.get("adamig")) == "MISMATCH"
