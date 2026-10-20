# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests

API_BASE_URL = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"
CACHE_SCHEMA_VERSION = 2

MAIN_DATASET_CODE = "gov_10a_main"
MAIN_SOURCE_URL = "https://ec.europa.eu/eurostat/databrowser/view/gov_10a_main/default/table"
DEBT_DATASET_CODE = "gov_10dd_edpt1"
DEBT_SOURCE_URL = "https://ec.europa.eu/eurostat/databrowser/view/gov_10dd_edpt1/default/table"

MAIN_INDICATORS = {
    "TE": ("expenditure", "Dépenses publiques"),
    "TR": ("revenue", "Recettes publiques"),
    "B9": ("balance", "Solde public"),
}
DEBT_INDICATORS = {
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
class MacroSource:
    dataset_code: str
    label: str
    source_url: str
    updated_at: str | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "dataset_code": self.dataset_code,
            "label": self.label,
            "source_url": self.source_url,
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True)
class MacroDataset:
    series: dict[str, MacroSeries]
    sources: tuple[MacroSource, ...]
    retrieved_at: str
    from_cache: bool = False

    @property
    def dataset_code(self) -> str:
        return " + ".join(source.dataset_code for source in self.sources)

    @property
    def source_url(self) -> str:
        return self.sources[0].source_url

    @property
    def updated_at(self) -> str | None:
        values = [source.updated_at for source in self.sources if source.updated_at]
        return max(values) if values else None

    def as_dict(self) -> dict[str, Any]:
        return {
            "dataset_code": self.dataset_code,
            "source_url": self.source_url,
            "updated_at": self.updated_at,
            "retrieved_at": self.retrieved_at,
            "from_cache": self.from_cache,
            "sources": [source.as_dict() for source in self.sources],
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


def get_source_catalog() -> list[dict[str, str]]:
    """Return the source metadata used by the macro dashboard, even when loading fails."""
    return [
        {
            "dataset_code": MAIN_DATASET_CODE,
            "label": "Government revenue, expenditure and main aggregates",
            "source_url": MAIN_SOURCE_URL,
        },
        {
            "dataset_code": DEBT_DATASET_CODE,
            "label": "Government deficit/surplus, debt and associated data",
            "source_url": DEBT_SOURCE_URL,
        },
    ]


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


def _parse_series_payload(
    payload: dict[str, Any],
    *,
    indicators: dict[str, tuple[str, str]],
    dataset_code: str,
    source_url: str,
    source_label: str,
) -> tuple[dict[str, MacroSeries], MacroSource]:
    dimension_ids = list(payload.get("id", []))
    sizes = list(payload.get("size", []))
    dimensions = payload.get("dimension", {})

    if "na_item" not in dimension_ids or "time" not in dimension_ids:
        raise EurostatError(
            f"Eurostat dataset {dataset_code} is missing na_item or time dimensions"
        )
    if len(dimension_ids) != len(sizes):
        raise EurostatError(f"Eurostat dataset {dataset_code} has inconsistent dimensions")

    try:
        positions_by_dimension = {
            dim: _category_positions(dimensions[dim]["category"]) for dim in dimension_ids
        }
        labels_by_dimension = {
            dim: dimensions[dim]["category"].get("label", {}) for dim in dimension_ids
        }
    except (KeyError, TypeError) as exc:
        raise EurostatError(f"Eurostat dataset {dataset_code} has an invalid structure") from exc

    for dim in dimension_ids:
        if dim not in {"na_item", "time"} and len(positions_by_dimension[dim]) != 1:
            raise EurostatError(f"Unexpected unfiltered dimension {dim} in {dataset_code}")

    time_positions = positions_by_dimension["time"]
    item_positions = positions_by_dimension["na_item"]
    raw_values = payload.get("value", {})

    unit_codes = positions_by_dimension.get("unit", {})
    unit_code = next(iter(unit_codes), "")
    unit_label = labels_by_dimension.get("unit", {}).get(unit_code, unit_code)

    result: dict[str, MacroSeries] = {}
    for code, (key, label) in indicators.items():
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
            source_item_label = labels_by_dimension["na_item"].get(code, code)
            result[key] = MacroSeries(
                key=key,
                code=code,
                label=label,
                source_label=source_item_label,
                unit=unit_label,
                values=series_values,
            )

    expected = {key for key, _ in indicators.values()}
    missing = expected.difference(result)
    if missing:
        raise EurostatError(
            f"Eurostat dataset {dataset_code} is missing required series: {sorted(missing)}"
        )

    source = MacroSource(
        dataset_code=dataset_code,
        label=source_label,
        source_url=source_url,
        updated_at=payload.get("updated"),
    )
    return result, source


def parse_macro_payloads(
    main_payload: dict[str, Any],
    debt_payload: dict[str, Any],
    *,
    from_cache: bool = False,
) -> MacroDataset:
    main_series, main_source = _parse_series_payload(
        main_payload,
        indicators=MAIN_INDICATORS,
        dataset_code=MAIN_DATASET_CODE,
        source_url=MAIN_SOURCE_URL,
        source_label="Government revenue, expenditure and main aggregates",
    )
    debt_series, debt_source = _parse_series_payload(
        debt_payload,
        indicators=DEBT_INDICATORS,
        dataset_code=DEBT_DATASET_CODE,
        source_url=DEBT_SOURCE_URL,
        source_label="Government deficit/surplus, debt and associated data",
    )

    return MacroDataset(
        series={**main_series, **debt_series},
        sources=(main_source, debt_source),
        retrieved_at=datetime.now(UTC).isoformat(),
        from_cache=from_cache,
    )


def _fetch_payload(
    dataset_code: str,
    *,
    timeout: float = 12.0,
    session: requests.Session | None = None,
) -> dict[str, Any]:
    client = session or requests.Session()
    params = {
        "lang": "EN",
        "freq": "A",
        "geo": "FR",
        "sector": "S13",
        "unit": "PC_GDP",
        "sinceTimePeriod": "2000",
        "untilTimePeriod": "2025",
    }
    try:
        response = client.get(
            f"{API_BASE_URL}/{dataset_code}",
            params=params,
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError) as exc:
        raise EurostatError(f"Unable to retrieve Eurostat dataset {dataset_code}") from exc


def fetch_macro_payloads(
    *, timeout: float = 12.0, session: requests.Session | None = None
) -> dict[str, Any]:
    client = session or requests.Session()
    return {
        "schema_version": CACHE_SCHEMA_VERSION,
        "main": _fetch_payload(MAIN_DATASET_CODE, timeout=timeout, session=client),
        "debt": _fetch_payload(DEBT_DATASET_CODE, timeout=timeout, session=client),
    }


def _parse_cache_payload(payload: dict[str, Any], *, from_cache: bool) -> MacroDataset:
    if payload.get("schema_version") != CACHE_SCHEMA_VERSION:
        raise EurostatError("Local Eurostat cache is incompatible with the current schema")
    if "main" not in payload or "debt" not in payload:
        raise EurostatError("Local Eurostat cache is incomplete")
    return parse_macro_payloads(payload["main"], payload["debt"], from_cache=from_cache)


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
            try:
                payload = json.loads(cache_path.read_text("utf-8"))
                return _parse_cache_payload(payload, from_cache=True)
            except (json.JSONDecodeError, EurostatError):
                pass

    try:
        payload = fetch_macro_payloads()
        dataset = _parse_cache_payload(payload, from_cache=False)
        cache_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return dataset
    except EurostatError as fetch_error:
        if cache_path.exists():
            try:
                payload = json.loads(cache_path.read_text("utf-8"))
                return _parse_cache_payload(payload, from_cache=True)
            except (json.JSONDecodeError, EurostatError):
                pass
        raise fetch_error
