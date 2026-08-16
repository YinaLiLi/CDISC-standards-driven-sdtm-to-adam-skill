"""Render pipeline reports into deterministic text formats."""

from __future__ import annotations

import json
from standards_driven_sdtm_adam.reporting.model import PipelineReport


def render_dict(report: PipelineReport) -> dict[str, Any]:
    """Return the report's deterministic machine-readable representation."""

    return report.to_dict()


def render_json(report: PipelineReport) -> str:
    """Return deterministic JSON for a report."""

    return json.dumps(report.to_dict(), indent=2, sort_keys=True)


def render_markdown(report: PipelineReport) -> str:
    """Return deterministic stakeholder-readable Markdown for a report."""

    payload = report.to_dict()
    lines: list[str] = [
        f"# {payload['title']}",
        "",
        f"Overall status: `{payload['overall_status']}`",
        "",
        "## Preprocessing Operations",
        "",
        "| Target | Operation | Basis |",
        "| --- | --- | --- |",
    ]
    for operation in payload["preprocessing"]["operations"]:
        lines.append(
            _table_row(
                (
                    operation["target"],
                    operation["operation"],
                    operation["basis"],
                )
            )
        )

    lines.extend(
        [
            "",
            "## ADaM Derivation Operations",
            "",
            "| Target | Operation | Basis |",
            "| --- | --- | --- |",
        ]
    )
    for variable in payload["adam"]["variables"]:
        lines.append(
            _table_row(
                (
                    variable["target"],
                    variable["operation"],
                    variable["basis"],
                )
            )
        )

    return "\n".join(lines).rstrip() + "\n"


def _table_row(values: tuple[object, ...]) -> str:
    return "| " + " | ".join(_cell(value) for value in values) + " |"


def _cell(value: object) -> str:
    text = "" if value is None else str(value)
    text = " ".join(text.split())
    return text.replace("|", "\\|")
