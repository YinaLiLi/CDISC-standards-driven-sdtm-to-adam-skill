"""Feasibility assessment against available SDTM source data."""

from __future__ import annotations

from standards_driven_sdtm_adam.feasibility.data import SDTMDataSnapshot
from standards_driven_sdtm_adam.feasibility.model import (
    FeasibilityAssessment,
    FeasibilityRequirement,
    FeasibilityResult,
    SupportedResearchObjective,
)
from standards_driven_sdtm_adam.feasibility.parser import ResearchObjectiveParser


class FeasibilityAssessor:
    """Assess whether available SDTM data can support research objectives."""

    def __init__(self) -> None:
        self.parser = ResearchObjectiveParser()

    def assess(
        self,
        objectives: list[str] | tuple[str, ...],
        sdtm_datasets,
        *,
        evidence_references: tuple[str, ...] = (),
    ) -> FeasibilityAssessment:
        snapshot = SDTMDataSnapshot(sdtm_datasets)
        requirements = self.parser.parse_many(objectives)
        results = tuple(
            self._assess_one(requirement, snapshot, evidence_references=evidence_references)
            for requirement in requirements
        )
        return FeasibilityAssessment(
            results=results,
            supported_research_objectives=self._supported_objectives(snapshot),
        )

    def _assess_one(
        self,
        requirement: FeasibilityRequirement,
        snapshot: SDTMDataSnapshot,
        *,
        evidence_references: tuple[str, ...],
    ) -> FeasibilityResult:
        available_domains = tuple(
            domain for domain in requirement.required_domains if snapshot.has_domain(domain)
        )
        missing_domains = tuple(
            domain for domain in requirement.required_domains if not snapshot.has_domain(domain)
        )

        missing_variables = {
            domain: tuple(
                variable
                for variable in variables
                if snapshot.has_domain(domain) and not snapshot.has_variable(domain, variable)
            )
            for domain, variables in requirement.required_variables.items()
        }
        missing_variables = {
            domain: variables for domain, variables in missing_variables.items() if variables
        }

        blocking_issues: list[str] = []
        limitations: list[str] = []

        for domain in missing_domains:
            blocking_issues.append(f"Required SDTM domain {domain} is not available.")

        for domain in available_domains:
            if snapshot.record_count(domain) == 0:
                blocking_issues.append(f"Required SDTM domain {domain} has no usable records.")
            if not snapshot.subject_ids(domain):
                blocking_issues.append(f"Required SDTM domain {domain} has no usable USUBJID values.")

        for domain, variables in missing_variables.items():
            blocking_issues.append(
                f"Required variables are missing from {domain}: {', '.join(variables)}."
            )

        subject_coverage = _subject_coverage(requirement.required_domains, snapshot)
        if subject_coverage.get("overlap_subject_count") == 0 and len(available_domains) > 1:
            blocking_issues.append("Required domains have no overlapping USUBJID values.")
        elif subject_coverage.get("overlap_subject_count") is not None and len(available_domains) > 1:
            min_subjects = subject_coverage.get("minimum_domain_subject_count") or 0
            overlap = subject_coverage.get("overlap_subject_count") or 0
            if min_subjects and overlap < min_subjects:
                limitations.append("Only a subset of subjects overlap across required domains.")

        date_coverage = _date_coverage(requirement, snapshot)
        if requirement.temporal_required:
            missing_temporal = [
                f"{domain}.{variable}"
                for domain, variables in date_coverage.get("variables", {}).items()
                for variable, coverage in variables.items()
                if coverage["non_missing"] == 0
            ]
            if missing_temporal:
                limitations.append(
                    "Temporal support is limited by missing date coverage: "
                    + ", ".join(missing_temporal)
                    + "."
                )

        status = _status(blocking_issues, limitations)

        return FeasibilityResult(
            objective_id=requirement.objective_id,
            objective_text=requirement.objective_text,
            status=status,
            required_domains=requirement.required_domains,
            available_domains=available_domains,
            missing_domains=missing_domains,
            required_variables=requirement.required_variables,
            missing_variables=missing_variables,
            subject_coverage=subject_coverage,
            date_coverage=date_coverage,
            blocking_issues=tuple(blocking_issues),
            limitations=tuple(limitations),
            evidence_references=evidence_references,
        )

    def _supported_objectives(self, snapshot: SDTMDataSnapshot) -> tuple[SupportedResearchObjective, ...]:
        candidates: list[SupportedResearchObjective] = []

        if _domain_supported(snapshot, "DM"):
            candidates.append(
                SupportedResearchObjective(
                    objective_text="Describe subject-level population availability using DM.",
                    supported_domains=("DM",),
                    support_reasons=("DM has usable subject identifiers.",),
                    support_score=_domain_score(snapshot, ("DM",)),
                )
            )
        if _domains_overlap(snapshot, ("DM", "AE")):
            candidates.append(
                SupportedResearchObjective(
                    objective_text="Assess adverse event data availability linked to subjects.",
                    supported_domains=("DM", "AE"),
                    support_reasons=("DM and AE have overlapping USUBJID values.",),
                    support_score=_domain_score(snapshot, ("DM", "AE")),
                )
            )
        if _domains_overlap(snapshot, ("DM", "LB")):
            candidates.append(
                SupportedResearchObjective(
                    objective_text="Assess laboratory result data availability linked to subjects.",
                    supported_domains=("DM", "LB"),
                    support_reasons=("DM and LB have overlapping USUBJID values.",),
                    support_score=_domain_score(snapshot, ("DM", "LB")),
                )
            )
        if _domains_overlap(snapshot, ("DM", "EX")):
            candidates.append(
                SupportedResearchObjective(
                    objective_text="Assess treatment exposure data availability linked to subjects.",
                    supported_domains=("DM", "EX"),
                    support_reasons=("DM and EX have overlapping USUBJID values.",),
                    support_score=_domain_score(snapshot, ("DM", "EX")),
                )
            )
        if _domains_overlap(snapshot, ("DM", "DS")):
            candidates.append(
                SupportedResearchObjective(
                    objective_text="Assess disposition data availability linked to subjects.",
                    supported_domains=("DM", "DS"),
                    support_reasons=("DM and DS have overlapping USUBJID values.",),
                    support_score=_domain_score(snapshot, ("DM", "DS")),
                )
            )
        if _domains_overlap(snapshot, ("DM", "SV")):
            candidates.append(
                SupportedResearchObjective(
                    objective_text="Assess subject visit data availability linked to subjects.",
                    supported_domains=("DM", "SV"),
                    support_reasons=("DM and SV have overlapping USUBJID values.",),
                    support_score=_domain_score(snapshot, ("DM", "SV")),
                )
            )

        ranked = sorted(candidates, key=lambda item: item.support_score, reverse=True)
        return tuple(ranked[:5])


def _subject_coverage(required_domains: tuple[str, ...], snapshot: SDTMDataSnapshot) -> dict[str, object]:
    subject_sets = {
        domain: snapshot.subject_ids(domain)
        for domain in required_domains
        if snapshot.has_domain(domain)
    }
    if not subject_sets:
        return {
            "subjects_by_domain": {},
            "overlap_subject_count": None,
            "minimum_domain_subject_count": None,
        }
    overlap = set.intersection(*subject_sets.values()) if len(subject_sets) > 1 else next(iter(subject_sets.values()))
    return {
        "subjects_by_domain": {domain: len(subjects) for domain, subjects in subject_sets.items()},
        "overlap_subject_count": len(overlap),
        "minimum_domain_subject_count": min(len(subjects) for subjects in subject_sets.values()),
    }


def _date_coverage(requirement: FeasibilityRequirement, snapshot: SDTMDataSnapshot) -> dict[str, object]:
    variables: dict[str, dict[str, object]] = {}
    for domain, required_variables in requirement.required_variables.items():
        date_variables = tuple(variable for variable in required_variables if variable.endswith("DTC"))
        if snapshot.has_domain(domain) and date_variables:
            variables[domain] = snapshot.coverage(domain, date_variables)
    return {"temporal_required": requirement.temporal_required, "variables": variables}


def _status(blocking_issues: list[str], limitations: list[str]) -> str:
    if blocking_issues:
        return "UNSUPPORTED"
    if limitations:
        return "PARTIALLY_FEASIBLE"
    return "FEASIBLE"


def _domain_supported(snapshot: SDTMDataSnapshot, domain: str) -> bool:
    return snapshot.has_domain(domain) and snapshot.record_count(domain) > 0 and bool(snapshot.subject_ids(domain))


def _domains_overlap(snapshot: SDTMDataSnapshot, domains: tuple[str, ...]) -> bool:
    if not all(_domain_supported(snapshot, domain) for domain in domains):
        return False
    subject_sets = [snapshot.subject_ids(domain) for domain in domains]
    return bool(set.intersection(*subject_sets))


def _domain_score(snapshot: SDTMDataSnapshot, domains: tuple[str, ...]) -> int:
    records = sum(snapshot.record_count(domain) for domain in domains)
    subjects = len(set.union(*(snapshot.subject_ids(domain) for domain in domains)))
    date_counts = sum(
        snapshot.non_missing_count(domain, variable)
        for domain in domains
        for variable in ("AESTDTC", "LBDTC", "DSSTDTC", "EXSTDTC", "SVSTDTC")
        if snapshot.has_variable(domain, variable)
    )
    return records + subjects + date_counts
