# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

import json

from acfpf.data.eurostat import load_macro_dataset, parse_macro_payload


def sample_payload() -> dict:
    return {
        "version": "2.0",
        "class": "dataset",
        "updated": "2026-04-22T09:00:00+0200",
        "id": ["freq", "unit", "sector", "na_item", "geo", "time"],
        "size": [1, 1, 1, 4, 1, 3],
        "dimension": {
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
                    "index": {"TE": 0, "TR": 1, "B9": 2, "GD": 3},
                    "label": {
                        "TE": "Total expenditure",
                        "TR": "Total revenue",
                        "B9": "Net lending (+) / net borrowing (-)",
                        "GD": "General government consolidated gross debt",
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
        },
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
            58.9,
            85.3,
            113.0,
        ],
    }


def test_parse_macro_payload_decodes_reference_values() -> None:
    dataset = parse_macro_payload(sample_payload())

    assert dataset.series["expenditure"].values[2000] == 52.6
    assert dataset.series["expenditure"].values[2025] == 57.3
    assert dataset.series["revenue"].values[2025] == 52.2
    assert dataset.series["balance"].values[2025] == -5.1
    assert dataset.series["debt"].values[2025] == 113.0
    assert dataset.dataset_code == "gov_10dd_edpt1"


def test_fresh_cache_avoids_network(tmp_path) -> None:
    cache = tmp_path / "macro.json"
    cache.write_text(json.dumps(sample_payload()), encoding="utf-8")

    dataset = load_macro_dataset(cache_path=cache)

    assert dataset.from_cache is True
    assert dataset.series["expenditure"].values[2000] == 52.6
