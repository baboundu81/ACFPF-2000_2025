# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests

DATASET_CODE = "gov_10dd_edpt1"
API_URL = (
    "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
    f"{DATASET_CODE}"
)
SOURCE_URL = "https://ec.europa.eu/eurostat/databrowser/view/gov_10dd_edpt1/default/table"

INDICATORS = {
    "TE": ("expenditure", "Dépenses publiques"),
    "TR": ("revenue", "Recettes publiques"),
    "B9": ("balance", "Solde public"),
    "GD": ("debt", "Dette publique"),
}


class EurostatError(RuntimeError):
    """Raised when Eurostat data cannot be retrieved or decoded."""


@dataclass(frozen=True)
class MacroSeries:
    key: str
    code: str
    label: str
    source_label: str
    unit: str
    values: dict[int, float]


@dataclass(frozen=True)
class MacroDataset:
    series: dict[str, MacroSeries]
    source_url: str
    dataset_code: str
    updated_at: str | None
    retrieved_at: str
    from_cache: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "dataset_code": self.dataset_code,
            "source_url": self.source_url,
            "updated_at": self.updated_at,
            "retrieved_at": self.retrieved_at,
            "from_cache": self.from_cache,
            "series": {
                key: {
                    "key": item.key,
                    "code": item.code,
                    "label": item.label,
                    "source_label": item.source_label,
                    "unit": item.unit,
                    "values": [
                        {"year": year, "value": value}
                        for year, value in sorted(item.values.items())
                    ],
                }
                for key, item in self.series.items()
            },
        }


def _category_positions(category: dict[str, Any]) -> dict[str, int]:
    index = category.get("index", {})
    if isinstance(index, dict):
        return {str(code): int(position) for code, position in index.items()}
    if isinstance(index, list):
        return {str(code): position for position, code in enumerate(index)}
    raise EurostatError("Unsupported JSON-stat category index format")


def _flat_index(positions: list[int], sizes: list[int]) -> int:
    index = 0
    for position, size in zip(positions, sizes, strict=True):
        index = index * size + position
    return index


def _value_at(values: Any, index: int) -> float | None:
    if isinstance(values, list):
        if index >= len(values):
            return None
        value = values[index]
    elif isinstance(values, dict):
        value = values.get(str(index))
    else:
        raise EurostatError("Unsupported JSON-stat value container")

    if value is None:
        return None
    return float(value)


def parse_macro_payload(payload: dict[str, Any], *, from_cache: bool = False) -> MacroDataset:
    """Decode the Eurostat JSON-stat response into the ACFPF macro model."""
    dimension_ids = list(payload.get("id", []))
    sizes = list(payload.get("size", []))
    dimensions = payload.get("dimension", {})

    if "na_item" not in dimension_ids or "time" not in dimension_ids:
        raise EurostatError("Eurostat response is missing na_item or time dimensions")
    if len(dimension_ids) != len(sizes):
        raise EurostatError("Eurostat response has inconsistent dimensions")

    positions_by_dimension = {
        dim: _category_positions(dimensions[dim]["category"]) for dim in dimension_ids
    }
    labels_by_dimension = {
        dim: dimensions[dim]["category"].get("label", {}) for dim in dimension_ids
    }

    # The API request filters every dimension except na_item and time to one value.
    for dim in dimension_ids:
        if dim not in {"na_item", "time"} and len(positions_by_dimension[dim]) != 1:
            raise EurostatError(f"Unexpected unfiltered dimension: {dim}")

    time_positions = positions_by_dimension["time"]
    item_positions = positions_by_dimension["na_item"]
    raw_values = payload.get("value", {})

    unit_codes = positions_by_dimension.get("unit", {})
    unit_code = next(iter(unit_codes), "")
    unit_label = labels_by_dimension.get("unit", {}).get(unit_code, unit_code)

    result: dict[str, MacroSeries] = {}
    for code, (key, label) in INDICATORS.items():
        if code not in item_positions:
            continue

        series_values: dict[int, float] = {}
        for time_code, time_position in time_positions.items():
            positions: list[int] = []
            for dim in dimension_ids:
                if dim == "na_item":
                    positions.append(item_positions[code])
                elif dim == "time":
                    positions.append(time_position)
                else:
                    positions.append(next(iter(positions_by_dimension[dim].values())))

            value = _value_at(raw_values, _flat_index(positions, sizes))
            if value is not None:
                series_values[int(time_code)] = value

        if series_values:
            source_label = labels_by_dimension["na_item"].get(code, code)
            result[key] = MacroSeries(
                key=key,
                code=code,
                label=label,
                source_label=source_label,
                unit=unit_label,
                values=series_values,
            )

    required = {"expenditure", "revenue", "balance"}
    missing = required.difference(result)
    if missing:
        raise EurostatError(f"Eurostat response is missing required series: {sorted(missing)}")

    return MacroDataset(
        series=result,
        source_url=SOURCE_URL,
        dataset_code=DATASET_CODE,
        updated_at=payload.get("updated"),
        retrieved_at=datetime.now(UTC).isoformat(),
        from_cache=from_cache,
    )


def fetch_macro_payload(
    *, timeout: float = 12.0, session: requests.Session | None = None
) -> dict[str, Any]:
    client = session or requests.Session()
    params = {
        "lang": "EN",
        "geo": "FR",
        "sector": "S13",
        "unit": "PC_GDP",
        "sinceTimePeriod": "2000",
        "untilTimePeriod": "2025",
    }
    try:
        response = client.get(API_URL, params=params, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError) as exc:
        raise EurostatError(f"Unable to retrieve Eurostat dataset {DATASET_CODE}") from exc


def load_macro_dataset(
    *,
    cache_path: Path,
    max_cache_age_seconds: int = 24 * 60 * 60,
    refresh: bool = False,
) -> MacroDataset:
    """Load macro data, preferring a fresh local cache and falling back to stale cache offline."""
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    if cache_path.exists() and not refresh:
        age = datetime.now(UTC).timestamp() - cache_path.stat().st_mtime
        if age <= max_cache_age_seconds:
            return parse_macro_payload(json.loads(cache_path.read_text("utf-8")), from_cache=True)

    try:
        payload = fetch_macro_payload()
        cache_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return parse_macro_payload(payload)
    except EurostatError:
        if cache_path.exists():
            return parse_macro_payload(json.loads(cache_path.read_text("utf-8")), from_cache=True)
        raise
