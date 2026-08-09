"""Structured feasibility assessment models."""

from __future__ import annotations

from dataclasses import dataclass, field


FEASIBILITY_STATUSES = ("FEASIBLE", "PARTIALLY_FEASIBLE", "UNSUPPORTED")


@dataclass(frozen=True)
class FeasibilityRequirement:
    """Source-data requirements parsed from one research objective."""

    objective_id: str
    objective_text: str
    required_domains: tuple[str, ...]
    required_variables: dict[str, tuple[str, ...]]
    temporal_required: bool = False
    abnormality_required: bool = False
    baseline_required: bool = False
    temporal_window_required: bool = False
    monitoring_profile_required: bool = False
    predictive_model_required: bool = False


@dataclass(frozen=True)
class FeasibilityResult:
    """Evidence-based feasibility result for one research objective."""

    objective_id: str
    objective_text: str
    status: str
    required_domains: tuple[str, ...]
    available_domains: tuple[str, ...]
    missing_domains: tuple[str, ...]
    required_variables: dict[str, tuple[str, ...]]
    missing_variables: dict[str, tuple[str, ...]]
    subject_coverage: dict[str, object]
    date_coverage: dict[str, object]
    blocking_issues: tuple[str, ...]
    limitations: tuple[str, ...]
    evidence_references: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class SupportedResearchObjective:
    """Research objective genuinely supported by available SDTM data."""

    objective_text: str
    supported_domains: tuple[str, ...]
    support_reasons: tuple[str, ...]
    support_score: int


@dataclass(frozen=True)
class FeasibilityAssessment:
    """Complete assessment response."""

    results: tuple[FeasibilityResult, ...]
    supported_research_objectives: tuple[SupportedResearchObjective, ...]
