# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

EVIDENCE_STAGES = {
    "statistical_observation",
    "forecast",
    "decision",
    "execution",
    "evaluation",
    "parliamentary_process",
    "interpretation",
}


@dataclass(frozen=True)
class EvidenceRef:
    """Traceable reference to one factual element used by ACFPF."""

    id: str
    source_id: str
    stage: str
    kind: str
    title: str
    source_url: str
    date: str | None = None
    period_start: int | None = None
    period_end: int | None = None
    scope: str | None = None
    document_id: str | None = None
    page: str | None = None
    section: str | None = None
    license: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.stage not in EVIDENCE_STAGES:
            raise ValueError(f"Unsupported evidence stage: {self.stage}")
        if not self.id or not self.source_id or not self.title or not self.source_url:
            raise ValueError("Evidence references require id, source_id, title and source_url")

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "stage": self.stage,
            "kind": self.kind,
            "title": self.title,
            "source_url": self.source_url,
            "date": self.date,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "scope": self.scope,
            "document_id": self.document_id,
            "page": self.page,
            "section": self.section,
            "license": self.license,
            "metadata": self.metadata,
        }
