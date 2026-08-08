from pathlib import Path

import pytest

from standards_driven_sdtm_adam.standards import StandardManifest, StandardsRegistry
from standards_driven_sdtm_adam.standards.errors import StandardsRegistryError


def test_standard_manifest_requires_expected_fields():
    payload = {
        "schema_version": 1,
        "standard": {
            "id": "adamig",
            "title": "ADaM Implementation Guide",
            "version": None,
            "scope_category": "primary",
            "official_url": None,
            "local_path": None,
            "sha256": None,
            "indexed": False,
            "verified": False,
            "enabled": False,
        },
    }

    manifest = StandardManifest.from_mapping(payload)

    assert manifest.id == "adamig"


def test_standard_manifest_rejects_invalid_version():
    payload = {
        "schema_version": 1,
        "standard": {
            "id": "adamig",
            "title": "ADaM Implementation Guide",
            "version": "draft version",
            "scope_category": "primary",
            "official_url": None,
            "local_path": None,
            "sha256": None,
            "indexed": False,
            "verified": False,
            "enabled": False,
        },
    }

    with pytest.raises(StandardsRegistryError, match="version"):
        StandardManifest.from_mapping(payload)


def test_standard_manifest_rejects_invalid_scope_category():
    payload = {
        "schema_version": 1,
        "standard": {
            "id": "adamig",
            "title": "ADaM Implementation Guide",
            "version": "1.3",
            "scope_category": "unsupported",
            "official_url": None,
            "local_path": None,
            "sha256": None,
            "indexed": False,
            "verified": False,
            "enabled": False,
        },
    }

    with pytest.raises(StandardsRegistryError, match="scope_category"):
        StandardManifest.from_mapping(payload)


def test_standard_manifest_accepts_identity_verification_statuses():
    statuses = ("VERIFIED", "PARTIALLY_VERIFIED", "UNVERIFIED", "MISMATCH")

    for status in statuses:
        payload = {
            "schema_version": 1,
            "standard": {
                "id": f"adamig-{status.lower().replace('_', '-')}",
                "title": "ADaM Implementation Guide",
                "role": "primary_standard",
                "version": "1.3",
                "release_date": None,
                "official_url": None,
                "local_path": None,
                "original_filename": None,
                "sha256": None,
                "sha256_status": "NOT_APPLICABLE",
                "verification_status": status,
                "indexed": False,
                "verified": status == "VERIFIED",
                "enabled": False,
            },
        }

        manifest = StandardManifest.from_mapping(payload)

        assert manifest.verification_status == status


def test_registry_loads_v1_manifests():
    registry = StandardsRegistry.load(Path("config") / "standards", validate_integrity=False)

    assert "adamig" in {manifest.id for manifest in registry.all()}


def test_registry_matches_approved_v1_primary_adam_scope():
    registry = StandardsRegistry.load(Path("config") / "standards", validate_integrity=False)

    primary = {
        (manifest.id, manifest.title, manifest.version)
        for manifest in registry.by_scope_category("primary")
    }

    assert primary == {
        ("adam-model", "ADaM Model", "2.1"),
        ("adam-important-considerations", "Important Considerations When Using ADaM", "2.1"),
        ("adamig", "ADaM Implementation Guide", "1.3"),
        ("adam-occds", "ADaM OCCDS Implementation Guide", "1.1"),
        ("adam-bds-tte", "ADaM BDS Time-to-Event Guide", "1.0"),
        ("adam-msg", "ADaM Metadata Submission Guidelines", "1.0"),
        ("adam-ct", "ADaM Controlled Terminology", None),
        ("adam-conformance-rules", "ADaM Conformance Rules", "5.0"),
    }


def test_sdtm_standards_are_upstream_references_only():
    registry = StandardsRegistry.load(Path("config") / "standards", validate_integrity=False)

    upstream_ids = {
        manifest.id
        for manifest in registry.by_scope_category("upstream_reference")
    }

    assert upstream_ids == {"sdtm-model", "sdtmig"}


def test_define_xml_and_sdrg_are_disabled_future_scope():
    registry = StandardsRegistry.load(Path("config") / "standards", validate_integrity=False)

    future_scope = {manifest.id: manifest for manifest in registry.by_scope_category("future_scope")}

    assert set(future_scope) == {"define-xml", "sdrg"}
    assert not future_scope["define-xml"].enabled
    assert not future_scope["sdrg"].enabled


def test_registry_rejects_duplicate_ids(tmp_path):
    manifest = """schema_version: 1
standard:
  id: adamig
  title: ADaM Implementation Guide
  version: null
  scope_category: primary
  official_url: null
  local_path: null
  sha256: null
  indexed: false
  verified: false
  enabled: false
"""
    (tmp_path / "one.yaml").write_text(manifest, encoding="utf-8")
    (tmp_path / "two.yaml").write_text(manifest, encoding="utf-8")

    with pytest.raises(StandardsRegistryError, match="Duplicate"):
        StandardsRegistry.load(tmp_path)


def test_registry_rejects_missing_declared_local_file(tmp_path):
    manifest = """schema_version: 1
standard:
  id: adamig
  title: ADaM Implementation Guide
  version: "1.3"
  scope_category: primary
  official_url: null
  local_path: missing.pdf
  sha256: null
  indexed: false
  verified: false
  enabled: false
"""
    (tmp_path / "adamig.yaml").write_text(manifest, encoding="utf-8")

    with pytest.raises(StandardsRegistryError, match="missing local files"):
        StandardsRegistry.load(tmp_path)
