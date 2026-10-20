# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from acfpf.data.cofog import CofogDataset, load_cofog_dataset


@dataclass(frozen=True)
class CofogChange:
    code: str
    label: str
    base_year: int
    base_value: float
    latest_year: int
    latest_value: float
    delta: float
    unit: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "label": self.label,
            "base_year": self.base_year,
            "base_value": self.base_value,
            "latest_year": self.latest_year,
            "latest_value": self.latest_value,
            "delta": self.delta,
            "unit": self.unit,
        }


@dataclass(frozen=True)
class CofogAnalysis:
    dataset: CofogDataset
    changes: tuple[CofogChange, ...]

    @property
    def increases(self) -> tuple[CofogChange, ...]:
        return tuple(sorted((item for item in self.changes if item.delta > 0), key=lambda x: x.delta, reverse=True))

    @property
    def decreases(self) -> tuple[CofogChange, ...]:
        return tuple(sorted((item for item in self.changes if item.delta < 0), key=lambda x: x.delta))

    def as_dict(self) -> dict[str, Any]:
        data = self.dataset.as_dict()
        data["changes"] = [item.as_dict() for item in self.changes]
        data["increases"] = [item.as_dict() for item in self.increases]
        data["decreases"] = [item.as_dict() for item in self.decreases]
        data["interpretation_note"] = (
            "Une baisse en points de PIB décrit une baisse de poids relatif dans l'économie ; "
            "elle ne prouve pas à elle seule une économie en euros courants ou constants."
        )
        return data


def build_cofog_analysis(dataset: CofogDataset, *, base_year: int = 2000) -> CofogAnalysis:
    changes: list[CofogChange] = []
    for series in dataset.series.values():
        if base_year not in series.values:
            continue
        latest_year = max(series.values)
        changes.append(
            CofogChange(
                code=series.code,
                label=series.label,
                base_year=base_year,
                base_value=series.values[base_year],
                latest_year=latest_year,
                latest_value=series.values[latest_year],
                delta=round(series.values[latest_year] - series.values[base_year], 1),
                unit=series.unit,
            )
        )
    return CofogAnalysis(dataset=dataset, changes=tuple(sorted(changes, key=lambda x: x.code)))


class CofogService:
    def __init__(self, cache_path: Path | None = None) -> None:
        self.cache_path = cache_path or Path.home() / ".cache" / "acfpf" / "cofog_fr_pc_gdp_v1.json"

    def analysis(self, *, refresh: bool = False) -> CofogAnalysis:
        return build_cofog_analysis(
            load_cofog_dataset(cache_path=self.cache_path, refresh=refresh)
        )
