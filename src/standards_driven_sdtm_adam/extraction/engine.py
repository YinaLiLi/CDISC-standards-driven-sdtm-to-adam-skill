"""Evidence extraction from discovered local standards."""

from __future__ import annotations

from pathlib import Path
import re

from standards_driven_sdtm_adam.discovery import StandardsDiscoveryEngine
from standards_driven_sdtm_adam.extraction.model import EvidenceRecord, RuleExtractionRun
from standards_driven_sdtm_adam.extraction.text import (
    TextBlock,
    TextExtractionError,
    extract_text_blocks,
)
from standards_driven_sdtm_adam.standards import StandardsRegistry


MAX_QUOTE_LENGTH = 240
MAX_RECORDS_PER_STANDARD = 5

CONCEPT_TERMS = {
    "adsl": ("adsl", "subject-level", "subject level", "population", "treatment"),
    "adae": ("adae", "adverse event", "adverse events", "treatment-emergent", "treatment emergent"),
    "adlb": ("adlb", "laboratory", "laboratory analysis", "lab", "baseline"),
    "adtte": ("adtte", "time-to-event", "time to event", "event", "censor"),
    "sdtm": ("sdtm", "preprocessing", "source-preserving", "source preserving", "source data"),
}


class RuleExtractionEngine:
    """Extract traceable evidence from discovered local standards."""

    def __init__(self, registry: StandardsRegistry) -> None:
        self.registry = registry
        self.discovery = StandardsDiscoveryEngine(registry)

    @classmethod
    def from_registry_dir(cls, registry_dir: str | Path) -> "RuleExtractionEngine":
        """Load a registry for extraction without failing on missing local files."""

        registry = StandardsRegistry.load(registry_dir, validate_integrity=False)
        return cls(registry)

    def extract(self, task_intent: str) -> RuleExtractionRun:
        """Extract relevant evidence from locally available discovered standards."""

        discovery_run = self.discovery.discover(task_intent)
        search_terms = _search_terms(task_intent)
        search_context = _search_context(search_terms)
        normalized_task = _normalize(task_intent)
        records: list[EvidenceRecord] = []

        for discovered in discovery_run.results:
            manifest = self.registry.get(discovered.standard_id)
            source_path = self.registry.resolve_local_path(manifest)

            if source_path is None:
                records.append(
                    self._status_record(
                        manifest,
                        search_context,
                        source_path=None,
                        extraction_status="STANDARD_FILE_UNAVAILABLE",
                    )
                )
                continue

            if not source_path.exists():
                records.append(
                    self._status_record(
                        manifest,
                        search_context,
                        source_path=source_path,
                        extraction_status="STANDARD_FILE_UNAVAILABLE",
                    )
                )
                continue

            try:
                blocks = extract_text_blocks(source_path)
            except (OSError, TextExtractionError):
                records.append(
                    self._status_record(
                        manifest,
                        search_context,
                        source_path=source_path,
                        extraction_status="TEXT_EXTRACTION_FAILED",
                    )
                )
                continue

            matches = _matching_blocks(blocks, search_terms)
            for match_index, block in enumerate(matches[:MAX_RECORDS_PER_STANDARD], start=1):
                status = "AMBIGUOUS_EVIDENCE" if _is_ambiguous(block.text, normalized_task) else "EXTRACTED"
                records.append(
                    EvidenceRecord(
                        evidence_id=f"{manifest.id}:{match_index}",
                        standard_id=manifest.id,
                        standard_title=manifest.title,
                        version=manifest.version,
                        evidence_type=_classify_evidence(block.text),
                        section=block.section,
                        page=block.page,
                        short_quote=_short_quote(block.text),
                        source_local_path=str(source_path),
                        official_url=manifest.official_url,
                        search_context=search_context,
                        extraction_status=status,
                    )
                )

        return RuleExtractionRun(
            task_intent=task_intent,
            evidence=tuple(records),
            no_relevant_evidence=not records,
        )

    def _status_record(
        self,
        manifest,
        search_context: str,
        *,
        source_path: Path | None,
        extraction_status: str,
    ) -> EvidenceRecord:
        return EvidenceRecord(
            evidence_id=f"{manifest.id}:status",
            standard_id=manifest.id,
            standard_title=manifest.title,
            version=manifest.version,
            evidence_type="CONTEXT",
            section=None,
            page=None,
            short_quote=None,
            source_local_path=str(source_path) if source_path is not None else manifest.local_path,
            official_url=manifest.official_url,
            search_context=search_context,
            extraction_status=extraction_status,
        )


def _matching_blocks(blocks: list[TextBlock], terms: tuple[str, ...]) -> list[TextBlock]:
    scored: list[tuple[int, int, TextBlock]] = []
    for index, block in enumerate(blocks):
        normalized = _normalize(block.text)
        score = sum(1 for term in terms if term in normalized)
        if score:
            scored.append((score, -index, block))

    return [block for _, _, block in sorted(scored, reverse=True)]


def _search_terms(task_intent: str) -> tuple[str, ...]:
    normalized = _normalize(task_intent)
    terms: set[str] = set()

    for concept, concept_terms in CONCEPT_TERMS.items():
        if concept in normalized or any(term in normalized for term in concept_terms):
            terms.update(concept_terms)

    for token in re.findall(r"[a-z][a-z0-9-]{2,}", normalized):
        if token not in {"derive", "create", "plan", "identify", "variables", "dataset", "analysis"}:
            terms.add(token)

    return tuple(sorted(terms, key=len, reverse=True))


def _classify_evidence(text: str) -> str:
    normalized = _normalize(text)
    if "example" in normalized:
        return "EXAMPLE"
    if "definition" in normalized or "defined as" in normalized:
        return "DEFINITION"
    if any(term in normalized for term in ("must", "required", "shall")):
        return "RULE"
    if any(term in normalized for term in ("should", "may", "guidance", "consider")):
        return "GUIDANCE"
    return "CONTEXT"


def _short_quote(text: str) -> str:
    normalized = re.sub(r"\s+", " ", text).strip()
    if len(normalized) <= MAX_QUOTE_LENGTH:
        return normalized
    return normalized[: MAX_QUOTE_LENGTH - 3].rstrip() + "..."


def _is_ambiguous(text: str, normalized_task: str) -> bool:
    normalized_text = _normalize(text)
    if _classify_evidence(text) in {"RULE", "GUIDANCE", "DEFINITION", "EXAMPLE"}:
        return False
    return not any(dataset in normalized_text and dataset in normalized_task for dataset in ("adsl", "adae", "adlb", "adtte"))


def _search_context(terms: tuple[str, ...]) -> str:
    return "metadata_search:" + ", ".join(terms)


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.lower()).strip()
