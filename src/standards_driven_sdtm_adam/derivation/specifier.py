"""Generate ADaM derivation specifications without executing derivations."""

from __future__ import annotations

from collections.abc import Iterable
import re

from standards_driven_sdtm_adam.derivation.model import (
    AdamDatasetSpecification,
    AdamDerivationSpecification,
    AdamVariableSpecification,
    StudyDecision,
)
from standards_driven_sdtm_adam.extraction.model import EvidenceRecord
from standards_driven_sdtm_adam.feasibility.data import SDTMDataSnapshot
from standards_driven_sdtm_adam.feasibility.model import FeasibilityAssessment, FeasibilityResult


DATASET_PURPOSES = {
    "ADSL": "Subject-level analysis dataset for core subject, population, and treatment context.",
    "ADAE": "Adverse event analysis dataset for occurrence analysis and supported treatment-emergent concepts.",
    "ADLB": "Laboratory analysis dataset for source laboratory measurements and analysis variables.",
    "ADTTE": "Time-to-event analysis dataset for supported objectives with explicit event and censoring definitions.",
}

DATASET_STRUCTURES = {
    "ADSL": "One record per subject.",
    "ADAE": "One record per adverse event occurrence or analysis occurrence.",
    "ADLB": "One record per subject per laboratory parameter per analysis timepoint.",
    "ADTTE": "One record per subject per time-to-event parameter.",
}

REQUIRED_DECISIONS = {
    "DECISION-SAFETY-POPULATION": StudyDecision(
        decision_id="DECISION-SAFETY-POPULATION",
        question="What is the study-defined Safety Population?",
        affected_datasets=("ADSL",),
        affected_variables=("ADSL.SAFFL",),
        required_before_implementation=True,
        status="MISSING",
    ),
    "DECISION-TREATMENT-EMERGENT-WINDOW": StudyDecision(
        decision_id="DECISION-TREATMENT-EMERGENT-WINDOW",
        question="What is the study-defined treatment-emergent analysis window?",
        affected_datasets=("ADAE",),
        affected_variables=("ADAE.TRTEMFL",),
        required_before_implementation=True,
        status="MISSING",
    ),
    "DECISION-TTE-EVENT-CENSOR": StudyDecision(
        decision_id="DECISION-TTE-EVENT-CENSOR",
        question="What are the study-defined event and censoring rules for ADTTE?",
        affected_datasets=("ADTTE",),
        affected_variables=("ADTTE.ADT", "ADTTE.CNSR", "ADTTE.AVAL"),
        required_before_implementation=True,
        status="MISSING",
    ),
}


class AdamDerivationSpecifier:
    """Create ADaM derivation specifications from source data, evidence, and decisions."""

    def specify(
        self,
        sdtm_datasets,
        feasibility: FeasibilityAssessment | Iterable[FeasibilityResult],
        discovery_results=None,
        evidence: Iterable[EvidenceRecord] = (),
        *,
        study_decisions: Iterable[StudyDecision] = (),
        requested_variables: Iterable[str] = (),
    ) -> AdamDerivationSpecification:
        snapshot = SDTMDataSnapshot(sdtm_datasets)
        _coerce_results(feasibility)
        evidence_index = _EvidenceIndex(evidence)
        decisions = _decision_map(study_decisions)

        variable_specs = [
            self._adsl_usubjid(snapshot, evidence_index),
            self._adsl_saffl(snapshot, decisions),
            self._adsl_trtsdt(snapshot),
            self._adsl_trtedt(snapshot),
            self._adae_astdt(snapshot),
            self._adae_trtemfl(snapshot, evidence_index, decisions),
            self._adlb_paramcd(snapshot),
            self._adlb_aval(snapshot, evidence_index),
            self._adlb_avisit(snapshot, evidence_index),
            self._adtte_startdt(snapshot),
            self._adtte_adt(snapshot, evidence_index, decisions),
            self._adtte_cnsr(snapshot, evidence_index, decisions),
            self._adtte_aval(snapshot, decisions),
        ]

        variable_specs.extend(
            self._requested_unsupported_specs(requested_variables, variable_specs, evidence_index)
        )

        unresolved_decisions = _unresolved_decisions(variable_specs, decisions)
        dataset_specs = _dataset_specs(variable_specs, evidence_index, unresolved_decisions)
        traceability = _traceability(variable_specs)

        return AdamDerivationSpecification(
            dataset_specs=dataset_specs,
            variable_specs=tuple(variable_specs),
            unresolved_decisions=unresolved_decisions,
            traceability=traceability,
        )

    def _adsl_usubjid(
        self,
        snapshot: SDTMDataSnapshot,
        evidence_index: "_EvidenceIndex",
    ) -> AdamVariableSpecification:
        return _variable_spec(
            dataset="ADSL",
            variable="USUBJID",
            label="Unique Subject Identifier",
            purpose="Identify each analysis subject.",
            source_domains=("DM",),
            source_variables=("DM.USUBJID",),
            derivation_logic="Carry DM.USUBJID into ADSL as the subject identifier.",
            classification="STANDARD_REQUIRED" if evidence_index.adsl else "STANDARD_GUIDED",
            evidence_references=evidence_index.adsl,
            validation_plan=("Confirm one ADSL record per subject.", "Confirm ADSL.USUBJID matches DM.USUBJID."),
            implementation_allowed=snapshot.has_variable("DM", "USUBJID"),
            unresolved_issues=_missing_sources(snapshot, ("DM.USUBJID",)),
        )

    def _adsl_saffl(
        self,
        snapshot: SDTMDataSnapshot,
        decisions: dict[str, StudyDecision],
    ) -> AdamVariableSpecification:
        decision_id = "DECISION-SAFETY-POPULATION"
        decision = decisions.get(decision_id)
        has_decision = decision is not None and decision.status == "PROVIDED"
        return _variable_spec(
            dataset="ADSL",
            variable="SAFFL",
            label="Safety Population Flag",
            purpose="Flag subjects included in the study-defined safety population.",
            source_domains=("DM", "EX"),
            source_variables=("DM.USUBJID", "EX.USUBJID"),
            derivation_logic=_decision_logic(decision, "Apply the study-defined Safety Population definition."),
            classification="USER_DEFINED",
            user_defined_inputs=(decision_id,),
            assumptions=() if has_decision else ("Safety Population is study-defined and is not invented from CDISC guidance.",),
            validation_plan=("Verify values are Y or N.", "Verify traceability to the documented Safety Population decision."),
            implementation_allowed=has_decision and snapshot.has_variable("DM", "USUBJID"),
            unresolved_issues=() if has_decision else ("Safety Population definition has not been provided.",),
        )

    def _adsl_trtsdt(self, snapshot: SDTMDataSnapshot) -> AdamVariableSpecification:
        missing = _missing_sources(snapshot, ("EX.EXSTDTC",))
        return _variable_spec(
            dataset="ADSL",
            variable="TRTSDT",
            label="Date of First Exposure to Treatment",
            purpose="Provide treatment start date context for downstream analysis flags.",
            source_domains=("EX",),
            source_variables=("EX.EXSTDTC",),
            derivation_logic="Specify first treatment exposure date from EX.EXSTDTC; do not execute derivation here.",
            classification="STANDARD_GUIDED",
            validation_plan=("Confirm treatment start date is traceable to EX.EXSTDTC.",),
            implementation_allowed=not missing,
            unresolved_issues=missing,
        )

    def _adsl_trtedt(self, snapshot: SDTMDataSnapshot) -> AdamVariableSpecification:
        missing = _missing_sources(snapshot, ("EX.EXENDTC",))
        return _variable_spec(
            dataset="ADSL",
            variable="TRTEDT",
            label="Date of Last Exposure to Treatment",
            purpose="Provide treatment end date context for downstream analysis flags.",
            source_domains=("EX",),
            source_variables=("EX.EXENDTC",),
            derivation_logic="Specify last treatment exposure date from EX.EXENDTC; do not execute derivation here.",
            classification="STANDARD_GUIDED",
            validation_plan=("Confirm treatment end date is traceable to EX.EXENDTC.",),
            implementation_allowed=not missing,
            unresolved_issues=missing,
        )

    def _adae_astdt(self, snapshot: SDTMDataSnapshot) -> AdamVariableSpecification:
        missing = _missing_sources(snapshot, ("AE.AESTDTC",))
        return _variable_spec(
            dataset="ADAE",
            variable="ASTDT",
            label="Analysis Start Date",
            purpose="Represent adverse event start date for analysis timing.",
            source_domains=("AE",),
            source_variables=("AE.AESTDTC",),
            derivation_logic="Specify deterministic date parsing from AE.AESTDTC; do not impute partial or missing dates.",
            classification="DATA_ENGINEERING",
            validation_plan=("Confirm ASTDT is reproducible from AE.AESTDTC.", "Confirm missing or partial source dates are not imputed."),
            implementation_allowed=not missing,
            unresolved_issues=missing,
        )

    def _adae_trtemfl(
        self,
        snapshot: SDTMDataSnapshot,
        evidence_index: "_EvidenceIndex",
        decisions: dict[str, StudyDecision],
    ) -> AdamVariableSpecification:
        decision_id = "DECISION-TREATMENT-EMERGENT-WINDOW"
        decision = decisions.get(decision_id)
        has_decision = decision is not None and decision.status == "PROVIDED"
        missing = _missing_sources(snapshot, ("AE.AESTDTC", "EX.EXSTDTC", "EX.EXENDTC"))
        unresolved = missing
        if not has_decision:
            unresolved = unresolved + ("Treatment-emergent window has not been provided.",)
        return _variable_spec(
            dataset="ADAE",
            variable="TRTEMFL",
            label="Treatment Emergent Analysis Flag",
            purpose="Identify adverse events meeting the study-defined treatment-emergent concept.",
            source_domains=("AE", "EX"),
            source_variables=("AE.AESTDTC", "EX.EXSTDTC", "EX.EXENDTC"),
            derivation_logic=_decision_logic(decision, "Compare ADAE.ASTDT with treatment dates using the study-defined treatment-emergent window."),
            dependencies=("ADSL.TRTSDT", "ADSL.TRTEDT", "ADAE.ASTDT"),
            classification="STUDY_SPECIFIC",
            evidence_references=evidence_index.trtemfl,
            user_defined_inputs=("treatment_emergent_window",),
            assumptions=("CDISC guidance supports treatment-emergent concepts but does not define this study's window.",),
            validation_plan=("Verify the treatment-emergent window is documented.", "Verify TRTEMFL is traceable to AE dates, ADSL treatment dates, and the study decision."),
            implementation_allowed=has_decision and not missing,
            unresolved_issues=unresolved,
        )

    def _adlb_paramcd(self, snapshot: SDTMDataSnapshot) -> AdamVariableSpecification:
        missing = _missing_sources(snapshot, ("LB.LBTESTCD",))
        return _variable_spec(
            dataset="ADLB",
            variable="PARAMCD",
            label="Parameter Code",
            purpose="Identify the laboratory analysis parameter.",
            source_domains=("LB",),
            source_variables=("LB.LBTESTCD",),
            derivation_logic="Specify parameter code from LB.LBTESTCD where supported by the source laboratory record.",
            classification="STANDARD_GUIDED",
            validation_plan=("Confirm PARAMCD remains traceable to LB.LBTESTCD.",),
            implementation_allowed=not missing,
            unresolved_issues=missing,
        )

    def _adlb_aval(
        self,
        snapshot: SDTMDataSnapshot,
        evidence_index: "_EvidenceIndex",
    ) -> AdamVariableSpecification:
        missing = _missing_sources(snapshot, ("LB.LBSTRESN", "LB.LBORRES"))
        return _variable_spec(
            dataset="ADLB",
            variable="AVAL",
            label="Analysis Value",
            purpose="Represent laboratory result value for analysis.",
            source_domains=("LB",),
            source_variables=("LB.LBSTRESN", "LB.LBORRES"),
            derivation_logic="Use LB.LBSTRESN when available, with LB.LBORRES retained as source traceability.",
            classification="STANDARD_GUIDED",
            evidence_references=evidence_index.aval,
            validation_plan=("Confirm AVAL is traceable to LB.LBSTRESN or LB.LBORRES.",),
            implementation_allowed=not missing,
            unresolved_issues=missing,
        )

    def _adlb_avisit(
        self,
        snapshot: SDTMDataSnapshot,
        evidence_index: "_EvidenceIndex",
    ) -> AdamVariableSpecification:
        evidence = evidence_index.example_avisit
        missing = _missing_sources(snapshot, ("LB.LBDTC",))
        return _variable_spec(
            dataset="ADLB",
            variable="AVISIT",
            label="Analysis Visit",
            purpose="Represent analysis visit timing when explicitly supported by study decisions or adapted examples.",
            source_domains=("LB",),
            source_variables=("LB.LBDTC",),
            derivation_logic="Adapt example visit timing logic only as a documented specification; do not treat example text as a CDISC requirement.",
            classification="EXAMPLE_ADAPTED" if evidence else "STUDY_SPECIFIC",
            evidence_references=evidence,
            assumptions=("CDISC examples are illustrative and are not mandatory rules.",),
            validation_plan=("Verify AVISIT logic is documented before implementation.",),
            implementation_allowed=bool(evidence) and not missing,
            unresolved_issues=missing if evidence else missing + ("No study visit-window decision or example evidence supports AVISIT implementation.",),
        )

    def _adtte_startdt(self, snapshot: SDTMDataSnapshot) -> AdamVariableSpecification:
        missing = _missing_sources(snapshot, ("EX.EXSTDTC",))
        return _variable_spec(
            dataset="ADTTE",
            variable="STARTDT",
            label="Time-to-Event Origin Date",
            purpose="Identify the origin date for time-to-event calculations.",
            source_domains=("EX",),
            source_variables=("EX.EXSTDTC",),
            derivation_logic="Specify time-to-event origin from treatment start date or another explicitly documented study origin.",
            classification="STUDY_SPECIFIC",
            validation_plan=("Verify the origin date rule is documented.",),
            implementation_allowed=False,
            unresolved_issues=missing + ("Time-to-event origin rule has not been provided.",),
        )

    def _adtte_adt(
        self,
        snapshot: SDTMDataSnapshot,
        evidence_index: "_EvidenceIndex",
        decisions: dict[str, StudyDecision],
    ) -> AdamVariableSpecification:
        missing = _missing_sources(snapshot, ("DS.DSSTDTC",))
        has_decision = _has_decision(decisions, "DECISION-TTE-EVENT-CENSOR")
        unresolved = missing
        if not has_decision and not missing:
            unresolved = unresolved + ("Event date rule has not been provided.",)
        return _variable_spec(
            dataset="ADTTE",
            variable="ADT",
            label="Analysis Date",
            purpose="Represent the event or censoring date for time-to-event analysis.",
            source_domains=("DS",),
            source_variables=("DS.DSSTDTC",),
            derivation_logic="Specify event or censoring date from source events according to documented study rules.",
            classification="STUDY_SPECIFIC" if not missing else "UNSUPPORTED",
            evidence_references=evidence_index.adtte,
            user_defined_inputs=("event_definition", "censoring_rules"),
            validation_plan=("Verify ADT follows the documented event or censoring date rule.",),
            implementation_allowed=has_decision and not missing,
            unresolved_issues=unresolved,
        )

    def _adtte_cnsr(
        self,
        snapshot: SDTMDataSnapshot,
        evidence_index: "_EvidenceIndex",
        decisions: dict[str, StudyDecision],
    ) -> AdamVariableSpecification:
        missing = _missing_sources(snapshot, ("DS.DSDECOD", "DS.DSSTDTC"))
        has_decision = _has_decision(decisions, "DECISION-TTE-EVENT-CENSOR")
        unresolved = missing
        if not has_decision:
            unresolved = unresolved + ("Event and censoring rules have not been provided.",)
        return _variable_spec(
            dataset="ADTTE",
            variable="CNSR",
            label="Censor",
            purpose="Identify whether the time-to-event record is censored according to study rules.",
            source_domains=("DS",),
            source_variables=("DS.DSDECOD", "DS.DSSTDTC"),
            derivation_logic="Classify event versus censoring using the documented study-specific event and censoring rules.",
            classification="STUDY_SPECIFIC" if not missing else "UNSUPPORTED",
            evidence_references=evidence_index.adtte,
            user_defined_inputs=("event_definition", "censoring_rules"),
            validation_plan=("Verify CNSR follows documented event and censoring rules.",),
            implementation_allowed=has_decision and not missing,
            unresolved_issues=unresolved,
        )

    def _adtte_aval(
        self,
        snapshot: SDTMDataSnapshot,
        decisions: dict[str, StudyDecision],
    ) -> AdamVariableSpecification:
        missing = _missing_sources(snapshot, ("DS.DSSTDTC", "EX.EXSTDTC"))
        has_decision = _has_decision(decisions, "DECISION-TTE-EVENT-CENSOR")
        unresolved = missing
        if not has_decision:
            unresolved = unresolved + ("Event, censoring, and time scale rules have not been provided.",)
        return _variable_spec(
            dataset="ADTTE",
            variable="AVAL",
            label="Analysis Value",
            purpose="Represent time-to-event duration.",
            source_domains=("DS", "EX"),
            source_variables=("DS.DSSTDTC", "EX.EXSTDTC"),
            derivation_logic="Calculate duration only after STARTDT, ADT, event rules, censoring rules, and time scale are specified.",
            dependencies=("ADTTE.STARTDT", "ADTTE.ADT"),
            classification="STUDY_SPECIFIC" if not missing else "UNSUPPORTED",
            user_defined_inputs=("event_definition", "censoring_rules"),
            validation_plan=("Verify duration uses the documented time scale and date rules.",),
            implementation_allowed=has_decision and not missing,
            unresolved_issues=unresolved,
        )

    def _requested_unsupported_specs(
        self,
        requested_variables: Iterable[str],
        existing_specs: list[AdamVariableSpecification],
        evidence_index: "_EvidenceIndex",
    ) -> list[AdamVariableSpecification]:
        existing = {f"{spec.dataset}.{spec.variable}" for spec in existing_specs}
        specs: list[AdamVariableSpecification] = []
        for name in requested_variables:
            dataset, variable = _split_variable_name(name)
            qualified = f"{dataset}.{variable}"
            if qualified in existing:
                continue
            evidence = evidence_index.for_text(qualified)
            specs.append(
                _variable_spec(
                    dataset=dataset,
                    variable=variable,
                    label=variable,
                    purpose=f"Requested derivation specification for {qualified}.",
                    source_domains=(),
                    source_variables=(),
                    derivation_logic="No derivation logic is specified because supporting evidence or study decision is missing.",
                    classification="UNSUPPORTED",
                    evidence_references=evidence,
                    validation_plan=("Do not implement until supporting evidence or explicit study decision is documented.",),
                    implementation_allowed=False,
                    unresolved_issues=(
                        f"No extracted CDISC evidence or explicit study decision supports {qualified}.",
                    ),
                )
            )
        return specs


class _EvidenceIndex:
    def __init__(self, evidence: Iterable[EvidenceRecord]) -> None:
        self._records = tuple(record for record in evidence if record.extraction_status == "EXTRACTED")

    @property
    def adsl(self) -> tuple[str, ...]:
        return self._matching_ids(("adsl", "subject-level", "one record per subject"))

    @property
    def trtemfl(self) -> tuple[str, ...]:
        return self._matching_ids(("trtemfl", "treatment-emergent", "treatment emergent"))

    @property
    def aval(self) -> tuple[str, ...]:
        return self._matching_ids(("aval", "analysis value"))

    @property
    def adtte(self) -> tuple[str, ...]:
        return self._matching_ids(("adtte", "time-to-event", "time to event", "censoring"))

    @property
    def example_avisit(self) -> tuple[str, ...]:
        return tuple(
            record.evidence_id
            for record in self._records
            if record.evidence_type == "EXAMPLE" and "avisit" in _record_text(record)
        )

    def for_text(self, text: str) -> tuple[str, ...]:
        requested_terms = set(_terms(text))
        matches: list[str] = []
        for record in self._records:
            record_terms = set(_terms(_record_text(record)))
            if requested_terms & record_terms:
                matches.append(record.evidence_id)
        return tuple(matches)

    def _matching_ids(self, phrases: tuple[str, ...]) -> tuple[str, ...]:
        normalized_phrases = tuple(_normalize(phrase) for phrase in phrases)
        return tuple(
            record.evidence_id
            for record in self._records
            if any(phrase in _record_text(record) for phrase in normalized_phrases)
        )


def _variable_spec(
    *,
    dataset: str,
    variable: str,
    label: str,
    purpose: str,
    source_domains: tuple[str, ...],
    source_variables: tuple[str, ...],
    derivation_logic: str,
    classification: str,
    dependencies: tuple[str, ...] = (),
    evidence_references: tuple[str, ...] = (),
    user_defined_inputs: tuple[str, ...] = (),
    assumptions: tuple[str, ...] = (),
    validation_plan: tuple[str, ...],
    implementation_allowed: bool,
    unresolved_issues: tuple[str, ...] = (),
) -> AdamVariableSpecification:
    return AdamVariableSpecification(
        specification_id=f"ADAM-SPEC-{dataset}-{variable}",
        dataset=dataset,
        variable=variable,
        label=label,
        purpose=purpose,
        source_domains=source_domains,
        source_variables=source_variables,
        derivation_logic=derivation_logic,
        dependencies=dependencies,
        classification=classification,
        evidence_references=evidence_references,
        user_defined_inputs=user_defined_inputs,
        assumptions=assumptions,
        validation_plan=validation_plan,
        implementation_allowed=implementation_allowed,
        unresolved_issues=unresolved_issues,
    )


def _dataset_specs(
    variable_specs: list[AdamVariableSpecification],
    evidence_index: _EvidenceIndex,
    unresolved_decisions: tuple[StudyDecision, ...],
) -> tuple[AdamDatasetSpecification, ...]:
    specs: list[AdamDatasetSpecification] = []
    for dataset in ("ADSL", "ADAE", "ADLB", "ADTTE"):
        variables = tuple(spec.variable for spec in variable_specs if spec.dataset == dataset)
        source_domains = tuple(
            sorted({domain for spec in variable_specs if spec.dataset == dataset for domain in spec.source_domains})
        )
        unresolved = tuple(
            decision.decision_id
            for decision in unresolved_decisions
            if dataset in decision.affected_datasets
        )
        evidence = evidence_index.for_text(dataset)
        dataset_variables = [spec for spec in variable_specs if spec.dataset == dataset]
        specs.append(
            AdamDatasetSpecification(
                dataset=dataset,
                purpose=DATASET_PURPOSES[dataset],
                structure=DATASET_STRUCTURES[dataset],
                source_domains=source_domains,
                supported_variables=variables,
                evidence_references=evidence,
                unresolved_decisions=unresolved,
                implementation_allowed=all(spec.implementation_allowed for spec in dataset_variables),
            )
        )
    return tuple(specs)


def _traceability(
    variable_specs: Iterable[AdamVariableSpecification],
) -> dict[str, dict[str, object]]:
    return {
        f"{spec.dataset}.{spec.variable}": {
            "adam_variable": f"{spec.dataset}.{spec.variable}",
            "derivation_specification_id": spec.specification_id,
            "source_sdtm_variables": spec.source_variables,
            "decision_classification": spec.classification,
            "evidence_references": spec.evidence_references,
            "study_decisions": spec.user_defined_inputs,
        }
        for spec in variable_specs
    }


def _unresolved_decisions(
    variable_specs: Iterable[AdamVariableSpecification],
    provided_decisions: dict[str, StudyDecision],
) -> tuple[StudyDecision, ...]:
    unresolved: list[StudyDecision] = []
    required_ids = set()
    for spec in variable_specs:
        for decision_id in spec.user_defined_inputs:
            if decision_id.startswith("DECISION-"):
                required_ids.add(decision_id)
        if spec.variable == "TRTEMFL" and spec.unresolved_issues:
            required_ids.add("DECISION-TREATMENT-EMERGENT-WINDOW")
        if spec.dataset == "ADTTE" and spec.unresolved_issues:
            required_ids.add("DECISION-TTE-EVENT-CENSOR")

    required_ids.add("DECISION-SAFETY-POPULATION")

    decision_order = (
        "DECISION-TREATMENT-EMERGENT-WINDOW",
        "DECISION-SAFETY-POPULATION",
        "DECISION-TTE-EVENT-CENSOR",
    )
    for decision_id in decision_order:
        if decision_id not in required_ids:
            continue
        decision = provided_decisions.get(decision_id)
        if decision is not None and decision.status == "PROVIDED":
            continue
        unresolved.append(REQUIRED_DECISIONS[decision_id])
    return tuple(unresolved)


def _decision_map(study_decisions: Iterable[StudyDecision]) -> dict[str, StudyDecision]:
    return {decision.decision_id: decision for decision in study_decisions}


def _has_decision(decisions: dict[str, StudyDecision], decision_id: str) -> bool:
    decision = decisions.get(decision_id)
    return decision is not None and decision.status == "PROVIDED"


def _decision_logic(decision: StudyDecision | None, fallback: str) -> str:
    if decision is not None and decision.status == "PROVIDED" and decision.value:
        return decision.value
    return fallback


def _missing_sources(snapshot: SDTMDataSnapshot, source_variables: tuple[str, ...]) -> tuple[str, ...]:
    missing = tuple(
        source_variable
        for source_variable in source_variables
        if not _has_source_variable(snapshot, source_variable)
    )
    if not missing:
        return ()
    return (f"Required source variables are missing: {', '.join(missing)}.",)


def _has_source_variable(snapshot: SDTMDataSnapshot, source_variable: str) -> bool:
    domain, variable = source_variable.split(".", 1)
    return snapshot.has_variable(domain, variable)


def _coerce_results(
    feasibility: FeasibilityAssessment | Iterable[FeasibilityResult],
) -> tuple[FeasibilityResult, ...]:
    if isinstance(feasibility, FeasibilityAssessment):
        return feasibility.results
    return tuple(feasibility)


def _split_variable_name(name: str) -> tuple[str, str]:
    if "." not in name:
        return "UNKNOWN", name.upper()
    dataset, variable = name.split(".", 1)
    return dataset.upper(), variable.upper()


def _record_text(record: EvidenceRecord) -> str:
    return _normalize(
        " ".join(
            (
                record.evidence_id,
                record.standard_id,
                record.standard_title,
                record.evidence_type,
                record.section or "",
                record.short_quote or "",
                record.search_context,
            )
        )
    )


def _terms(value: str) -> tuple[str, ...]:
    return tuple(term for term in re.split(r"[^a-z0-9]+", _normalize(value)) if len(term) > 2)


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.lower()).strip()
