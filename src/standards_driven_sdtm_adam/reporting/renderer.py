"""Render pipeline reports into deterministic text formats."""

from __future__ import annotations

import json
from typing import Any

from standards_driven_sdtm_adam.reporting.model import PipelineReport


def render_dict(report: PipelineReport) -> dict[str, Any]:
    """Return the report's deterministic machine-readable representation."""

    return report.to_dict()


def render_json(report: PipelineReport) -> str:
    """Return deterministic JSON for a report."""

    return json.dumps(report.to_dict(), indent=2, sort_keys=True)


def render_markdown(report: PipelineReport) -> str:
    """Return deterministic human-readable Markdown for a report."""

    payload = report.to_dict()
    lines: list[str] = [
        f"# {payload['title']}",
        "",
        f"Overall status: `{payload['overall_status']}`",
        "",
        "## Preprocessing Summary",
        "",
        f"- Operations: {payload['preprocessing']['operation_count']}",
    ]
    for operation in payload["preprocessing"]["operations"]:
        target = operation["dataset"]
        if operation["variable"]:
            target += f".{operation['variable']}"
        lines.append(
            "- "
            f"{operation['operation_id']} | {target} | "
            f"{operation['operation']} | {operation['classification']}"
        )

    lines.extend(
        [
            "",
            "## ADaM Derivation Summary",
            "",
            f"- Datasets: {payload['adam']['dataset_count']}",
            f"- Variables: {payload['adam']['variable_count']}",
        ]
    )
    for dataset in payload["adam"]["datasets"]:
        lines.append(
            "- "
            f"{dataset['dataset']} | {dataset['structure']} | "
            f"Sources: {', '.join(dataset['source_domains'])}"
        )
    for variable in payload["adam"]["variables"]:
        lines.append(
            "- "
            f"{variable['specification_id']} | "
            f"{variable['classification']} | "
            f"Sources: {', '.join(variable['source_domains'])}"
        )

    lines.extend(
        [
            "",
            "## Validation Summary",
            "",
            f"- Validation status: {payload['validation']['status']}",
            "",
            "| Status | Count |",
            "| --- | ---: |",
        ]
    )
    for status, count in payload["validation"]["counts_by_status"].items():
        lines.append(f"| {status} | {count} |")
    if payload["validation"]["failures"]:
        lines.extend(["", "### Validation Failures", ""])
        for failure in payload["validation"]["failures"]:
            lines.append(
                "- "
                f"{failure['validation_id']} | {failure['category']} | "
                f"{failure['specification_reference']} | {failure['message']}"
            )

    lines.extend(
        [
            "",
            "## Traceability and Evidence Summary",
            "",
            f"- Traceability items: {payload['traceability']['item_count']}",
            f"- Normative citations: {payload['traceability']['normative_citation_count']}",
            "- Validation/supporting citations: "
            f"{payload['traceability']['validation_support_citation_count']}",
            "",
        ]
    )
    for item in payload["traceability"]["items"]:
        lines.append(
            "### "
            f"{item['rule_specification_id']} "
            f"({item['decision_classification']}, {item['resolution_status']})"
        )
        if item["unresolved_evidence_references"]:
            lines.append(
                f"Unresolved: {', '.join(item['unresolved_evidence_references'])}"
            )
        if item["excluded_evidence_references"]:
            lines.append(
                f"Excluded: {', '.join(item['excluded_evidence_references'])}"
            )
        for citation in item["citations"]:
            locator = _locator(citation)
            lines.append(
                "- "
                f"{citation['citation_purpose']} | "
                f"{citation['source_role']} | "
                f"{citation['source_id']} | "
                f"{citation['document_title']} | "
                f"{locator} | "
                f"{citation['evidence_reference']}"
            )
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _locator(citation: dict[str, Any]) -> str:
    parts: list[str] = []
    if citation["page"] is not None:
        parts.append(f"page {citation['page']}")
    if citation["section"]:
        parts.append(f"section {citation['section']}")
    if citation["table"]:
        parts.append(f"table {citation['table']}")
    if citation["row"]:
        parts.append(f"row {citation['row']}")
    return "; ".join(parts) if parts else "locator unavailable"
