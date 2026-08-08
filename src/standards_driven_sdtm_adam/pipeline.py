"""Version 1 orchestration facade for end-to-end validation."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from standards_driven_sdtm_adam.derivation import (
    AdamDerivationEngine,
    AdamDerivationExecutionResult,
    AdamDerivationSpecification,
    AdamDerivationSpecifier,
    StudyDecision,
)
from standards_driven_sdtm_adam.discovery import DiscoveryRun, StandardsDiscoveryEngine
from standards_driven_sdtm_adam.extraction import EvidenceRecord, RuleExtractionRun
from standards_driven_sdtm_adam.extraction import RuleExtractionEngine
from standards_driven_sdtm_adam.feasibility import FeasibilityAssessment, FeasibilityAssessor
from standards_driven_sdtm_adam.preprocessing.execution import (
    PreprocessingExecutionEngine,
    PreprocessingExecutionResult,
)
from standards_driven_sdtm_adam.preprocessing.model import PreprocessingSpecification
from standards_driven_sdtm_adam.preprocessing.specifier import PreprocessingSpecifier
from standards_driven_sdtm_adam.reporting import (
    PipelineReport,
    ReportBuilder,
    render_json,
    render_markdown,
)
from standards_driven_sdtm_adam.standards import (
    StandardsRegistry,
    acquire_required_standards,
    manual_setup_lines,
    plan_required_standards_for_tasks,
)
from standards_driven_sdtm_adam.standards.errors import StandardsRegistryError
from standards_driven_sdtm_adam.traceability import (
    DecisionEvidenceRequest,
    EvidenceResolutionResult,
    EvidenceResolver,
)
from standards_driven_sdtm_adam.validation import AdamValidationEngine, AdamValidationResult


RecordsByDomain = Mapping[str, Iterable[Mapping[str, object]]]


@dataclass(frozen=True)
class V1PipelineResult:
    """Auditable outputs from every Version 1 pipeline stage."""

    registry: StandardsRegistry
    discovery_runs: tuple[DiscoveryRun, ...]
    rule_extraction: RuleExtractionRun
    feasibility: FeasibilityAssessment
    preprocessing_specification: PreprocessingSpecification
    preprocessing_execution: PreprocessingExecutionResult
    adam_specification: AdamDerivationSpecification
    adam_execution: AdamDerivationExecutionResult
    validation: AdamValidationResult
    evidence_resolution: EvidenceResolutionResult
    report: PipelineReport
    markdown_report: str
    json_report: str


class V1Pipeline:
    """Sequence existing Version 1 components without adding domain logic."""

    def run(
        self,
        *,
        registry_dir: str | Path,
        task_intents: Iterable[str],
        research_objectives: Iterable[str],
        sdtm_datasets: RecordsByDomain,
        study_decisions: Iterable[StudyDecision] = (),
        requested_preprocessing_operations: Iterable[str] = (),
        requested_variables: Iterable[str] = (),
        evidence_resolution_requests: Iterable[DecisionEvidenceRequest] = (),
        standards_acquisition_downloader: Any | None = None,
        adam_specification_transform: Callable[
            [AdamDerivationSpecification], AdamDerivationSpecification
        ]
        | None = None,
    ) -> V1PipelineResult:
        """Run the v1 workflow and expose each intermediate result."""

        registry = StandardsRegistry.load(registry_dir, validate_integrity=False)
        task_intents = tuple(task_intents)
        if standards_acquisition_downloader is not None:
            plan = plan_required_standards_for_tasks(
                registry,
                task_intents=task_intents,
            )
            acquisition = acquire_required_standards(
                plan.registry,
                standards_acquisition_downloader,
            )
            if acquisition.manual_setup_required:
                details = " ".join(manual_setup_lines(acquisition))
                raise StandardsRegistryError(
                    f"Required CDISC standards are unavailable after acquisition. {details}"
                )

        study_decisions = tuple(study_decisions)

        discovery_engine = StandardsDiscoveryEngine(registry)
        discovery_runs = tuple(discovery_engine.discover(intent) for intent in task_intents)

        extraction_engine = RuleExtractionEngine(registry)
        extraction_runs = tuple(extraction_engine.extract(intent) for intent in task_intents)
        rule_extraction = _combine_extraction_runs(task_intents, extraction_runs)

        feasibility = FeasibilityAssessor().assess(
            tuple(research_objectives),
            sdtm_datasets,
            evidence_references=tuple(record.evidence_id for record in rule_extraction.evidence),
        )

        preprocessing_specification = PreprocessingSpecifier().specify(
            sdtm_datasets,
            feasibility,
            discovery_runs,
            rule_extraction.evidence,
            requested_operations=requested_preprocessing_operations,
        )
        preprocessing_execution = PreprocessingExecutionEngine().execute(
            sdtm_datasets,
            preprocessing_specification,
        )

        adam_specification = AdamDerivationSpecifier().specify(
            preprocessing_execution.processed_datasets,
            feasibility,
            discovery_runs,
            rule_extraction.evidence,
            study_decisions=study_decisions,
            requested_variables=requested_variables,
        )
        if adam_specification_transform is not None:
            adam_specification = adam_specification_transform(adam_specification)

        adam_execution = AdamDerivationEngine().execute(
            preprocessing_execution.processed_datasets,
            adam_specification,
            study_decisions=study_decisions,
        )

        validation = AdamValidationEngine().validate(
            source_sdtm_datasets=sdtm_datasets,
            preprocessed_datasets=preprocessing_execution.processed_datasets,
            preprocessing_specification=preprocessing_specification,
            preprocessing_execution_records=preprocessing_execution.execution_records,
            adam_specification=adam_specification,
            adam_datasets=adam_execution.datasets,
            derivation_execution_records=adam_execution.execution_records,
            evidence=rule_extraction.evidence,
            study_decisions=study_decisions,
        )

        evidence_items = tuple(adam_specification.variable_specs) + tuple(
            evidence_resolution_requests
        )
        evidence_resolution = EvidenceResolver(registry).resolve(
            evidence_items,
            rule_extraction,
        )

        report = ReportBuilder().build(
            preprocessing_specification=preprocessing_specification,
            adam_derivation_specification=adam_specification,
            validation_result=validation,
            evidence_resolution_result=evidence_resolution,
        )

        return V1PipelineResult(
            registry=registry,
            discovery_runs=discovery_runs,
            rule_extraction=rule_extraction,
            feasibility=feasibility,
            preprocessing_specification=preprocessing_specification,
            preprocessing_execution=preprocessing_execution,
            adam_specification=adam_specification,
            adam_execution=adam_execution,
            validation=validation,
            evidence_resolution=evidence_resolution,
            report=report,
            markdown_report=render_markdown(report),
            json_report=render_json(report),
        )


def _combine_extraction_runs(
    task_intents: tuple[str, ...],
    runs: tuple[RuleExtractionRun, ...],
) -> RuleExtractionRun:
    records_by_id: dict[str, EvidenceRecord] = {}
    for record in sorted(
        (record for run in runs for record in run.evidence),
        key=lambda item: (item.standard_id, item.evidence_id, item.search_context),
    ):
        records_by_id.setdefault(record.evidence_id, record)
    evidence = tuple(records_by_id[key] for key in sorted(records_by_id))
    return RuleExtractionRun(
        task_intent=" | ".join(task_intents),
        evidence=evidence,
        no_relevant_evidence=not evidence,
    )
