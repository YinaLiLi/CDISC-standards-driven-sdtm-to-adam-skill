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


MIN_ANALYZABLE_SUBJECTS = 5
MIN_ANALYZABLE_RECORDS = 5
MIN_PREDICTIVE_OUTCOME_SUBJECTS = 20


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
            if 0 < overlap < MIN_ANALYZABLE_SUBJECTS:
                blocking_issues.append(
                    "Required domains have fewer than "
                    f"{MIN_ANALYZABLE_SUBJECTS} overlapping analyzable subjects."
                )
            elif min_subjects and overlap < min_subjects:
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

        blocking_issues.extend(_data_sufficiency_blockers(requirement, snapshot))
        limitations.extend(_data_sufficiency_limitations(requirement, snapshot))

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
        if _domains_overlap(snapshot, ("DM", "AE"), min_subjects=MIN_ANALYZABLE_SUBJECTS):
            candidates.append(
                SupportedResearchObjective(
                    objective_text="Assess adverse event data availability linked to subjects.",
                    supported_domains=("DM", "AE"),
                    support_reasons=("DM and AE have overlapping USUBJID values.",),
                    support_score=_domain_score(snapshot, ("DM", "AE")),
                )
            )
        if _domains_overlap(snapshot, ("DM", "LB"), min_subjects=MIN_ANALYZABLE_SUBJECTS):
            candidates.append(
                SupportedResearchObjective(
                    objective_text="Assess laboratory result data availability linked to subjects.",
                    supported_domains=("DM", "LB"),
                    support_reasons=("DM and LB have overlapping USUBJID values.",),
                    support_score=_domain_score(snapshot, ("DM", "LB")),
                )
            )
        if _domains_overlap(snapshot, ("DM", "EX"), min_subjects=MIN_ANALYZABLE_SUBJECTS):
            candidates.append(
                SupportedResearchObjective(
                    objective_text="Assess treatment exposure data availability linked to subjects.",
                    supported_domains=("DM", "EX"),
                    support_reasons=("DM and EX have overlapping USUBJID values.",),
                    support_score=_domain_score(snapshot, ("DM", "EX")),
                )
            )
        if _domains_overlap(snapshot, ("DM", "DS"), min_subjects=MIN_ANALYZABLE_SUBJECTS):
            candidates.append(
                SupportedResearchObjective(
                    objective_text="Assess disposition data availability linked to subjects.",
                    supported_domains=("DM", "DS"),
                    support_reasons=("DM and DS have overlapping USUBJID values.",),
                    support_score=_domain_score(snapshot, ("DM", "DS")),
                )
            )
        if _domains_overlap(snapshot, ("DM", "SV"), min_subjects=MIN_ANALYZABLE_SUBJECTS):
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


def _data_sufficiency_blockers(
    requirement: FeasibilityRequirement,
    snapshot: SDTMDataSnapshot,
) -> list[str]:
    blockers: list[str] = []

    for domain in requirement.required_domains:
        if domain == "DM" or not snapshot.has_domain(domain):
            continue
        record_count = snapshot.record_count(domain)
        subject_count = len(snapshot.subject_ids(domain))
        if 0 < record_count < MIN_ANALYZABLE_RECORDS:
            blockers.append(
                f"Required SDTM domain {domain} has only {record_count} usable records; "
                f"at least {MIN_ANALYZABLE_RECORDS} are required for feasibility."
            )
        if 0 < subject_count < MIN_ANALYZABLE_SUBJECTS:
            blockers.append(
                f"Required SDTM domain {domain} has only {subject_count} subjects with usable records; "
                f"at least {MIN_ANALYZABLE_SUBJECTS} are required for feasibility."
            )

    if requirement.abnormality_required and snapshot.has_domain("LB"):
        if not _has_lab_abnormality_source(snapshot):
            blockers.append(
                "LB lacks an abnormality indicator or reference range variables needed to identify abnormal laboratory results."
            )

    if requirement.baseline_required and snapshot.has_domain("LB"):
        baseline_counts = _baseline_counts(snapshot)
        baseline_subjects = baseline_counts["baseline_subject_count"]
        post_baseline_subjects = baseline_counts["post_baseline_subject_count"]
        if baseline_counts["lbbfl_record_count"] is None:
            blockers.append("LB.LBBLFL is required to evaluate laboratory change from baseline.")
        elif baseline_subjects < MIN_ANALYZABLE_SUBJECTS:
            blockers.append(
                "LB has only "
                f"{baseline_subjects} subjects with baseline-flagged records; at least "
                f"{MIN_ANALYZABLE_SUBJECTS} are required for change-from-baseline feasibility."
            )
        elif post_baseline_subjects < MIN_ANALYZABLE_SUBJECTS:
            blockers.append(
                "LB has only "
                f"{post_baseline_subjects} baseline subjects with post-baseline records; at least "
                f"{MIN_ANALYZABLE_SUBJECTS} are required for change-from-baseline feasibility."
            )

    if requirement.predictive_model_required:
        blockers.append(
            "Predictive machine learning is outside Version 1 feasibility scope; only descriptive or rule-based summaries can be assessed."
        )
        outcome_subjects = _predictive_outcome_subject_count(requirement, snapshot)
        if outcome_subjects is not None and outcome_subjects < MIN_PREDICTIVE_OUTCOME_SUBJECTS:
            blockers.append(
                "The requested predictive endpoint has only "
                f"{outcome_subjects} outcome-positive subjects; at least "
                f"{MIN_PREDICTIVE_OUTCOME_SUBJECTS} are required before predictive feasibility can be considered."
            )

    return blockers


def _data_sufficiency_limitations(
    requirement: FeasibilityRequirement,
    snapshot: SDTMDataSnapshot,
) -> list[str]:
    limitations: list[str] = []

    if requirement.baseline_required and snapshot.has_domain("LB"):
        baseline_counts = _baseline_counts(snapshot)
        lbbfl_record_count = baseline_counts["lbbfl_record_count"]
        if lbbfl_record_count is not None:
            record_count = snapshot.record_count("LB")
            if record_count and lbbfl_record_count / record_count < 0.5:
                limitations.append(
                    "LB.LBBLFL is sparsely populated, so baseline-derived interpretations are limited."
                )

    return limitations


def _status(blocking_issues: list[str], limitations: list[str]) -> str:
    if blocking_issues:
        return "UNSUPPORTED"
    if limitations:
        return "PARTIALLY_FEASIBLE"
    return "FEASIBLE"


def _domain_supported(snapshot: SDTMDataSnapshot, domain: str) -> bool:
    return snapshot.has_domain(domain) and snapshot.record_count(domain) > 0 and bool(snapshot.subject_ids(domain))


def _domains_overlap(
    snapshot: SDTMDataSnapshot,
    domains: tuple[str, ...],
    *,
    min_subjects: int = 1,
) -> bool:
    if not all(_domain_supported(snapshot, domain) for domain in domains):
        return False
    subject_sets = [snapshot.subject_ids(domain) for domain in domains]
    return len(set.intersection(*subject_sets)) >= min_subjects


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


def _has_lab_abnormality_source(snapshot: SDTMDataSnapshot) -> bool:
    return snapshot.has_variable("LB", "LBNRIND") or (
        snapshot.has_variable("LB", "LBSTNRLO") and snapshot.has_variable("LB", "LBSTNRHI")
    )


def _baseline_counts(snapshot: SDTMDataSnapshot) -> dict[str, int | None]:
    if not snapshot.has_variable("LB", "LBBLFL"):
        return {
            "lbbfl_record_count": None,
            "baseline_subject_count": 0,
            "post_baseline_subject_count": 0,
        }

    baseline_subjects = {
        str(record.get("USUBJID")).strip()
        for record in snapshot.records("LB")
        if _is_yes(record.get("LBBLFL")) and _present(record.get("USUBJID"))
    }
    post_baseline_subjects = {
        str(record.get("USUBJID")).strip()
        for record in snapshot.records("LB")
        if str(record.get("USUBJID")).strip() in baseline_subjects
        and not _is_yes(record.get("LBBLFL"))
        and _present(record.get("USUBJID"))
    }
    return {
        "lbbfl_record_count": snapshot.non_missing_count("LB", "LBBLFL"),
        "baseline_subject_count": len(baseline_subjects),
        "post_baseline_subject_count": len(post_baseline_subjects),
    }


def _predictive_outcome_subject_count(
    requirement: FeasibilityRequirement,
    snapshot: SDTMDataSnapshot,
) -> int | None:
    objective = requirement.objective_text.lower()
    if not snapshot.has_domain("AE"):
        return None
    if ("serious" in objective or "sae" in objective) and snapshot.has_variable("AE", "AESER"):
        return len(
            {
                str(record.get("USUBJID")).strip()
                for record in snapshot.records("AE")
                if _is_yes(record.get("AESER")) and _present(record.get("USUBJID"))
            }
        )
    return len(snapshot.subject_ids("AE"))


def _present(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str) and not value.strip():
        return False
    return True


def _is_yes(value: object) -> bool:
    return str(value).strip().upper() == "Y"
