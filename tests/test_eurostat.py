# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

import json

from acfpf.data.eurostat import (
    CACHE_SCHEMA_VERSION,
    load_macro_dataset,
    parse_macro_payloads,
)


def _dimensions(items: dict[str, int]) -> dict:
    return {
        "freq": {"category": {"index": {"A": 0}, "label": {"A": "Annual"}}},
        "unit": {
            "category": {
                "index": {"PC_GDP": 0},
                "label": {"PC_GDP": "Percentage of gross domestic product (GDP)"},
            }
        },
        "sector": {
            "category": {"index": {"S13": 0}, "label": {"S13": "General government"}}
        },
        "na_item": {
            "category": {
                "index": items,
                "label": {
                    "TE": "Total expenditure",
                    "TR": "Total revenue",
                    "B9": "Net lending (+) / net borrowing (-)",
                    "GD": "Government consolidated gross debt",
                },
            }
        },
        "geo": {"category": {"index": {"FR": 0}, "label": {"FR": "France"}}},
        "time": {
            "category": {
                "index": {"2000": 0, "2010": 1, "2025": 2},
                "label": {"2000": "2000", "2010": "2010", "2025": "2025"},
            }
        },
    }


def sample_main_payload() -> dict:
    return {
        "version": "2.0",
        "class": "dataset",
        "updated": "2026-04-22T09:00:00+0200",
        "id": ["freq", "unit", "sector", "na_item", "geo", "time"],
        "size": [1, 1, 1, 3, 1, 3],
        "dimension": _dimensions({"TE": 0, "TR": 1, "B9": 2}),
        "value": [
            52.6,
            56.9,
            57.3,
            51.3,
            50.1,
            52.2,
            -1.3,
            -6.9,
            -5.1,
        ],
    }


def sample_debt_payload() -> dict:
    return {
        "version": "2.0",
        "class": "dataset",
        "updated": "2026-04-22T09:00:00+0200",
        "id": ["freq", "unit", "sector", "na_item", "geo", "time"],
        "size": [1, 1, 1, 1, 1, 3],
        "dimension": _dimensions({"GD": 0}),
        "value": [58.9, 85.3, 113.0],
    }


def sample_dataset():
    return parse_macro_payloads(sample_main_payload(), sample_debt_payload())


def test_parse_macro_payloads_combines_reference_values() -> None:
    dataset = sample_dataset()

    assert dataset.series["expenditure"].values[2000] == 52.6
    assert dataset.series["expenditure"].values[2025] == 57.3
    assert dataset.series["revenue"].values[2025] == 52.2
    assert dataset.series["balance"].values[2025] == -5.1
    assert dataset.series["debt"].values[2025] == 113.0
    assert dataset.dataset_code == "gov_10a_main + gov_10dd_edpt1"
    assert [source.dataset_code for source in dataset.sources] == [
        "gov_10a_main",
        "gov_10dd_edpt1",
    ]


def test_fresh_cache_avoids_network(tmp_path) -> None:
    cache = tmp_path / "macro.json"
    cache.write_text(
        json.dumps(
            {
                "schema_version": CACHE_SCHEMA_VERSION,
                "main": sample_main_payload(),
                "debt": sample_debt_payload(),
            }
        ),
        encoding="utf-8",
    )

    dataset = load_macro_dataset(cache_path=cache)

    assert dataset.from_cache is True
    assert dataset.series["expenditure"].values[2000] == 52.6
    assert dataset.series["debt"].values[2025] == 113.0
