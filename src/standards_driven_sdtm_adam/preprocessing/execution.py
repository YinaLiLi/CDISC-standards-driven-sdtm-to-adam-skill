"""Execute approved source-preserving preprocessing specifications."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
import re

from standards_driven_sdtm_adam.feasibility.data import SDTMDataSnapshot
from standards_driven_sdtm_adam.preprocessing.model import (
    PreprocessingOperationSpec,
    PreprocessingSpecification,
)


SUPPORTED_EXECUTION_OPERATIONS = (
    "deterministic_date_parsing",
    "deterministic_numeric_parsing",
    "missingness_quality_flag",
    "quality_flag_creation",
    "neutral_whitespace_normalization",
    "technical_datatype_normalization",
)


@dataclass(frozen=True)
class PreprocessingExecutionRecord:
    """Trace record for one preprocessing operation execution."""

    execution_id: str
    operation_id: str
    dataset: str
    variable: str | None
    operation: str
    classification: str
    input_record_count: int
    output_record_count: int
    affected_record_count: int
    status: str
    validation_status: str
    warnings: tuple[str, ...]
    source_reference: dict[str, object]


@dataclass(frozen=True)
class PreprocessingExecutionResult:
    """Processed SDTM copies and operation-level execution records."""

    processed_datasets: dict[str, tuple[dict[str, object], ...]]
    execution_records: tuple[PreprocessingExecutionRecord, ...]


class PreprocessingExecutionEngine:
    """Execute only explicitly approved preprocessing specifications."""

    def execute(
        self,
        sdtm_datasets,
        specification: PreprocessingSpecification | tuple[PreprocessingOperationSpec, ...],
        *,
        requested_operation_ids: tuple[str, ...] | None = None,
    ) -> PreprocessingExecutionResult:
        snapshot = SDTMDataSnapshot(sdtm_datasets)
        processed = {
            domain: tuple(dict(record) for record in snapshot.records(domain))
            for domain in snapshot.domains
        }
        specs = _coerce_specs(specification)
        spec_by_id = {spec.operation_id: spec for spec in specs}
        selected_specs = (
            tuple(spec_by_id[operation_id] for operation_id in requested_operation_ids if operation_id in spec_by_id)
            if requested_operation_ids is not None
            else specs
        )

        records: list[PreprocessingExecutionRecord] = []
        execution_index = 1

        if requested_operation_ids is not None:
            for operation_id in requested_operation_ids:
                if operation_id not in spec_by_id:
                    records.append(
                        _record(
                            execution_index,
                            operation_id=operation_id,
                            dataset="UNKNOWN",
                            variable=None,
                            operation="unapproved_operation",
                            classification="UNAPPROVED",
                            input_count=0,
                            output_count=0,
                            affected_count=0,
                            status="REJECTED",
                            validation_status="NOT_RUN",
                            warnings=("Operation id is absent from the approved preprocessing specification.",),
                            source_reference={},
                        )
                    )
                    execution_index += 1

        for spec in selected_specs:
            result_record = self._execute_spec(execution_index, processed, spec)
            records.append(result_record)
            execution_index += 1

        return PreprocessingExecutionResult(
            processed_datasets=processed,
            execution_records=tuple(records),
        )

    def _execute_spec(
        self,
        execution_index: int,
        processed: dict[str, tuple[dict[str, object], ...]],
        spec: PreprocessingOperationSpec,
    ) -> PreprocessingExecutionRecord:
        records = processed.get(spec.dataset, ())
        input_count = len(records)
        warnings: list[str] = []

        if not _is_approved(spec):
            return _record(
                execution_index,
                spec=spec,
                input_count=input_count,
                output_count=input_count,
                affected_count=0,
                status="REJECTED",
                validation_status="NOT_RUN",
                warnings=("Specification is not approved for source-preserving execution.",),
            )

        if spec.operation not in SUPPORTED_EXECUTION_OPERATIONS:
            return _record(
                execution_index,
                spec=spec,
                input_count=input_count,
                output_count=input_count,
                affected_count=0,
                status="FAILED",
                validation_status="FAILED",
                warnings=(f"Unsupported execution operation: {spec.operation}.",),
            )

        if spec.operation == "deterministic_date_parsing":
            affected = _execute_date_parsing(records, spec.variable, warnings)
        elif spec.operation == "deterministic_numeric_parsing":
            affected = _execute_numeric_parsing(records, spec.variable, warnings)
        elif spec.operation == "neutral_whitespace_normalization":
            affected = _execute_whitespace_normalization(records, spec.variable, warnings)
        elif spec.operation in {"missingness_quality_flag", "quality_flag_creation"}:
            affected = _execute_missingness_flags(records, warnings)
        elif spec.operation == "technical_datatype_normalization":
            affected = _execute_datatype_normalization(records, spec.variable, warnings)
        else:
            affected = 0

        validation_status = "PASSED" if len(records) == input_count else "FAILED"
        status = "EXECUTED" if validation_status == "PASSED" else "FAILED"
        if warnings and status == "EXECUTED":
            validation_status = "PASSED_WITH_WARNINGS"

        return _record(
            execution_index,
            spec=spec,
            input_count=input_count,
            output_count=len(records),
            affected_count=affected,
            status=status,
            validation_status=validation_status,
            warnings=tuple(warnings),
        )


def _execute_date_parsing(
    records: tuple[dict[str, object], ...],
    variable: str | None,
    warnings: list[str],
) -> int:
    if variable is None:
        warnings.append("Date parsing requires a variable.")
        return 0

    affected = 0
    parsed_field = f"__{variable}_PARSED"
    flag_field = f"__{variable}_PARSE_STATUS"
    for record in records:
        original = record.get(variable)
        parsed = _parse_iso_date(original)
        record[parsed_field] = parsed
        if _present(original) and parsed is None:
            record[flag_field] = "UNPARSABLE"
            warnings.append(f"Unparsable date value retained for {variable}.")
        elif parsed is not None:
            record[flag_field] = "PARSED"
            affected += 1
        else:
            record[flag_field] = "MISSING"
    return affected


def _execute_numeric_parsing(
    records: tuple[dict[str, object], ...],
    variable: str | None,
    warnings: list[str],
) -> int:
    if variable is None:
        warnings.append("Numeric parsing requires a variable.")
        return 0

    affected = 0
    parsed_field = f"__{variable}_NUM"
    flag_field = f"__{variable}_NUM_PARSE_STATUS"
    for record in records:
        original = record.get(variable)
        parsed = _parse_decimal(original)
        record[parsed_field] = parsed
        if _present(original) and parsed is None:
            record[flag_field] = "UNPARSABLE"
            warnings.append(f"Unparsable numeric value retained for {variable}.")
        elif parsed is not None:
            record[flag_field] = "PARSED"
            affected += 1
        else:
            record[flag_field] = "MISSING"
    return affected


def _execute_whitespace_normalization(
    records: tuple[dict[str, object], ...],
    variable: str | None,
    warnings: list[str],
) -> int:
    if variable is None:
        warnings.append("Whitespace normalization requires a variable.")
        return 0

    affected = 0
    normalized_field = f"__{variable}_NORM"
    flag_field = f"__{variable}_NORM_STATUS"
    for record in records:
        original = record.get(variable)
        normalized = _normalize_whitespace(original)
        record[normalized_field] = normalized
        if _present(original) and normalized != original:
            record[flag_field] = "NORMALIZED"
            affected += 1
        elif _present(original):
            record[flag_field] = "UNCHANGED"
        else:
            record[flag_field] = "MISSING"
    return affected


def _execute_missingness_flags(
    records: tuple[dict[str, object], ...],
    warnings: list[str],
) -> int:
    affected = 0
    for record in records:
        missing = tuple(sorted(key for key, value in record.items() if not _present(value)))
        record["__SOURCE_MISSINGNESS_FLAG"] = bool(missing)
        record["__SOURCE_MISSING_VARIABLES"] = "|".join(missing)
        if missing:
            affected += 1
    return affected


def _execute_datatype_normalization(
    records: tuple[dict[str, object], ...],
    variable: str | None,
    warnings: list[str],
) -> int:
    if variable is None:
        warnings.append("Technical datatype normalization requires a variable.")
        return 0
    field = f"__{variable}_TEXT"
    affected = 0
    for record in records:
        value = record.get(variable)
        record[field] = None if value is None else str(value)
        if value is not None:
            affected += 1
    return affected


def _is_approved(spec: PreprocessingOperationSpec) -> bool:
    return (
        spec.implementation_allowed
        and spec.source_preserving
        and not spec.clinical_meaning_changed
        and spec.classification != "UNSUPPORTED"
    )


def _record(
    execution_index: int,
    *,
    spec: PreprocessingOperationSpec | None = None,
    operation_id: str | None = None,
    dataset: str | None = None,
    variable: str | None = None,
    operation: str | None = None,
    classification: str | None = None,
    input_count: int,
    output_count: int,
    affected_count: int,
    status: str,
    validation_status: str,
    warnings: tuple[str, ...],
    source_reference: dict[str, object] | None = None,
) -> PreprocessingExecutionRecord:
    source = source_reference or {}
    if spec is not None:
        source = {
            "operation_id": spec.operation_id,
            "classification": spec.classification,
            "evidence_references": spec.evidence_references,
            "validation_plan": spec.validation_plan,
        }
    return PreprocessingExecutionRecord(
        execution_id=f"EXEC-{execution_index:03d}",
        operation_id=spec.operation_id if spec is not None else operation_id or "UNKNOWN",
        dataset=spec.dataset if spec is not None else dataset or "UNKNOWN",
        variable=spec.variable if spec is not None else variable,
        operation=spec.operation if spec is not None else operation or "UNKNOWN",
        classification=spec.classification if spec is not None else classification or "UNKNOWN",
        input_record_count=input_count,
        output_record_count=output_count,
        affected_record_count=affected_count,
        status=status,
        validation_status=validation_status,
        warnings=warnings,
        source_reference=source,
    )


def _coerce_specs(
    specification: PreprocessingSpecification | tuple[PreprocessingOperationSpec, ...],
) -> tuple[PreprocessingOperationSpec, ...]:
    if isinstance(specification, PreprocessingSpecification):
        return specification.operations
    return tuple(specification)


def _parse_iso_date(value: object) -> str | None:
    if not _present(value):
        return None
    text = str(value).strip()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return None
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError:
        return None


def _parse_decimal(value: object) -> Decimal | None:
    if not _present(value):
        return None
    text = str(value).strip()
    if not re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)", text):
        return None
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def _normalize_whitespace(value: object) -> str | None:
    if value is None:
        return None
    return re.sub(r"\s+", " ", str(value)).strip()


def _present(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str) and not value.strip():
        return False
    return True
