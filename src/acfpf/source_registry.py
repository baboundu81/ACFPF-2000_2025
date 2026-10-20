# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Source:
    id: str
    name: str
    base_url: str
    priority: str
    themes: tuple[str, ...]
    status: str = "catalogued"
    access: str = "direct"
    license: str | None = None
    evidence_stages: tuple[str, ...] = ()
    data_types: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "base_url": self.base_url,
            "priority": self.priority,
            "themes": list(self.themes),
            "status": self.status,
            "access": self.access,
            "license": self.license,
            "evidence_stages": list(self.evidence_stages),
            "data_types": list(self.data_types),
        }


def load_sources(path: str | Path = "config/sources.yml") -> list[Source]:
    """Charge le registre de sources du projet."""
    with Path(path).open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)

    return [
        Source(
            id=item["id"],
            name=item["name"],
            base_url=item["base_url"],
            priority=item["priority"],
            themes=tuple(item.get("themes", [])),
            status=item.get("status", "catalogued"),
            access=item.get("access", "direct"),
            license=item.get("license"),
            evidence_stages=tuple(item.get("evidence_stages", [])),
            data_types=tuple(item.get("data_types", [])),
        )
        for item in payload["sources"]
    ]


def load_source_map(path: str | Path = "config/sources.yml") -> dict[str, Source]:
    return {source.id: source for source in load_sources(path)}
