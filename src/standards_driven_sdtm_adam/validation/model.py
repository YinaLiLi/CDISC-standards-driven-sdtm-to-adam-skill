"""Structured independent validation models."""

from __future__ import annotations

from dataclasses import dataclass


VALIDATION_CATEGORIES = ("STRUCTURAL", "LOGICAL", "TRACEABILITY")
VALIDATION_STATUSES = ("PASS", "FAIL", "WARNING", "NOT_APPLICABLE", "NOT_EVALUATED")
VALIDATION_SEVERITIES = ("ERROR", "WARNING", "INFO")


@dataclass(frozen=True)
class ValidationResult:
    """One independent validation check result."""

    validation_id: str
    category: str
    dataset: str | None
    variable: str | None
    check_id: str
    description: str
    status: str
    severity: str
    expected: object
    observed: object
    specification_reference: str | None
    evidence_references: tuple[str, ...]
    execution_references: tuple[str, ...]
    source_references: tuple[str, ...]
    message: str


@dataclass(frozen=True)
class AdamValidationResult:
    """Complete independent validation response."""

    validation_results: tuple[ValidationResult, ...]
    status: str
