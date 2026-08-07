"""Execute approved ADaM derivation specifications."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date

from standards_driven_sdtm_adam.derivation.model import (
    AdamDerivationExecutionRecord,
    AdamDerivationExecutionResult,
    AdamDerivationSpecification,
    AdamVariableSpecification,
    StudyDecision,
)
from standards_driven_sdtm_adam.feasibility.data import SDTMDataSnapshot


SUPPORTED_EXECUTIONS = {
    "ADSL.USUBJID",
    "ADSL.TRTSDT",
    "ADSL.TRTEDT",
    "ADSL.SAFFL",
    "ADAE.ASTDT",
    "ADAE.TRTEMFL",
    "ADLB.PARAMCD",
    "ADLB.AVAL",
    "ADTTE.STARTDT",
    "ADTTE.ADT",
    "ADTTE.CNSR",
    "ADTTE.AVAL",
}

PRIMARY_SOURCE_DOMAIN = {
    "ADSL": "DM",
    "ADAE": "AE",
    "ADLB": "LB",
    "ADTTE": "DS",
}

STUDY_INPUT_DECISION_IDS = {
    "DECISION-SAFETY-POPULATION": ("DECISION-SAFETY-POPULATION",),
    "treatment_emergent_window": ("DECISION-TREATMENT-EMERGENT-WINDOW",),
    "event_definition": ("DECISION-TTE-EVENT-CENSOR",),
    "censoring_rules": ("DECISION-TTE-EVENT-CENSOR",),
    "baseline_definition": ("DECISION-BASELINE-DEFINITION",),
}


class AdamDerivationEngine:
    """Execute only approved ADaM derivation specifications."""

    def execute(
        self,
        sdtm_datasets,
        specification: AdamDerivationSpecification,
        *,
        study_decisions: Iterable[StudyDecision] = (),
    ) -> AdamDerivationExecutionResult:
        snapshot = SDTMDataSnapshot(sdtm_datasets)
        decision_map = {decision.decision_id: decision for decision in study_decisions}
        ordered_specs = _dependency_order(specification.variable_specs)
        datasets: dict[str, list[dict[str, object]]] = {}
        records: list[AdamDerivationExecutionRecord] = []
        completed: dict[str, AdamDerivationExecutionRecord] = {}
        run_warnings: list[str] = []

        for spec in ordered_specs:
            qualified = f"{spec.dataset}.{spec.variable}"
            dependency_records = tuple(
                completed[dependency].execution_id
                for dependency in spec.dependencies
                if dependency in completed and completed[dependency].status == "DERIVED"
            )
            warnings = list(
                _blocking_warnings(
                    spec,
                    snapshot,
                    completed,
                    decision_map,
                )
            )

            if qualified not in SUPPORTED_EXECUTIONS:
                warnings.append(f"No Version 1 executor is registered for {qualified}.")

            if warnings:
                record = _execution_record(
                    spec,
                    snapshot,
                    dependency_executions=dependency_records,
                    output_record_count=0,
                    derived_value_count=0,
                    status="BLOCKED",
                    validation_status="NOT_RUN",
                    warnings=tuple(warnings),
                )
                records.append(record)
                completed[qualified] = record
                continue

            dataset_records = _ensure_dataset_records(datasets, spec.dataset, snapshot)
            before_count = _derived_value_count(dataset_records, spec.variable)
            derive_warnings = _derive_variable(spec, dataset_records, snapshot, datasets, decision_map)
            after_count = _derived_value_count(dataset_records, spec.variable)
            status = "DERIVED"
            validation_status = _validation_status(spec.dataset, dataset_records, snapshot, derive_warnings)
            if after_count < len(dataset_records):
                derive_warnings = derive_warnings + (
                    f"{spec.dataset}.{spec.variable} could not be derived for every output record.",
                )
                status = "FAILED"
                validation_status = "FAILED"
            if derive_warnings:
                run_warnings.extend(derive_warnings)

            record = _execution_record(
                spec,
                snapshot,
                dependency_executions=dependency_records,
                output_record_count=len(dataset_records),
                derived_value_count=max(0, after_count - before_count),
                status=status,
                validation_status=validation_status,
                warnings=tuple(derive_warnings),
            )
            records.append(record)
            completed[qualified] = record

        frozen_datasets = {
            dataset: tuple(dict(record) for record in records_for_dataset)
            for dataset, records_for_dataset in datasets.items()
            if records_for_dataset and any(records_for_dataset)
        }
        overall_status = "COMPLETED"
        if any(record.status == "BLOCKED" for record in records):
            overall_status = "COMPLETED_WITH_BLOCKED_VARIABLES"
        if records and all(record.status == "BLOCKED" for record in records):
            overall_status = "BLOCKED"

        return AdamDerivationExecutionResult(
            datasets=frozen_datasets,
            execution_records=tuple(records),
            status=overall_status,
            warnings=tuple(dict.fromkeys(run_warnings)),
        )


def _blocking_warnings(
    spec: AdamVariableSpecification,
    snapshot: SDTMDataSnapshot,
    completed: dict[str, AdamDerivationExecutionRecord],
    decisions: dict[str, StudyDecision],
) -> tuple[str, ...]:
    warnings: list[str] = []
    if not spec.implementation_allowed:
        warnings.append("Specification is not approved for implementation.")
    for source_variable in spec.source_variables:
        domain, variable = source_variable.split(".", 1)
        if not snapshot.has_variable(domain, variable):
            warnings.append(f"Required source variable is missing: {source_variable}.")
    for dependency in spec.dependencies:
        record = completed.get(dependency)
        if record is None or record.status != "DERIVED":
            warnings.append(f"Dependency {dependency} did not complete successfully.")
    for study_input in spec.user_defined_inputs:
        if not _study_input_resolved(study_input, decisions):
            warnings.append(f"Required study decision is unresolved: {study_input}.")
    return tuple(dict.fromkeys(warnings))


def _derive_variable(
    spec: AdamVariableSpecification,
    dataset_records: list[dict[str, object]],
    snapshot: SDTMDataSnapshot,
    datasets: dict[str, list[dict[str, object]]],
    decisions: dict[str, StudyDecision],
) -> tuple[str, ...]:
    qualified = f"{spec.dataset}.{spec.variable}"
    if qualified == "ADSL.USUBJID":
        for record, dm_record in zip(dataset_records, _unique_subject_records(snapshot), strict=False):
            record["USUBJID"] = _value(dm_record, "USUBJID")
        return _adsl_grain_warnings(snapshot)
    if qualified == "ADSL.TRTSDT":
        first_exposure = _subject_extreme(snapshot.records("EX"), "EXSTDTC", min)
        for record, subject in zip(dataset_records, _adsl_subjects(snapshot), strict=False):
            record["TRTSDT"] = first_exposure.get(subject)
        return ()
    if qualified == "ADSL.TRTEDT":
        last_exposure = _subject_extreme(snapshot.records("EX"), "EXENDTC", max)
        for record, subject in zip(dataset_records, _adsl_subjects(snapshot), strict=False):
            record["TRTEDT"] = last_exposure.get(subject)
        return ()
    if qualified == "ADSL.SAFFL":
        exposed_subjects = {str(record.get("USUBJID")).strip() for record in snapshot.records("EX")}
        for record, subject in zip(dataset_records, _adsl_subjects(snapshot), strict=False):
            record["SAFFL"] = "Y" if subject in exposed_subjects else "N"
        return ()
    if qualified == "ADAE.ASTDT":
        for record, ae_record in zip(dataset_records, snapshot.records("AE"), strict=False):
            record["ASTDT"] = _value(ae_record, "AESTDTC")
        return ()
    if qualified == "ADAE.TRTEMFL":
        adsl_by_subject = _adsl_records_by_subject(datasets.get("ADSL", []), snapshot)
        ae_records = snapshot.records("AE")
        window_days = _treatment_window_days(decisions)
        for record, ae_record in zip(dataset_records, ae_records, strict=False):
            subject = _value(ae_record, "USUBJID")
            adsl = adsl_by_subject.get(subject, {})
            record["TRTEMFL"] = _treatment_emergent_flag(
                record.get("ASTDT"),
                adsl.get("TRTSDT"),
                adsl.get("TRTEDT"),
                window_days,
            )
        return ()
    if qualified == "ADLB.PARAMCD":
        for record, lb_record in zip(dataset_records, snapshot.records("LB"), strict=False):
            record["PARAMCD"] = _value(lb_record, "LBTESTCD")
        return ()
    if qualified == "ADLB.AVAL":
        for record, lb_record in zip(dataset_records, snapshot.records("LB"), strict=False):
            record["AVAL"] = _numeric_value(lb_record.get("LBSTRESN"))
        return ()
    if qualified == "ADTTE.STARTDT":
        first_exposure = _subject_extreme(snapshot.records("EX"), "EXSTDTC", min)
        for record, ds_record in zip(dataset_records, snapshot.records("DS"), strict=False):
            record["STARTDT"] = first_exposure.get(_value(ds_record, "USUBJID"))
        return ()
    if qualified == "ADTTE.ADT":
        for record, ds_record in zip(dataset_records, snapshot.records("DS"), strict=False):
            record["ADT"] = _value(ds_record, "DSSTDTC")
        return ()
    if qualified == "ADTTE.CNSR":
        event_terms = _event_terms(decisions)
        for record, ds_record in zip(dataset_records, snapshot.records("DS"), strict=False):
            record["CNSR"] = 0 if _value(ds_record, "DSDECOD").upper() in event_terms else 1
        return ()
    if qualified == "ADTTE.AVAL":
        for record in dataset_records:
            record["AVAL"] = _days_between(record.get("STARTDT"), record.get("ADT"))
        return ()
    return (f"No Version 1 derivation logic is implemented for {qualified}.",)


def _ensure_dataset_records(
    datasets: dict[str, list[dict[str, object]]],
    dataset: str,
    snapshot: SDTMDataSnapshot,
) -> list[dict[str, object]]:
    if dataset in datasets:
        return datasets[dataset]
    if dataset == "ADSL":
        datasets[dataset] = [{} for _ in _unique_subject_records(snapshot)]
    else:
        domain = PRIMARY_SOURCE_DOMAIN[dataset]
        datasets[dataset] = [{} for _ in snapshot.records(domain)]
    return datasets[dataset]


def _execution_record(
    spec: AdamVariableSpecification,
    snapshot: SDTMDataSnapshot,
    *,
    dependency_executions: tuple[str, ...],
    output_record_count: int,
    derived_value_count: int,
    status: str,
    validation_status: str,
    warnings: tuple[str, ...],
) -> AdamDerivationExecutionRecord:
    return AdamDerivationExecutionRecord(
        execution_id=f"EXEC-{spec.specification_id}",
        specification_id=spec.specification_id,
        dataset=spec.dataset,
        variable=spec.variable,
        classification=spec.classification,
        source_domains=spec.source_domains,
        source_variables=spec.source_variables,
        dependency_executions=dependency_executions,
        input_record_count=_input_record_count(spec, snapshot),
        output_record_count=output_record_count,
        derived_value_count=derived_value_count,
        status=status,
        validation_status=validation_status,
        warnings=warnings,
        evidence_references=spec.evidence_references,
        study_decision_references=spec.user_defined_inputs,
    )


def _dependency_order(
    specs: Iterable[AdamVariableSpecification],
) -> tuple[AdamVariableSpecification, ...]:
    remaining = list(specs)
    ordered: list[AdamVariableSpecification] = []
    completed: set[str] = set()
    while remaining:
        progressed = False
        for spec in tuple(remaining):
            if all(dependency in completed or dependency not in _qualified_names(remaining) for dependency in spec.dependencies):
                ordered.append(spec)
                completed.add(f"{spec.dataset}.{spec.variable}")
                remaining.remove(spec)
                progressed = True
        if not progressed:
            ordered.extend(remaining)
            break
    return tuple(ordered)


def _qualified_names(specs: Iterable[AdamVariableSpecification]) -> set[str]:
    return {f"{spec.dataset}.{spec.variable}" for spec in specs}


def _study_input_resolved(study_input: str, decisions: dict[str, StudyDecision]) -> bool:
    decision_ids = STUDY_INPUT_DECISION_IDS.get(study_input, (study_input,))
    return any(
        decision_id in decisions
        and decisions[decision_id].status == "PROVIDED"
        and bool(decisions[decision_id].value)
        for decision_id in decision_ids
    )


def _input_record_count(spec: AdamVariableSpecification, snapshot: SDTMDataSnapshot) -> int:
    if spec.dataset == "ADSL":
        return snapshot.record_count("DM")
    if spec.source_domains:
        return max(snapshot.record_count(domain) for domain in spec.source_domains)
    return 0


def _validation_status(
    dataset: str,
    dataset_records: list[dict[str, object]],
    snapshot: SDTMDataSnapshot,
    warnings: tuple[str, ...],
) -> str:
    if dataset == "ADSL" and _adsl_grain_warnings(snapshot):
        return "PASSED_WITH_WARNINGS"
    if not dataset_records:
        return "FAILED"
    if warnings:
        return "PASSED_WITH_WARNINGS"
    return "PASSED"


def _adsl_grain_warnings(snapshot: SDTMDataSnapshot) -> tuple[str, ...]:
    dm_subjects = [_value(record, "USUBJID") for record in snapshot.records("DM")]
    if len(dm_subjects) != len(set(dm_subjects)):
        return ("ADSL input DM contained duplicate USUBJID values; output was de-duplicated.",)
    return ()


def _unique_subject_records(snapshot: SDTMDataSnapshot) -> tuple[dict[str, object], ...]:
    records: list[dict[str, object]] = []
    seen: set[str] = set()
    for record in snapshot.records("DM"):
        subject = _value(record, "USUBJID")
        if subject in seen:
            continue
        seen.add(subject)
        records.append(dict(record))
    return tuple(records)


def _adsl_subjects(snapshot: SDTMDataSnapshot) -> tuple[str, ...]:
    return tuple(_value(record, "USUBJID") for record in _unique_subject_records(snapshot))


def _subject_extreme(records: Iterable[dict[str, object]], variable: str, chooser) -> dict[str, object]:
    values: dict[str, list[object]] = {}
    for record in records:
        subject = _value(record, "USUBJID")
        value = record.get(variable)
        if value is None or value == "":
            continue
        values.setdefault(subject, []).append(value)
    return {subject: chooser(subject_values) for subject, subject_values in values.items()}


def _records_by_subject(records: Iterable[dict[str, object]]) -> dict[str, dict[str, object]]:
    return {_value(record, "USUBJID"): record for record in records if record.get("USUBJID") is not None}


def _adsl_records_by_subject(
    records: Iterable[dict[str, object]],
    snapshot: SDTMDataSnapshot,
) -> dict[str, dict[str, object]]:
    by_subject = _records_by_subject(records)
    if by_subject:
        return by_subject
    return {
        subject: record
        for subject, record in zip(_adsl_subjects(snapshot), records, strict=False)
    }


def _treatment_emergent_flag(
    ae_start,
    treatment_start,
    treatment_end,
    window_days: int,
) -> str | None:
    if ae_start is None or treatment_start is None or treatment_end is None:
        return None
    ae_date = _parse_date(str(ae_start))
    start_date = _parse_date(str(treatment_start))
    end_date = _parse_date(str(treatment_end))
    if ae_date is None or start_date is None or end_date is None:
        return None
    return "Y" if start_date <= ae_date and (ae_date - end_date).days <= window_days else "N"


def _treatment_window_days(decisions: dict[str, StudyDecision]) -> int:
    decision = decisions.get("DECISION-TREATMENT-EMERGENT-WINDOW")
    if decision is None or decision.value is None:
        return 0
    if "30" in decision.value:
        return 30
    return 0


def _event_terms(decisions: dict[str, StudyDecision]) -> set[str]:
    decision = decisions.get("DECISION-TTE-EVENT-CENSOR")
    if decision is None or decision.value is None:
        return set()
    terms: set[str] = set()
    for part in decision.value.split(";"):
        key, _, value = part.partition("=")
        if key.strip().lower() == "event_terms":
            terms.update(term.strip().upper() for term in value.split(",") if term.strip())
    return terms


def _days_between(start, end) -> int | None:
    start_date = _parse_date(str(start)) if start is not None else None
    end_date = _parse_date(str(end)) if end is not None else None
    if start_date is None or end_date is None:
        return None
    return (end_date - start_date).days


def _parse_date(value: str) -> date | None:
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _numeric_value(value: object) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _derived_value_count(records: Iterable[dict[str, object]], variable: str) -> int:
    return sum(1 for record in records if record.get(variable) is not None)


def _value(record: dict[str, object], variable: str) -> str:
    value = record.get(variable)
    if value is None:
        return ""
    return str(value).strip()
