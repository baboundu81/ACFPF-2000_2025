# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

import pytest

from acfpf.data.documents import extract_html_text, split_document_text
from acfpf.document_corpus import OfficialDocumentCorpus
from acfpf.evidence import EvidenceChunk, EvidenceRef


def test_evidence_ref_rejects_unknown_stage() -> None:
    with pytest.raises(ValueError):
        EvidenceRef(
            id="x",
            source_id="official",
            stage="rumour",
            kind="text",
            title="Titre",
            source_url="https://example.test",
        )


def test_html_extraction_ignores_scripts_and_preserves_visible_text() -> None:
    html = """
    <html><body><h1>Loi de finances</h1><script>secret()</script>
    <p>Les crédits sont autorisés pour 2025.</p></body></html>
    """
    text = extract_html_text(html)

    assert "Loi de finances" in text
    assert "Les crédits sont autorisés" in text
    assert "secret" not in text


def test_split_document_text_produces_non_empty_chunks() -> None:
    chunks = split_document_text("Premier paragraphe.\nDeuxième paragraphe.", max_chars=30)

    assert chunks
    assert all(chunk.strip() for chunk in chunks)


def test_document_corpus_searches_only_seed_documents(tmp_path, monkeypatch) -> None:
    catalog = tmp_path / "documents.yml"
    catalog.write_text(
        """
documents:
  - id: finance-law
    source_id: legifrance
    stage: decision
    kind: finance_law
    title: Loi de finances de test
    source_url: https://official.test/law
    scope: budget_etat
    status: seed
  - id: future-source
    source_id: senate
    stage: parliamentary_process
    kind: amendment_collection
    title: Collection future
    source_url: https://official.test/future
    status: catalogued
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "acfpf.document_corpus.fetch_official_document_text",
        lambda url: (
            "La loi de finances prévoit une évolution des crédits de l'éducation. "
            "Ce texte constitue une décision budgétaire officielle."
        ),
    )

    corpus = OfficialDocumentCorpus(cache_dir=tmp_path / "cache", catalog_path=catalog)
    result = corpus.search("crédits éducation", limit=3)

    assert len(result.chunks) == 1
    chunk = result.chunks[0]
    assert isinstance(chunk, EvidenceChunk)
    assert chunk.evidence.id == "finance-law"
    assert chunk.evidence.stage == "decision"
    assert "éducation" in chunk.text
