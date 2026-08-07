"""Standards manifest registry loading and integrity validation."""

from __future__ import annotations

from pathlib import Path
import hashlib
import os
from typing import Any, Iterable

import yaml

from standards_driven_sdtm_adam.standards.errors import StandardsRegistryError
from standards_driven_sdtm_adam.standards.model import StandardManifest


class StandardsRegistry:
    """Load and validate standards manifests from a registry directory."""

    def __init__(self, manifests: Iterable[StandardManifest], *, root: Path) -> None:
        self.root = root
        self._manifests = {manifest.id: manifest for manifest in manifests}

    @classmethod
    def load(
        cls,
        registry_dir: str | Path,
        *,
        validate_integrity: bool = True,
    ) -> "StandardsRegistry":
        """Load all YAML standards manifests from a directory."""

        root = Path(registry_dir)
        if not root.exists() or not root.is_dir():
            raise StandardsRegistryError(f"Registry directory does not exist: {root}")

        manifests: list[StandardManifest] = []
        seen_ids: set[str] = set()
        duplicate_ids: set[str] = set()

        for manifest_path in sorted(root.glob("*.yaml")):
            payload = _load_yaml_mapping(manifest_path)
            manifest = StandardManifest.from_mapping(payload, manifest_path=manifest_path)

            if manifest.id in seen_ids:
                duplicate_ids.add(manifest.id)
            seen_ids.add(manifest.id)
            manifests.append(manifest)

        if duplicate_ids:
            raise StandardsRegistryError(
                f"Duplicate standard ids: {', '.join(sorted(duplicate_ids))}."
            )

        registry = cls(manifests, root=root)
        if validate_integrity:
            registry.validate_integrity()
        return registry

    def resolve_local_path(self, manifest: StandardManifest) -> Path | None:
        """Resolve a manifest local path relative to the registry root."""

        if manifest.local_path is None:
            return None
        return _resolve_local_path(self.root, manifest.local_path)

    def resolve_local_root(self, manifest: StandardManifest) -> Path | None:
        """Resolve a package local root relative to the registry root."""

        if manifest.local_root is None:
            return None
        return _resolve_local_path(self.root, manifest.local_root)

    def local_file_status(self, manifest: StandardManifest) -> str:
        """Return local source availability without interpreting document identity."""

        path = self.resolve_local_path(manifest)
        if path is not None:
            return "AVAILABLE" if path.exists() else "MISSING"

        root = self.resolve_local_root(manifest)
        if root is not None:
            if not root.exists() or not root.is_dir():
                return "MISSING"
            missing_members = self.missing_package_members(manifest)
            return "AVAILABLE" if not missing_members else "PARTIAL"

        return "NOT_APPLICABLE"

    def sha256_status(self, manifest: StandardManifest) -> str:
        """Return whether a local file digest is present and matches when checkable."""

        if manifest.sha256 is None:
            return "NOT_APPLICABLE" if manifest.local_path is None else "MISSING"
        path = self.resolve_local_path(manifest)
        if path is None:
            return "NOT_APPLICABLE"
        if not path.exists():
            return "MISSING"
        return "PRESENT" if _sha256(path) == manifest.sha256.lower() else "MISMATCH"

    def calculate_sha256(self, manifest: StandardManifest) -> str:
        """Calculate a local file digest for Developer Standards Setup."""

        path = self.resolve_local_path(manifest)
        if path is None or not path.exists():
            raise StandardsRegistryError(f"Cannot calculate sha256 for unavailable source: {manifest.id}")
        return _sha256(path)

    def missing_package_members(self, manifest: StandardManifest) -> tuple[str, ...]:
        """Return package members absent from a registered local root."""

        root = self.resolve_local_root(manifest)
        if root is None:
            return ()
        return tuple(member for member in manifest.members if not (root / member).exists())

    def all(self) -> list[StandardManifest]:
        """Return all registered standards sorted by id."""

        return [self._manifests[id_] for id_ in sorted(self._manifests)]

    def enabled(self) -> list[StandardManifest]:
        """Return enabled standards sorted by id."""

        return [manifest for manifest in self.all() if manifest.enabled]

    def by_scope_category(self, scope_category: str) -> list[StandardManifest]:
        """Return standards matching one scope category sorted by id."""

        return [
            manifest
            for manifest in self.all()
            if manifest.scope_category == scope_category
        ]

    def get(self, standard_id: str) -> StandardManifest:
        """Return one standard manifest by id."""

        try:
            return self._manifests[standard_id]
        except KeyError as exc:
            raise StandardsRegistryError(f"Unknown standard id: {standard_id}") from exc

    def validate_integrity(self) -> None:
        """Validate cross-manifest integrity constraints."""

        missing_files = [
            manifest.id
            for manifest in self._manifests.values()
            if manifest.local_path is not None
            and not _resolve_local_path(self.root, manifest.local_path).exists()
        ]

        if missing_files:
            raise StandardsRegistryError(
                f"Standards reference missing local files: {', '.join(sorted(missing_files))}."
            )

        incomplete_packages = [
            manifest.id
            for manifest in self._manifests.values()
            if manifest.local_root is not None and self.missing_package_members(manifest)
        ]

        if incomplete_packages:
            raise StandardsRegistryError(
                f"Standards reference packages with missing members: {', '.join(sorted(incomplete_packages))}."
            )


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)

    if not isinstance(payload, dict):
        raise StandardsRegistryError(f"Invalid manifest schema in {path}.")

    return payload


def _resolve_local_path(registry_root: Path, local_path: str) -> Path:
    expanded = os.path.expandvars(local_path)
    path = Path(expanded)
    if path.is_absolute():
        return path
    return (registry_root / path).resolve()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
