"""Read-only SDTM data inspection helpers."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable, Mapping


SUPPORTED_SDTM_DOMAINS = ("DM", "AE", "LB", "DS", "EX", "SV")

RecordsByDomain = Mapping[str, Iterable[Mapping[str, object]]] | Mapping[str, str | Path]


class SDTMDataSnapshot:
    """Read-only snapshot of available SDTM records."""

    def __init__(self, datasets: RecordsByDomain) -> None:
        self._records = _normalize_datasets(datasets)

    @property
    def domains(self) -> tuple[str, ...]:
        return tuple(sorted(self._records))

    def has_domain(self, domain: str) -> bool:
        return domain.upper() in self._records

    def records(self, domain: str) -> tuple[dict[str, object], ...]:
        return self._records.get(domain.upper(), ())

    def variables(self, domain: str) -> tuple[str, ...]:
        variables: set[str] = set()
        for record in self.records(domain):
            variables.update(record)
        return tuple(sorted(variables))

    def has_variable(self, domain: str, variable: str) -> bool:
        return variable in self.variables(domain)

    def record_count(self, domain: str) -> int:
        return len(self.records(domain))

    def subject_ids(self, domain: str) -> set[str]:
        return {
            str(record.get("USUBJID")).strip()
            for record in self.records(domain)
            if _present(record.get("USUBJID"))
        }

    def non_missing_count(self, domain: str, variable: str) -> int:
        return sum(1 for record in self.records(domain) if _present(record.get(variable)))

    def coverage(self, domain: str, variables: Iterable[str]) -> dict[str, object]:
        record_count = self.record_count(domain)
        return {
            variable: {
                "non_missing": self.non_missing_count(domain, variable),
                "record_count": record_count,
            }
            for variable in variables
        }


def _normalize_datasets(datasets: RecordsByDomain) -> dict[str, tuple[dict[str, object], ...]]:
    normalized: dict[str, tuple[dict[str, object], ...]] = {}
    for domain, source in datasets.items():
        domain_key = domain.upper()
        if domain_key not in SUPPORTED_SDTM_DOMAINS:
            continue

        if isinstance(source, (str, Path)):
            normalized[domain_key] = tuple(_read_csv(Path(source)))
        else:
            normalized[domain_key] = tuple(dict(record) for record in source)
    return normalized


def _read_csv(path: Path) -> list[dict[str, object]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _present(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str) and not value.strip():
        return False
    return True
