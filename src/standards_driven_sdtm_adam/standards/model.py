"""Standards manifest data model."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

from standards_driven_sdtm_adam.standards.errors import StandardsRegistryError


REQUIRED_STANDARD_FIELDS = (
    "id",
    "title",
    "official_url",
    "sha256",
    "indexed",
    "verified",
    "enabled",
)

STANDARD_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")
VERSION_PATTERN = re.compile(r"^[0-9]+(?:\.[0-9]+)*(?:[-+][A-Za-z0-9.-]+)?$")
ALLOWED_SOURCE_ROLES = (
    "primary_standard",
    "upstream_reference",
    "validation_reference",
    "future_scope",
)
LEGACY_SCOPE_TO_ROLE = {
    "primary": "primary_standard",
    "upstream_reference": "upstream_reference",
    "example_reference": "validation_reference",
    "future_scope": "future_scope",
}
ROLE_TO_SCOPE = {
    "primary_standard": "primary",
    "upstream_reference": "upstream_reference",
    "validation_reference": "validation_reference",
    "future_scope": "future_scope",
}
VERIFICATION_STATUSES = (
    "VERIFIED",
    "PARTIALLY_VERIFIED",
    "UNVERIFIED",
    "MISMATCH",
    "MISSING",
    "NOT_APPLICABLE",
)
SHA256_STATUSES = ("PRESENT", "MISSING", "MISMATCH", "NOT_APPLICABLE")


@dataclass(frozen=True)
class StandardManifest:
    """Registration metadata for one CDISC standard."""

    id: str
    title: str
    role: str
    version: str | None
    release_date: str | None
    official_url: str | None
    package_url: str | None
    local_path: str | None
    local_root: str | None
    original_filename: str | None
    sha256: str | None
    sha256_status: str
    verification_status: str
    indexed: bool
    verified: bool
    enabled: bool
    members: tuple[str, ...] = ()
    manifest_path: Path | None = None

    @property
    def scope_category(self) -> str:
        """Backward-compatible discovery category."""

        return ROLE_TO_SCOPE[self.role]

    @property
    def package_version(self) -> str | None:
        """Alias package version onto version for package references."""

        return self.version

    @classmethod
    def from_mapping(
        cls,
        payload: dict[str, Any],
        *,
        manifest_path: Path | None = None,
    ) -> "StandardManifest":
        """Create a manifest from a parsed YAML mapping."""

        if not isinstance(payload, dict):
            raise StandardsRegistryError("Manifest schema must be a mapping.")

        if payload.get("schema_version") != 1:
            raise StandardsRegistryError("Manifest schema_version must be 1.")

        standard = payload.get("standard")
        if not isinstance(standard, dict):
            raise StandardsRegistryError("Manifest must contain a standard mapping.")

        role = standard.get("role")
        if role is None and "scope_category" in standard:
            role = LEGACY_SCOPE_TO_ROLE.get(standard["scope_category"])
            if role is None:
                raise StandardsRegistryError(
                    "scope_category must be one of: "
                    f"{', '.join(LEGACY_SCOPE_TO_ROLE)}."
                )
        missing = [field for field in REQUIRED_STANDARD_FIELDS if field not in standard]
        if "role" not in standard and "scope_category" not in standard:
            missing.append("role")
        if missing:
            raise StandardsRegistryError(
                f"Manifest is missing required fields: {', '.join(missing)}."
            )

        manifest = cls(
            id=standard["id"],
            title=standard["title"],
            role=role,
            version=standard["version"],
            release_date=standard.get("release_date"),
            official_url=standard["official_url"],
            package_url=standard.get("package_url"),
            local_path=standard.get("local_path"),
            local_root=standard.get("local_root"),
            original_filename=standard.get("original_filename"),
            sha256=standard["sha256"],
            sha256_status=standard.get("sha256_status") or ("PRESENT" if standard["sha256"] else "MISSING"),
            verification_status=standard.get("verification_status") or ("VERIFIED" if standard["verified"] else "UNVERIFIED"),
            indexed=standard["indexed"],
            verified=standard["verified"],
            enabled=standard["enabled"],
            members=tuple(standard.get("members") or ()),
            manifest_path=manifest_path,
        )
        manifest.validate_schema()
        return manifest

    def validate_schema(self) -> None:
        """Validate manifest field types and values."""

        if not isinstance(self.id, str) or not STANDARD_ID_PATTERN.fullmatch(self.id):
            raise StandardsRegistryError("Standard id must be a lowercase slug.")

        if not isinstance(self.title, str) or not self.title.strip():
            raise StandardsRegistryError("Standard title must be a non-empty string.")

        if self.role not in ALLOWED_SOURCE_ROLES:
            raise StandardsRegistryError(
                "role must be one of: "
                f"{', '.join(ALLOWED_SOURCE_ROLES)}."
            )

        if self.version is not None:
            if not isinstance(self.version, str) or not VERSION_PATTERN.fullmatch(self.version):
                raise StandardsRegistryError("Standard version is invalid.")

        if self.release_date is not None:
            if not isinstance(self.release_date, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", self.release_date):
                raise StandardsRegistryError("release_date must use YYYY-MM-DD format or null.")

        if self.official_url is not None and not isinstance(self.official_url, str):
            raise StandardsRegistryError("official_url must be a string or null.")

        if self.package_url is not None and not isinstance(self.package_url, str):
            raise StandardsRegistryError("package_url must be a string or null.")

        if self.local_path is not None and not isinstance(self.local_path, str):
            raise StandardsRegistryError("local_path must be a string or null.")

        if self.local_root is not None and not isinstance(self.local_root, str):
            raise StandardsRegistryError("local_root must be a string or null.")

        if self.original_filename is not None and not isinstance(self.original_filename, str):
            raise StandardsRegistryError("original_filename must be a string or null.")

        if self.sha256 is not None:
            if not isinstance(self.sha256, str) or not re.fullmatch(r"[a-fA-F0-9]{64}", self.sha256):
                raise StandardsRegistryError("sha256 must be a 64-character hex digest or null.")

        if self.sha256_status not in SHA256_STATUSES:
            raise StandardsRegistryError(
                "sha256_status must be one of: "
                f"{', '.join(SHA256_STATUSES)}."
            )

        if self.verification_status not in VERIFICATION_STATUSES:
            raise StandardsRegistryError(
                "verification_status must be one of: "
                f"{', '.join(VERIFICATION_STATUSES)}."
            )

        if not isinstance(self.members, tuple) or not all(isinstance(member, str) for member in self.members):
            raise StandardsRegistryError("members must be a list of strings.")

        for field_name in ("indexed", "verified", "enabled"):
            if not isinstance(getattr(self, field_name), bool):
                raise StandardsRegistryError(f"{field_name} must be a boolean.")
