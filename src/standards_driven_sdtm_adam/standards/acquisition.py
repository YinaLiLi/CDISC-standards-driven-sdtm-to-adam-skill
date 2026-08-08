"""Authorized first-run acquisition for configured standards sources."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, replace
from pathlib import Path
import os
import subprocess
import tempfile
import time
import urllib.parse
import zipfile
from typing import Any

from standards_driven_sdtm_adam.standards.errors import StandardsRegistryError
from standards_driven_sdtm_adam.standards.model import StandardManifest
from standards_driven_sdtm_adam.standards.registry import StandardsRegistry


RUNTIME_REQUIRED_ROLES = ("primary_standard", "upstream_reference")
VALIDATION_REFERENCE_ROLES = ("validation_reference",)
CDISC_HOME_ENV_VAR = "CDISC_HOME"
CONTENT_TYPES_BY_SUFFIX = {
    ".pdf": "application/pdf",
    ".zip": "application/zip",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xls": "application/vnd.ms-excel",
}
ACQUISITION_DIRECT_FILE = "DIRECT_FILE"
ACQUISITION_PACKAGE_MEMBER = "PACKAGE_MEMBER"
ACQUISITION_PRODUCT_PAGE = "PRODUCT_PAGE"


class StandardsAcquisitionError(RuntimeError):
    """Raised when a standard cannot be acquired safely or with authorization."""


class StandardsAuthorizationError(StandardsAcquisitionError):
    """Raised when authorized CDISC access is not available."""


class StandardsDownloadError(StandardsAcquisitionError):
    """Raised when an authorized download fails."""


@dataclass(frozen=True)
class DownloadReceipt:
    """Result returned by an authorized downloader."""

    path: Path
    authorized: bool = True
    message: str = ""


@dataclass(frozen=True)
class StandardLocation:
    """Resolved official source and local cache location for one standard."""

    source_id: str
    title: str
    required_version: str | None
    release_date: str | None
    product_page: str | None
    acquisition_url: str | None
    expected_filename: str | None
    expected_content_type: str | None
    local_path: Path | None
    acquisition_type: str


@dataclass(frozen=True)
class StandardsAcquisitionItem:
    """Acquisition status for one configured standard."""

    standard_id: str
    title: str
    status: str
    source_url: str | None
    local_path: Path | None
    official_filename: str | None
    message: str = ""
    sha256: str | None = None
    location: StandardLocation | None = None


@dataclass(frozen=True)
class StandardsAcquisitionResult:
    """Structured result for first-run standards availability and acquisition."""

    available: tuple[StandardsAcquisitionItem, ...]
    missing: tuple[StandardsAcquisitionItem, ...]
    acquired: tuple[StandardsAcquisitionItem, ...]
    failed: tuple[StandardsAcquisitionItem, ...]

    @property
    def ok(self) -> bool:
        """Return whether all required standards were available or acquired."""

        return not self.missing and not self.failed

    @property
    def manual_setup_required(self) -> bool:
        """Return whether the user must manually provide at least one source."""

        return bool(self.missing or self.failed)


@dataclass(frozen=True)
class StandardsAcquisitionPlan:
    """Aggregated one-prompt plan for required standards acquisition."""

    required: tuple[StandardsAcquisitionItem, ...]
    available: tuple[StandardsAcquisitionItem, ...]
    missing: tuple[StandardsAcquisitionItem, ...]
    registry: StandardsRegistry

    @property
    def authorization_required(self) -> bool:
        """Return whether missing sources require authorized retrieval."""

        return any(item.source_url for item in self.missing)


class BrowserAuthenticatedStandardsDownloader:
    """Acquire standards through one user-authenticated CDISC browser session."""

    def __init__(
        self,
        *,
        login_url: str = "https://www.cdisc.org/user/login",
        headless: bool = False,
        timeout_ms: int = 180_000,
        playwright_factory: Callable[[], Any] | None = None,
    ) -> None:
        self.login_url = login_url
        self.headless = headless
        self.timeout_ms = timeout_ms
        self.playwright_factory = playwright_factory
        self._playwright_manager: Any | None = None
        self._playwright: Any | None = None
        self._context: Any | None = None
        self._page: Any | None = None
        self._user_data_dir: tempfile.TemporaryDirectory[str] | None = None
        self._authenticated = False
        self._cdisc_authenticated_once = False
        self._package_cache: dict[str, Path] = {}
        self.network_downloads = 0
        self.deduplicated_package_downloads = 0
        self.browser_contexts_created = 0
        self.cdisc_login_prompts = 0
        self.authentication_successes = 0
        self.reauthentication_attempts = 0
        self.sources_acquired: list[str] = []

    def __enter__(self) -> "BrowserAuthenticatedStandardsDownloader":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()

    def authenticate_once(self, protected_url: str | None = None) -> None:
        """Prompt for one CDISC login at the start of a batch."""

        if self._cdisc_authenticated_once:
            return
        page = self._ensure_page()
        self._complete_login(page, protected_url or self.login_url)

    def download(self, manifest: StandardManifest, destination: Path) -> DownloadReceipt:
        """Download one manifest source after one user-driven cdiscID login."""

        source_url = source_url_for(manifest)
        if source_url is None:
            raise StandardsDownloadError(
                f"{manifest.id} does not declare an official_url or package_url for automatic acquisition."
            )

        destination.parent.mkdir(parents=True, exist_ok=True)
        if acquisition_type_for(manifest) == ACQUISITION_PACKAGE_MEMBER:
            return self._download_package_member(manifest, destination)

        if acquisition_type_for(manifest) == ACQUISITION_PRODUCT_PAGE:
            source_url = self._resolve_product_page_download_url(manifest, source_url)

        self._ensure_authenticated(source_url)
        temporary = destination.with_name(f"{destination.name}.part")
        if temporary.exists():
            temporary.unlink()

        try:
            response, status, content_type = self._request_resource(source_url, resource_id=manifest.id)
            if not getattr(response, "ok", False):
                raise StandardsDownloadError(
                    f"Authenticated request failed for {manifest.id} (status={status}, content_type={content_type})."
                )
            temporary.write_bytes(response.body())
            self.network_downloads += 1
        except StandardsDownloadError:
            temporary.unlink(missing_ok=True)
            raise
        except Exception as exc:
            temporary.unlink(missing_ok=True)
            raise StandardsDownloadError(f"Authenticated browser-context request failed for {manifest.id}: {exc}.") from exc

        validation_error = validate_downloaded_content(
            temporary,
            expected_filename=destination.name,
            expected_content_type=expected_content_type_for_filename(destination.name),
            response_content_type=content_type,
        )
        if validation_error is not None:
            temporary.unlink(missing_ok=True)
            raise StandardsDownloadError(
                f"Downloaded content failed validation for {manifest.id}: {validation_error} "
                f"(status={status}, content_type={content_type})."
            )

        temporary.replace(destination)
        self.sources_acquired.append(manifest.id)
        return DownloadReceipt(path=destination, authorized=True, message="Downloaded through authenticated browser context.")

    def _download_package_member(self, manifest: StandardManifest, destination: Path) -> DownloadReceipt:
        package_url = manifest.package_url
        if package_url is None:
            raise StandardsDownloadError(f"{manifest.id} does not declare a package_url for package member acquisition.")

        package_path = self._download_package_once(package_url, resource_id=manifest.id)
        member_name = _select_archive_member(package_path, manifest)
        temporary = destination.with_name(f"{destination.name}.part")
        if temporary.exists():
            temporary.unlink()
        try:
            with zipfile.ZipFile(package_path) as archive:
                temporary.write_bytes(archive.read(member_name))
        except (KeyError, zipfile.BadZipFile) as exc:
            temporary.unlink(missing_ok=True)
            raise StandardsDownloadError(f"Could not extract {member_name} from package for {manifest.id}.") from exc

        validation_error = validate_downloaded_content(
            temporary,
            expected_filename=destination.name,
            expected_content_type=expected_content_type_for_filename(destination.name),
            response_content_type=expected_content_type_for_filename(destination.name),
        )
        if validation_error is not None:
            temporary.unlink(missing_ok=True)
            raise StandardsDownloadError(
                f"Extracted package member failed validation for {manifest.id}: {validation_error}."
            )

        temporary.replace(destination)
        self.sources_acquired.append(manifest.id)
        return DownloadReceipt(
            path=destination,
            authorized=True,
            message=f"Extracted {member_name} from authenticated package {Path(urllib.parse.urlparse(package_url).path).name}.",
        )

    def download_package(self, manifest: StandardManifest, destination_root: Path) -> DownloadReceipt:
        """Download a package once and extract configured members under a destination root."""

        package_url = manifest.package_url
        if package_url is None:
            raise StandardsDownloadError(f"{manifest.id} does not declare a package_url for package acquisition.")
        if not manifest.members:
            raise StandardsDownloadError(f"{manifest.id} does not declare package members for extraction.")

        package_path = self._download_package_once(package_url, resource_id=manifest.id)
        destination_root.mkdir(parents=True, exist_ok=True)
        try:
            with zipfile.ZipFile(package_path) as archive:
                names = tuple(name for name in archive.namelist() if not name.endswith("/"))
                for member in manifest.members:
                    archive_name = member if member in names else _find_archive_member_by_basename(names, member)
                    target = (destination_root / member).resolve()
                    if destination_root.resolve() not in target.parents and target != destination_root.resolve():
                        raise StandardsDownloadError(f"Refusing to extract package member outside destination root: {member}.")
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(archive.read(archive_name))
        except (KeyError, zipfile.BadZipFile) as exc:
            raise StandardsDownloadError(f"Could not extract configured package members for {manifest.id}.") from exc

        missing = [member for member in manifest.members if not (destination_root / member).exists()]
        if missing:
            raise StandardsDownloadError(f"Package extraction did not create expected members for {manifest.id}: {', '.join(missing)}.")

        self.sources_acquired.append(manifest.id)
        return DownloadReceipt(
            path=destination_root,
            authorized=True,
            message=f"Extracted configured members from authenticated package {Path(urllib.parse.urlparse(package_url).path).name}.",
        )

    def _download_package_once(self, package_url: str, *, resource_id: str) -> Path:
        cached = self._package_cache.get(package_url)
        if cached is not None and cached.exists():
            self.deduplicated_package_downloads += 1
            return cached

        self._ensure_authenticated(package_url)
        package_name = Path(urllib.parse.unquote(urllib.parse.urlparse(package_url).path)).name or "package.zip"
        if self._user_data_dir is None:
            raise StandardsDownloadError("Browser context is not initialized.")
        package_path = Path(self._user_data_dir.name) / package_name
        try:
            response, status, content_type = self._request_resource(package_url, resource_id=resource_id)
            if not getattr(response, "ok", False):
                raise StandardsDownloadError(
                    f"Authenticated package request failed for {resource_id} (status={status}, content_type={content_type})."
                )
            package_path.write_bytes(response.body())
            self.network_downloads += 1
        except StandardsDownloadError:
            package_path.unlink(missing_ok=True)
            raise
        except Exception as exc:
            package_path.unlink(missing_ok=True)
            raise StandardsDownloadError(f"Authenticated package request failed for {resource_id}: {exc}.") from exc

        validation_error = validate_downloaded_content(
            package_path,
            expected_filename=package_name,
            expected_content_type=expected_content_type_for_filename(package_name),
            response_content_type=content_type,
        )
        if validation_error is not None:
            package_path.unlink(missing_ok=True)
            raise StandardsDownloadError(
                f"Downloaded package failed validation for {resource_id}: {validation_error} "
                f"(status={status}, content_type={content_type})."
            )

        self._package_cache[package_url] = package_path
        return package_path

    def _request_resource(self, url: str, *, resource_id: str) -> tuple[Any, Any, str | None]:
        last_exc: Exception | None = None
        for _attempt in range(3):
            try:
                response = self._context.request.get(url, timeout=self.timeout_ms)
                break
            except Exception as exc:
                last_exc = exc
                if not _is_transient_request_error(exc):
                    raise
                time.sleep(1)
        else:
            assert last_exc is not None
            raise last_exc

        status = getattr(response, "status", "unknown")
        content_type = _response_content_type(response)
        if status in {401, 403}:
            self._authenticated = False
            self.reauthentication_attempts += 1
            self._ensure_authenticated(url)
            response = self._context.request.get(url, timeout=self.timeout_ms)
            status = getattr(response, "status", "unknown")
            content_type = _response_content_type(response)
        return response, status, content_type

    def _resolve_product_page_download_url(self, manifest: StandardManifest, product_url: str) -> str:
        expected_filename = manifest.original_filename
        if expected_filename is None:
            raise StandardsDownloadError(f"{manifest.id} does not declare an official filename for product page resolution.")

        page = self._ensure_authenticated(product_url)
        page.goto(product_url, wait_until="networkidle", timeout=self.timeout_ms)
        page.wait_for_timeout(1000)
        links = _page_links(page)
        match = _match_download_link(links, expected_filename, product_url)
        if match is None:
            raise StandardsDownloadError(
                f"Could not resolve an official download link for {manifest.id} from {product_url}."
            )
        return match

    def close(self) -> None:
        """Close the browser context and remove temporary auth state."""

        if self._context is not None:
            self._context.close()
            self._context = None
        if self._playwright is not None:
            self._playwright.stop()
            self._playwright = None
        if self._user_data_dir is not None:
            self._user_data_dir.cleanup()
            self._user_data_dir = None

    def _ensure_authenticated(self, protected_url: str) -> Any:
        page = self._ensure_page()
        if self._authenticated:
            return page
        if urllib.parse.urlparse(protected_url).hostname not in {"www.cdisc.org", "cdisc.org"}:
            self._authenticated = True
            return page

        try:
            page.goto(protected_url, wait_until="domcontentloaded", timeout=self.timeout_ms)
        except Exception as exc:
            if "net::ERR_ABORTED" in str(exc) or "Download is starting" in str(exc):
                self._authenticated = True
                return page
            raise
        if _page_login_failed(page):
            raise StandardsAuthorizationError("CDISC login failed or access was denied.")
        if not _resource_requires_login(page):
            self._authenticated = True
            return page

        self._complete_login(page, protected_url)
        return page

    def _complete_login(self, page: Any, protected_url: str) -> None:
        if self._cdisc_authenticated_once:
            self._authenticated = True
            return
        self.cdisc_login_prompts += 1
        page.goto(self.login_url, wait_until="domcontentloaded", timeout=self.timeout_ms)
        deadline = time.monotonic() + (self.timeout_ms / 1000)
        while time.monotonic() < deadline:
            if _page_is_closed(page):
                raise StandardsAuthorizationError("CDISC login was cancelled before authentication completed.")
            if _page_login_failed(page):
                raise StandardsAuthorizationError("CDISC login failed or access was denied.")
            if not _page_is_login_flow(page):
                self._authenticated = True
                self._cdisc_authenticated_once = True
                self.authentication_successes += 1
                return
            page.wait_for_timeout(1000)

        raise StandardsAuthorizationError(
            f"Timed out waiting for CDISC authentication before accessing {protected_url}."
        )

    def _ensure_page(self) -> Any:
        if self._page is not None:
            return self._page

        playwright = self._start_playwright()
        self._user_data_dir = tempfile.TemporaryDirectory(prefix="cdisc-browser-auth-", ignore_cleanup_errors=True)
        self._context = playwright.chromium.launch_persistent_context(
            self._user_data_dir.name,
            accept_downloads=True,
            headless=self.headless,
        )
        self.browser_contexts_created += 1
        pages = getattr(self._context, "pages", [])
        self._page = pages[0] if pages else self._context.new_page()
        return self._page

    def _start_playwright(self) -> Any:
        if self._playwright is not None:
            return self._playwright
        if self.playwright_factory is not None:
            self._playwright = self.playwright_factory()
            return self._playwright
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise StandardsAcquisitionError(
                "Playwright is required for browser-authenticated CDISC acquisition. "
                "Install the project dependencies and run: python -m playwright install chromium"
            ) from exc
        self._playwright_manager = sync_playwright()
        self._playwright = self._playwright_manager.start()
        return self._playwright


def check_required_standards(registry: StandardsRegistry) -> StandardsAcquisitionResult:
    """Detect missing enabled runtime standards without attempting downloads."""

    return check_manifest_sources(registry, required_runtime_manifests(registry))


def check_manifest_sources(
    registry: StandardsRegistry,
    manifests: Iterable[StandardManifest],
) -> StandardsAcquisitionResult:
    """Detect missing configured manifests without attempting downloads."""

    available: list[StandardsAcquisitionItem] = []
    missing: list[StandardsAcquisitionItem] = []
    for manifest in manifests:
        item = _availability_item(registry, manifest)
        if item.status == "available":
            available.append(item)
        else:
            missing.append(item)
    return StandardsAcquisitionResult(
        available=tuple(available),
        missing=tuple(missing),
        acquired=(),
        failed=(),
    )


def acquire_required_standards(
    registry: StandardsRegistry,
    downloader: Any,
    *,
    git_tracked_checker: Callable[[Path], bool] | None = None,
) -> StandardsAcquisitionResult:
    """Acquire missing enabled runtime standards through an authorized downloader."""

    return acquire_manifest_sources(
        registry,
        required_runtime_manifests(registry),
        downloader,
        git_tracked_checker=git_tracked_checker,
    )


def acquire_manifest_sources(
    registry: StandardsRegistry,
    manifests: Iterable[StandardManifest],
    downloader: Any,
    *,
    git_tracked_checker: Callable[[Path], bool] | None = None,
) -> StandardsAcquisitionResult:
    """Acquire missing configured manifests through an authorized downloader."""

    git_tracked_checker = git_tracked_checker or is_git_tracked_path
    selected_manifests = tuple(manifests)
    initial = check_manifest_sources(registry, selected_manifests)
    available = list(initial.available)
    missing: list[StandardsAcquisitionItem] = []
    acquired: list[StandardsAcquisitionItem] = []
    failed: list[StandardsAcquisitionItem] = []

    manifests_by_id = {manifest.id: manifest for manifest in selected_manifests}
    for item in initial.missing:
        manifest = manifests_by_id[item.standard_id]
        destination = registry.resolve_local_path(manifest)
        destination_root = registry.resolve_local_root(manifest)
        if destination is None and destination_root is None:
            missing.append(
                _replace_item(
                    item,
                    status="missing",
                    message="Manual setup required because no local_path is configured.",
                )
            )
            continue

        if destination is not None and manifest.original_filename and destination.name != manifest.original_filename:
            failed.append(
                _replace_item(
                    item,
                    status="failed",
                    message="Configured local_path does not preserve the official filename.",
                )
            )
            continue

        if destination is not None and git_tracked_checker(destination):
            failed.append(
                _replace_item(
                    item,
                    status="failed",
                    message="Refusing to write a licensed CDISC source over a Git-tracked path.",
                )
            )
            continue

        try:
            if destination_root is not None and destination is None:
                receipt = downloader.download_package(manifest, destination_root)
            else:
                assert destination is not None
                receipt = downloader.download(manifest, destination)
        except StandardsAuthorizationError as exc:
            failed.append(_replace_item(item, status="failed", message=_redact(str(exc))))
            continue
        except StandardsAcquisitionError as exc:
            failed.append(_replace_item(item, status="failed", message=_redact(str(exc))))
            continue

        if not receipt.authorized:
            failed.append(
                _replace_item(
                    item,
                    status="failed",
                    message="Downloader did not confirm authorized access.",
                )
            )
            continue

        if destination is not None and not destination.exists():
            failed.append(
                _replace_item(
                    item,
                    status="failed",
                    message="Downloader completed but the expected local file does not exist.",
                )
            )
            continue
        if destination_root is not None and manifest.members:
            absent = tuple(member for member in manifest.members if not (destination_root / member).exists())
            if absent:
                failed.append(
                    _replace_item(
                        item,
                        status="failed",
                        message=f"Downloader completed but expected package members are missing: {', '.join(absent)}.",
                    )
                )
                continue

        acquired.append(
            _replace_item(
                item,
                status="acquired",
                message=receipt.message or "Acquired official configured source.",
                sha256=registry.calculate_sha256(manifest) if destination is not None else None,
            )
        )

    return StandardsAcquisitionResult(
        available=tuple(available),
        missing=tuple(missing),
        acquired=tuple(acquired),
        failed=tuple(failed),
    )


def bootstrap_standards(
    registry_dir: str | Path,
    *,
    downloader: Any | None = None,
) -> StandardsAcquisitionResult:
    """Explicit first-run preflight for configured required standards."""

    registry = StandardsRegistry.load(registry_dir, validate_integrity=False)
    if downloader is None:
        return check_required_standards(registry)
    return acquire_required_standards(registry, downloader)


def first_user_preflight(
    registry_dir: str | Path,
    *,
    cdisc_home: str | Path | None = None,
    task_intents: Iterable[str] = (),
    downloader: Any | None = None,
) -> StandardsAcquisitionResult:
    """User-facing first-run preflight for production standards setup."""

    registry = StandardsRegistry.load(registry_dir, validate_integrity=False)
    production_registry = registry_with_standard_root(
        registry,
        production_standards_dir(resolve_cdisc_home(cdisc_home)),
    )
    plan = plan_required_standards_for_tasks(
        production_registry,
        task_intents=tuple(task_intents),
    )
    check = StandardsAcquisitionResult(
        available=plan.available,
        missing=plan.missing,
        acquired=(),
        failed=(),
    )
    if not plan.missing:
        return check

    if downloader is None:
        downloader = BrowserAuthenticatedStandardsDownloader()

    return acquire_required_standards(
        plan.registry,
        downloader,
    )


def authorized_access_instructions() -> str:
    """Return concise setup instructions for user-authorized CDISC access."""

    return (
        "Sign in to CDISC through the supported browser authorization flow when prompted. "
        "Do not store passwords or session cookies in this project."
    )


def required_runtime_manifests(registry: StandardsRegistry) -> tuple[StandardManifest, ...]:
    """Return enabled runtime-required manifests, excluding validation and future scope."""

    return tuple(
        manifest
        for manifest in registry.enabled()
        if manifest.role in RUNTIME_REQUIRED_ROLES
    )


def validation_reference_manifests(registry: StandardsRegistry) -> tuple[StandardManifest, ...]:
    """Return enabled validation/reference assets used outside primary discovery."""

    return tuple(
        manifest
        for manifest in registry.enabled()
        if manifest.role in VALIDATION_REFERENCE_ROLES
    )


def plan_required_standards_for_tasks(
    registry: StandardsRegistry,
    *,
    task_intents: Iterable[str],
) -> StandardsAcquisitionPlan:
    """Plan the minimum relevant standards for one requested run."""

    selected_ids = required_standard_ids_for_tasks(registry, task_intents=task_intents)
    plan_registry = registry_with_only_standard_ids(registry, selected_ids)
    result = check_required_standards(plan_registry)
    required = tuple(
        _availability_item(plan_registry, manifest)
        for manifest in required_runtime_manifests(plan_registry)
    )
    return StandardsAcquisitionPlan(
        required=required,
        available=result.available,
        missing=result.missing,
        registry=plan_registry,
    )


def required_standard_ids_for_tasks(
    registry: StandardsRegistry,
    *,
    task_intents: Iterable[str],
) -> tuple[str, ...]:
    """Return standards relevant to the requested run, not the full catalog."""

    intents = tuple(task_intents)
    if not intents:
        return tuple(manifest.id for manifest in required_runtime_manifests(registry))

    from standards_driven_sdtm_adam.discovery import StandardsDiscoveryEngine

    discovery = StandardsDiscoveryEngine(registry)
    selected: set[str] = set()
    for intent in intents:
        run = discovery.discover(intent)
        selected.update(item.standard_id for item in run.results)
    return tuple(sorted(selected))


def registry_with_only_standard_ids(
    registry: StandardsRegistry,
    standard_ids: Iterable[str],
) -> StandardsRegistry:
    """Return a registry containing only selected standard manifests."""

    selected_ids = set(standard_ids)
    return StandardsRegistry(
        (manifest for manifest in registry.all() if manifest.id in selected_ids),
        root=registry.root,
    )


def locate_standard(registry: StandardsRegistry, manifest: StandardManifest) -> StandardLocation:
    """Resolve official source and cache metadata from one manifest."""

    return StandardLocation(
        source_id=manifest.id,
        title=manifest.title,
        required_version=manifest.version,
        release_date=manifest.release_date,
        product_page=manifest.official_url,
        acquisition_url=source_url_for(manifest),
        expected_filename=manifest.original_filename,
        expected_content_type=expected_content_type_for_filename(manifest.original_filename),
        local_path=registry.resolve_local_path(manifest),
        acquisition_type=acquisition_type_for(manifest),
    )


def registry_with_standard_root(
    registry: StandardsRegistry,
    standards_root: str | Path,
    *,
    standard_ids: Iterable[str] | None = None,
) -> StandardsRegistry:
    """Return a registry overlay whose file sources live under one standards root."""

    standards_root = Path(standards_root).resolve()
    selected_ids = set(standard_ids) if standard_ids is not None else None
    manifests: list[StandardManifest] = []
    for manifest in registry.all():
        if selected_ids is not None and manifest.id not in selected_ids:
            manifests.append(manifest)
            continue
        if manifest.local_path is None or manifest.original_filename is None:
            manifests.append(manifest)
            continue
        manifests.append(
            replace(
                manifest,
                local_path=str(standards_root / manifest.original_filename),
                local_root=None,
            )
        )
    return StandardsRegistry(manifests, root=registry.root)


def registry_with_storage_roots(
    registry: StandardsRegistry,
    *,
    standards_root: str | Path,
    examples_root: str | Path,
    standard_ids: Iterable[str] | None = None,
) -> StandardsRegistry:
    """Return a registry overlay split between standards and examples roots."""

    standards_root = Path(standards_root).resolve()
    examples_root = Path(examples_root).resolve()
    selected_ids = set(standard_ids) if standard_ids is not None else None
    manifests: list[StandardManifest] = []
    for manifest in registry.all():
        if selected_ids is not None and manifest.id not in selected_ids:
            manifests.append(manifest)
            continue
        root = examples_root if manifest.role == "validation_reference" else standards_root
        if manifest.local_root is not None:
            manifests.append(
                replace(
                    manifest,
                    local_root=str(root / Path(manifest.local_root).name),
                    local_path=None,
                )
            )
            continue
        if manifest.local_path is not None and manifest.original_filename is not None:
            manifests.append(
                replace(
                    manifest,
                    local_path=str(root / manifest.original_filename),
                    local_root=None,
                )
            )
            continue
        manifests.append(manifest)
    return StandardsRegistry(manifests, root=registry.root)


def resolve_cdisc_home(cdisc_home: str | Path | None = None) -> Path:
    """Resolve the managed CDISC cache root, with CDISC_HOME as an advanced override."""

    raw = cdisc_home if cdisc_home is not None else os.environ.get(CDISC_HOME_ENV_VAR)
    if raw is not None:
        return Path(raw).expanduser().resolve()
    return managed_cache_root()


def managed_cache_root() -> Path:
    """Return the default user-managed cache root for CDISC standards."""

    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return (Path(local_app_data) / "standards_driven_sdtm_adam" / "cdisc").resolve()
    return (Path.home() / ".standards_driven_sdtm_adam" / "cdisc").resolve()


def production_standards_dir(cdisc_home: str | Path) -> Path:
    """Return the production standards directory under CDISC_HOME."""

    return Path(cdisc_home).resolve() / "standards"


def manual_setup_lines(result: StandardsAcquisitionResult) -> tuple[str, ...]:
    """Return user-facing manual fallback instructions for missing/failed sources."""

    lines: list[str] = []
    for item in sorted(result.missing + result.failed, key=lambda value: value.standard_id):
        source = item.source_url or "No official source URL is configured in the manifest."
        filename = item.official_filename or "No official filename is configured."
        destination = str(item.local_path) if item.local_path is not None else "No local_path is configured."
        lines.append(
            f"{item.title} ({item.standard_id}): the Skill identified {source} and expects {filename}; place the authorized download at {destination}."
        )
    return tuple(lines)


def render_missing_standard_plan(plan: StandardsAcquisitionPlan) -> str:
    """Render one aggregated user-facing missing standards prompt."""

    if not plan.missing:
        return "All required CDISC sources are available locally."
    lines = ["Required CDISC sources not available locally:"]
    for item in sorted(plan.missing, key=lambda value: value.title):
        version = item.location.required_version if item.location else None
        suffix = f" {version}" if version else ""
        lines.append(f"- {item.title}{suffix}")
    lines.append("")
    lines.append("Authorization is required to retrieve these official sources.")
    return "\n".join(lines)


def source_url_for(manifest: StandardManifest) -> str | None:
    """Return the configured official acquisition URL for one manifest."""

    return manifest.package_url or manifest.official_url


def acquisition_type_for(manifest: StandardManifest) -> str:
    """Return the explicit acquisition mode implied by one manifest."""

    if manifest.package_url and manifest.members:
        return ACQUISITION_PACKAGE_MEMBER
    source_url = source_url_for(manifest)
    if source_url is None:
        return ACQUISITION_DIRECT_FILE
    suffix = Path(urllib.parse.unquote(urllib.parse.urlparse(source_url).path)).suffix.lower()
    if suffix in CONTENT_TYPES_BY_SUFFIX:
        return ACQUISITION_DIRECT_FILE
    return ACQUISITION_PRODUCT_PAGE


def expected_content_type_for_filename(filename: str | None) -> str | None:
    """Infer expected content type from an official filename."""

    if filename is None:
        return None
    return CONTENT_TYPES_BY_SUFFIX.get(Path(filename).suffix.lower())


def validate_downloaded_content(
    path: Path | None,
    *,
    expected_filename: str | None,
    expected_content_type: str | None = None,
    response_content_type: str | None = None,
) -> str | None:
    """Validate downloaded content before marking acquisition successful."""

    if path is None:
        return "missing local path"
    if expected_filename is not None:
        final_name = path.name[:-5] if path.name.endswith(".part") else path.name
        if final_name != expected_filename:
            return "wrong filename"
    if not path.exists() or path.stat().st_size == 0:
        return "empty or missing file"
    prefix = path.read_bytes()[:4096]
    lower_prefix = prefix.lower().lstrip()
    if lower_prefix.startswith(b"<html") or b"<form" in lower_prefix:
        return "HTML/login page content"
    if lower_prefix.startswith(b"{") or lower_prefix.startswith(b"["):
        return "JSON response content"
    if b"access denied" in lower_prefix or b"sign in" in lower_prefix or b"login" in lower_prefix:
        return "access denied or sign-in content"

    if expected_content_type and response_content_type:
        normalized = response_content_type.split(";", 1)[0].strip().lower()
        if normalized and normalized not in _allowed_content_types(expected_content_type):
            return "wrong content type"

    suffix = Path(expected_filename or path.name).suffix.lower()
    if suffix == ".pdf":
        return None if prefix.startswith(b"%PDF-") else "wrong PDF signature"
    if suffix in {".zip", ".xlsx"}:
        return _validate_zip(path)
    if suffix == ".xls":
        return None if prefix.startswith(b"\xd0\xcf\x11\xe0") else "wrong XLS signature"
    return None


def is_git_tracked_path(path: Path) -> bool:
    """Return whether Git already tracks the exact destination path."""

    try:
        subprocess.run(
            ["git", "-C", str(path.parent), "ls-files", "--error-unmatch", str(path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return False
    return True


def _availability_item(
    registry: StandardsRegistry,
    manifest: StandardManifest,
) -> StandardsAcquisitionItem:
    status = registry.local_file_status(manifest)
    local_path = registry.resolve_local_path(manifest) or registry.resolve_local_root(manifest)
    location = locate_standard(registry, manifest)
    if status == "AVAILABLE":
        return StandardsAcquisitionItem(
            standard_id=manifest.id,
            title=manifest.title,
            status="available",
            source_url=source_url_for(manifest),
            local_path=local_path,
            official_filename=manifest.original_filename,
            message="Local configured source is available.",
            location=location,
        )
    return StandardsAcquisitionItem(
        standard_id=manifest.id,
        title=manifest.title,
        status="missing",
        source_url=source_url_for(manifest),
        local_path=local_path,
        official_filename=manifest.original_filename,
        message=f"Local source status is {status}.",
        location=location,
    )


def _replace_item(
    item: StandardsAcquisitionItem,
    *,
    status: str,
    message: str,
    sha256: str | None = None,
) -> StandardsAcquisitionItem:
    return StandardsAcquisitionItem(
        standard_id=item.standard_id,
        title=item.title,
        status=status,
        source_url=item.source_url,
        local_path=item.local_path,
        official_filename=item.official_filename,
        message=message,
        sha256=sha256,
        location=item.location,
    )


def _validate_zip(path: Path) -> str | None:
    if path.read_bytes()[:4] != b"PK\x03\x04":
        return "wrong ZIP signature"
    try:
        with zipfile.ZipFile(path) as archive:
            archive.testzip()
    except zipfile.BadZipFile:
        return "unreadable ZIP archive"
    return None


def _select_archive_member(package_path: Path, manifest: StandardManifest) -> str:
    expected = manifest.original_filename
    configured_members = manifest.members or ((expected,) if expected else ())
    try:
        with zipfile.ZipFile(package_path) as archive:
            names = tuple(name for name in archive.namelist() if not name.endswith("/"))
    except zipfile.BadZipFile as exc:
        raise StandardsDownloadError(f"Unreadable package for {manifest.id}.") from exc

    for configured in configured_members:
        if configured in names:
            return configured
    for configured in configured_members:
        configured_name = Path(configured).name
        matches = [name for name in names if Path(name).name == configured_name]
        if len(matches) == 1:
            return matches[0]
    raise StandardsDownloadError(
        f"Package for {manifest.id} does not contain expected member {', '.join(configured_members)}."
    )


def _find_archive_member_by_basename(names: tuple[str, ...], configured: str) -> str:
    configured_name = Path(configured).name
    matches = [name for name in names if Path(name).name == configured_name]
    if len(matches) == 1:
        return matches[0]
    raise KeyError(configured)


def _page_links(page: Any) -> tuple[dict[str, str], ...]:
    try:
        links = page.locator("a").evaluate_all(
            """elements => elements.map(element => ({
                href: element.href || '',
                text: element.textContent || '',
                download: element.getAttribute('download') || ''
            }))"""
        )
    except Exception:
        return ()
    if not isinstance(links, list):
        return ()
    normalized = []
    for link in links:
        if isinstance(link, dict):
            normalized.append(
                {
                    "href": str(link.get("href") or ""),
                    "text": str(link.get("text") or ""),
                    "download": str(link.get("download") or ""),
                }
            )
    return tuple(normalized)


def _match_download_link(
    links: tuple[dict[str, str], ...],
    expected_filename: str,
    product_url: str,
) -> str | None:
    expected = _normalize_filename(expected_filename)
    for link in links:
        href = link["href"]
        if not href:
            continue
        resolved = urllib.parse.urljoin(product_url, href)
        basename = _normalize_filename(Path(urllib.parse.unquote(urllib.parse.urlparse(resolved).path)).name)
        text = _normalize_filename(link["text"])
        download = _normalize_filename(link["download"])
        if expected in {basename, text, download}:
            return resolved
        if expected and expected in _normalize_filename(urllib.parse.unquote(resolved)):
            return resolved
    suffix = Path(expected_filename).suffix.lower()
    candidates = []
    for link in links:
        href = link["href"]
        if not href:
            continue
        resolved = urllib.parse.urljoin(product_url, href)
        path = urllib.parse.unquote(urllib.parse.urlparse(resolved).path)
        if "/system/files/" in path and Path(path).suffix.lower() == suffix:
            candidates.append(resolved)
    if len(candidates) == 1:
        return candidates[0]
    return None


def _normalize_filename(value: str) -> str:
    return " ".join(value.replace("\xa0", " ").split()).lower()


def _allowed_content_types(expected_content_type: str) -> set[str]:
    allowed = {expected_content_type.lower()}
    if expected_content_type in {
        "application/pdf",
        "application/zip",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",
    }:
        allowed.add("application/octet-stream")
    if expected_content_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
        allowed.add("application/zip")
    return allowed


def _response_content_type(response: Any) -> str | None:
    headers = getattr(response, "headers", None)
    if not headers:
        return None
    if isinstance(headers, dict):
        return headers.get("content-type") or headers.get("Content-Type")
    try:
        return headers.get("content-type") or headers.get("Content-Type")
    except Exception:
        return None


def _is_transient_request_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return any(marker in message for marker in ("econnreset", "socket hang up", "net::err_connection_reset"))


def _resource_requires_login(page: Any) -> bool:
    try:
        title = page.title().lower()
    except Exception:
        title = ""
    try:
        body = page.locator("body").inner_text(timeout=1000).lower()
    except Exception:
        body = ""
    return (
        "sign in/sign up" in title
        or "information you are attempting to access requires" in body
        or "please sign in/sign up" in body
        or "sign in or sign up" in body
        or "sign in/signup" in body
        or body.strip() == "sign in"
    )


def _page_is_login_flow(page: Any) -> bool:
    url = str(getattr(page, "url", "")).lower()
    if any(marker in url for marker in ("b2clogin", "/user/login", "signin", "login")):
        return True
    try:
        body = page.locator("body").inner_text(timeout=1000).lower()
    except Exception:
        body = ""
    return "sign in" in body and "don't have an account" in body


def _page_is_closed(page: Any) -> bool:
    try:
        return bool(page.is_closed())
    except Exception:
        return False


def _page_login_failed(page: Any) -> bool:
    try:
        body = page.locator("body").inner_text(timeout=1000).lower()
    except Exception:
        return False
    return any(
        marker in body
        for marker in (
            "we can't seem to find your account",
            "your password is incorrect",
            "access denied",
            "login failed",
        )
    )


def _redact(message: str) -> str:
    redacted = message
    for marker in ("api-key", "authorization", "password", "token", "cookie"):
        redacted = redacted.replace(marker.upper(), marker)
    return redacted
