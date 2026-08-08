from pathlib import Path

from devtools.live_acquisition_acceptance import (
    cleanup_refusal_reason,
    cleanup_standards_test,
    live_test_standards_dir,
    main,
    validate_downloaded_content,
)
import devtools.live_acquisition_acceptance as live_module
from standards_driven_sdtm_adam.standards import (
    check_required_standards,
    production_standards_dir,
    registry_with_standard_root,
)
from standards_driven_sdtm_adam.standards.registry import StandardsRegistry


def _write_manifest(
    standards_dir: Path,
    *,
    standard_id: str = "adamig",
    title: str = "ADaM Implementation Guide",
    role: str = "primary_standard",
    local_path: str = "docs/ADaMIG_v1.3.pdf",
    original_filename: str = "ADaMIG_v1.3.pdf",
) -> None:
    manifest = f"""schema_version: 1
standard:
  id: {standard_id}
  title: {title}
  role: {role}
  version: "1.3"
  release_date: null
  official_url: https://www.cdisc.org/system/files/members/standard/foundational/ADaMIG_v1.3.pdf
  package_url: null
  local_path: {local_path}
  local_root: null
  original_filename: {original_filename}
  sha256: null
  sha256_status: NOT_APPLICABLE
  verification_status: UNVERIFIED
  indexed: false
  verified: false
  enabled: true
"""
    (standards_dir / f"{standard_id}.yaml").write_text(manifest, encoding="utf-8")


def _registry(tmp_path: Path) -> tuple[Path, StandardsRegistry]:
    standards_dir = tmp_path / "registry"
    standards_dir.mkdir()
    _write_manifest(standards_dir)
    return standards_dir, StandardsRegistry.load(standards_dir, validate_integrity=False)


def test_live_test_destination_is_standards_test(tmp_path):
    cdisc_home = tmp_path / "cdisc"

    assert live_test_standards_dir(cdisc_home) == cdisc_home.resolve() / "standards_test"
    assert live_test_standards_dir(cdisc_home, "full_run") == cdisc_home.resolve() / "standards_test" / "full_run"


def test_production_destination_remains_standards(tmp_path):
    cdisc_home = tmp_path / "cdisc"

    assert production_standards_dir(cdisc_home) == cdisc_home.resolve() / "standards"


def test_live_test_ignores_production_files(tmp_path):
    _, registry = _registry(tmp_path)
    cdisc_home = tmp_path / "cdisc"
    production_file = production_standards_dir(cdisc_home) / "ADaMIG_v1.3.pdf"
    production_file.parent.mkdir(parents=True)
    production_file.write_bytes(b"%PDF- production")

    live_registry = registry_with_standard_root(registry, live_test_standards_dir(cdisc_home))
    result = check_required_standards(live_registry)

    assert live_registry.resolve_local_path(live_registry.get("adamig")) == live_test_standards_dir(cdisc_home) / "ADaMIG_v1.3.pdf"
    assert result.missing


def test_live_command_uses_browser_authenticated_downloader(monkeypatch, tmp_path, capsys):
    standards_dir, _ = _registry(tmp_path)
    cdisc_home = tmp_path / "cdisc"
    monkeypatch.setenv("CDISC_HOME", str(cdisc_home))

    class FakeBrowserDownloader:
        browser_contexts_created = 1
        cdisc_login_prompts = 1
        authentication_successes = 1
        reauthentication_attempts = 0
        network_downloads = 0
        deduplicated_package_downloads = 0

        def authenticate_once(self):
            return None

        def download(self, manifest, destination: Path):
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(b"%PDF-1.7\nADaMIG")
            from standards_driven_sdtm_adam.standards import DownloadReceipt

            return DownloadReceipt(path=destination, authorized=True, message="browser")

        def close(self):
            return None

    monkeypatch.setattr(live_module, "BrowserAuthenticatedStandardsDownloader", FakeBrowserDownloader)

    code = main(["--registry-dir", str(standards_dir)])

    output = capsys.readouterr().out
    assert code == 0
    assert "A Chromium window will open" in output
    assert "LIVE ACQUISITION TEST COMPLETE" in output
    assert (live_test_standards_dir(cdisc_home) / "ADaMIG_v1.3.pdf").exists()


def test_live_command_can_write_to_full_run_subdir(monkeypatch, tmp_path, capsys):
    standards_dir, _ = _registry(tmp_path)
    cdisc_home = tmp_path / "cdisc"
    monkeypatch.setenv("CDISC_HOME", str(cdisc_home))

    class FakeBrowserDownloader:
        browser_contexts_created = 1
        cdisc_login_prompts = 1
        authentication_successes = 1
        reauthentication_attempts = 0
        network_downloads = 0
        deduplicated_package_downloads = 0

        def authenticate_once(self):
            return None

        def download(self, manifest, destination: Path):
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(b"%PDF-1.7\nADaMIG")
            from standards_driven_sdtm_adam.standards import DownloadReceipt

            return DownloadReceipt(path=destination, authorized=True, message="browser")

        def close(self):
            return None

    monkeypatch.setattr(live_module, "BrowserAuthenticatedStandardsDownloader", FakeBrowserDownloader)

    code = main(["--registry-dir", str(standards_dir), "--test-subdir", "full_run"])

    output = capsys.readouterr().out
    assert code == 0
    assert "standards_test" in output
    assert (live_test_standards_dir(cdisc_home, "full_run") / "ADaMIG_v1.3.pdf").exists()


def test_live_command_can_reuse_existing_subdir_without_prompt(monkeypatch, tmp_path, capsys):
    standards_dir, _ = _registry(tmp_path)
    cdisc_home = tmp_path / "cdisc"
    monkeypatch.setenv("CDISC_HOME", str(cdisc_home))
    existing = live_test_standards_dir(cdisc_home, "full_run")
    existing.mkdir(parents=True)
    (existing / "ADaMIG_v1.3.pdf").write_bytes(b"%PDF-1.7\nADaMIG")

    code = main(["--registry-dir", str(standards_dir), "--test-subdir", "full_run", "--reuse-existing"])

    output = capsys.readouterr().out
    assert code == 0
    assert "already contains files" in output
    assert "Selected standards are already present" in output


def test_cleanup_refuses_production_standards_path(tmp_path):
    cdisc_home = tmp_path / "cdisc"

    refusal = cleanup_refusal_reason(
        production_standards_dir(cdisc_home),
        cdisc_home=cdisc_home,
        production_dir=production_standards_dir(cdisc_home),
    )

    assert refusal == "Refusing to delete the production standards directory."


def test_cleanup_refuses_dangerous_paths(tmp_path):
    cdisc_home = tmp_path / "cdisc"

    assert cleanup_refusal_reason(
        cdisc_home,
        cdisc_home=cdisc_home,
        production_dir=production_standards_dir(cdisc_home),
    ) == "Refusing to delete CDISC_HOME."
    root_refusal = cleanup_refusal_reason(
        Path(cdisc_home.anchor),
        cdisc_home=cdisc_home,
        production_dir=production_standards_dir(cdisc_home),
    )
    assert root_refusal in {
        "Refusing to delete a filesystem root.",
        "Refusing to delete a path outside CDISC_HOME.",
    }


def test_cleanup_removes_only_standards_test(tmp_path):
    cdisc_home = tmp_path / "cdisc"
    test_dir = live_test_standards_dir(cdisc_home)
    production_dir = production_standards_dir(cdisc_home)
    test_dir.mkdir(parents=True)
    production_dir.mkdir(parents=True)
    (test_dir / "file.pdf").write_bytes(b"%PDF- test")
    (production_dir / "file.pdf").write_bytes(b"%PDF- prod")

    code = cleanup_standards_test(cdisc_home, yes=True)

    assert code == 0
    assert not test_dir.exists()
    assert production_dir.exists()
    assert (production_dir / "file.pdf").exists()


def test_false_success_content_validation_helpers(tmp_path):
    pdf = tmp_path / "ADaMIG_v1.3.pdf"
    pdf.write_bytes(b"%PDF-1.7\nbody")
    html = tmp_path / "login.pdf"
    html.write_text("<html><form>Sign in</form></html>", encoding="utf-8")
    empty = tmp_path / "empty.pdf"
    empty.write_bytes(b"")
    json_error = tmp_path / "error.pdf"
    json_error.write_text('{"error":"access denied"}', encoding="utf-8")
    zip_path = tmp_path / "archive.zip"
    import zipfile

    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("file.txt", "content")

    assert validate_downloaded_content(pdf, expected_filename="ADaMIG_v1.3.pdf") is None
    assert validate_downloaded_content(html, expected_filename="login.pdf") == "HTML/login page content"
    assert validate_downloaded_content(empty, expected_filename="empty.pdf") == "empty or missing file"
    assert validate_downloaded_content(json_error, expected_filename="error.pdf") == "JSON response content"
    assert validate_downloaded_content(zip_path, expected_filename="archive.zip") is None
    assert validate_downloaded_content(pdf, expected_filename="wrong.pdf") == "wrong filename"
