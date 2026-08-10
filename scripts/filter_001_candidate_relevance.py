"""FILTER-001 relevance pass for reconstructed SDTM-to-ADaM candidate rules."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import re
from pathlib import Path
from typing import Any


KEEP_RELEVANT = "KEEP_RELEVANT"
REMOVE_NON_RELEVANT = "REMOVE_NON_RELEVANT"
REVIEW_AMBIGUOUS = "REVIEW_AMBIGUOUS"
FILTER_SCHEMA_VERSION = "filter-001-sdtm-adam-transfer-relevance-v1"

RELEVANT_STRUCTURED_FIELDS = (
    "dataset_scope",
    "structure_scope",
    "variable_scope",
    "expected_outputs",
    "required_inputs",
    "keys",
    "validation_requirements",
)
RELEVANT_TEXT_REASONS = (
    (
        "traceability_origin_lineage",
        (
            "traceability",
            "traceable",
            "origin",
            "lineage",
            "source / deriv",
            "source/deriv",
            "predecessor",
            "source record",
            "source data",
            "srcdom",
            "srcvar",
            "srcseq",
        ),
    ),
    (
        "mapping_derivation_calculation",
        (
            "mapping",
            "mapped",
            "derive",
            "derived",
            "derivation",
            "calculation",
            "algorithm",
            "impute",
            "imputation",
            "analysis day",
            "aval",
            "avalc",
            "chg",
            "change from baseline",
        ),
    ),
    (
        "baseline_treatment_datetime",
        (
            "baseline",
            "treatment",
            "on treatment",
            "date",
            "time",
            "datetime",
            "analysis visit",
            "avisit",
            "ady",
            "trtsdt",
            "trtedt",
        ),
    ),
    (
        "event_or_censor_logic",
        (
            "event",
            "censor",
            "cnsr",
            "time to",
            "tte",
            "adverse event",
            "ae",
        ),
    ),
    (
        "specification_or_study_decision",
        (
            "specification",
            "metadata",
            "parameter",
            "paramcd",
            "study decision",
            "sap",
            "selection criteria",
            "population flag",
            "analysis dataset creation",
        ),
    ),
    (
        "sdtm_source_or_adam_output",
        (
            "sdtm",
            "adam",
            "adsl",
            "adae",
            "adlb",
            "adtte",
            "bds",
            "occds",
            "analysis dataset",
            "domain",
        ),
    ),
    (
        "transfer_validation_or_conformance",
        (
            "validation",
            "validate",
            "conformance",
            "nonconformant",
            "required",
            "must be present",
            "must be populated",
            "one record per",
            "key variable",
        ),
    ),
    (
        "controlled_terminology",
        (
            "controlled terminology",
            "codelist",
            "controlled terms",
            "valid values",
            "code",
            "decode",
        ),
    ),
)
NON_RELEVANT_PATTERNS = (
    ("document_noise_header_footer_page_date", ("all rights reserved", "page ", "final ", "copyright")),
    ("legal_patent_license_disclaimer", ("patent", "license", "disclaimer", "legal", "trademark")),
    (
        "publication_management",
        (
            "table of contents",
            "acknowledgement",
            "acknowledgment",
            "revision history",
            "bibliography",
            "references",
            "cdisc organization",
            "standards publication",
        ),
    ),
)
PURE_ANALYSIS_TERMS = (
    "exploratory data analysis",
    "machine learning",
    "dashboard",
    "visualization",
    "interpretation of results",
    "model statement",
    "p-value",
)
NON_RELEVANT_REASON_TERMS = {reason: needles for reason, needles in NON_RELEVANT_PATTERNS}


def classify_rule(
    rule: dict[str, Any],
    *,
    seen_fingerprints: set[str],
    seen_semantic_fingerprints: set[str] | None = None,
) -> dict[str, str]:
    """Classify one candidate into exactly one FILTER-001 decision."""

    fingerprint = _candidate_fingerprint(rule)
    if fingerprint in seen_fingerprints:
        return {"decision": REMOVE_NON_RELEVANT, "reason": "exact_extraction_duplicate"}
    seen_fingerprints.add(fingerprint)
    semantic_fingerprint = _semantic_duplicate_fingerprint(rule)
    if semantic_fingerprint and seen_semantic_fingerprints is not None:
        if semantic_fingerprint in seen_semantic_fingerprints:
            return {"decision": REMOVE_NON_RELEVANT, "reason": "semantic_duplicate_requirement"}
        seen_semantic_fingerprints.add(semantic_fingerprint)

    text = _rule_text(rule)
    standard_id = str(rule.get("standard_id") or "").lower()
    rule_type = str(rule.get("rule_type") or "").upper()
    source_section = str(rule.get("source_section_classification") or "").upper()

    if _is_define_xml_or_regulatory_only(standard_id, text):
        return {"decision": REMOVE_NON_RELEVANT, "reason": "define_xml_or_regulatory_only"}
    if _is_pure_analysis_only(text):
        return {"decision": REMOVE_NON_RELEVANT, "reason": "pure_analysis_or_results_interpretation"}
    if source_section in {"FRONT_MATTER", "REVISION_HISTORY", "SUBMISSION_CONTEXT"} or rule_type in {
        "FRONT_MATTER",
        "REVISION_HISTORY",
    }:
        return {"decision": REMOVE_NON_RELEVANT, "reason": "document_publication_management"}
    if _is_publication_management_record(rule, text):
        return {"decision": REMOVE_NON_RELEVANT, "reason": "publication_management"}
    primary_text = _primary_rule_text(rule)
    if _is_page_stamp_noise(primary_text):
        return {"decision": REMOVE_NON_RELEVANT, "reason": "document_noise_header_footer_page_date"}
    if _contains_any(primary_text, NON_RELEVANT_REASON_TERMS["legal_patent_license_disclaimer"]):
        return {"decision": REMOVE_NON_RELEVANT, "reason": "legal_patent_license_disclaimer"}
    for reason, needles in NON_RELEVANT_PATTERNS:
        if _non_relevant_only(text, needles):
            return {"decision": REMOVE_NON_RELEVANT, "reason": reason}
    if _is_example_only_atomic_requirement(rule):
        return {"decision": REVIEW_AMBIGUOUS, "reason": "example_only_atomic_requirement"}
    if "example" in standard_id or source_section == "EXAMPLE" or rule_type == "EXAMPLE":
        return {"decision": REVIEW_AMBIGUOUS, "reason": "example_may_contain_derivation_logic"}
    for reason, needles in RELEVANT_TEXT_REASONS:
        if reason == "traceability_origin_lineage" and _contains_any(text, needles):
            return {"decision": KEEP_RELEVANT, "reason": reason}
    if _has_structured_relevance(rule):
        return {"decision": KEEP_RELEVANT, "reason": _structured_relevance_reason(rule)}
    if rule.get("conformance_metadata") or standard_id == "adam-conformance-rules":
        return {"decision": KEEP_RELEVANT, "reason": "transfer_validation_or_conformance"}

    for reason, needles in RELEVANT_TEXT_REASONS:
        if _contains_any(text, needles):
            return {"decision": KEEP_RELEVANT, "reason": reason}
    if source_section == "CONTROLLED_TERMINOLOGY" or rule_type == "CONTROLLED_TERMINOLOGY":
        return {"decision": KEEP_RELEVANT, "reason": "controlled_terminology"}

    return {"decision": REVIEW_AMBIGUOUS, "reason": "conversion_relevance_uncertain"}


def apply_filter(rule_catalog: str | Path, *, audit_root: str | Path | None = None) -> dict[str, Any]:
    """Overwrite canonical rule shards with KEEP and REVIEW_AMBIGUOUS candidates."""

    catalog = Path(rule_catalog)
    audit_dir = Path(audit_root) if audit_root else catalog.parent / "filter_001"
    audit_dir.mkdir(parents=True, exist_ok=True)
    seen_fingerprints: set[str] = set()
    seen_semantic_fingerprints: set[str] = set()
    summary = {
        "schema_version": FILTER_SCHEMA_VERSION,
        "filter_id": "FILTER-001",
        "created_at": _utc_now(),
        "before": 0,
        KEEP_RELEVANT: 0,
        REMOVE_NON_RELEVANT: 0,
        REVIEW_AMBIGUOUS: 0,
        "after": 0,
        "remove_reasons": Counter(),
        "keep_reasons": Counter(),
        "ambiguous_reasons": Counter(),
        "shards": [],
    }
    removed: list[dict[str, Any]] = []
    ambiguous: list[dict[str, Any]] = []

    for shard_path in sorted(path for path in catalog.glob("*.json") if path.name != "index.json"):
        payload = json.loads(shard_path.read_text(encoding="utf-8"))
        retained_rules = []
        before_count = len(payload.get("rules") or [])
        shard_counts = Counter()
        for rule in payload.get("rules") or []:
            decision = classify_rule(
                rule,
                seen_fingerprints=seen_fingerprints,
                seen_semantic_fingerprints=seen_semantic_fingerprints,
            )
            retained_rule = dict(rule)
            retained_rule.pop("filter_001", None)
            summary["before"] += 1
            summary[decision["decision"]] += 1
            shard_counts[decision["decision"]] += 1
            if decision["decision"] == REMOVE_NON_RELEVANT:
                summary["remove_reasons"][decision["reason"]] += 1
                removed.append(_audit_record(rule, decision, shard_path))
                continue
            if decision["decision"] == KEEP_RELEVANT:
                summary["keep_reasons"][decision["reason"]] += 1
            else:
                summary["ambiguous_reasons"][decision["reason"]] += 1
                ambiguous.append(_audit_record(rule, decision, shard_path))
            retained_rules.append(retained_rule)

        payload["rules"] = retained_rules
        shard_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        summary["after"] += len(retained_rules)
        summary["shards"].append(
            {
                "file": shard_path.name,
                "before": before_count,
                KEEP_RELEVANT: shard_counts[KEEP_RELEVANT],
                REMOVE_NON_RELEVANT: shard_counts[REMOVE_NON_RELEVANT],
                REVIEW_AMBIGUOUS: shard_counts[REVIEW_AMBIGUOUS],
                "after": len(retained_rules),
            }
        )

    summary["remove_reasons"] = dict(sorted(summary["remove_reasons"].items()))
    summary["keep_reasons"] = dict(sorted(summary["keep_reasons"].items()))
    summary["ambiguous_reasons"] = dict(sorted(summary["ambiguous_reasons"].items()))
    _write_audit_files(audit_dir, summary, removed, ambiguous)
    _rewrite_index(catalog)
    return summary


def _has_structured_relevance(rule: dict[str, Any]) -> bool:
    if rule.get("grain") or rule.get("validation_requirement"):
        return True
    return any(bool(rule.get(field)) for field in RELEVANT_STRUCTURED_FIELDS)


def _structured_relevance_reason(rule: dict[str, Any]) -> str:
    if rule.get("structure_scope") or rule.get("grain") or rule.get("keys"):
        return "dataset_structure_name_label_grain_keys"
    if rule.get("variable_scope") or rule.get("validation_requirement") or rule.get("validation_requirements"):
        return "variable_requirement_or_applicability"
    if rule.get("required_inputs"):
        return "sdtm_source_input"
    if rule.get("expected_outputs") or rule.get("dataset_scope"):
        return "adam_output"
    return "specification_or_study_decision"


def _is_define_xml_or_regulatory_only(standard_id: str, text: str) -> bool:
    define_signal = "define-xml" in standard_id or "define-xml" in text or "define.xml" in text
    regulatory_signal = "regulatory certification" in text or "submission metadata" in text
    transfer_signal = any(
        _contains_any(text, needles)
        for reason, needles in RELEVANT_TEXT_REASONS
        if reason
        in {
            "traceability_origin_lineage",
            "mapping_derivation_calculation",
            "baseline_treatment_datetime",
            "event_or_censor_logic",
            "sdtm_source_or_adam_output",
            "transfer_validation_or_conformance",
            "controlled_terminology",
        }
    )
    return (define_signal or regulatory_signal) and not transfer_signal


def _is_pure_analysis_only(text: str) -> bool:
    if not _contains_any(text, PURE_ANALYSIS_TERMS):
        return False
    return not any(_contains_any(text, needles) for _, needles in RELEVANT_TEXT_REASONS)


def _is_publication_management_record(rule: dict[str, Any], text: str) -> bool:
    primary = _primary_rule_text(rule)
    if "appendix" in primary and "glossary" in primary and "abbreviations" in primary:
        return True
    if "viewed " in primary and ("http://" in primary or "https://" in primary):
        return True
    return False


def _primary_rule_text(rule: dict[str, Any]) -> str:
    return re.sub(
        r"\s+",
        " ",
        " ".join(
            str(rule.get(field) or "")
            for field in ("normalized_atomic_requirement", "required_behavior", "validation_requirement")
        ),
    ).strip().lower()


def _is_page_stamp_noise(primary_text: str) -> bool:
    if not _contains_any(primary_text, NON_RELEVANT_REASON_TERMS["document_noise_header_footer_page_date"]):
        return False
    return bool(
        re.fullmatch(
            r".*all rights reserved\s+page\s+\d+\s+final\s+[a-z]+\s+\d{1,2},\s+\d{4}.*",
            primary_text,
        )
    )


def _is_example_only_atomic_requirement(rule: dict[str, Any]) -> bool:
    requirement = re.sub(
        r"\s+",
        " ",
        str(rule.get("normalized_atomic_requirement") or rule.get("required_behavior") or ""),
    ).strip().lower()
    return requirement.startswith(("for example,", "for example ", "e.g.,", "for instance,"))


def _non_relevant_only(text: str, needles: tuple[str, ...]) -> bool:
    if not _contains_any(text, needles):
        return False
    return not any(_contains_any(text, relevant) for _, relevant in RELEVANT_TEXT_REASONS)


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)


def _rule_text(rule: dict[str, Any]) -> str:
    values = [
        rule.get("normalized_atomic_requirement"),
        rule.get("required_behavior"),
        rule.get("validation_requirement"),
        rule.get("exact_source_excerpt"),
        " ".join(str(item) for item in rule.get("applicability_conditions") or []),
        " ".join(str(item) for item in rule.get("permitted_variations") or []),
        " ".join(str(item) for item in rule.get("prohibited_behavior") or []),
        " ".join(str(item) for item in rule.get("validation_requirements") or []),
    ]
    return re.sub(r"\s+", " ", " ".join(str(value or "") for value in values)).strip().lower()


def _candidate_fingerprint(rule: dict[str, Any]) -> str:
    identity = {
        "standard_id": rule.get("standard_id"),
        "source_hash": rule.get("source_hash"),
        "locator": rule.get("evidence_locator") or {},
        "requirement": rule.get("normalized_atomic_requirement") or rule.get("required_behavior"),
        "excerpt": rule.get("exact_source_excerpt"),
    }
    return hashlib.sha256(json.dumps(identity, sort_keys=True).encode("utf-8")).hexdigest()


def _semantic_duplicate_fingerprint(rule: dict[str, Any]) -> str | None:
    if str(rule.get("rule_type") or "").upper() != "CONFORMANCE_RULE" and not rule.get("conformance_metadata"):
        return None
    requirement = _normalized_requirement(rule)
    if not requirement:
        return None
    official_rule_identifier = _official_rule_identifier(rule)
    if official_rule_identifier:
        identity = {
            "standard_id": rule.get("standard_id"),
            "official_rule_identifier": official_rule_identifier,
            "requirement": requirement,
            "dataset_scope": _normalized_scope_values(rule, "dataset_scope", "datasets"),
            "variable_scope": _normalized_scope_values(rule, "variable_scope", "variables"),
        }
        return hashlib.sha256(json.dumps(identity, sort_keys=True).encode("utf-8")).hexdigest()
    identity = {
        "standard_id": rule.get("standard_id"),
        "rule_type": rule.get("rule_type"),
        "requirement": requirement,
        "dataset_scope": _normalized_scope_values(rule, "dataset_scope", "datasets"),
        "variable_scope": _normalized_scope_values(rule, "variable_scope", "variables"),
        "structure_scope": _normalized_scope_values(rule, "structure_scope", "structures"),
    }
    return hashlib.sha256(json.dumps(identity, sort_keys=True).encode("utf-8")).hexdigest()


def _official_rule_identifier(rule: dict[str, Any]) -> str:
    value = (rule.get("conformance_metadata") or {}).get("official_rule_identifier")
    if not value:
        value = (rule.get("evidence_locator") or {}).get("official_rule_identifier")
    return re.sub(r"\s+", " ", str(value or "")).strip().lower()


def _normalized_requirement(rule: dict[str, Any]) -> str:
    text = str(
        rule.get("normalized_atomic_requirement")
        or rule.get("validation_requirement")
        or rule.get("required_behavior")
        or ""
    )
    return re.sub(r"\s+", " ", text).strip().lower()


def _normalized_scope_values(rule: dict[str, Any], field: str, scope_field: str) -> list[str]:
    values = rule.get(field)
    if not values:
        values = (rule.get("scope") or {}).get(field) or (rule.get("scope") or {}).get(scope_field)
    if not values:
        return []
    if not isinstance(values, list):
        values = [values]
    return sorted({re.sub(r"\s+", " ", str(value)).strip().lower() for value in values if str(value).strip()})


def _audit_record(rule: dict[str, Any], decision: dict[str, str], shard_path: Path) -> dict[str, Any]:
    return {
        "rule_id": rule.get("rule_id"),
        "standard_id": rule.get("standard_id"),
        "shard": shard_path.name,
        "decision": decision["decision"],
        "reason": decision["reason"],
        "source_section_classification": rule.get("source_section_classification"),
        "rule_type": rule.get("rule_type"),
        "normalized_atomic_requirement": rule.get("normalized_atomic_requirement"),
        "citation_status": _citation_status(rule),
    }


def _citation_status(rule: dict[str, Any]) -> str:
    locator = rule.get("evidence_locator") or {}
    if rule.get("source_hash") and rule.get("local_relative_source_path") and locator.get("source_binding_status"):
        return "RESOLVED"
    return "UNRESOLVED"


def _write_audit_files(
    audit_dir: Path,
    summary: dict[str, Any],
    removed: list[dict[str, Any]],
    ambiguous: list[dict[str, Any]],
) -> None:
    (audit_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    (audit_dir / "removed_candidates.json").write_text(
        json.dumps({"schema_version": FILTER_SCHEMA_VERSION, "removed_count": len(removed), "candidates": removed}, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (audit_dir / "ambiguous_candidates.json").write_text(
        json.dumps(
            {"schema_version": FILTER_SCHEMA_VERSION, "ambiguous_count": len(ambiguous), "candidates": ambiguous},
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    readme = _summary_markdown(summary)
    (audit_dir / "README.md").write_text(readme, encoding="utf-8")


def _summary_markdown(summary: dict[str, Any]) -> str:
    remove_lines = "\n".join(
        f"- `{reason}`: {count}" for reason, count in summary["remove_reasons"].items()
    ) or "- none"
    keep_lines = "\n".join(f"- `{reason}`: {count}" for reason, count in summary["keep_reasons"].items()) or "- none"
    ambiguous_lines = "\n".join(
        f"- `{reason}`: {count}" for reason, count in summary["ambiguous_reasons"].items()
    ) or "- none"
    shard_lines = "\n".join(
        "| {file} | {before} | {keep} | {remove} | {ambiguous} | {after} |".format(
            file=shard["file"],
            before=shard["before"],
            keep=shard[KEEP_RELEVANT],
            remove=shard[REMOVE_NON_RELEVANT],
            ambiguous=shard[REVIEW_AMBIGUOUS],
            after=shard["after"],
        )
        for shard in summary["shards"]
    )
    return f"""# FILTER-001 SDTM-to-ADaM Transfer Relevance Filter

FILTER-001 was applied to all canonical reconstructed candidate rules. The pass classifies every candidate as `KEEP_RELEVANT`, `REMOVE_NON_RELEVANT`, or `REVIEW_AMBIGUOUS`. `REVIEW_AMBIGUOUS` candidates remain in the canonical rule catalog.

## Counts

- Before: {summary["before"]}
- KEEP_RELEVANT: {summary[KEEP_RELEVANT]}
- REMOVE_NON_RELEVANT: {summary[REMOVE_NON_RELEVANT]}
- REVIEW_AMBIGUOUS: {summary[REVIEW_AMBIGUOUS]}
- After: {summary["after"]}

## KEEP_RELEVANT Reasons

{keep_lines}

## REMOVE_NON_RELEVANT Reasons

{remove_lines}

## REVIEW_AMBIGUOUS Reasons

{ambiguous_lines}

## Shards

| Shard | Before | KEEP | REMOVE | AMBIGUOUS | After |
|---|---:|---:|---:|---:|---:|
{shard_lines}
"""


def _rewrite_index(catalog: Path) -> None:
    shards = []
    for shard_path in sorted(path for path in catalog.glob("*.json") if path.name != "index.json"):
        text = shard_path.read_text(encoding="utf-8")
        payload = json.loads(text)
        rules = payload.get("rules") or []
        resolved = sum(1 for rule in rules if rule.get("classification_status") == "RESOLVED")
        standard_versions = [rule.get("standard_version") for rule in rules if rule.get("standard_version")]
        standard_ids = [rule.get("standard_id") for rule in rules if rule.get("standard_id")]
        shards.append(
            {
                "file_path": f"knowledge/v1/rule_catalog/{shard_path.name}",
                "standard_id": standard_ids[0] if standard_ids else shard_path.stem,
                "standard_version": standard_versions[0] if standard_versions else None,
                "candidate_count": len(rules),
                "resolved_count": resolved,
                "unresolved_count": len(rules) - resolved,
                "content_hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            }
        )
    (catalog / "index.json").write_text(json.dumps({"shards": shards}, indent=2, sort_keys=True), encoding="utf-8")


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--rule-catalog",
        default="knowledge/v1/rule_catalog",
        help="Canonical reconstructed rule catalog directory to overwrite.",
    )
    parser.add_argument(
        "--audit-root",
        default="knowledge/v1/filter_001",
        help="FILTER-001 audit output directory.",
    )
    args = parser.parse_args()
    summary = apply_filter(args.rule_catalog, audit_root=args.audit_root)
    print(f"before={summary['before']}")
    print(f"KEEP_RELEVANT={summary[KEEP_RELEVANT]}")
    print(f"REMOVE_NON_RELEVANT={summary[REMOVE_NON_RELEVANT]}")
    print(f"REVIEW_AMBIGUOUS={summary[REVIEW_AMBIGUOUS]}")
    print(f"after={summary['after']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
