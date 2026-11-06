# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

"""Explicit opt-in: live discovery and reading, independently of any LLM or dossier API."""

import os
from urllib.parse import urlparse

import pytest

from acfpf.live_research import LiveOfficialResearch


@pytest.mark.skipif(
    os.environ.get("ACFPF_LIVE_DOCUMENTARY") != "1",
    reason="Discovery-index integration requires ACFPF_LIVE_DOCUMENTARY=1 (separate from CI)",
)
def test_live_discover_and_read_without_dossier():
    research = LiveOfficialResearch(timeout=20)
    results = research.search(
        "logement sollicitations sexuelles abusives",
        source_ids=["assemblee_nationale_open_data"],
        limit=2,
    )
    assert results, "No official URL returned by the live discovery index"
    document = research.open(results[0].url)
    unit = research.read(document.document_id, 1)
    assert document.source_id == "assemblee_nationale_open_data"
    assert urlparse(document.url).hostname.endswith("assemblee-nationale.fr")
    assert document.title and document.retrieved_at and len(document.sha256) == 64
    assert unit.text.strip() and unit.locator
    print("LIVE-DOCUMENTARY:", document.url, document.sha256, unit.locator, len(unit.text))
