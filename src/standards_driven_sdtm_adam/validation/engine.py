"""Independent validation for generated preprocessing and ADaM outputs."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import date

from standards_driven_sdtm_adam.derivation.model import (
    AdamDerivationExecutionRecord,
    AdamDerivationSpecification,
    AdamVariableSpecification,
    StudyDecision,
)
from standards_driven_sdtm_adam.extraction.model import EvidenceRecord
from standards_driven_sdtm_adam.feasibility.data import SDTMDataSnapshot
from standards_driven_sdtm_adam.preprocessing.execution import PreprocessingExecutionRecord
from standards_driven_sdtm_adam.preprocessing.model import (
    PreprocessingOperationSpec,
    PreprocessingSpecification,
)
from standards_driven_sdtm_adam.validation.model import AdamValidationResult, ValidationResult


RecordsByDomain = Mapping[str, Iterable[Mapping[str, object]]]

STUDY_INPUT_DECISION_IDS = {
    "DECISION-SAFETY-POPULATION": ("DECISION-SAFETY-POPULATION",),
    "treatment_emergent_window": ("DECISION-TREATMENT-EMERGENT-WINDOW",),
    "event_definition": ("DECISION-TTE-EVENT-CENSOR",),
    "censoring_rules": ("DECISION-TTE-EVENT-CENSOR",),
    "baseline_definition": ("DECISION-BASELINE-DEFINITION",),
}


class AdamValidationEngine:
    """Validate generated outputs without modifying or repairing them."""

    def validate(
        self,
        *,
        source_sdtm_datasets: RecordsByDomain,
        adam_specification: AdamDerivationSpecification,
        adam_datasets: RecordsByDomain,
        derivation_execution_records: Iterable[AdamDerivationExecutionRecord],
        preprocessed_datasets: RecordsByDomain | None = None,
        preprocessing_specification: PreprocessingSpecification | None = None,
        preprocessing_execution_records: Iterable[PreprocessingExecutionRecord] = (),
        evidence: Iterable[EvidenceRecord] = (),
        study_decisions: Iterable[StudyDecision] = (),
    ) -> AdamValidationResult:
        source = SDTMDataSnapshot(source_sdtm_datasets)
        adam = _normalize_records(adam_datasets)
        specs = {f"{spec.dataset}.{spec.variable}": spec for spec in adam_specification.variable_specs}
        executions = tuple(derivation_execution_records)
        execution_by_spec = {record.specification_id: record for record in executions}
        execution_by_var = {f"{record.dataset}.{record.variable}": record for record in executions}
        evidence_ids = {record.evidence_id for record in evidence}
        decisions = {decision.decision_id: decision for decision in study_decisions}

        results: list[ValidationResult] = []
        add = _ResultBuilder(results)

        self._structural_checks(add, source, adam)
        self._traceability_checks(add, source, adam, specs, executions, execution_by_spec, evidence_ids)
        self._logical_checks(add, source, adam, specs, execution_by_var, decisions)
        self._preprocessing_checks(
            add,
            preprocessing_specification,
            tuple(preprocessing_execution_records),
            preprocessed_datasets,
        )

        overall = "PASS"
        if any(result.status == "FAIL" for result in results):
            overall = "FAIL"
        elif any(result.status in {"WARNING", "NOT_EVALUATED"} for result in results):
            overall = "WARNING"
        return AdamValidationResult(validation_results=tuple(results), status=overall)

    def _structural_checks(
        self,
        add: "_ResultBuilder",
        source: SDTMDataSnapshot,
        adam: dict[str, tuple[dict[str, object], ...]],
    ) -> None:
        expected_datasets = {"ADSL", "ADAE", "ADLB", "ADTTE"}
        unexpected = tuple(sorted(set(adam) - expected_datasets))
        add(
            category="STRUCTURAL",
            dataset=None,
            variable=None,
            check_id="STRUCTURE-EXPECTED-DATASETS",
            description="Generated outputs contain only supported ADaM datasets.",
            status="PASS" if not unexpected else "FAIL",
            severity="ERROR" if unexpected else "INFO",
            expected=tuple(sorted(expected_datasets)),
            observed=unexpected,
            message="No unexpected ADaM datasets found." if not unexpected else f"Unexpected datasets found: {unexpected}.",
        )

        adsl = adam.get("ADSL", ())
        subjects = [_value(record.get("USUBJID")) for record in adsl if _present(record.get("USUBJID"))]
        duplicate_subjects = tuple(sorted(subject for subject in set(subjects) if subjects.count(subject) > 1))
        add(
            category="STRUCTURAL",
            dataset="ADSL",
            variable="USUBJID",
            check_id="STRUCTURE-ADSL-USUBJID-GRAIN",
            description="ADSL has no duplicate subject records.",
            status="PASS" if not duplicate_subjects else "FAIL",
            severity="ERROR" if duplicate_subjects else "INFO",
            expected="One record per USUBJID",
            observed=duplicate_subjects or f"{len(subjects)} unique subject records",
            message="ADSL subject grain is valid." if not duplicate_subjects else f"Duplicate ADSL subjects: {duplicate_subjects}.",
        )

        for dataset in ("ADSL", "ADAE", "ADLB", "ADTTE"):
            records = adam.get(dataset, ())
            if not records:
                continue
            missing = sum(1 for record in records if not _present(record.get("USUBJID")))
            expected = "USUBJID present on every record"
            if dataset != "ADSL":
                expected = "Subject linkage available or derivable from source record order"
            status = "PASS"
            observed = "USUBJID present"
            if dataset == "ADSL" and missing:
                status = "FAIL"
                observed = f"{missing} records missing USUBJID"
            elif dataset != "ADSL" and missing == len(records):
                observed = "USUBJID absent in output; source-order linkage required"
            add(
                category="STRUCTURAL",
                dataset=dataset,
                variable="USUBJID",
                check_id="STRUCTURE-REQUIRED-USUBJID",
                description="Required subject key or linkage is available.",
                status=status,
                severity="ERROR" if status == "FAIL" else "INFO",
                expected=expected,
                observed=observed,
                message="Required subject linkage is available." if status == "PASS" else "ADSL requires USUBJID on every record.",
            )

        expected_counts = {"ADAE": source.record_count("AE"), "ADLB": source.record_count("LB"), "ADTTE": source.record_count("DS")}
        for dataset, expected_count in expected_counts.items():
            if dataset not in adam:
                continue
            observed_count = len(adam[dataset])
            add(
                category="STRUCTURAL",
                dataset=dataset,
                variable=None,
                check_id=f"STRUCTURE-{dataset}-RECORD-GRAIN",
                description=f"{dataset} record grain matches the supported source-domain grain.",
                status="PASS" if observed_count == expected_count else "FAIL",
                severity="ERROR" if observed_count != expected_count else "INFO",
                expected=expected_count,
                observed=observed_count,
                source_references=(dataset,),
                message=f"{dataset} record count is structurally valid." if observed_count == expected_count else f"{dataset} record count does not match expected source grain.",
            )

    def _traceability_checks(
        self,
        add: "_ResultBuilder",
        source: SDTMDataSnapshot,
        adam: dict[str, tuple[dict[str, object], ...]],
        specs: dict[str, AdamVariableSpecification],
        executions: tuple[AdamDerivationExecutionRecord, ...],
        execution_by_spec: dict[str, AdamDerivationExecutionRecord],
        evidence_ids: set[str],
    ) -> None:
        execution_ids = {record.execution_id for record in executions}
        spec_ids = {spec.specification_id for spec in specs.values()}

        for dataset, records in adam.items():
            for variable in _dataset_variables(records):
                qualified = f"{dataset}.{variable}"
                spec = specs.get(qualified)
                add(
                    category="TRACEABILITY",
                    dataset=dataset,
                    variable=variable,
                    check_id="TRACE-SPEC-REFERENCE",
                    description="Every populated ADaM variable has an approved specification.",
                    status="PASS" if spec is not None else "FAIL",
                    severity="ERROR" if spec is None else "INFO",
                    expected="Approved variable specification",
                    observed=spec.specification_id if spec is not None else None,
                    specification_reference=spec.specification_id if spec is not None else None,
                    message="Specification reference exists." if spec is not None else f"No specification found for {qualified}.",
                )

        for qualified, spec in specs.items():
            execution = execution_by_spec.get(spec.specification_id)
            dataset, variable = qualified.split(".", 1)
            add(
                category="TRACEABILITY",
                dataset=dataset,
                variable=variable,
                check_id="TRACE-EXECUTION-REFERENCE",
                description="Every specification has a corresponding execution record.",
                status="PASS" if execution is not None else "FAIL",
                severity="ERROR" if execution is None else "INFO",
                expected=spec.specification_id,
                observed=execution.execution_id if execution is not None else None,
                specification_reference=spec.specification_id,
                execution_references=(execution.execution_id,) if execution is not None else (),
                message="Execution references the specification." if execution is not None else "No execution record references the specification.",
            )

            missing_sources = tuple(
                source_variable
                for source_variable in spec.source_variables
                if not _source_variable_exists(source, source_variable)
            )
            add(
                category="TRACEABILITY",
                dataset=dataset,
                variable=variable,
                check_id="TRACE-SOURCE-REFERENCE",
                description="Source variables referenced by the specification exist.",
                status="PASS" if not missing_sources else "FAIL",
                severity="ERROR" if missing_sources else "INFO",
                expected=spec.source_variables,
                observed=missing_sources or spec.source_variables,
                specification_reference=spec.specification_id,
                source_references=spec.source_variables,
                message="Source references exist." if not missing_sources else f"Missing source references: {missing_sources}.",
            )

            missing_evidence = tuple(
                evidence_id
                for evidence_id in spec.evidence_references
                if evidence_id not in evidence_ids
            )
            evidence_required = spec.classification in {"STANDARD_REQUIRED", "STANDARD_GUIDED", "EXAMPLE_ADAPTED"} and bool(spec.evidence_references)
            add(
                category="TRACEABILITY",
                dataset=dataset,
                variable=variable,
                check_id="TRACE-EVIDENCE-REFERENCE",
                description="Evidence references exist when the classification depends on evidence.",
                status="PASS" if not evidence_required or not missing_evidence else "FAIL",
                severity="ERROR" if evidence_required and missing_evidence else "INFO",
                expected=spec.evidence_references,
                observed=missing_evidence or spec.evidence_references,
                specification_reference=spec.specification_id,
                evidence_references=spec.evidence_references,
                message="Evidence references are available." if not missing_evidence else f"Missing evidence references: {missing_evidence}.",
            )

        for record in executions:
            qualified = f"{record.dataset}.{record.variable}"
            is_orphan = record.specification_id not in spec_ids or qualified not in specs
            add(
                category="TRACEABILITY",
                dataset=record.dataset,
                variable=record.variable,
                check_id="TRACE-ORPHAN-EXECUTION",
                description="Execution records must correspond to a known specification.",
                status="FAIL" if is_orphan else "PASS",
                severity="ERROR" if is_orphan else "INFO",
                expected="Execution record references an approved specification",
                observed=record.specification_id,
                specification_reference=record.specification_id,
                execution_references=(record.execution_id,) if record.execution_id in execution_ids else (),
                message="Execution record is linked." if not is_orphan else "Execution record is orphaned from approved specifications.",
            )

    def _logical_checks(
        self,
        add: "_ResultBuilder",
        source: SDTMDataSnapshot,
        adam: dict[str, tuple[dict[str, object], ...]],
        specs: dict[str, AdamVariableSpecification],
        execution_by_var: dict[str, AdamDerivationExecutionRecord],
        decisions: dict[str, StudyDecision],
    ) -> None:
        for qualified, spec in specs.items():
            dataset, variable = qualified.split(".", 1)
            execution = execution_by_var.get(qualified)
            populated = _variable_populated(adam.get(dataset, ()), variable)
            if (not spec.implementation_allowed or (execution is not None and execution.status != "DERIVED")) and populated:
                add(
                    category="LOGICAL",
                    dataset=dataset,
                    variable=variable,
                    check_id="LOGIC-BLOCKED-VARIABLE-NOT-POPULATED",
                    description="Blocked variables are not silently populated.",
                    status="FAIL",
                    severity="ERROR",
                    expected="No populated values for blocked variable",
                    observed="Populated values found",
                    specification_reference=spec.specification_id,
                    execution_references=(execution.execution_id,) if execution is not None else (),
                    message=f"{qualified} is blocked but contains populated values.",
                )

        self._validate_adlb_aval(add, source, adam, specs)
        self._validate_adae_trtemfl(add, source, adam, specs, decisions)
        self._validate_adtte_cnsr(add, source, adam, specs, decisions)

    def _validate_adlb_aval(
        self,
        add: "_ResultBuilder",
        source: SDTMDataSnapshot,
        adam: dict[str, tuple[dict[str, object], ...]],
        specs: dict[str, AdamVariableSpecification],
    ) -> None:
        spec = specs.get("ADLB.AVAL")
        if spec is None:
            return
        expected = tuple(_numeric(record.get("LBSTRESN")) for record in source.records("LB"))
        observed = tuple(record.get("AVAL") for record in adam.get("ADLB", ()))
        add(
            category="LOGICAL",
            dataset="ADLB",
            variable="AVAL",
            check_id="LOGIC-ADLB-AVAL",
            description="ADLB.AVAL agrees with deterministic LB source value.",
            status="PASS" if observed == expected else "FAIL",
            severity="ERROR" if observed != expected else "INFO",
            expected=expected,
            observed=observed,
            specification_reference=spec.specification_id,
            source_references=spec.source_variables,
            message="ADLB.AVAL values match LB.LBSTRESN." if observed == expected else "ADLB.AVAL values do not match LB.LBSTRESN.",
        )

    def _validate_adae_trtemfl(
        self,
        add: "_ResultBuilder",
        source: SDTMDataSnapshot,
        adam: dict[str, tuple[dict[str, object], ...]],
        specs: dict[str, AdamVariableSpecification],
        decisions: dict[str, StudyDecision],
    ) -> None:
        spec = specs.get("ADAE.TRTEMFL")
        if spec is None:
            return
        if not _study_input_resolved("treatment_emergent_window", decisions):
            add(
                category="LOGICAL",
                dataset="ADAE",
                variable="TRTEMFL",
                check_id="LOGIC-ADAE-TRTEMFL",
                description="ADAE.TRTEMFL respects resolved treatment-emergent definition.",
                status="NOT_EVALUATED",
                severity="INFO",
                expected="Resolved treatment-emergent decision",
                observed="Decision unresolved",
                specification_reference=spec.specification_id,
                source_references=spec.source_variables,
                message="Treatment-emergent logic was not evaluated because the study decision is unresolved.",
            )
            return
        adsl_by_subject = _adsl_by_source_subject(adam.get("ADSL", ()), source)
        window_days = _window_days(decisions)
        expected = []
        for index, ae_record in enumerate(source.records("AE")):
            subject = _value(ae_record.get("USUBJID"))
            adsl = adsl_by_subject.get(subject, {})
            ae_adam = _record_at(adam.get("ADAE", ()), index)
            expected.append(_trtemfl(ae_adam.get("ASTDT"), adsl.get("TRTSDT"), adsl.get("TRTEDT"), window_days))
        observed = tuple(record.get("TRTEMFL") for record in adam.get("ADAE", ()))
        expected_tuple = tuple(expected)
        add(
            category="LOGICAL",
            dataset="ADAE",
            variable="TRTEMFL",
            check_id="LOGIC-ADAE-TRTEMFL",
            description="ADAE.TRTEMFL respects resolved treatment-emergent definition.",
            status="PASS" if observed == expected_tuple else "FAIL",
            severity="ERROR" if observed != expected_tuple else "INFO",
            expected=expected_tuple,
            observed=observed,
            specification_reference=spec.specification_id,
            source_references=spec.source_variables,
            message="ADAE.TRTEMFL values match resolved treatment-emergent logic." if observed == expected_tuple else "ADAE.TRTEMFL values do not match resolved treatment-emergent logic.",
        )

    def _validate_adtte_cnsr(
        self,
        add: "_ResultBuilder",
        source: SDTMDataSnapshot,
        adam: dict[str, tuple[dict[str, object], ...]],
        specs: dict[str, AdamVariableSpecification],
        decisions: dict[str, StudyDecision],
    ) -> None:
        spec = specs.get("ADTTE.CNSR")
        if spec is None:
            return
        if not _study_input_resolved("censoring_rules", decisions):
            add(
                category="LOGICAL",
                dataset="ADTTE",
                variable="CNSR",
                check_id="LOGIC-ADTTE-CNSR",
                description="ADTTE.CNSR respects explicit event and censoring logic.",
                status="NOT_EVALUATED",
                severity="INFO",
                expected="Resolved event and censoring rules",
                observed="Decision unresolved",
                specification_reference=spec.specification_id,
                source_references=spec.source_variables,
                message="ADTTE censoring logic was not evaluated because the study decision is unresolved.",
            )
            return
        event_terms = _event_terms(decisions)
        expected = tuple(0 if _value(record.get("DSDECOD")).upper() in event_terms else 1 for record in source.records("DS"))
        observed = tuple(record.get("CNSR") for record in adam.get("ADTTE", ()))
        add(
            category="LOGICAL",
            dataset="ADTTE",
            variable="CNSR",
            check_id="LOGIC-ADTTE-CNSR",
            description="ADTTE.CNSR respects explicit event and censoring logic.",
            status="PASS" if observed == expected else "FAIL",
            severity="ERROR" if observed != expected else "INFO",
            expected=expected,
            observed=observed,
            specification_reference=spec.specification_id,
            source_references=spec.source_variables,
            message="ADTTE.CNSR values match explicit censoring logic." if observed == expected else "ADTTE.CNSR values do not match explicit censoring logic.",
        )

    def _preprocessing_checks(
        self,
        add: "_ResultBuilder",
        preprocessing_specification: PreprocessingSpecification | None,
        preprocessing_execution_records: tuple[PreprocessingExecutionRecord, ...],
        preprocessed_datasets: RecordsByDomain | None,
    ) -> None:
        if preprocessing_specification is None and not preprocessing_execution_records:
            return
        specs: dict[str, PreprocessingOperationSpec] = {}
        if preprocessing_specification is not None:
            specs = {spec.operation_id: spec for spec in preprocessing_specification.operations}
        for record in preprocessing_execution_records:
            spec = specs.get(record.operation_id)
            status = "PASS" if spec is not None and record.status in {"EXECUTED", "REJECTED", "FAILED"} else "FAIL"
            add(
                category="TRACEABILITY",
                dataset=record.dataset,
                variable=record.variable,
                check_id="TRACE-PREPROCESSING-EXECUTION",
                description="Preprocessing execution records trace to preprocessing specifications.",
                status=status,
                severity="ERROR" if status == "FAIL" else "INFO",
                expected=record.operation_id,
                observed=spec.operation_id if spec is not None else None,
                specification_reference=spec.operation_id if spec is not None else None,
                execution_references=(record.execution_id,),
                source_references=(record.dataset,),
                message="Preprocessing traceability is valid." if status == "PASS" else "Preprocessing execution record is missing its specification.",
            )


class _ResultBuilder:
    def __init__(self, results: list[ValidationResult]) -> None:
        self._results = results

    def __call__(
        self,
        *,
        category: str,
        dataset: str | None,
        variable: str | None,
        check_id: str,
        description: str,
        status: str,
        severity: str,
        expected: object,
        observed: object,
        message: str,
        specification_reference: str | None = None,
        evidence_references: tuple[str, ...] = (),
        execution_references: tuple[str, ...] = (),
        source_references: tuple[str, ...] = (),
    ) -> None:
        self._results.append(
            ValidationResult(
                validation_id=f"VAL-{len(self._results) + 1:04d}",
                category=category,
                dataset=dataset,
                variable=variable,
                check_id=check_id,
                description=description,
                status=status,
                severity=severity,
                expected=expected,
                observed=observed,
                specification_reference=specification_reference,
                evidence_references=evidence_references,
                execution_references=execution_references,
                source_references=source_references,
                message=message,
            )
        )


def _normalize_records(datasets: RecordsByDomain) -> dict[str, tuple[dict[str, object], ...]]:
    return {
        dataset.upper(): tuple(dict(record) for record in records)
        for dataset, records in datasets.items()
    }


def _dataset_variables(records: tuple[dict[str, object], ...]) -> tuple[str, ...]:
    variables: set[str] = set()
    for record in records:
        variables.update(record)
    return tuple(sorted(variables))


def _source_variable_exists(source: SDTMDataSnapshot, source_variable: str) -> bool:
    if "." not in source_variable:
        return False
    dataset, variable = source_variable.split(".", 1)
    return source.has_variable(dataset, variable)


def _variable_populated(records: tuple[dict[str, object], ...], variable: str) -> bool:
    return any(_present(record.get(variable)) for record in records)


def _study_input_resolved(study_input: str, decisions: dict[str, StudyDecision]) -> bool:
    decision_ids = STUDY_INPUT_DECISION_IDS.get(study_input, (study_input,))
    return any(
        decision_id in decisions
        and decisions[decision_id].status == "PROVIDED"
        and bool(decisions[decision_id].value)
        for decision_id in decision_ids
    )


def _adsl_by_source_subject(
    adsl_records: tuple[dict[str, object], ...],
    source: SDTMDataSnapshot,
) -> dict[str, dict[str, object]]:
    subjects = []
    seen: set[str] = set()
    for record in source.records("DM"):
        subject = _value(record.get("USUBJID"))
        if subject in seen:
            continue
        seen.add(subject)
        subjects.append(subject)
    return {
        subject: record
        for subject, record in zip(subjects, adsl_records, strict=False)
    }


def _record_at(records: tuple[dict[str, object], ...], index: int) -> dict[str, object]:
    if index >= len(records):
        return {}
    return records[index]


def _trtemfl(ae_start, treatment_start, treatment_end, window_days: int) -> str | None:
    ae_date = _parse_date(ae_start)
    start_date = _parse_date(treatment_start)
    end_date = _parse_date(treatment_end)
    if ae_date is None or start_date is None or end_date is None:
        return None
    return "Y" if start_date <= ae_date and (ae_date - end_date).days <= window_days else "N"


def _window_days(decisions: dict[str, StudyDecision]) -> int:
    decision = decisions.get("DECISION-TREATMENT-EMERGENT-WINDOW")
    if decision and decision.value and "30" in decision.value:
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


def _parse_date(value: object) -> date | None:
    if not _present(value):
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def _numeric(value: object) -> float | None:
    if not _present(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _present(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str) and not value.strip():
        return False
    return True


def _value(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()
