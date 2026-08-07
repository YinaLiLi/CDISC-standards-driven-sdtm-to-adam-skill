"""Build deterministic report models from existing pipeline outputs."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, is_dataclass
from typing import Any

from standards_driven_sdtm_adam.derivation.model import AdamDerivationSpecification
from standards_driven_sdtm_adam.preprocessing.model import PreprocessingSpecification
from standards_driven_sdtm_adam.reporting.model import (
    SUPPORTED_ADAM_DATASETS,
    PipelineReport,
)
from standards_driven_sdtm_adam.traceability import EvidenceResolutionResult
from standards_driven_sdtm_adam.validation.model import AdamValidationResult


REPORT_TITLE = "Standards-Driven SDTM-to-ADaM Pipeline Report"


class ReportBuilder:
    """Construct presentation reports without running pipeline logic."""

    def build(
        self,
        *,
        preprocessing_specification: PreprocessingSpecification | None,
        adam_derivation_specification: AdamDerivationSpecification | None,
        validation_result: AdamValidationResult | None,
        evidence_resolution_result: EvidenceResolutionResult | None,
    ) -> PipelineReport:
        """Build a stable report representation from supplied outputs."""

        validation = _validation_summary(validation_result)
        traceability = _traceability_summary(evidence_resolution_result)
        preprocessing = _preprocessing_summary(preprocessing_specification)
        adam = _adam_summary(adam_derivation_specification)
        status = _overall_status(validation)
        evidence = {
            "resolved_item_count": traceability["resolved_item_count"],
            "unresolved_item_count": traceability["unresolved_item_count"],
            "excluded_evidence_reference_count": traceability[
                "excluded_evidence_reference_count"
            ],
            "normative_citation_count": traceability["normative_citation_count"],
            "validation_support_citation_count": traceability[
                "validation_support_citation_count"
            ],
        }

        return PipelineReport(
            title=REPORT_TITLE,
            overall_status=status,
            metadata={
                "report_version": "1",
                "scope": "v1",
                "supported_source_domains": ["AE", "DM", "DS", "EX", "LB", "SV"],
                "supported_adam_datasets": list(SUPPORTED_ADAM_DATASETS),
            },
            preprocessing_summary=preprocessing,
            adam_summary=adam,
            validation_summary=validation,
            traceability_summary=traceability,
            evidence_summary=evidence,
        )


def _preprocessing_summary(
    specification: PreprocessingSpecification | None,
) -> dict[str, Any]:
    operations = [] if specification is None else list(specification.operations)
    sorted_operations = sorted(operations, key=lambda item: item.operation_id)
    return {
        "operation_count": len(sorted_operations),
        "operations": [
            {
                "operation_id": item.operation_id,
                "dataset": item.dataset,
                "variable": item.variable,
                "operation": item.operation,
                "classification": item.classification,
                "implementation_allowed": item.implementation_allowed,
                "source_preserving": item.source_preserving,
                "clinical_meaning_changed": item.clinical_meaning_changed,
                "evidence_references": list(item.evidence_references),
                "validation_plan": list(item.validation_plan),
                "notes": list(item.notes),
            }
            for item in sorted_operations
        ],
    }


def _adam_summary(
    specification: AdamDerivationSpecification | None,
) -> dict[str, Any]:
    dataset_specs = [] if specification is None else list(specification.dataset_specs)
    variable_specs = [] if specification is None else list(specification.variable_specs)

    datasets = [
        {
            "dataset": item.dataset,
            "purpose": item.purpose,
            "structure": item.structure,
            "source_domains": sorted(item.source_domains),
            "supported_variables": sorted(item.supported_variables),
            "evidence_references": list(item.evidence_references),
            "implementation_allowed": item.implementation_allowed,
            "unresolved_decisions": list(item.unresolved_decisions),
        }
        for item in sorted(dataset_specs, key=lambda item: item.dataset)
    ]
    variables = [
        {
            "specification_id": item.specification_id,
            "dataset": item.dataset,
            "variable": item.variable,
            "classification": item.classification,
            "source_domains": sorted(item.source_domains),
            "source_variables": sorted(item.source_variables),
            "dependencies": list(item.dependencies),
            "evidence_references": list(item.evidence_references),
            "implementation_allowed": item.implementation_allowed,
            "unresolved_issues": list(item.unresolved_issues),
        }
        for item in sorted(variable_specs, key=lambda item: item.specification_id)
    ]
    return {
        "dataset_count": len(datasets),
        "variable_count": len(variables),
        "datasets": datasets,
        "variables": variables,
        "unresolved_decision_count": 0
        if specification is None
        else len(specification.unresolved_decisions),
    }


def _validation_summary(result: AdamValidationResult | None) -> dict[str, Any]:
    validation_results = [] if result is None else list(result.validation_results)
    counts_by_status = Counter(item.status for item in validation_results)
    counts_by_severity = Counter(item.severity for item in validation_results)
    sorted_results = sorted(validation_results, key=lambda item: item.validation_id)
    failures = [item for item in sorted_results if item.status == "FAIL"]
    warnings = [item for item in sorted_results if item.status == "WARNING"]
    return {
        "status": "NOT_EVALUATED" if result is None else result.status,
        "check_count": len(sorted_results),
        "counts_by_status": _sorted_counter(counts_by_status),
        "counts_by_severity": _sorted_counter(counts_by_severity),
        "failures": [_validation_detail(item) for item in failures],
        "warnings": [_validation_detail(item) for item in warnings],
        "results": [_validation_detail(item) for item in sorted_results],
    }


def _validation_detail(item) -> dict[str, Any]:
    return {
        "validation_id": item.validation_id,
        "category": item.category,
        "dataset": item.dataset,
        "variable": item.variable,
        "check_id": item.check_id,
        "description": item.description,
        "status": item.status,
        "severity": item.severity,
        "specification_reference": item.specification_reference,
        "evidence_references": list(item.evidence_references),
        "execution_references": list(item.execution_references),
        "source_references": list(item.source_references),
        "message": item.message,
    }


def _traceability_summary(
    result: EvidenceResolutionResult | None,
) -> dict[str, Any]:
    items = [] if result is None else list(result.items)
    sorted_items = sorted(items, key=lambda item: item.rule_specification_id)
    rendered_items = [_resolved_item(item) for item in sorted_items]
    citations = [
        citation
        for item in sorted_items
        for citation in sorted(item.citations, key=lambda citation: citation.citation_id)
    ]
    return {
        "item_count": len(rendered_items),
        "resolved_item_count": sum(
            1 for item in sorted_items if item.resolution_status == "RESOLVED"
        ),
        "unresolved_item_count": sum(
            1 for item in sorted_items if item.resolution_status != "RESOLVED"
        ),
        "unresolved_evidence_reference_count": sum(
            len(item.unresolved_evidence_references) for item in sorted_items
        ),
        "excluded_evidence_reference_count": sum(
            len(item.excluded_evidence_references) for item in sorted_items
        ),
        "normative_citation_count": sum(
            1 for citation in citations if citation.citation_purpose == "normative"
        ),
        "validation_support_citation_count": sum(
            1
            for citation in citations
            if citation.citation_purpose == "validation_support"
        ),
        "items": rendered_items,
    }


def _resolved_item(item) -> dict[str, Any]:
    return {
        "rule_specification_id": item.rule_specification_id,
        "decision_classification": item.decision_classification,
        "evidence_use": item.evidence_use,
        "resolution_status": item.resolution_status,
        "unresolved_evidence_references": sorted(
            item.unresolved_evidence_references
        ),
        "excluded_evidence_references": sorted(item.excluded_evidence_references),
        "citations": [
            _citation_detail(citation)
            for citation in sorted(item.citations, key=lambda citation: citation.citation_id)
        ],
    }


def _citation_detail(citation) -> dict[str, Any]:
    return {
        "citation_id": citation.citation_id,
        "citation_purpose": citation.citation_purpose,
        "evidence_reference": citation.evidence_reference,
        "source_id": citation.source_id,
        "source_role": citation.source_role,
        "document_title": citation.document_title,
        "official_filename": citation.official_filename,
        "standard_version": citation.standard_version,
        "standard_release_date": citation.standard_release_date,
        "page": citation.page,
        "section": citation.section,
        "table": citation.table,
        "row": citation.row,
        "evidence_type": citation.evidence_type,
        "evidence_text": citation.evidence_text,
        "extraction_status": citation.extraction_status,
        "official_url": citation.official_url,
    }


def _overall_status(validation: dict[str, Any]) -> str:
    if validation["status"] == "NOT_EVALUATED":
        return "NOT_EVALUATED"
    if validation["counts_by_status"].get("FAIL", 0):
        return "FAIL"
    if validation["counts_by_status"].get("WARNING", 0):
        return "PASS_WITH_WARNINGS"
    return "PASS"


def _sorted_counter(counter: Counter) -> dict[str, int]:
    return {key: counter[key] for key in sorted(counter)}


def _to_builtin(value: Any) -> Any:
    if is_dataclass(value):
        return {key: _to_builtin(item) for key, item in asdict(value).items()}
    if isinstance(value, tuple):
        return [_to_builtin(item) for item in value]
    if isinstance(value, list):
        return [_to_builtin(item) for item in value]
    if isinstance(value, dict):
        return {key: _to_builtin(value[key]) for key in sorted(value)}
    return value
