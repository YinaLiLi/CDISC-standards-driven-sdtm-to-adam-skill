"""Structured evidence extraction models."""

from __future__ import annotations

from dataclasses import dataclass


EVIDENCE_TYPES = ("RULE", "GUIDANCE", "DEFINITION", "EXAMPLE", "CONTEXT")


@dataclass(frozen=True)
class EvidenceRecord:
    """Traceable evidence from a local registered standard."""

    evidence_id: str
    standard_id: str
    standard_title: str
    version: str | None
    evidence_type: str
    section: str | None
    page: int | None
    short_quote: str | None
    source_local_path: str | None
    official_url: str | None
    search_context: str
    extraction_status: str


@dataclass(frozen=True)
class RuleExtractionRun:
    """Complete evidence extraction response for one task intent."""

    task_intent: str
    evidence: tuple[EvidenceRecord, ...]
    no_relevant_evidence: bool = False
