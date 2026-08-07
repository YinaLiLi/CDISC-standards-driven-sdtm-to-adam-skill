from pathlib import Path

from standards_driven_sdtm_adam.discovery import StandardsDiscoveryEngine


REGISTRY_DIR = Path("config") / "standards"


def _result_ids(task_intent: str) -> list[str]:
    engine = StandardsDiscoveryEngine.from_registry_dir(REGISTRY_DIR)
    return [result.standard_id for result in engine.discover(task_intent).results]


def test_discovers_standards_for_adsl():
    result_ids = _result_ids("Create ADSL subject-level analysis dataset metadata")

    assert result_ids == [
        "adam-conformance-rules",
        "adam-ct",
        "adam-important-considerations",
        "adam-model",
        "adam-msg",
        "adamig",
    ]


def test_discovers_standards_for_adae():
    run = StandardsDiscoveryEngine.from_registry_dir(REGISTRY_DIR).discover(
        "Derive treatment-emergent adverse event variables for ADAE"
    )

    assert [result.standard_id for result in run.results] == [
        "adam-conformance-rules",
        "adam-ct",
        "adam-occds",
        "adamig",
    ]
    assert all(result.scope_category == "primary" for result in run.results)
    assert any("OCCDS" in result.relevance_reason for result in run.results)


def test_discovers_standards_for_adlb():
    result_ids = _result_ids("Plan ADLB laboratory analysis dataset development")

    assert result_ids == [
        "adam-conformance-rules",
        "adam-ct",
        "adam-model",
        "adamig",
    ]


def test_discovers_standards_for_adtte():
    result_ids = _result_ids("Identify standards for ADTTE time-to-event output")

    assert result_ids == [
        "adam-bds-tte",
        "adam-conformance-rules",
        "adam-ct",
        "adamig",
    ]


def test_discovers_upstream_reference_for_sdtm_preprocessing_intent():
    run = StandardsDiscoveryEngine.from_registry_dir(REGISTRY_DIR).discover(
        "Evaluate source-preserving SDTM preprocessing for source SDTM inputs"
    )

    assert [result.standard_id for result in run.results] == ["sdtm-model", "sdtmig"]
    assert run.upstream_only
    assert all(result.scope_category == "upstream_reference" for result in run.results)
    assert all("upstream reference only" in result.relevance_reason for result in run.results)


def test_reports_missing_local_standard_file(tmp_path):
    standards_dir = tmp_path / "standards"
    standards_dir.mkdir()
    manifest = """schema_version: 1
standard:
  id: adamig
  title: ADaM Implementation Guide
  version: "1.3"
  scope_category: primary
  official_url: null
  local_path: missing-adamig.pdf
  sha256: null
  indexed: false
  verified: false
  enabled: true
"""
    (standards_dir / "adamig.yaml").write_text(manifest, encoding="utf-8")

    run = StandardsDiscoveryEngine.from_registry_dir(standards_dir).discover(
        "Derive ADSL analysis dataset"
    )

    assert len(run.results) == 1
    assert run.results[0].standard_id == "adamig"
    assert run.results[0].availability_status == "local_file_missing"


def test_unsupported_request_returns_no_applicable_standard():
    run = StandardsDiscoveryEngine.from_registry_dir(REGISTRY_DIR).discover(
        "Build an oncology listing dashboard"
    )

    assert run.results == ()
    assert run.no_applicable_standard


def test_future_scope_request_is_detected_but_not_used():
    run = StandardsDiscoveryEngine.from_registry_dir(REGISTRY_DIR).discover(
        "Prepare Define-XML metadata package"
    )

    assert run.results == ()
    assert run.no_applicable_standard
    assert [result.standard_id for result in run.excluded_future_scope] == ["define-xml"]
    assert run.excluded_future_scope[0].scope_category == "future_scope"
