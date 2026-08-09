from pathlib import Path

from standards_driven_sdtm_adam.discovery import StandardsDiscoveryEngine
from standards_driven_sdtm_adam.pipeline import V1Pipeline
from standards_driven_sdtm_adam.reporting import render_json, render_markdown
from standards_driven_sdtm_adam.standards import StandardsRegistry


ROOT = Path(__file__).resolve().parents[2]


def _doc_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_documented_public_imports_exist():
    assert StandardsRegistry is not None
    assert StandardsDiscoveryEngine is not None
    assert V1Pipeline is not None
    assert callable(render_json)
    assert callable(render_markdown)


def test_readme_documents_current_v1_scope_without_scaffold_text():
    readme = _doc_text("README.md")

    assert "Placeholder" not in readme
    assert "ADSL" in readme
    assert "ADAE" in readme
    assert "ADLB" in readme
    assert "ADTTE" in readme
    assert "Raw -> SDTM" in readme
    assert "regulatory certification" in readme


def test_docs_do_not_present_developer_setup_as_runtime_workflow():
    combined = "\n".join(
        _doc_text(path)
        for path in (
            "README.md",
            "docs/architecture/overview.md",
            "skills/cdisc-sdtm-to-adam/SKILL.md",
        )
    )

    development_phase_label = "mile" + "stone"
    assert development_phase_label not in combined.lower()
    assert "10.5." not in combined
    assert "10.6." not in combined
    assert "Runtime users do not perform standards intake" in combined
