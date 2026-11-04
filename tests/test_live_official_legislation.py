# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

"""Integration smoke test using live Assemblée nationale open data (opt-in)."""

from __future__ import annotations

import os

import pytest

from acfpf.legislation_detail import AmendmentService, LegislativeDetailError
from tests.test_legislation_detail import assembly_dossier


@pytest.mark.skipif(
    os.environ.get("ACFPF_LIVE_SOURCES") != "1",
    reason="Live source check requires ACFPF_LIVE_SOURCES=1",
)
def test_live_assembly_dossier_amendments_and_xml(tmp_path) -> None:
    """Exercise index + detailed XML with no mocked transport or source records."""
    service = AmendmentService(cache_dir=tmp_path)
    collection = service.for_dossier(assembly_dossier(), refresh=True)
    assert collection.available is True
    assert collection.from_cache is False
    assert len(collection.amendments) > 0, "Official dossier 54629 has no readable amendments"
    assert collection.source_url.startswith("https://data.assemblee-nationale.fr/")

    failures = []
    for amendment in collection.amendments[:5]:
        assert amendment.id
        assert amendment.number
        assert amendment.official_url.startswith("https://www.assemblee-nationale.fr/")
        try:
            detail = service.detail_for(
                assembly_dossier(), amendment.id, refresh=True
            )
        except LegislativeDetailError as exc:
            failures.append(f"{amendment.id}: {exc}")
            continue
        assert detail is not None
        assert detail.amendment.id == amendment.id
        assert detail.dispositif or detail.purpose, (
            f"Official amendment XML lacks both dispositif and exposed motivation: {amendment.id}"
        )
        return

    pytest.fail(
        "Could not load any of the first five official amendment XML files: "
        + "; ".join(failures)
    )
