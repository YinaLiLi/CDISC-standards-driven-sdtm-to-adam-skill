"""Structured preprocessing specification models."""

from __future__ import annotations

from dataclasses import dataclass


DECISION_CLASSIFICATIONS = (
    "STANDARD_REQUIRED",
    "STANDARD_GUIDED",
    "STUDY_SPECIFIC",
    "USER_DEFINED",
    "DATA_ENGINEERING",
    "EXAMPLE_ADAPTED",
    "UNSUPPORTED",
)


SUPPORTED_PREPROCESSING_DOMAINS = ("DM", "AE", "LB", "DS", "EX", "SV")


@dataclass(frozen=True)
class PreprocessingOperationSpec:
    """Specification for one proposed source-preserving preprocessing operation."""

    operation_id: str
    dataset: str
    variable: str | None
    operation: str
    purpose: str
    classification: str
    evidence_references: tuple[str, ...]
    source_preserving: bool
    clinical_meaning_changed: bool
    implementation_allowed: bool
    validation_plan: tuple[str, ...]
    notes: tuple[str, ...]


@dataclass(frozen=True)
class PreprocessingSpecification:
    """Complete preprocessing specification response."""

    operations: tuple[PreprocessingOperationSpec, ...]
