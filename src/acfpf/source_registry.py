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
        )
        for item in payload["sources"]
    ]
