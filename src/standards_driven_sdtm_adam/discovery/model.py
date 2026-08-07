"""Structured discovery result models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DiscoveryResult:
    """Potentially relevant standard for a requested task."""

    standard_id: str
    title: str
    version: str | None
    scope_category: str
    relevance_reason: str
    local_path: str | None
    availability_status: str


@dataclass(frozen=True)
class DiscoveryRun:
    """Complete standards discovery response."""

    task_intent: str
    results: tuple[DiscoveryResult, ...]
    excluded_future_scope: tuple[DiscoveryResult, ...] = ()
    upstream_only: bool = False
    no_applicable_standard: bool = False
