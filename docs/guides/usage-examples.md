# Usage Examples

These examples use the implemented public APIs. They assume local standards manifests are configured under `config/standards` and local standard files are available where the manifests point.

## Skill Invocation Examples

Use a concrete clinical or analysis question as the objective. Do not require the user to know the ADaM dataset name before feasibility is checked.

```text
Use CDISC Feasibility Checker.

Objective: When and why do subjects discontinue the trial?
Available SDTM: DM, DS, SV, AE, EX, LB.

Check whether this objective is feasible with the available SDTM data. Identify required domains, missing variables, assumptions, and the ADaM outputs needed.
```

```text
Use CDISC SDTM to ADaM.

Objective: Which subjects experienced treatment-emergent adverse events, and how severe were they?
Available SDTM: DM, AE, EX.

First check feasibility, then show the derivation plan before transfer.
```

```text
Use CDISC SDTM to ADaM Transfer.

Objective: How do key lab values change from baseline over scheduled visits?

Use the confirmed feasibility result and derivation plan to derive the supported ADaM outputs, validate them independently, and generate the traceability report.
```

## Registry And Discovery

```python
from standards_driven_sdtm_adam.discovery import StandardsDiscoveryEngine
from standards_driven_sdtm_adam.standards import StandardsRegistry

registry = StandardsRegistry.load("config/standards", validate_integrity=False)
discovery = StandardsDiscoveryEngine(registry)

run = discovery.discover("Create ADSL subject-level analysis dataset")
print([result.standard_id for result in run.results])
```

## Version 1 Pipeline

```python
from standards_driven_sdtm_adam.pipeline import V1Pipeline

sdtm_datasets = {
    "DM": ({"USUBJID": "01"},),
    "AE": ({"USUBJID": "01", "AESTDTC": "2024-01-03"},),
    "LB": ({"USUBJID": "01", "LBTESTCD": "ALT", "LBORRES": "70", "LBSTRESN": "70", "LBDTC": "2024-01-02"},),
    "DS": ({"USUBJID": "01", "DSDECOD": "COMPLETED", "DSSTDTC": "2024-02-01"},),
    "EX": ({"USUBJID": "01", "EXTRT": "A", "EXSTDTC": "2024-01-01", "EXENDTC": "2024-01-14"},),
    "SV": ({"USUBJID": "01", "SVSTDTC": "2024-01-02"},),
}

result = V1Pipeline().run(
    registry_dir="config/standards",
    task_intents=(
        "Create ADSL subject-level analysis dataset",
        "Derive treatment-emergent adverse event variables for ADAE",
        "Plan ADLB laboratory analysis",
        "Identify ADTTE time-to-event evidence",
    ),
    research_objectives=(
        "Evaluate adverse events, laboratory values, and time-to-event outcomes.",
    ),
    sdtm_datasets=sdtm_datasets,
)

print(result.validation.status)
print(result.report.overall_status)
```

Study-specific derivations remain blocked until explicit study decisions are supplied through `study_decisions`.

## Report Rendering

```python
from standards_driven_sdtm_adam.reporting import render_json, render_markdown

print(result.report.to_dict())
print(render_json(result.report))
print(render_markdown(result.report))
```

Reports present supplied pipeline outputs, validation results, and evidence resolution results. They do not perform validation or evidence resolution.

## Developer SHA256 Utility

```python
from standards_driven_sdtm_adam.standards import StandardsRegistry

registry = StandardsRegistry.load("config/standards", validate_integrity=False)
manifest = registry.get("adamig")
digest = registry.calculate_sha256(manifest)
print(digest)
```

SHA256 calculation is Developer Standards Setup work. Runtime users do not need to recompute SHA256 during normal workflow.
