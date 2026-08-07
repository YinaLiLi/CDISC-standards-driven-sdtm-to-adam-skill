"""Stable report models for presenting pipeline outputs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


SUPPORTED_ADAM_DATASETS = ("ADAE", "ADLB", "ADSL", "ADTTE")


@dataclass(frozen=True)
class PipelineReport:
    """Presentation-ready report constructed from existing pipeline outputs."""

    title: str
    overall_status: str
    metadata: dict[str, Any]
    preprocessing_summary: dict[str, Any]
    adam_summary: dict[str, Any]
    validation_summary: dict[str, Any]
    traceability_summary: dict[str, Any]
    evidence_summary: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Return deterministic machine-readable report content."""

        return {
            "title": self.title,
            "overall_status": self.overall_status,
            "metadata": self.metadata,
            "preprocessing": self.preprocessing_summary,
            "adam": self.adam_summary,
            "validation": self.validation_summary,
            "traceability": self.traceability_summary,
            "evidence": self.evidence_summary,
        }
