# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

from acfpf.cofog import build_cofog_analysis
from acfpf.data.cofog import parse_cofog_payload


def sample_cofog_payload() -> dict:
    codes = [f"GF{index:02d}" for index in range(1, 11)]
    labels = {
        "GF01": "Services généraux des administrations publiques",
        "GF02": "Défense",
        "GF03": "Ordre et sécurité publics",
        "GF04": "Affaires économiques",
        "GF05": "Protection de l'environnement",
        "GF06": "Logements et équipements collectifs",
        "GF07": "Santé",
        "GF08": "Loisirs, culture et culte",
        "GF09": "Enseignement",
        "GF10": "Protection sociale",
    }
    values = []
    bases = [6.0, 2.0, 1.2, 5.0, 0.8, 1.0, 7.0, 1.1, 6.5, 19.0]
    latest = [5.5, 1.8, 1.5, 6.0, 1.0, 0.7, 8.0, 1.0, 5.8, 22.0]
    for first, last in zip(bases, latest, strict=True):
        values.extend([first, last])

    return {
        "version": "2.0",
        "class": "dataset",
        "updated": "2026-09-16T21:00:00+0200",
        "id": ["freq", "unit", "sector", "cofog99", "na_item", "geo", "time"],
        "size": [1, 1, 1, 10, 1, 1, 2],
        "dimension": {
            "freq": {"category": {"index": {"A": 0}, "label": {"A": "Annuel"}}},
            "unit": {
                "category": {
                    "index": {"PC_GDP": 0},
                    "label": {"PC_GDP": "Pourcentage du PIB"},
                }
            },
            "sector": {"category": {"index": {"S13": 0}, "label": {"S13": "APU"}}},
            "cofog99": {
                "category": {
                    "index": {code: index for index, code in enumerate(codes)},
                    "label": labels,
                }
            },
            "na_item": {"category": {"index": {"TE": 0}, "label": {"TE": "Dépense totale"}}},
            "geo": {"category": {"index": {"FR": 0}, "label": {"FR": "France"}}},
            "time": {
                "category": {
                    "index": {"2000": 0, "2025": 1},
                    "label": {"2000": "2000", "2025": "2025"},
                }
            },
        },
        "value": values,
    }


def test_parse_cofog_payload_extracts_ten_top_level_functions() -> None:
    dataset = parse_cofog_payload(sample_cofog_payload())

    assert len(dataset.series) == 10
    assert dataset.series["GF09"].label == "Enseignement"
    assert dataset.series["GF09"].values == {2000: 6.5, 2025: 5.8}
    assert dataset.series["GF10"].values[2025] == 22.0


def test_cofog_analysis_ranks_increases_and_decreases() -> None:
    analysis = build_cofog_analysis(parse_cofog_payload(sample_cofog_payload()))

    assert analysis.increases[0].code == "GF10"
    assert analysis.increases[0].delta == 3.0
    assert analysis.decreases[0].code == "GF09"
    assert analysis.decreases[0].delta == -0.7
    assert "ne prouve pas" in analysis.as_dict()["interpretation_note"]
