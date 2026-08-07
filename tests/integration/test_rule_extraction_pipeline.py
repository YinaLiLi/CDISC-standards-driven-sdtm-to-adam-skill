from pathlib import Path

import pytest

from standards_driven_sdtm_adam.extraction import RuleExtractionEngine


def _write_manifest(
    standards_dir: Path,
    standard_id: str,
    title: str,
    version: str | None,
    scope_category: str,
    local_path: str,
) -> None:
    version_value = "null" if version is None else f'"{version}"'
    manifest = f"""schema_version: 1
standard:
  id: {standard_id}
  title: {title}
  version: {version_value}
  scope_category: {scope_category}
  official_url: https://example.org/{standard_id}
  local_path: {local_path}
  sha256: null
  indexed: false
  verified: false
  enabled: true
"""
    (standards_dir / f"{standard_id}.yaml").write_text(manifest, encoding="utf-8")


def _write_standard(standards_dir: Path, relative_path: str, text: str) -> None:
    path = standards_dir / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture()
def registry_dir(tmp_path):
    standards_dir = tmp_path / "standards"
    standards_dir.mkdir()
    manifests = [
        ("adamig", "ADaM Implementation Guide", "1.3", "primary", "docs/adamig.md"),
        ("adam-model", "ADaM Model", "2.1", "primary", "docs/adam-model.md"),
        ("adam-occds", "ADaM OCCDS Implementation Guide", "1.1", "primary", "docs/occds.md"),
        ("adam-bds-tte", "ADaM BDS Time-to-Event Guide", "1.0", "primary", "docs/tte.md"),
        ("adam-ct", "ADaM Controlled Terminology", None, "primary", "docs/ct.md"),
        ("adam-conformance-rules", "ADaM Conformance Rules", "5.0", "primary", "docs/rules.md"),
        ("sdtm-model", "Study Data Tabulation Model", None, "upstream_reference", "docs/sdtm.md"),
        ("sdtmig", "SDTM Implementation Guide", None, "upstream_reference", "docs/sdtmig.md"),
    ]
    for manifest in manifests:
        _write_manifest(standards_dir, *manifest)

    _write_standard(standards_dir, "docs/adamig.md", "# ADSL\nADSL guidance should be consulted for subject-level analysis.\n\n# ADLB\nADLB laboratory analysis guidance may be relevant.\n")
    _write_standard(standards_dir, "docs/adam-model.md", "# ADLB\nThe ADLB laboratory analysis context includes analysis values.\n")
    _write_standard(standards_dir, "docs/occds.md", "# ADAE\nTreatment-emergent adverse event guidance should be reviewed for ADAE.\n")
    _write_standard(standards_dir, "docs/tte.md", "# ADTTE\nTime-to-event definition is defined as event or censoring analysis context.\n")
    _write_standard(standards_dir, "docs/ct.md", "# Terminology\nExample: ADaM terminology values may support adverse event review.\n")
    _write_standard(standards_dir, "docs/rules.md", "# Conformance\nADaM conformance rules may be consulted after extraction.\n")
    _write_standard(standards_dir, "docs/sdtm.md", "# SDTM\nSDTM source-preserving preprocessing guidance may be used as upstream reference only.\n")
    _write_standard(standards_dir, "docs/sdtmig.md", "# SDTMIG\nSDTMIG source data context may be consulted as upstream reference only.\n")
    return standards_dir


@pytest.mark.parametrize(
    ("task", "expected_ids"),
    [
        ("Create ADSL subject-level analysis dataset", {"adamig"}),
        ("Derive treatment-emergent adverse event variables for ADAE", {"adam-occds", "adam-ct"}),
        ("Plan ADLB laboratory analysis", {"adam-model", "adamig"}),
        ("Identify ADTTE time-to-event evidence", {"adam-bds-tte"}),
        ("Evaluate source-preserving SDTM preprocessing concepts", {"sdtm-model", "sdtmig"}),
    ],
)
def test_rule_extraction_pipeline_returns_traceable_evidence(registry_dir, task, expected_ids):
    run = RuleExtractionEngine.from_registry_dir(registry_dir).extract(task)

    assert expected_ids.issubset({record.standard_id for record in run.evidence})
    assert all(record.short_quote for record in run.evidence)
    assert all(record.source_local_path for record in run.evidence)
    assert all(record.page is None for record in run.evidence)
