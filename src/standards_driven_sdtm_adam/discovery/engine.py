"""Metadata-only standards discovery engine."""

from __future__ import annotations

from pathlib import Path
import re

from standards_driven_sdtm_adam.discovery.model import DiscoveryResult, DiscoveryRun
from standards_driven_sdtm_adam.standards import StandardManifest, StandardsRegistry


V1_APPLICABLE_ROLES = ("primary_standard", "upstream_reference")

COMMON_ADAM_STANDARD_IDS = (
    "adam-model",
    "adam-important-considerations",
    "adamig",
    "adam-msg",
    "adam-ct",
    "adam-conformance-rules",
)

DATASET_STANDARD_IDS = {
    "adsl": COMMON_ADAM_STANDARD_IDS,
    "adae": (
        "adamig",
        "adam-occds",
        "adam-ct",
        "adam-conformance-rules",
    ),
    "adlb": (
        "adam-model",
        "adamig",
        "adam-ct",
        "adam-conformance-rules",
    ),
    "adtte": (
        "adamig",
        "adam-bds-tte",
        "adam-ct",
        "adam-conformance-rules",
    ),
}

CONCEPT_DATASET_HINTS = {
    "adae": ("adverse event", "adverse events", "treatment-emergent", "treatment emergent"),
    "adlb": ("laboratory", "laboratory analysis", "lab result", "lab results"),
    "adtte": ("time-to-event", "time to event", "survival", "censor"),
}

FUTURE_SCOPE_KEYWORDS = {
    "define-xml": ("define", "define.xml", "define-xml", "metadata xml"),
    "sdrg": ("sdrg", "reviewer's guide", "reviewers guide", "study data reviewer"),
}

SDTM_INTENT_KEYWORDS = (
    "sdtm preprocessing",
    "source-preserving",
    "source preserving",
    "upstream sdtm",
    "sdtm source",
)


class StandardsDiscoveryEngine:
    """Identify registered standards that should be consulted."""

    def __init__(self, registry: StandardsRegistry) -> None:
        self.registry = registry

    @classmethod
    def from_registry_dir(cls, registry_dir: str | Path) -> "StandardsDiscoveryEngine":
        """Load a registry for discovery without enforcing local-file integrity."""

        registry = StandardsRegistry.load(registry_dir, validate_integrity=False)
        return cls(registry)

    def discover(self, task_intent: str) -> DiscoveryRun:
        """Return standards that may be relevant to the task intent."""

        normalized = _normalize(task_intent)
        future_scope_matches = self._future_scope_matches(normalized)
        candidate_ids = self._candidate_standard_ids(normalized)
        results = tuple(
            self._to_result(manifest, self._relevance_reason(manifest, normalized))
            for manifest in self._candidate_manifests(candidate_ids)
        )
        upstream_only = bool(results) and all(
            result.scope_category == "upstream_reference" for result in results
        )

        return DiscoveryRun(
            task_intent=task_intent,
            results=results,
            excluded_future_scope=future_scope_matches,
            upstream_only=upstream_only,
            no_applicable_standard=not results,
        )

    def _candidate_standard_ids(self, normalized_task: str) -> tuple[str, ...]:
        if _is_sdtm_preprocessing_intent(normalized_task):
            return ("sdtm-model", "sdtm", "sdtmig")

        dataset = _find_dataset(normalized_task)
        if dataset is not None:
            return DATASET_STANDARD_IDS[dataset]

        hinted_dataset = _find_concept_dataset_hint(normalized_task)
        if hinted_dataset is not None:
            return DATASET_STANDARD_IDS[hinted_dataset]

        if _is_adam_intent(normalized_task):
            return COMMON_ADAM_STANDARD_IDS

        return ()

    def _candidate_manifests(self, candidate_ids: tuple[str, ...]) -> list[StandardManifest]:
        manifests: list[StandardManifest] = []
        for standard_id in candidate_ids:
            try:
                manifest = self.registry.get(standard_id)
            except Exception:
                continue

            if not manifest.enabled:
                continue
            if manifest.role not in V1_APPLICABLE_ROLES:
                continue
            if manifest.role == "validation_reference":
                continue
            if manifest.role == "upstream_reference" and standard_id not in {"sdtm-model", "sdtm", "sdtmig"}:
                continue
            manifests.append(manifest)
        return sorted(manifests, key=lambda manifest: manifest.id)

    def _future_scope_matches(self, normalized_task: str) -> tuple[DiscoveryResult, ...]:
        matches: list[DiscoveryResult] = []
        for standard_id, keywords in FUTURE_SCOPE_KEYWORDS.items():
            if not any(keyword in normalized_task for keyword in keywords):
                continue

            try:
                manifest = self.registry.get(standard_id)
            except Exception:
                continue

            if manifest.role == "future_scope":
                matches.append(
                    self._to_result(
                        manifest,
                        "Matched task metadata, but this standard is future scope and is not used in Version 1 discovery.",
                    )
                )
        return tuple(matches)

    def _to_result(self, manifest: StandardManifest, reason: str) -> DiscoveryResult:
        return DiscoveryResult(
            standard_id=manifest.id,
            title=manifest.title,
            version=manifest.version,
            scope_category=manifest.scope_category,
            relevance_reason=reason,
            local_path=manifest.local_path,
            availability_status=self._availability_status(manifest),
        )

    def _availability_status(self, manifest: StandardManifest) -> str:
        resolved = self.registry.resolve_local_path(manifest)
        if resolved is None:
            return "local_path_not_registered"
        if not resolved.exists():
            return "local_file_missing"
        if manifest.verified:
            return "local_file_verified"
        return "local_file_available_unverified"

    def _relevance_reason(self, manifest: StandardManifest, normalized_task: str) -> str:
        dataset = _find_dataset(normalized_task)

        if manifest.role == "upstream_reference":
            return "Task intent references source-preserving SDTM preprocessing; consult as upstream reference only."

        if manifest.id == "adam-occds":
            return "Task intent references ADAE or adverse event outputs; OCCDS guidance may be applicable."

        if manifest.id == "adam-bds-tte":
            return "Task intent references ADTTE or time-to-event outputs; BDS TTE guidance may be applicable."

        if manifest.id == "adam-ct":
            return "Task intent may require controlled terminology alignment for requested ADaM outputs."

        if manifest.id == "adam-conformance-rules":
            return "Task intent may require ADaM conformance checks after future derivation work."

        if dataset is not None:
            return f"Task intent references {dataset.upper()}; this ADaM standard is part of the Version 1 metadata scope."

        return "Task intent references ADaM development; this standard is part of the Version 1 metadata scope."


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.lower()).strip()


def _find_dataset(normalized_task: str) -> str | None:
    for dataset in DATASET_STANDARD_IDS:
        if re.search(rf"\b{dataset}\b", normalized_task):
            return dataset
    return None


def _find_concept_dataset_hint(normalized_task: str) -> str | None:
    for dataset, hints in CONCEPT_DATASET_HINTS.items():
        if any(hint in normalized_task for hint in hints):
            return dataset
    return None


def _is_adam_intent(normalized_task: str) -> bool:
    return any(keyword in normalized_task for keyword in ("adam", "derive", "analysis dataset"))


def _is_sdtm_preprocessing_intent(normalized_task: str) -> bool:
    return any(keyword in normalized_task for keyword in SDTM_INTENT_KEYWORDS)
