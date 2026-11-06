# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

"""Live source smoke test, deliberately separate from deterministic unit tests."""

import os

import pytest

from acfpf.legislative_articles import detect_article_candidates
from acfpf.legislative_fulltext import fetch_official_text


@pytest.mark.skipif(
    os.environ.get("ACFPF_LIVE_SOURCES") != "1",
    reason="Live official-source checks are opt-in",
)
def test_live_official_document_html():
    # Official XVIIth-legislature text verified on the publisher's own website.
    document = fetch_official_text("PIONANR5L17B2562")
    assert document.url == (
        "https://www.assemblee-nationale.fr/dyn/opendata/PIONANR5L17B2562.html"
    )
    assert "ASSEMBLÉE NATIONALE" in document.text.upper()
    assert "PROPOSITION DE LOI" in document.text.upper()
    assert len(document.sha256) == 64
    candidates = detect_article_candidates(document)
    assert any(item['heading'].lower() == 'article unique' for item in candidates['candidates'])
    assert candidates['article_structure_verified'] is False
