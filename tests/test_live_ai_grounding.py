# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

"""Small, versioned provider evaluation. Opt-in only; never run by default CI."""

import json
import os
from pathlib import Path

import pytest

from acfpf.ai.grounding import review_answer
from acfpf.ai.registry import build_provider_from_env

BENCHMARK = json.loads((Path(__file__).parent / "fixtures/ai_grounding_benchmark.json").read_text())


@pytest.mark.skipif(
    os.environ.get("ACFPF_LIVE_AI") != "1",
    reason="Requires explicit live-provider opt-in and server-side credentials",
)
@pytest.mark.parametrize("case", BENCHMARK["cases"], ids=lambda case: case["id"])
def test_live_grounding_benchmark(case):
    provider = build_provider_from_env()
    accepted = review_answer(
        provider,
        {
            "QUESTION": "Que peut-on conclure de ce passage ?",
            "NUMERIC_CONTEXT": {},
            "EVIDENCE_AVAILABLE": {
                "E1": {
                    "text": case["evidence"],
                    "title": "Fixture synthétique",
                    "locator": "segment 1",
                }
            },
            "CITATIONS_USED": [
                {"id": "E1", "source_id": "synthetic_fixture", "locator": "segment 1"}
            ],
        },
        {"answer": case["answer"], "citations": ["E1"], "limitations": []},
    )
    assert accepted is case["expected"]
