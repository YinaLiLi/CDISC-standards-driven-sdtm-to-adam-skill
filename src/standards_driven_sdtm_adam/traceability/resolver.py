"""Resolve specification evidence references into citation records."""

from __future__ import annotations

from typing import Iterable, Protocol

from standards_driven_sdtm_adam.extraction.model import EvidenceRecord, RuleExtractionRun
from standards_driven_sdtm_adam.standards import StandardManifest, StandardsRegistry
from standards_driven_sdtm_adam.standards.errors import StandardsRegistryError
from standards_driven_sdtm_adam.traceability.model import (
    CitationRecord,
    DECISION_CLASSIFICATIONS,
    DecisionEvidenceRequest,
    EvidenceResolutionResult,
    ResolvedEvidenceItem,
)


STANDARD_DECISIONS = {"STANDARD_REQUIRED", "STANDARD_GUIDED"}
VALID_EXTRACTION_STATUSES = {"EXTRACTED", "AMBIGUOUS_EVIDENCE"}
ROLE_SORT_ORDER = {
    "primary_standard": 0,
    "upstream_reference": 1,
    "validation_reference": 2,
    "future_scope": 3,
}


class EvidenceBearingItem(Protocol):
    """Shape accepted from existing pipeline specification models."""

    classification: str
    evidence_references: tuple[str, ...]


class EvidenceResolver:
    """Resolve evidence references into deterministic citation records."""

    def __init__(self, registry: StandardsRegistry) -> None:
        self.registry = registry

    def resolve(
        self,
        items: Iterable[DecisionEvidenceRequest | EvidenceBearingItem],
        extraction_run: RuleExtractionRun,
    ) -> EvidenceResolutionResult:
        """Resolve evidence for decisions or existing specification items."""

        evidence_by_id = {
            record.evidence_id: record
            for record in sorted(extraction_run.evidence, key=_evidence_sort_key)
        }
        resolved = [
            self._resolve_one(_request_from_item(item), evidence_by_id)
            for item in items
        ]
        return EvidenceResolutionResult(items=tuple(resolved))

    def _resolve_one(
        self,
        request: DecisionEvidenceRequest,
        evidence_by_id: dict[str, EvidenceRecord],
    ) -> ResolvedEvidenceItem:
        citation_inputs: list[tuple[EvidenceRecord, StandardManifest, str]] = []
        unresolved: list[str] = []
        excluded: list[str] = []

        for evidence_reference in request.evidence_references:
            evidence = evidence_by_id.get(evidence_reference)
            if evidence is None:
                unresolved.append(evidence_reference)
                continue

            manifest = self._manifest_for(evidence)
            if manifest is None:
                unresolved.append(evidence_reference)
                continue

            purpose = _citation_purpose(request, manifest)
            if purpose is None or evidence.extraction_status not in VALID_EXTRACTION_STATUSES:
                excluded.append(evidence_reference)
                continue

            citation_inputs.append((evidence, manifest, purpose))

        if request.evidence_use == "decision_support" and request.decision_classification not in STANDARD_DECISIONS:
            return ResolvedEvidenceItem(
                rule_specification_id=request.rule_specification_id,
                decision_classification=request.decision_classification,
                evidence_use=request.evidence_use,
                resolution_status="NON_STANDARD_DECISION",
                citations=(),
                unresolved_evidence_references=tuple(unresolved),
                excluded_evidence_references=tuple(
                    sorted(set(excluded + [record.evidence_id for record, _, _ in citation_inputs]))
                ),
            )

        citations = tuple(
            self._citation_from(record, manifest, request, purpose)
            for record, manifest, purpose in sorted(citation_inputs, key=_citation_input_sort_key)
        )

        status = "RESOLVED" if citations else "NO_VALID_STANDARD_EVIDENCE"
        return ResolvedEvidenceItem(
            rule_specification_id=request.rule_specification_id,
            decision_classification=request.decision_classification,
            evidence_use=request.evidence_use,
            resolution_status=status,
            citations=citations,
            unresolved_evidence_references=tuple(sorted(unresolved)),
            excluded_evidence_references=tuple(sorted(excluded)),
        )

    def _manifest_for(self, evidence: EvidenceRecord) -> StandardManifest | None:
        try:
            return self.registry.get(evidence.standard_id)
        except StandardsRegistryError:
            return None

    def _citation_from(
        self,
        evidence: EvidenceRecord,
        manifest: StandardManifest,
        request: DecisionEvidenceRequest,
        citation_purpose: str,
    ) -> CitationRecord:
        return CitationRecord(
            citation_id=f"{request.rule_specification_id}:{evidence.evidence_id}",
            rule_specification_id=request.rule_specification_id,
            decision_classification=request.decision_classification,
            citation_purpose=citation_purpose,
            evidence_reference=evidence.evidence_id,
            source_id=evidence.standard_id,
            source_role=manifest.role,
            document_title=manifest.title or evidence.standard_title,
            official_filename=manifest.original_filename,
            standard_version=manifest.version or evidence.version,
            standard_release_date=manifest.release_date,
            page=evidence.page,
            section=evidence.section,
            table=None,
            row=None,
            evidence_type=evidence.evidence_type,
            evidence_text=evidence.short_quote,
            extraction_status=evidence.extraction_status,
            official_url=manifest.official_url or evidence.official_url,
        )


def _request_from_item(
    item: DecisionEvidenceRequest | EvidenceBearingItem,
) -> DecisionEvidenceRequest:
    if isinstance(item, DecisionEvidenceRequest):
        return item

    classification = getattr(item, "classification")
    if classification not in DECISION_CLASSIFICATIONS:
        raise ValueError(
            "classification must be one of: "
            f"{', '.join(DECISION_CLASSIFICATIONS)}."
        )

    return DecisionEvidenceRequest(
        rule_specification_id=_item_identifier(item),
        decision_classification=classification,
        evidence_references=tuple(getattr(item, "evidence_references")),
    )


def _item_identifier(item: object) -> str:
    for field_name in (
        "rule_specification_id",
        "specification_id",
        "operation_id",
        "validation_id",
        "decision_id",
    ):
        value = getattr(item, field_name, None)
        if value:
            return str(value)
    dataset = getattr(item, "dataset", None)
    variable = getattr(item, "variable", None)
    if dataset and variable:
        return f"{dataset}.{variable}"
    if dataset:
        return str(dataset)
    raise ValueError("Evidence-bearing item must have a stable identifier.")


def _citation_purpose(
    request: DecisionEvidenceRequest,
    manifest: StandardManifest,
) -> str | None:
    if manifest.role == "future_scope":
        return None
    if request.evidence_use == "validation_support":
        if manifest.role == "validation_reference":
            return "validation_support"
        if manifest.role == "primary_standard":
            return "normative"
        if manifest.role == "upstream_reference":
            return "upstream_context"
        return None

    if request.decision_classification not in STANDARD_DECISIONS:
        return None
    if manifest.role == "primary_standard":
        return "normative"
    if manifest.role == "upstream_reference":
        return "upstream_context"
    return None


def _evidence_sort_key(record: EvidenceRecord) -> tuple[str, int | None, str]:
    return (record.standard_id, record.page, record.evidence_id)


def _citation_input_sort_key(
    item: tuple[EvidenceRecord, StandardManifest, str],
) -> tuple[int, str, int, str]:
    record, manifest, _ = item
    page = record.page if record.page is not None else 10**9
    return (ROLE_SORT_ORDER[manifest.role], record.standard_id, page, record.evidence_id)
