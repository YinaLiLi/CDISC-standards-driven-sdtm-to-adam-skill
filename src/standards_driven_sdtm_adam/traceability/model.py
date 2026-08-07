"""Evidence resolution and citation models."""

from __future__ import annotations

from dataclasses import dataclass


DECISION_CLASSIFICATIONS = (
    "STANDARD_REQUIRED",
    "STANDARD_GUIDED",
    "STUDY_SPECIFIC",
    "USER_DEFINED",
    "DATA_ENGINEERING",
    "EXAMPLE_ADAPTED",
    "UNSUPPORTED",
)

EVIDENCE_USES = ("decision_support", "validation_support")
RESOLUTION_STATUSES = (
    "RESOLVED",
    "NO_VALID_STANDARD_EVIDENCE",
    "NON_STANDARD_DECISION",
)


@dataclass(frozen=True)
class DecisionEvidenceRequest:
    """Minimal explicit request for resolving evidence for one decision."""

    rule_specification_id: str
    decision_classification: str
    evidence_references: tuple[str, ...]
    evidence_use: str = "decision_support"

    def __post_init__(self) -> None:
        if self.decision_classification not in DECISION_CLASSIFICATIONS:
            raise ValueError(
                "decision_classification must be one of: "
                f"{', '.join(DECISION_CLASSIFICATIONS)}."
            )
        if self.evidence_use not in EVIDENCE_USES:
            raise ValueError(
                f"evidence_use must be one of: {', '.join(EVIDENCE_USES)}."
            )


@dataclass(frozen=True)
class CitationRecord:
    """Deterministic citation for one resolved evidence record."""

    citation_id: str
    rule_specification_id: str
    decision_classification: str
    citation_purpose: str
    evidence_reference: str
    source_id: str
    source_role: str
    document_title: str
    official_filename: str | None
    standard_version: str | None
    standard_release_date: str | None
    page: int | None
    section: str | None
    table: str | None
    row: str | None
    evidence_type: str
    evidence_text: str | None
    extraction_status: str
    official_url: str | None


@dataclass(frozen=True)
class ResolvedEvidenceItem:
    """Resolved citation outcome for one decision or specification item."""

    rule_specification_id: str
    decision_classification: str
    evidence_use: str
    resolution_status: str
    citations: tuple[CitationRecord, ...]
    unresolved_evidence_references: tuple[str, ...]
    excluded_evidence_references: tuple[str, ...]


@dataclass(frozen=True)
class EvidenceResolutionResult:
    """Complete evidence resolution output."""

    items: tuple[ResolvedEvidenceItem, ...]
