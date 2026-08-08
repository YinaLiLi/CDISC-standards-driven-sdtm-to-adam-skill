"""Manual live CDISC acquisition acceptance test for maintainers."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil

from standards_driven_sdtm_adam.discovery import StandardsDiscoveryEngine
from standards_driven_sdtm_adam.standards.acquisition import (
    BrowserAuthenticatedStandardsDownloader,
    StandardsAcquisitionError,
    acquire_manifest_sources,
    acquire_required_standards,
    plan_required_standards_for_tasks,
    production_standards_dir,
    registry_with_storage_roots,
    registry_with_standard_root,
    required_runtime_manifests,
    render_missing_standard_plan,
    resolve_cdisc_home,
    validate_downloaded_content,
    validation_reference_manifests,
)
from standards_driven_sdtm_adam.standards.registry import StandardsRegistry


DEFAULT_LIVE_STANDARD_IDS = ("adamig",)
DEFAULT_REGISTRY_DIR = Path("config") / "standards"


def live_test_standards_dir(cdisc_home: str | Path, subdir: str | None = None) -> Path:
    """Return the isolated live acceptance test standards directory under CDISC_HOME."""

    root = Path(cdisc_home).resolve() / "standards_test"
    if subdir is None:
        return root
    return (root / subdir).resolve()


def main(argv: list[str] | None = None) -> int:
    """Run the manual live acceptance command."""

    parser = argparse.ArgumentParser(
        description="Run an isolated live CDISC standards acquisition acceptance test.",
    )
    parser.add_argument("--registry-dir", default=str(DEFAULT_REGISTRY_DIR))
    parser.add_argument("--standard-id", action="append", dest="standard_ids")
    parser.add_argument("--full-plan", action="store_true")
    parser.add_argument("--test-subdir")
    parser.add_argument("--reuse-existing", action="store_true")
    parser.add_argument("--cleanup", action="store_true")
    parser.add_argument("--yes", action="store_true")
    args = parser.parse_args(argv)

    try:
        cdisc_home = resolve_cdisc_home()
    except StandardsAcquisitionError as exc:
        print(str(exc))
        return 2

    production_dir = production_standards_dir(cdisc_home)
    test_dir = live_test_standards_dir(cdisc_home, args.test_subdir)
    test_root = live_test_standards_dir(cdisc_home)

    if args.cleanup:
        return cleanup_standards_test(cdisc_home, yes=args.yes)

    print("LIVE CDISC ACQUISITION TEST")
    print("This command performs live CDISC network access using your authorized CDISC credentials.")
    print(f"Production standards directory: {production_dir}")
    standards_dir = test_dir / "standards" if args.full_plan else test_dir
    examples_dir = test_dir / "examples" if args.full_plan else test_dir

    print(f"Test standards directory: {standards_dir}")
    if args.full_plan:
        print(f"Test examples directory: {examples_dir}")
    print(f"Active isolated test destination: {test_dir.relative_to(Path(cdisc_home).resolve())}")

    try:
        test_dir.relative_to(test_root)
    except ValueError:
        print("Refusing to run because the active test destination is outside standards_test.")
        return 2
    if production_dir == test_dir or production_dir in test_dir.parents:
        print("Refusing to run because the active test destination overlaps production standards.")
        return 2

    if test_dir.exists() and any(test_dir.iterdir()):
        print(f"{test_dir} already contains files.")
        if not args.reuse_existing and not _confirm("Type REUSE to run against existing standards_test files: ", expected="REUSE"):
            print("Cleanup first with: python -m devtools.live_acquisition_acceptance --cleanup")
            return 2

    registry = StandardsRegistry.load(args.registry_dir, validate_integrity=False)
    validation_ids: tuple[str, ...] = ()
    if args.standard_ids:
        selected_ids = tuple(args.standard_ids)
        overlay_registry = registry_with_standard_root(
            registry,
            standards_dir,
            standard_ids=selected_ids,
        )
    elif args.full_plan:
        selected_ids = tuple(manifest.id for manifest in required_runtime_manifests(registry))
        validation_ids = tuple(manifest.id for manifest in validation_reference_manifests(registry))
        overlay_registry = registry_with_storage_roots(
            registry,
            standards_root=standards_dir,
            examples_root=examples_dir,
            standard_ids=selected_ids + validation_ids,
        )
    else:
        selected_ids = DEFAULT_LIVE_STANDARD_IDS
        overlay_registry = registry_with_standard_root(
            registry,
            standards_dir,
            standard_ids=selected_ids,
        )
    live_registry = _selected_required_registry(overlay_registry, selected_ids)
    selected = _selected_required_manifests(live_registry, selected_ids)
    if not selected:
        print("No selected required runtime standards are configured for live acquisition.")
        return 2

    print("Selected live standard sources:")
    for manifest in selected:
        print(f"- {manifest.title} ({manifest.id})")
        print(f"  Official location: {manifest.package_url or manifest.official_url}")
        print(f"  Expected file: {manifest.original_filename}")
        print("  Reason: required Version 1 primary standard resolved automatically from the registry.")

    task_intents = () if args.full_plan else ("Create ADSL subject-level analysis dataset",)
    plan = plan_required_standards_for_tasks(live_registry, task_intents=task_intents)
    validation_manifests = tuple(
        manifest for manifest in validation_reference_manifests(overlay_registry) if manifest.id in validation_ids
    )
    validation_check = None
    if validation_manifests:
        from standards_driven_sdtm_adam.standards.acquisition import check_manifest_sources

        validation_check = check_manifest_sources(overlay_registry, validation_manifests)
    print("")
    print("Exact planned source list:")
    for item in plan.required:
        print(f"- {item.title} ({item.standard_id})")
        print(f"  Official filename: {item.official_filename}")
        print(f"  Source URL: {item.source_url}")
        print(f"  Destination: {item.local_path}")
    print("")
    print(render_missing_standard_plan(plan))
    if validation_manifests:
        print("")
        print("Validation/reference assets:")
        for manifest in validation_manifests:
            location = overlay_registry.resolve_local_path(manifest) or overlay_registry.resolve_local_root(manifest)
            print(f"- {manifest.title} ({manifest.id})")
            print(f"  Official location: {manifest.package_url or manifest.official_url}")
            print(f"  Destination: {location}")
    selected_missing = tuple(item for item in plan.missing if item.standard_id in selected_ids)
    selected_available = tuple(item for item in plan.available if item.standard_id in selected_ids)
    if selected_available and not selected_missing:
        print("Selected standards are already present in standards_test; discovery recognition will be checked.")
    else:
        print("Selected standards missing from standards_test:")
        for item in selected_missing:
            print(f"- {item.title} ({item.standard_id}) -> {item.local_path}")

    validation_missing = tuple(validation_check.missing if validation_check is not None else ())
    needs_acquisition = bool(selected_missing or validation_missing)
    if needs_acquisition:
        print("")
        print("A Chromium window will open. Sign in to CDISC with your cdiscID once, then leave the browser open.")
        downloader = BrowserAuthenticatedStandardsDownloader()
        try:
            downloader.authenticate_once()
            result = (
                acquire_required_standards(plan.registry, downloader)
                if selected_missing
                else plan_result_from_available(plan)
            )
            validation_result = (
                acquire_manifest_sources(overlay_registry, validation_manifests, downloader)
                if validation_missing
                else validation_check
            )
        finally:
            downloader.close()
        print("")
        print("Session instrumentation:")
        print(f"- BrowserContext count: {downloader.browser_contexts_created}")
        print(f"- CDISC login prompt count: {downloader.cdisc_login_prompts}")
        print(f"- Successful CDISC auth count: {downloader.authentication_successes}")
        print(f"- Re-authentication attempts: {downloader.reauthentication_attempts}")
        print(f"- Network downloads: {downloader.network_downloads}")
        print(f"- Deduplicated package downloads: {downloader.deduplicated_package_downloads}")
        print("Per-source acquisition result:")
        print("Runtime-required sources:")
        _print_result_table(plan, result)
        if validation_result is not None:
            print("Validation/reference assets:")
            _print_result_table_from_items(validation_result)
        failed = bool(result.missing or result.failed or (validation_result and (validation_result.missing or validation_result.failed)))
        if failed:
            print("Live acquisition did not complete.")
            for item in result.missing + result.failed:
                if item.standard_id in selected_ids:
                    print(_ascii_safe(f"- {item.title} ({item.standard_id}): {item.message}"))
            if validation_result is not None:
                for item in validation_result.missing + validation_result.failed:
                    print(_ascii_safe(f"- {item.title} ({item.standard_id}): {item.message}"))
            _print_downloaded_files(test_dir)
            return 1
    else:
        result = None
        validation_result = validation_check

    validation_errors = []
    for manifest in selected:
        path = live_registry.resolve_local_path(manifest)
        error = validate_downloaded_content(
            path,
            expected_filename=manifest.original_filename,
            expected_content_type=None,
            response_content_type=None,
        )
        if error is not None:
            validation_errors.append(f"{manifest.id}: {error}")
    for manifest in validation_manifests:
        path = overlay_registry.resolve_local_path(manifest)
        root = overlay_registry.resolve_local_root(manifest)
        if path is not None:
            error = validate_downloaded_content(
                path,
                expected_filename=manifest.original_filename,
                expected_content_type=None,
                response_content_type=None,
            )
            if error is not None:
                validation_errors.append(f"{manifest.id}: {error}")
        elif root is not None:
            missing = tuple(member for member in manifest.members if not (root / member).exists())
            if missing:
                validation_errors.append(f"{manifest.id}: missing members {', '.join(missing)}")

    if validation_errors:
        print("Downloaded content failed false-success validation:")
        for error in validation_errors:
            print(f"- {error}")
        return 1

    discovery = StandardsDiscoveryEngine(live_registry).discover("Create ADSL subject-level analysis dataset")
    discovered_ids = {item.standard_id for item in discovery.results}
    if not set(selected_ids).intersection(discovered_ids):
        print("Downloaded standards were not recognized by existing discovery logic.")
        return 1

    print("LIVE ACQUISITION TEST COMPLETE")
    print("One-login reuse result: one BrowserAuthenticatedStandardsDownloader instance was used for all missing planned sources and validation/reference assets.")
    print("")
    print("Downloaded:")
    for manifest in selected:
        print(f"- {manifest.title}")
        print(f"- {manifest.original_filename}")
    print("")
    print("Location:")
    print(standards_dir)
    if args.full_plan:
        print("Examples:")
        print(examples_dir)
    print("")
    print("Manual review required:")
    print("- confirm files exist")
    print("- confirm filenames match official filenames")
    print("- open files manually")
    print("- confirm they are actual CDISC documents/data")
    print("- confirm no HTML/login/error content")
    return 0


def cleanup_standards_test(cdisc_home: str | Path, *, yes: bool = False) -> int:
    """Delete only CDISC_HOME/standards_test after path safety checks."""

    home = Path(cdisc_home).resolve()
    production_dir = production_standards_dir(home)
    test_dir = live_test_standards_dir(home)
    refusal = cleanup_refusal_reason(test_dir, cdisc_home=home, production_dir=production_dir)
    if refusal is not None:
        print(refusal)
        return 2

    print("Cleanup will delete:")
    print(test_dir)
    if not test_dir.exists():
        print("Nothing to delete.")
        return 0

    if not yes and not _confirm("Type DELETE to remove standards_test: ", expected="DELETE"):
        print("Cleanup cancelled.")
        return 2

    shutil.rmtree(test_dir)
    print("Deleted standards_test.")
    return 0


def cleanup_refusal_reason(
    candidate: str | Path,
    *,
    cdisc_home: str | Path,
    production_dir: str | Path,
) -> str | None:
    """Return a refusal reason when a cleanup path is unsafe."""

    candidate_path = Path(candidate).resolve()
    home = Path(cdisc_home).resolve()
    production_path = Path(production_dir).resolve()

    if candidate_path == production_path:
        return "Refusing to delete the production standards directory."
    if candidate_path == home:
        return "Refusing to delete CDISC_HOME."
    if candidate_path == Path(candidate_path.anchor):
        return "Refusing to delete a filesystem root."
    if candidate_path.name != "standards_test":
        return "Refusing to delete anything except standards_test."
    expected = home / "standards_test"
    try:
        candidate_path.relative_to(home)
    except ValueError:
        return "Refusing to delete a path outside CDISC_HOME."
    if candidate_path != expected:
        return "Refusing to delete a nonstandard standards_test path."
    return None


def _selected_required_manifests(registry: StandardsRegistry, standard_ids: tuple[str, ...]):
    selected = []
    required = {manifest.id: manifest for manifest in required_runtime_manifests(registry)}
    for standard_id in standard_ids:
        manifest = required.get(standard_id)
        if manifest is not None:
            selected.append(manifest)
    return tuple(selected)


def _selected_required_registry(registry: StandardsRegistry, standard_ids: tuple[str, ...]) -> StandardsRegistry:
    selected = _selected_required_manifests(registry, standard_ids)
    return StandardsRegistry(selected, root=registry.root)


def plan_result_from_available(plan):
    from standards_driven_sdtm_adam.standards.acquisition import StandardsAcquisitionResult

    return StandardsAcquisitionResult(
        available=plan.available,
        missing=(),
        acquired=(),
        failed=(),
    )


def _confirm(prompt: str, *, expected: str) -> bool:
    try:
        value = input(prompt)
    except EOFError:
        return False
    return value == expected


def _print_result_table(plan, result) -> None:
    acquired = {item.standard_id: item for item in result.acquired}
    available = {item.standard_id: item for item in result.available}
    failed = {item.standard_id: item for item in result.failed}
    missing = {item.standard_id: item for item in result.missing}
    for planned in plan.required:
        item = acquired.get(planned.standard_id) or available.get(planned.standard_id) or failed.get(planned.standard_id) or missing.get(planned.standard_id) or planned
        path = item.local_path
        size = path.stat().st_size if path is not None and path.exists() else 0
        validation = None
        if path is not None and path.exists():
            validation = validate_downloaded_content(
                path,
                expected_filename=item.official_filename,
                expected_content_type=None,
                response_content_type=None,
            )
        validation_text = "PASS" if path is not None and path.exists() and validation is None else (validation or "not available")
        print(
            _ascii_safe(
                f"- {item.status.upper()}: {item.title} ({item.standard_id}) | "
                f"filename={item.official_filename} | source={item.source_url} | "
                f"size={size} | validation={validation_text} | path={item.local_path} | "
                f"message={item.message}"
            )
        )


def _print_result_table_from_items(result) -> None:
    for item in result.available + result.acquired + result.missing + result.failed:
        path = item.local_path
        size = 0
        validation_text = "not available"
        if path is not None and path.exists() and path.is_file():
            size = path.stat().st_size
            validation = validate_downloaded_content(
                path,
                expected_filename=item.official_filename,
                expected_content_type=None,
                response_content_type=None,
            )
            validation_text = validation or "PASS"
        elif path is not None and path.exists() and path.is_dir():
            files = [child for child in path.rglob("*") if child.is_file()]
            size = sum(child.stat().st_size for child in files)
            validation_text = "PASS"
        print(
            _ascii_safe(
                f"- {item.status.upper()}: {item.title} ({item.standard_id}) | "
                f"filename={item.official_filename} | source={item.source_url} | "
                f"size={size} | validation={validation_text} | path={item.local_path} | "
                f"message={item.message}"
            )
        )


def _print_downloaded_files(test_dir: Path) -> None:
    print("")
    print("Downloaded files currently present:")
    if not test_dir.exists():
        print("- none")
        return
    files = sorted(path for path in test_dir.rglob("*") if path.is_file())
    if not files:
        print("- none")
        return
    for path in files:
        print(f"- {path.name} | size={path.stat().st_size} | path={path}")


def _ascii_safe(value: str) -> str:
    return value.replace("→", "->").encode("ascii", errors="replace").decode("ascii")


if __name__ == "__main__":
    raise SystemExit(main())
