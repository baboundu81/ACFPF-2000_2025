# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from acfpf.data.eurostat import MacroDataset, load_macro_dataset


@dataclass(frozen=True)
class Kpi:
    key: str
    label: str
    value: float
    year: int
    base_value: float | None
    base_year: int | None
    delta: float | None
    unit: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "value": self.value,
            "year": self.year,
            "base_value": self.base_value,
            "base_year": self.base_year,
            "delta": self.delta,
            "unit": self.unit,
        }


@dataclass(frozen=True)
class Dashboard:
    dataset: MacroDataset
    kpis: tuple[Kpi, ...]
    insight: str

    def as_dict(self) -> dict[str, Any]:
        data = self.dataset.as_dict()
        data["kpis"] = [kpi.as_dict() for kpi in self.kpis]
        data["insight"] = self.insight
        data["rows"] = self._table_rows()
        return data

    def _table_rows(self) -> list[dict[str, Any]]:
        years = sorted(
            {
                year
                for series in self.dataset.series.values()
                for year in series.values
            }
        )
        return [
            {
                "year": year,
                **{
                    key: series.values.get(year)
                    for key, series in self.dataset.series.items()
                },
            }
            for year in years
        ]


def _kpi(dataset: MacroDataset, key: str, *, base_year: int = 2000) -> Kpi | None:
    series = dataset.series.get(key)
    if not series or not series.values:
        return None

    latest_year = max(series.values)
    latest_value = series.values[latest_year]
    base_value = series.values.get(base_year)
    delta = round(latest_value - base_value, 1) if base_value is not None else None
    return Kpi(
        key=key,
        label=series.label,
        value=latest_value,
        year=latest_year,
        base_value=base_value,
        base_year=base_year if base_value is not None else None,
        delta=delta,
        unit=series.unit,
    )


def build_dashboard(dataset: MacroDataset) -> Dashboard:
    keys = ("expenditure", "revenue", "balance", "debt")
    kpis = tuple(item for key in keys if (item := _kpi(dataset, key)) is not None)

    expenditure = next((item for item in kpis if item.key == "expenditure"), None)
    revenue = next((item for item in kpis if item.key == "revenue"), None)

    if expenditure and expenditure.delta is not None and revenue and revenue.delta is not None:
        insight = (
            f"Entre {expenditure.base_year} et {expenditure.year}, les dépenses publiques ont "
            f"varié de {expenditure.delta:+.1f} point(s) de PIB, contre "
            f"{revenue.delta:+.1f} point(s) pour les recettes publiques."
        )
    else:
        insight = "Les séries disponibles ne permettent pas encore une comparaison complète avec 2000."

    return Dashboard(dataset=dataset, kpis=kpis, insight=insight)


class MacroService:
    def __init__(self, cache_path: Path | None = None) -> None:
        self.cache_path = cache_path or Path.home() / ".cache" / "acfpf" / "gov_10dd_edpt1.json"

    def dashboard(self, *, refresh: bool = False) -> Dashboard:
        dataset = load_macro_dataset(cache_path=self.cache_path, refresh=refresh)
        return build_dashboard(dataset)
