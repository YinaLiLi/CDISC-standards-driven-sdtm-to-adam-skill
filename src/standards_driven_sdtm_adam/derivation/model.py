"""Structured ADaM derivation specification models."""

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

SUPPORTED_ADAM_DATASETS = ("ADSL", "ADAE", "ADLB", "ADTTE")


@dataclass(frozen=True)
class StudyDecision:
    """Structured study-specific decision needed before derivation implementation."""

    decision_id: str
    question: str
    affected_datasets: tuple[str, ...]
    affected_variables: tuple[str, ...]
    required_before_implementation: bool
    status: str
    value: str | None = None


@dataclass(frozen=True)
class AdamDatasetSpecification:
    """Dataset-level ADaM derivation specification."""

    dataset: str
    purpose: str
    structure: str
    source_domains: tuple[str, ...]
    supported_variables: tuple[str, ...]
    evidence_references: tuple[str, ...]
    unresolved_decisions: tuple[str, ...]
    implementation_allowed: bool


@dataclass(frozen=True)
class AdamVariableSpecification:
    """Variable-level ADaM derivation specification."""

    specification_id: str
    dataset: str
    variable: str
    label: str
    purpose: str
    source_domains: tuple[str, ...]
    source_variables: tuple[str, ...]
    derivation_logic: str
    dependencies: tuple[str, ...]
    classification: str
    evidence_references: tuple[str, ...]
    user_defined_inputs: tuple[str, ...]
    assumptions: tuple[str, ...]
    validation_plan: tuple[str, ...]
    implementation_allowed: bool
    unresolved_issues: tuple[str, ...]


@dataclass(frozen=True)
class AdamDerivationSpecification:
    """Complete ADaM derivation specification response."""

    dataset_specs: tuple[AdamDatasetSpecification, ...]
    variable_specs: tuple[AdamVariableSpecification, ...]
    unresolved_decisions: tuple[StudyDecision, ...]
    traceability: dict[str, dict[str, object]]


@dataclass(frozen=True)
class AdamDerivationExecutionRecord:
    """Traceability for one ADaM variable execution attempt."""

    execution_id: str
    specification_id: str
    dataset: str
    variable: str
    classification: str
    source_domains: tuple[str, ...]
    source_variables: tuple[str, ...]
    dependency_executions: tuple[str, ...]
    input_record_count: int
    output_record_count: int
    derived_value_count: int
    status: str
    validation_status: str
    warnings: tuple[str, ...]
    evidence_references: tuple[str, ...]
    study_decision_references: tuple[str, ...]


@dataclass(frozen=True)
class AdamDerivationExecutionResult:
    """ADaM derivation execution response."""

    datasets: dict[str, tuple[dict[str, object], ...]]
    execution_records: tuple[AdamDerivationExecutionRecord, ...]
    status: str
    warnings: tuple[str, ...]
