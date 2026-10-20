# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

import pytest

from acfpf.data.documents import extract_html_text
from acfpf.evidence import EvidenceRef
from acfpf.live_research import DISCOVERY_URL, LiveOfficialResearch, SourceNotAllowed
from acfpf.source_registry import Source


class FakeResponse:
    def __init__(
        self,
        *,
        text: str,
        url: str,
        content_type: str = "text/html; charset=utf-8",
    ) -> None:
        self.text = text
        self.url = url
        self.headers = {"Content-Type": content_type}
        self.content = text.encode("utf-8")

    def raise_for_status(self) -> None:
        return None


class FakeSession:
    def __init__(self, responses: dict[str, FakeResponse]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, dict | None]] = []

    def get(self, url, *, params=None, headers=None, timeout=None):
        del headers, timeout
        self.calls.append((url, params))
        return self.responses[url]


def source_map() -> dict[str, Source]:
    return {
        "official": Source(
            id="official",
            name="Source officielle",
            base_url="https://official.test/",
            priority="primary",
            themes=("public_finance",),
            evidence_stages=("decision",),
            allowed_domains=("official.test",),
        )
    }


def test_evidence_ref_rejects_unknown_stage() -> None:
    with pytest.raises(ValueError):
        EvidenceRef(
            id="x",
            source_id="official",
            stage="rumour",
            kind="text",
            title="Titre",
            source_url="https://official.test",
        )


def test_html_extraction_preserves_all_visible_text_in_source_order() -> None:
    html = """
    <html><body><h1>Loi de finances</h1><script>secret()</script>
    <p>Premier paragraphe.</p><p>Paragraphe éloigné mais important.</p></body></html>
    """
    text = extract_html_text(html)

    assert "Loi de finances" in text
    assert text.index("Premier paragraphe") < text.index("Paragraphe éloigné")
    assert "secret" not in text


def test_live_research_rejects_non_allowlisted_domain() -> None:
    research = LiveOfficialResearch(sources=source_map(), session=FakeSession({}))

    with pytest.raises(SourceNotAllowed):
        research.open("https://example.com/not-official")


def test_discovery_returns_only_allowlisted_urls_and_never_snippets() -> None:
    html = """
    <html><body>
      <a class="result__a" href="https://official.test/report">Rapport officiel</a>
      <div class="result__snippet">Texte provenant du moteur qui ne doit jamais devenir une preuve.</div>
      <a class="result__a" href="https://example.com/article">Article externe</a>
    </body></html>
    """
    session = FakeSession(
        {DISCOVERY_URL: FakeResponse(text=html, url=DISCOVERY_URL)}
    )
    research = LiveOfficialResearch(sources=source_map(), session=session)

    results = research.search("dépenses", source_ids=["official"])

    assert [item.url for item in results] == ["https://official.test/report"]
    assert results[0].title == "Rapport officiel"
    assert "snippet" not in results[0].as_dict()
    assert session.calls[0][1]["q"].startswith("(site:official.test)")


def test_open_reads_official_html_without_relevance_filtering() -> None:
    html = "<html><head><title>Rapport public</title></head><body>" + (
        "<p>Texte général sans le mot recherché.</p>" * 400
    ) + "<p>Conclusion décisive située à la fin.</p></body></html>"
    response = FakeResponse(text=html, url="https://official.test/report")
    research = LiveOfficialResearch(
        sources=source_map(),
        session=FakeSession({"https://official.test/report": response}),
    )

    document = research.open("https://official.test/report")

    assert document.title == "Rapport public"
    assert len(document.units) >= 2
    combined = "\n".join(unit.text for unit in document.units)
    assert "Texte général sans le mot recherché" in combined
    assert "Conclusion décisive située à la fin" in combined
    assert document.sha256


def test_redirect_to_non_allowlisted_domain_is_rejected() -> None:
    response = FakeResponse(text="<html><body>Texte officiel</body></html>", url="https://evil.test/")
    research = LiveOfficialResearch(
        sources=source_map(),
        session=FakeSession({"https://official.test/start": response}),
    )

    with pytest.raises(SourceNotAllowed):
        research.open("https://official.test/start")
