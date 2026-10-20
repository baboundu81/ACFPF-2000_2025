# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests

from acfpf.data.eurostat import API_BASE_URL, EurostatError

DATASET_CODE = "gov_10a_exp"
SOURCE_URL = "https://ec.europa.eu/eurostat/databrowser/view/gov_10a_exp/default/table"
CACHE_SCHEMA_VERSION = 1
TOP_LEVEL_RE = re.compile(r"^GF\d{2}$")


@dataclass(frozen=True)
class CofogSeries:
    code: str
    label: str
    unit: str
    values: dict[int, float]

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "label": self.label,
            "unit": self.unit,
            "values": [
                {"year": year, "value": value}
                for year, value in sorted(self.values.items())
            ],
        }


@dataclass(frozen=True)
class CofogDataset:
    series: dict[str, CofogSeries]
    updated_at: str | None
    retrieved_at: str
    from_cache: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "dataset_code": DATASET_CODE,
            "source_url": SOURCE_URL,
            "updated_at": self.updated_at,
            "retrieved_at": self.retrieved_at,
            "from_cache": self.from_cache,
            "series": {code: item.as_dict() for code, item in self.series.items()},
        }


def _positions(category: dict[str, Any]) -> dict[str, int]:
    index = category.get("index", {})
    if isinstance(index, dict):
        return {str(code): int(position) for code, position in index.items()}
    if isinstance(index, list):
        return {str(code): position for position, code in enumerate(index)}
    raise EurostatError("Unsupported JSON-stat category index format")


def _flat_index(positions: list[int], sizes: list[int]) -> int:
    result = 0
    for position, size in zip(positions, sizes, strict=True):
        result = result * size + position
    return result


def _value_at(values: Any, index: int) -> float | None:
    if isinstance(values, list):
        value = values[index] if index < len(values) else None
    elif isinstance(values, dict):
        value = values.get(str(index))
    else:
        raise EurostatError("Unsupported JSON-stat value container")
    return None if value is None else float(value)


def parse_cofog_payload(payload: dict[str, Any], *, from_cache: bool = False) -> CofogDataset:
    dimension_ids = list(payload.get("id", []))
    sizes = list(payload.get("size", []))
    dimensions = payload.get("dimension", {})

    if "cofog99" not in dimension_ids or "time" not in dimension_ids:
        raise EurostatError("Eurostat COFOG response is missing cofog99 or time dimensions")
    if len(dimension_ids) != len(sizes):
        raise EurostatError("Eurostat COFOG response has inconsistent dimensions")

    try:
        positions_by_dim = {
            dim: _positions(dimensions[dim]["category"]) for dim in dimension_ids
        }
        labels_by_dim = {
            dim: dimensions[dim]["category"].get("label", {}) for dim in dimension_ids
        }
    except (KeyError, TypeError) as exc:
        raise EurostatError("Eurostat COFOG response has an invalid structure") from exc

    for dim in dimension_ids:
        if dim not in {"cofog99", "time"} and len(positions_by_dim[dim]) != 1:
            raise EurostatError(f"Unexpected unfiltered COFOG dimension: {dim}")

    raw_values = payload.get("value", {})
    time_positions = positions_by_dim["time"]
    cofog_positions = positions_by_dim["cofog99"]
    unit_codes = positions_by_dim.get("unit", {})
    unit_code = next(iter(unit_codes), "")
    unit_label = labels_by_dim.get("unit", {}).get(unit_code, unit_code)

    result: dict[str, CofogSeries] = {}
    for code, cofog_position in cofog_positions.items():
        if not TOP_LEVEL_RE.fullmatch(code):
            continue

        values: dict[int, float] = {}
        for year_code, time_position in time_positions.items():
            coordinates: list[int] = []
            for dim in dimension_ids:
                if dim == "cofog99":
                    coordinates.append(cofog_position)
                elif dim == "time":
                    coordinates.append(time_position)
                else:
                    coordinates.append(next(iter(positions_by_dim[dim].values())))
            value = _value_at(raw_values, _flat_index(coordinates, sizes))
            if value is not None:
                values[int(year_code)] = value

        if values:
            result[code] = CofogSeries(
                code=code,
                label=labels_by_dim["cofog99"].get(code, code),
                unit=unit_label,
                values=values,
            )

    if len(result) < 10:
        raise EurostatError(
            f"Eurostat COFOG response contains only {len(result)} top-level functions"
        )

    return CofogDataset(
        series=result,
        updated_at=payload.get("updated"),
        retrieved_at=datetime.now(UTC).isoformat(),
        from_cache=from_cache,
    )


def fetch_cofog_payload(
    *, timeout: float = 15.0, session: requests.Session | None = None
) -> dict[str, Any]:
    client = session or requests.Session()
    params = {
        "lang": "FR",
        "freq": "A",
        "geo": "FR",
        "sector": "S13",
        "unit": "PC_GDP",
        "na_item": "TE",
        "sinceTimePeriod": "2000",
        "untilTimePeriod": "2025",
    }
    try:
        response = client.get(
            f"{API_BASE_URL}/{DATASET_CODE}",
            params=params,
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError) as exc:
        raise EurostatError(f"Unable to retrieve Eurostat dataset {DATASET_CODE}") from exc


def _parse_cache(payload: dict[str, Any], *, from_cache: bool) -> CofogDataset:
    if payload.get("schema_version") != CACHE_SCHEMA_VERSION or "payload" not in payload:
        raise EurostatError("Local COFOG cache is incompatible or incomplete")
    return parse_cofog_payload(payload["payload"], from_cache=from_cache)


def load_cofog_dataset(
    *,
    cache_path: Path,
    max_cache_age_seconds: int = 24 * 60 * 60,
    refresh: bool = False,
) -> CofogDataset:
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    if cache_path.exists() and not refresh:
        age = datetime.now(UTC).timestamp() - cache_path.stat().st_mtime
        if age <= max_cache_age_seconds:
            try:
                return _parse_cache(json.loads(cache_path.read_text("utf-8")), from_cache=True)
            except (json.JSONDecodeError, EurostatError):
                pass

    try:
        payload = {
            "schema_version": CACHE_SCHEMA_VERSION,
            "payload": fetch_cofog_payload(),
        }
        dataset = _parse_cache(payload, from_cache=False)
        cache_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return dataset
    except EurostatError:
        if cache_path.exists():
            try:
                return _parse_cache(json.loads(cache_path.read_text("utf-8")), from_cache=True)
            except (json.JSONDecodeError, EurostatError):
                pass
        raise
