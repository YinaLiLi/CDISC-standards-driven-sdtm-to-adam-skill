"""Generate preprocessing specifications without executing preprocessing."""

from __future__ import annotations

from collections.abc import Iterable
import re

from standards_driven_sdtm_adam.extraction.model import EvidenceRecord
from standards_driven_sdtm_adam.feasibility.data import SDTMDataSnapshot, SUPPORTED_SDTM_DOMAINS
from standards_driven_sdtm_adam.feasibility.model import FeasibilityAssessment, FeasibilityResult
from standards_driven_sdtm_adam.preprocessing.model import (
    PreprocessingOperationSpec,
    PreprocessingSpecification,
)


DATE_VARIABLES = {
    "AE": ("AESTDTC",),
    "LB": ("LBDTC",),
    "DS": ("DSSTDTC",),
    "EX": ("EXSTDTC",),
    "SV": ("SVSTDTC",),
}

NUMERIC_VARIABLES = {
    "LB": ("LBORRES", "LBSTRESN"),
}

TEXT_VARIABLES = {
    "DM": ("USUBJID",),
    "AE": ("USUBJID", "AETERM"),
    "LB": ("USUBJID", "LBTESTCD", "LBORRES"),
    "DS": ("USUBJID", "DSDECOD"),
    "EX": ("USUBJID", "EXTRT"),
    "SV": ("USUBJID",),
}

PROHIBITED_OPERATION_KEYWORDS = {
    "impute_clinical_value": ("impute", "imputation", "fill missing clinical", "replace missing clinical"),
    "silent_record_deletion": ("delete records", "drop records", "remove records", "exclude records silently"),
    "adam_variable_derivation": ("derive adam", "create adam", "analysis variable", "aval", "trtemfl"),
    "clinical_recode": ("recode medical", "recode adverse event", "change terminology", "map terms"),
    "raw_to_sdtm_mapping": ("raw-to-sdtm", "raw to sdtm", "sdtm compliance transformation"),
}


class PreprocessingSpecifier:
    """Propose justified preprocessing specifications."""

    def specify(
        self,
        sdtm_datasets,
        feasibility: FeasibilityAssessment | Iterable[FeasibilityResult],
        discovery_results=None,
        evidence: Iterable[EvidenceRecord] = (),
        *,
        requested_operations: Iterable[str] = (),
    ) -> PreprocessingSpecification:
        snapshot = SDTMDataSnapshot(sdtm_datasets)
        feasibility_results = _coerce_results(feasibility)
        evidence_by_topic = _index_evidence(evidence)

        operations: list[PreprocessingOperationSpec] = []
        operations.extend(self._prohibited_specs(requested_operations, evidence_by_topic))

        for domain in snapshot.domains:
            if domain not in SUPPORTED_SDTM_DOMAINS:
                continue
            operations.extend(
                self._domain_specs(
                    domain,
                    snapshot,
                    feasibility_results,
                    evidence_by_topic,
                )
            )

        return PreprocessingSpecification(operations=tuple(operations))

    def _domain_specs(
        self,
        domain: str,
        snapshot: SDTMDataSnapshot,
        feasibility_results: tuple[FeasibilityResult, ...],
        evidence_by_topic: dict[str, tuple[str, ...]],
    ) -> list[PreprocessingOperationSpec]:
        specs: list[PreprocessingOperationSpec] = []
        available_variables = set(snapshot.variables(domain))

        for variable in DATE_VARIABLES.get(domain, ()):
            if variable in available_variables:
                specs.append(
                    _allowed_spec(
                        domain=domain,
                        variable=variable,
                        operation="deterministic_date_parsing",
                        purpose="Parse source date text into a machine-readable representation while preserving the original SDTM value.",
                        classification=_classification_for("date", evidence_by_topic),
                        evidence_references=evidence_by_topic.get("date", ()),
                        notes=("Do not impute partial or missing dates.",),
                    )
                )

        for variable in NUMERIC_VARIABLES.get(domain, ()):
            if variable in available_variables:
                specs.append(
                    _allowed_spec(
                        domain=domain,
                        variable=variable,
                        operation="deterministic_numeric_parsing",
                        purpose="Parse numeric-looking source values into technical numeric form for downstream checks without changing the source value.",
                        classification="DATA_ENGINEERING",
                        evidence_references=(),
                        notes=("No CDISC requirement is claimed for technical numeric parsing.",),
                    )
                )

        for variable in TEXT_VARIABLES.get(domain, ()):
            if variable in available_variables:
                specs.append(
                    _allowed_spec(
                        domain=domain,
                        variable=variable,
                        operation="neutral_whitespace_normalization",
                        purpose="Normalize leading, trailing, or repeated technical whitespace for stable joins and checks while preserving clinical meaning.",
                        classification="DATA_ENGINEERING",
                        evidence_references=(),
                        notes=("Do not recode controlled terminology or medical terms.",),
                    )
                )

        if _domain_has_missingness_limitation(domain, feasibility_results):
            specs.append(
                _allowed_spec(
                    domain=domain,
                    variable=None,
                    operation="missingness_quality_flag",
                    purpose="Flag source records with missing required source-data elements for transparent downstream review.",
                    classification="DATA_ENGINEERING",
                    evidence_references=(),
                    notes=("Flag records only; do not delete records or impute values.",),
                )
            )

        return specs

    def _prohibited_specs(
        self,
        requested_operations: Iterable[str],
        evidence_by_topic: dict[str, tuple[str, ...]],
    ) -> list[PreprocessingOperationSpec]:
        specs: list[PreprocessingOperationSpec] = []
        for index, request in enumerate(requested_operations, start=1):
            normalized = _normalize(request)
            operation_kind = _prohibited_kind(normalized)
            if operation_kind is None:
                continue
            specs.append(
                PreprocessingOperationSpec(
                    operation_id=f"PREP-BLOCKED-{index:03d}",
                    dataset=_dataset_hint(normalized),
                    variable=_variable_hint(request),
                    operation=operation_kind,
                    purpose=request,
                    classification="UNSUPPORTED",
                    evidence_references=evidence_by_topic.get(operation_kind, ()),
                    source_preserving=False,
                    clinical_meaning_changed=True,
                    implementation_allowed=False,
                    validation_plan=(
                        "Confirm the requested operation is not executed in source-preserving preprocessing.",
                    ),
                    notes=(
                        "Operation is prohibited in preprocessing because it may alter clinical meaning, delete source records, create ADaM variables, or imply Raw-to-SDTM/SDTM compliance transformation.",
                    ),
                )
            )
        return specs


def _allowed_spec(
    *,
    domain: str,
    variable: str | None,
    operation: str,
    purpose: str,
    classification: str,
    evidence_references: tuple[str, ...],
    notes: tuple[str, ...],
) -> PreprocessingOperationSpec:
    return PreprocessingOperationSpec(
        operation_id=f"PREP-{domain}-{operation}-{variable or 'DOMAIN'}",
        dataset=domain,
        variable=variable,
        operation=operation,
        purpose=purpose,
        classification=classification,
        evidence_references=evidence_references,
        source_preserving=True,
        clinical_meaning_changed=False,
        implementation_allowed=True,
        validation_plan=(
            "Verify source value is retained unchanged.",
            "Verify generated technical representation or flag is reproducible from the source value.",
            "Verify no records are deleted.",
        ),
        notes=notes,
    )


def _classification_for(topic: str, evidence_by_topic: dict[str, tuple[str, ...]]) -> str:
    if evidence_by_topic.get(topic):
        return "STANDARD_GUIDED"
    return "DATA_ENGINEERING"


def _index_evidence(evidence: Iterable[EvidenceRecord]) -> dict[str, tuple[str, ...]]:
    indexed: dict[str, list[str]] = {}
    for record in evidence:
        if record.extraction_status != "EXTRACTED":
            continue
        text = _normalize(" ".join((record.short_quote or "", record.search_context or "")))
        evidence_id = record.evidence_id
        if any(term in text for term in ("date", "dtc", "temporal", "time")):
            indexed.setdefault("date", []).append(evidence_id)
        if "example" in text:
            indexed.setdefault("example", []).append(evidence_id)
    return {key: tuple(values) for key, values in indexed.items()}


def _coerce_results(
    feasibility: FeasibilityAssessment | Iterable[FeasibilityResult],
) -> tuple[FeasibilityResult, ...]:
    if isinstance(feasibility, FeasibilityAssessment):
        return feasibility.results
    return tuple(feasibility)


def _domain_has_missingness_limitation(
    domain: str,
    feasibility_results: tuple[FeasibilityResult, ...],
) -> bool:
    for result in feasibility_results:
        if domain in result.missing_variables:
            return True
        if any(domain in limitation for limitation in result.limitations):
            return True
    return False


def _prohibited_kind(normalized_request: str) -> str | None:
    for operation_kind, keywords in PROHIBITED_OPERATION_KEYWORDS.items():
        if any(keyword in normalized_request for keyword in keywords):
            return operation_kind
    return None


def _dataset_hint(normalized_request: str) -> str:
    for domain in SUPPORTED_SDTM_DOMAINS:
        if re.search(rf"\b{domain.lower()}\b", normalized_request):
            return domain
    return "UNKNOWN"


def _variable_hint(request: str) -> str | None:
    match = re.search(r"\b[A-Z][A-Z0-9]{2,7}\b", request)
    if match:
        return match.group(0)
    return None


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.lower()).strip()
