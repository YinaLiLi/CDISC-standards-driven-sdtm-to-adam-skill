"""Parse research objectives into source-data feasibility requirements."""

from __future__ import annotations

import re

from standards_driven_sdtm_adam.feasibility.model import FeasibilityRequirement


BASE_REQUIREMENTS: dict[str, tuple[str, ...]] = {
    "DM": ("USUBJID",),
    "AE": ("USUBJID", "AETERM"),
    "LB": ("USUBJID", "LBTESTCD", "LBORRES"),
    "DS": ("USUBJID", "DSDECOD"),
    "EX": ("USUBJID", "EXTRT"),
    "SV": ("USUBJID", "SVSTDTC"),
}

DATE_VARIABLES: dict[str, tuple[str, ...]] = {
    "AE": ("AESTDTC",),
    "LB": ("LBDTC",),
    "DS": ("DSSTDTC",),
    "EX": ("EXSTDTC",),
    "SV": ("SVSTDTC",),
}


class ResearchObjectiveParser:
    """Keyword parser for feasibility requirements."""

    def parse_many(self, objectives: list[str] | tuple[str, ...]) -> tuple[FeasibilityRequirement, ...]:
        return tuple(
            self.parse(objective, objective_id=f"OBJ{i:03d}")
            for i, objective in enumerate(objectives, start=1)
        )

    def parse(self, objective_text: str, *, objective_id: str) -> FeasibilityRequirement:
        normalized = _normalize(objective_text)
        required_domains = set(["DM"])

        if _mentions_any(normalized, ("adverse event", "adverse events", "adae", "treatment-emergent", "treatment emergent")):
            required_domains.add("AE")
        if _mentions_any(normalized, ("laboratory", "laboratory values", "lab ", "adlb", "abnormal laboratory")):
            required_domains.add("LB")
        if _mentions_any(normalized, ("disposition", "discontinue", "completion", "withdrawal", "ds ")):
            required_domains.add("DS")
        if _mentions_any(normalized, ("exposure", "treatment exposure", "dose", "ex ")):
            required_domains.add("EX")
        if _mentions_any(normalized, ("visit", "scheduled visit", "sv ")):
            required_domains.add("SV")

        temporal_required = _mentions_any(
            normalized,
            (
                "associated with",
                "association",
                "after",
                "before",
                "during",
                "temporal",
                "time-to-event",
                "time to event",
                "treatment-emergent",
                "treatment emergent",
            ),
        )

        required_variables = {
            domain: _variables_for_domain(domain, temporal_required)
            for domain in sorted(required_domains)
        }

        return FeasibilityRequirement(
            objective_id=objective_id,
            objective_text=objective_text,
            required_domains=tuple(sorted(required_domains)),
            required_variables=required_variables,
            temporal_required=temporal_required,
        )


def _variables_for_domain(domain: str, temporal_required: bool) -> tuple[str, ...]:
    variables = set(BASE_REQUIREMENTS[domain])
    if temporal_required:
        variables.update(DATE_VARIABLES.get(domain, ()))
    return tuple(sorted(variables))


def _mentions_any(value: str, terms: tuple[str, ...]) -> bool:
    return any(term in value for term in terms)


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.lower()).strip() + " "
