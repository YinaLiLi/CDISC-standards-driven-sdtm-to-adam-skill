from pathlib import Path

import pytest
import zipfile

from standards_driven_sdtm_adam.standards import (
    BrowserAuthenticatedStandardsDownloader,
    DownloadReceipt,
    StandardsAuthorizationError,
    StandardsDownloadError,
    acquire_required_standards,
    check_required_standards,
    locate_standard,
    manual_setup_lines,
    plan_required_standards_for_tasks,
    required_runtime_manifests,
    render_missing_standard_plan,
    validate_downloaded_content,
)
from standards_driven_sdtm_adam.standards.acquisition import (
    ACQUISITION_DIRECT_FILE,
    ACQUISITION_PACKAGE_MEMBER,
    ACQUISITION_PRODUCT_PAGE,
    acquisition_type_for,
)
from standards_driven_sdtm_adam.standards.registry import StandardsRegistry


class _WritingDownloader:
    def __init__(self, content: bytes = b"official cdisc source") -> None:
        self.content = content
        self.destinations: list[Path] = []

    def download(self, manifest, destination: Path) -> DownloadReceipt:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(self.content)
        self.destinations.append(destination)
        return DownloadReceipt(path=destination, authorized=True, message=f"downloaded {manifest.id}")


class _AuthorizationFailingDownloader:
    def download(self, manifest, destination: Path) -> DownloadReceipt:
        raise StandardsAuthorizationError("CDISC authorization denied")


class _DownloadFailingDownloader:
    def download(self, manifest, destination: Path) -> DownloadReceipt:
        raise StandardsDownloadError("CDISC download failed")


class _FakeDownload:
    def __init__(self, filename: str, content: bytes) -> None:
        self.suggested_filename = filename
        self.content = content

    def save_as(self, path: str) -> None:
        Path(path).write_bytes(self.content)


class _FakeDownloadEvent:
    def __init__(self, page) -> None:
        self.page = page
        self.value = page.download

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False


class _FakeAPIResponse:
    def __init__(self, content: bytes, *, status: int = 200, content_type: str = "application/pdf") -> None:
        self._content = content
        self.status = status
        self.ok = 200 <= status < 400
        self.headers = {"content-type": content_type}

    def body(self) -> bytes:
        return self._content


class _FakeRequestContext:
    def __init__(self, page) -> None:
        self.page = page
        self.urls: list[str] = []

    def get(self, url: str, **kwargs) -> _FakeAPIResponse:
        self.urls.append(url)
        return _FakeAPIResponse(self.page.download.content, content_type=self.page.response_content_type)


class _MappedRequestContext:
    def __init__(self, responses: dict[str, _FakeAPIResponse]) -> None:
        self.responses = responses
        self.urls: list[str] = []

    def get(self, url: str, **kwargs) -> _FakeAPIResponse:
        self.urls.append(url)
        return self.responses[url]


class _FakeLocator:
    def __init__(self, page) -> None:
        self.page = page

    def inner_text(self, timeout: int = 1000) -> str:
        return self.page.body_text

    def evaluate_all(self, script: str):
        return self.page.links


class _FakePage:
    def __init__(
        self,
        *,
        body_text: str = "My Account",
        download_filename: str = "ADaMIG_v1.3.pdf",
        download_content: bytes = b"%PDF-1.7\nADaMIG",
        response_content_type: str = "application/pdf",
    ) -> None:
        self.url = "about:blank"
        self.body_text = body_text
        self.download = _FakeDownload(download_filename, download_content)
        self.response_content_type = response_content_type
        self.links: list[dict[str, str]] = []
        self.goto_urls: list[str] = []
        self.waits = 0
        self.expect_download_calls = 0

    def goto(self, url: str, **kwargs) -> None:
        self.url = "https://www.cdisc.org/user/profile" if "my account" in self.body_text.lower() else url
        self.goto_urls.append(url)

    def expect_download(self, timeout: int = 180000) -> _FakeDownloadEvent:
        self.expect_download_calls += 1
        return _FakeDownloadEvent(self)

    def locator(self, selector: str) -> _FakeLocator:
        return _FakeLocator(self)

    def wait_for_timeout(self, timeout: int) -> None:
        self.waits += 1

    def is_closed(self) -> bool:
        return False


class _LoginRequiredThenAuthenticatedPage(_FakePage):
    def __init__(self) -> None:
        super().__init__(body_text="Sign in required")
        self.body_text = "Please Sign in/Sign up. The information you are attempting to access requires you to create a cdiscID account."

    def goto(self, url: str, **kwargs) -> None:
        self.goto_urls.append(url)
        if url.endswith("/user/login"):
            self.url = "https://cdisclibrary.b2clogin.com/cdisclibrary.onmicrosoft.com/B2C_1A_SIGNUPSIGNINRESET/oauth2/v2.0/authorize"
            self.body_text = "Sign in Don't have an account?"
        else:
            self.url = url

    def wait_for_timeout(self, timeout: int) -> None:
        self.waits += 1
        self.url = "https://www.cdisc.org/user/profile"
        self.body_text = "My Account"


class _FakeContext:
    def __init__(self, page: _FakePage) -> None:
        self.pages = [page]
        self.closed = False
        self.request = _FakeRequestContext(page)

    def new_page(self) -> _FakePage:
        return self.pages[0]

    def close(self) -> None:
        self.closed = True


class _FakeChromium:
    def __init__(self, page: _FakePage) -> None:
        self.page = page
        self.launch_count = 0
        self.contexts: list[_FakeContext] = []

    def launch_persistent_context(self, user_data_dir: str, **kwargs) -> _FakeContext:
        self.launch_count += 1
        context = _FakeContext(self.page)
        self.contexts.append(context)
        return context


class _FakePlaywright:
    def __init__(self, page: _FakePage) -> None:
        self.chromium = _FakeChromium(page)
        self.stopped = False

    def stop(self) -> None:
        self.stopped = True


class _MappedContext(_FakeContext):
    def __init__(self, page: _FakePage, responses: dict[str, _FakeAPIResponse]) -> None:
        super().__init__(page)
        self.request = _MappedRequestContext(responses)


class _MappedChromium(_FakeChromium):
    def __init__(self, page: _FakePage, responses: dict[str, _FakeAPIResponse]) -> None:
        super().__init__(page)
        self.responses = responses

    def launch_persistent_context(self, user_data_dir: str, **kwargs) -> _FakeContext:
        self.launch_count += 1
        context = _MappedContext(self.page, self.responses)
        self.contexts.append(context)
        return context


class _MappedPlaywright(_FakePlaywright):
    def __init__(self, page: _FakePage, responses: dict[str, _FakeAPIResponse]) -> None:
        super().__init__(page)
        self.chromium = _MappedChromium(page, responses)


def _write_manifest(
    standards_dir: Path,
    *,
    standard_id: str,
    title: str,
    role: str,
    local_path: str | None,
    original_filename: str | None,
    official_url: str | None = None,
    package_url: str | None = None,
    members: tuple[str, ...] = (),
    enabled: bool = True,
) -> None:
    local_path_value = "null" if local_path is None else local_path
    filename_value = "null" if original_filename is None else original_filename
    url_value = "null" if official_url is None else official_url
    package_url_value = "null" if package_url is None else package_url
    member_lines = "".join(f"\n    - {member}" for member in members)
    members_value = f"\n  members:{member_lines}" if members else ""
    manifest = f"""schema_version: 1
standard:
  id: {standard_id}
  title: {title}
  role: {role}
  version: "1.0"
  release_date: "2026-03-27"
  official_url: {url_value}
  package_url: {package_url_value}
  local_path: {local_path_value}
  local_root: null
  original_filename: {filename_value}
  sha256: null
  sha256_status: NOT_APPLICABLE
  verification_status: UNVERIFIED
  indexed: false
  verified: false
  enabled: {str(enabled).lower()}
{members_value}
"""
    (standards_dir / f"{standard_id}.yaml").write_text(manifest, encoding="utf-8")


def _registry(tmp_path: Path) -> StandardsRegistry:
    standards_dir = tmp_path / "standards"
    standards_dir.mkdir()
    _write_manifest(
        standards_dir,
        standard_id="adamig",
        title="ADaM Implementation Guide",
        role="primary_standard",
        local_path="docs/ADaMIG_v1.3.pdf",
        original_filename="ADaMIG_v1.3.pdf",
        official_url="https://www.cdisc.org/system/files/members/standard/foundational/ADaMIG_v1.3.pdf",
    )
    _write_manifest(
        standards_dir,
        standard_id="sdtmig",
        title="SDTM Implementation Guide",
        role="upstream_reference",
        local_path="docs/SDTMIG_v3.4.pdf",
        original_filename="SDTMIG_v3.4.pdf",
        official_url="https://www.cdisc.org/system/files/members/standard/foundational/SDTMIG_v3.4.pdf",
    )
    _write_manifest(
        standards_dir,
        standard_id="adam-examples",
        title="ADaM Examples",
        role="validation_reference",
        local_path="docs/examples.pdf",
        original_filename="examples.pdf",
        official_url="https://www.cdisc.org/examples.pdf",
    )
    _write_manifest(
        standards_dir,
        standard_id="define-xml",
        title="Define-XML",
        role="future_scope",
        local_path="docs/define.pdf",
        original_filename="define.pdf",
        official_url="https://www.cdisc.org/define.pdf",
        enabled=False,
    )
    return StandardsRegistry.load(standards_dir, validate_integrity=False)


def test_no_op_when_all_required_standards_exist(tmp_path):
    registry = _registry(tmp_path)
    for manifest in required_runtime_manifests(registry):
        path = registry.resolve_local_path(manifest)
        assert path is not None
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("available", encoding="utf-8")

    result = acquire_required_standards(registry, _WritingDownloader())

    assert {item.standard_id for item in result.available} == {"adamig", "sdtmig"}
    assert result.missing == ()
    assert result.acquired == ()
    assert result.failed == ()


def test_missing_source_detection_reports_required_unavailable_sources(tmp_path):
    result = check_required_standards(_registry(tmp_path))

    assert {item.standard_id for item in result.missing} == {"adamig", "sdtmig"}
    assert result.available == ()


def test_future_scope_and_validation_references_are_excluded(tmp_path):
    result = check_required_standards(_registry(tmp_path))

    assert "define-xml" not in {item.standard_id for item in result.missing}
    assert "adam-examples" not in {item.standard_id for item in result.missing}


def test_successful_acquisition_uses_mocked_authorized_download(tmp_path):
    registry = _registry(tmp_path)
    downloader = _WritingDownloader()

    result = acquire_required_standards(registry, downloader)

    assert {item.standard_id for item in result.acquired} == {"adamig", "sdtmig"}
    assert result.failed == ()
    assert all(item.sha256 for item in result.acquired)
    assert all(path.exists() for path in downloader.destinations)


def test_official_filename_is_preserved(tmp_path):
    registry = _registry(tmp_path)
    downloader = _WritingDownloader()

    result = acquire_required_standards(registry, downloader)

    assert {path.name for path in downloader.destinations} == {"ADaMIG_v1.3.pdf", "SDTMIG_v3.4.pdf"}
    assert {item.official_filename for item in result.acquired} == {"ADaMIG_v1.3.pdf", "SDTMIG_v3.4.pdf"}


def test_failed_authorization_reports_failure(tmp_path):
    result = acquire_required_standards(_registry(tmp_path), _AuthorizationFailingDownloader())

    assert {item.standard_id for item in result.failed} == {"adamig", "sdtmig"}
    assert all("authorization denied" in item.message for item in result.failed)


def test_failed_download_reports_failure(tmp_path):
    result = acquire_required_standards(_registry(tmp_path), _DownloadFailingDownloader())

    assert {item.standard_id for item in result.failed} == {"adamig", "sdtmig"}
    assert all("download failed" in item.message for item in result.failed)


def test_manual_fallback_names_standard_source_url_and_destination(tmp_path):
    result = acquire_required_standards(_registry(tmp_path), _DownloadFailingDownloader())

    lines = manual_setup_lines(result)

    assert any("ADaM Implementation Guide" in line for line in lines)
    assert any("https://www.cdisc.org/system/files/members/standard/foundational/ADaMIG_v1.3.pdf" in line for line in lines)
    assert any("ADaMIG_v1.3.pdf" in line for line in lines)


def test_no_licensed_files_are_written_into_git_tracked_destinations(tmp_path):
    result = acquire_required_standards(
        _registry(tmp_path),
        _WritingDownloader(),
        git_tracked_checker=lambda path: path.name == "ADaMIG_v1.3.pdf",
    )

    assert "adamig" in {item.standard_id for item in result.failed}
    adamig = next(item for item in result.failed if item.standard_id == "adamig")
    assert "Git-tracked" in adamig.message


def test_manual_fallback_when_no_local_path_is_configured(tmp_path):
    standards_dir = tmp_path / "standards"
    standards_dir.mkdir()
    _write_manifest(
        standards_dir,
        standard_id="sdtm-model",
        title="SDTM Model",
        role="upstream_reference",
        local_path=None,
        original_filename=None,
        official_url="https://www.cdisc.org/standards/foundational/sdtm",
    )
    registry = StandardsRegistry.load(standards_dir, validate_integrity=False)

    result = acquire_required_standards(registry, _WritingDownloader())

    assert result.acquired == ()
    assert result.missing[0].standard_id == "sdtm-model"
    assert "no local_path" in result.missing[0].message


def test_locator_resolves_source_metadata_from_manifest(tmp_path):
    registry = _registry(tmp_path)
    manifest = registry.get("adamig")

    location = locate_standard(registry, manifest)

    assert location.source_id == "adamig"
    assert location.title == "ADaM Implementation Guide"
    assert location.required_version == "1.0"
    assert location.product_page == "https://www.cdisc.org/system/files/members/standard/foundational/ADaMIG_v1.3.pdf"
    assert location.acquisition_url == location.product_page
    assert location.expected_filename == "ADaMIG_v1.3.pdf"
    assert location.expected_content_type == "application/pdf"
    assert location.acquisition_type == ACQUISITION_DIRECT_FILE


def test_acquisition_type_distinguishes_package_members_and_product_pages(tmp_path):
    standards_dir = tmp_path / "standards"
    standards_dir.mkdir()
    _write_manifest(
        standards_dir,
        standard_id="package-member",
        title="Package Member",
        role="primary_standard",
        local_path="docs/member.pdf",
        original_filename="member.pdf",
        official_url="https://www.cdisc.org/standards/product",
        package_url="https://www.cdisc.org/package.zip",
        members=("member.pdf",),
    )
    _write_manifest(
        standards_dir,
        standard_id="product-page",
        title="Product Page",
        role="primary_standard",
        local_path="docs/file.pdf",
        original_filename="file.pdf",
        official_url="https://www.cdisc.org/standards/product",
    )
    registry = StandardsRegistry.load(standards_dir, validate_integrity=False)

    assert acquisition_type_for(registry.get("package-member")) == ACQUISITION_PACKAGE_MEMBER
    assert acquisition_type_for(registry.get("product-page")) == ACQUISITION_PRODUCT_PAGE


def test_required_plan_uses_task_discovery_instead_of_full_catalog(tmp_path):
    standards_dir = tmp_path / "standards"
    standards_dir.mkdir()
    for standard_id, title in (
        ("adamig", "ADaM Implementation Guide"),
        ("adam-occds", "ADaM OCCDS Implementation Guide"),
        ("adam-ct", "ADaM Controlled Terminology"),
        ("adam-conformance-rules", "ADaM Conformance Rules"),
        ("adam-bds-tte", "ADaM BDS Time-to-Event Guide"),
    ):
        _write_manifest(
            standards_dir,
            standard_id=standard_id,
            title=title,
            role="primary_standard",
            local_path=f"docs/{standard_id}.pdf",
            original_filename=f"{standard_id}.pdf",
            official_url=f"https://www.cdisc.org/{standard_id}.pdf",
        )
    registry = StandardsRegistry.load(standards_dir, validate_integrity=False)

    plan = plan_required_standards_for_tasks(
        registry,
        task_intents=("Derive treatment-emergent adverse event variables for ADAE",),
    )

    assert {item.standard_id for item in plan.required} == {
        "adamig",
        "adam-occds",
        "adam-ct",
        "adam-conformance-rules",
    }
    assert "adam-bds-tte" not in {item.standard_id for item in plan.required}


def test_missing_standard_plan_is_aggregated_for_one_prompt(tmp_path):
    plan = plan_required_standards_for_tasks(
        _registry(tmp_path),
        task_intents=("Create ADSL subject-level analysis dataset",),
    )

    text = render_missing_standard_plan(plan)

    assert text.startswith("Required CDISC sources not available locally:")
    assert "ADaM Implementation Guide" in text
    assert text.count("Authorization is required") == 1


def test_content_validation_rejects_wrong_content_type(tmp_path):
    path = tmp_path / "ADaMIG_v1.3.pdf"
    path.write_bytes(b"%PDF-1.7\nbody")

    assert validate_downloaded_content(
        path,
        expected_filename="ADaMIG_v1.3.pdf",
        expected_content_type="application/pdf",
        response_content_type="text/html",
    ) == "wrong content type"


def test_browser_authenticated_downloader_downloads_after_login(tmp_path):
    page = _FakePage()
    fake_playwright = _FakePlaywright(page)
    downloader = BrowserAuthenticatedStandardsDownloader(
        playwright_factory=lambda: fake_playwright,
        timeout_ms=100,
    )
    registry = _registry(tmp_path)
    manifest = registry.get("adamig")
    destination = registry.resolve_local_path(manifest)
    assert destination is not None

    receipt = downloader.download(manifest, destination)
    downloader.close()

    assert receipt.authorized
    assert destination.read_bytes().startswith(b"%PDF-")
    assert fake_playwright.chromium.launch_count == 1
    assert manifest.official_url in page.goto_urls
    assert manifest.official_url in fake_playwright.chromium.contexts[0].request.urls
    assert page.expect_download_calls == 0
    assert "https://www.cdisc.org/user/login" not in page.goto_urls
    assert all("api.developer.library.cdisc.org" not in url for url in page.goto_urls)
    assert fake_playwright.stopped


def test_browser_authenticated_downloader_reports_failed_login(tmp_path):
    page = _FakePage(body_text="Access denied")
    downloader = BrowserAuthenticatedStandardsDownloader(
        playwright_factory=lambda: _FakePlaywright(page),
        timeout_ms=100,
    )
    registry = _registry(tmp_path)
    manifest = registry.get("adamig")
    destination = registry.resolve_local_path(manifest)
    assert destination is not None

    with pytest.raises(StandardsAuthorizationError, match="failed"):
        downloader.download(manifest, destination)


def test_browser_authenticated_downloader_uses_normal_cdisc_login_for_protected_resource(tmp_path):
    page = _LoginRequiredThenAuthenticatedPage()
    fake_playwright = _FakePlaywright(page)
    downloader = BrowserAuthenticatedStandardsDownloader(
        playwright_factory=lambda: fake_playwright,
        timeout_ms=100,
    )
    registry = _registry(tmp_path)
    manifest = registry.get("adamig")
    destination = registry.resolve_local_path(manifest)
    assert destination is not None

    receipt = downloader.download(manifest, destination)
    downloader.close()

    assert receipt.authorized
    assert manifest.official_url in page.goto_urls
    assert manifest.official_url in fake_playwright.chromium.contexts[0].request.urls
    assert "https://www.cdisc.org/user/login" in page.goto_urls
    assert all("api.developer.library.cdisc.org" not in url for url in page.goto_urls)


def test_browser_authenticated_downloader_times_out_waiting_for_login(tmp_path):
    page = _FakePage(body_text="Sign in")
    downloader = BrowserAuthenticatedStandardsDownloader(
        playwright_factory=lambda: _FakePlaywright(page),
        timeout_ms=1,
    )
    registry = _registry(tmp_path)
    manifest = registry.get("adamig")
    destination = registry.resolve_local_path(manifest)
    assert destination is not None

    with pytest.raises(StandardsAuthorizationError, match="Timed out"):
        downloader.download(manifest, destination)


def test_browser_authenticated_downloader_reports_cancelled_login(tmp_path):
    class ClosedPage(_FakePage):
        def is_closed(self) -> bool:
            return True

    page = ClosedPage(body_text="Sign in")
    downloader = BrowserAuthenticatedStandardsDownloader(
        playwright_factory=lambda: _FakePlaywright(page),
        timeout_ms=100,
    )
    registry = _registry(tmp_path)
    manifest = registry.get("adamig")
    destination = registry.resolve_local_path(manifest)
    assert destination is not None

    with pytest.raises(StandardsAuthorizationError, match="cancelled"):
        downloader.download(manifest, destination)


def test_browser_authenticated_context_is_reused_for_multiple_downloads(tmp_path):
    standards_dir = tmp_path / "standards"
    standards_dir.mkdir()
    _write_manifest(
        standards_dir,
        standard_id="adamig",
        title="ADaM Implementation Guide",
        role="primary_standard",
        local_path="docs/ADaMIG_v1.3.pdf",
        original_filename="ADaMIG_v1.3.pdf",
        official_url="https://www.cdisc.org/adamig.pdf",
    )
    _write_manifest(
        standards_dir,
        standard_id="adam-model",
        title="ADaM Model",
        role="primary_standard",
        local_path="docs/ADaMIG_v1.3.pdf",
        original_filename="ADaMIG_v1.3.pdf",
        official_url="https://www.cdisc.org/adam-model.pdf",
    )
    registry = StandardsRegistry.load(standards_dir, validate_integrity=False)
    page = _FakePage()
    fake_playwright = _FakePlaywright(page)
    downloader = BrowserAuthenticatedStandardsDownloader(
        playwright_factory=lambda: fake_playwright,
        timeout_ms=100,
    )

    result = acquire_required_standards(registry, downloader)
    downloader.close()

    assert {item.standard_id for item in result.acquired} == {"adamig", "adam-model"}
    assert fake_playwright.chromium.launch_count == 1
    assert "https://www.cdisc.org/adamig.pdf" in fake_playwright.chromium.contexts[0].request.urls
    assert "https://www.cdisc.org/adam-model.pdf" in fake_playwright.chromium.contexts[0].request.urls
    assert page.expect_download_calls == 0


def test_browser_authenticated_downloader_resolves_product_page_link(tmp_path):
    standards_dir = tmp_path / "standards"
    standards_dir.mkdir()
    product_url = "https://www.cdisc.org/standards/product"
    file_url = "https://www.cdisc.org/system/files/file.pdf"
    _write_manifest(
        standards_dir,
        standard_id="product-page",
        title="Product Page",
        role="primary_standard",
        local_path="docs/file.pdf",
        original_filename="file.pdf",
        official_url=product_url,
    )
    registry = StandardsRegistry.load(standards_dir, validate_integrity=False)
    page = _FakePage(body_text="My Account")
    page.links = [{"href": file_url, "text": "file.pdf", "download": ""}]
    responses = {file_url: _FakeAPIResponse(b"%PDF-1.7\nbody", content_type="application/pdf")}
    fake_playwright = _MappedPlaywright(page, responses)
    downloader = BrowserAuthenticatedStandardsDownloader(
        playwright_factory=lambda: fake_playwright,
        timeout_ms=100,
    )
    manifest = registry.get("product-page")
    destination = registry.resolve_local_path(manifest)
    assert destination is not None

    receipt = downloader.download(manifest, destination)
    downloader.close()

    assert receipt.authorized
    assert destination.read_bytes().startswith(b"%PDF-")
    assert product_url in page.goto_urls
    assert file_url in fake_playwright.chromium.contexts[0].request.urls


def test_browser_authenticated_downloader_extracts_package_members_once(tmp_path):
    standards_dir = tmp_path / "standards"
    standards_dir.mkdir()
    package_url = "https://www.cdisc.org/package.zip"
    _write_manifest(
        standards_dir,
        standard_id="member-one",
        title="Member One",
        role="primary_standard",
        local_path="docs/member-one.pdf",
        original_filename="member-one.pdf",
        official_url="https://www.cdisc.org/product",
        package_url=package_url,
        members=("member-one.pdf",),
    )
    _write_manifest(
        standards_dir,
        standard_id="member-two",
        title="Member Two",
        role="primary_standard",
        local_path="docs/member-two.pdf",
        original_filename="member-two.pdf",
        official_url="https://www.cdisc.org/product",
        package_url=package_url,
        members=("member-two.pdf",),
    )
    package_path = tmp_path / "package.zip"
    with zipfile.ZipFile(package_path, "w") as archive:
        archive.writestr("member-one.pdf", b"%PDF-1.7\none")
        archive.writestr("nested/member-two.pdf", b"%PDF-1.7\ntwo")
    page = _FakePage(body_text="My Account")
    responses = {package_url: _FakeAPIResponse(package_path.read_bytes(), content_type="application/zip")}
    fake_playwright = _MappedPlaywright(page, responses)
    downloader = BrowserAuthenticatedStandardsDownloader(
        playwright_factory=lambda: fake_playwright,
        timeout_ms=100,
    )
    registry = StandardsRegistry.load(standards_dir, validate_integrity=False)

    result = acquire_required_standards(registry, downloader)
    downloader.close()

    assert {item.standard_id for item in result.acquired} == {"member-one", "member-two"}
    assert fake_playwright.chromium.contexts[0].request.urls.count(package_url) == 1
    assert downloader.network_downloads == 1
    assert downloader.deduplicated_package_downloads == 1
    assert (standards_dir / "docs" / "member-one.pdf").read_bytes().startswith(b"%PDF-")
    assert (standards_dir / "docs" / "member-two.pdf").read_bytes().startswith(b"%PDF-")


@pytest.mark.parametrize(
    ("content", "content_type", "message"),
    (
        (b"<html>login</html>", "text/html", "HTML/login page content"),
        (b'{"error":"denied"}', "application/json", "JSON response content"),
        (b"Access denied", "application/pdf", "access denied"),
        (b"not a pdf", "application/pdf", "wrong PDF signature"),
    ),
)
def test_browser_authenticated_invalid_context_response_is_rejected(
    tmp_path,
    content: bytes,
    content_type: str,
    message: str,
):
    page = _FakePage(download_content=content, response_content_type=content_type)
    downloader = BrowserAuthenticatedStandardsDownloader(
        playwright_factory=lambda: _FakePlaywright(page),
        timeout_ms=100,
    )
    registry = _registry(tmp_path)
    manifest = registry.get("adamig")
    destination = registry.resolve_local_path(manifest)
    assert destination is not None

    with pytest.raises(StandardsDownloadError, match=message):
        downloader.download(manifest, destination)
    assert not destination.exists()
