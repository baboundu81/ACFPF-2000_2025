# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

from io import BytesIO
from urllib.parse import quote

import pytest
import requests
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
from requests.structures import CaseInsensitiveDict

from acfpf import live_research as live
from tests.test_evidence import source_map

URL = "https://official.test/report"


class StreamResponse:
    """HTTP boundary fake: no content/text property, so eager reads fail the tests."""

    def __init__(
        self,
        content=b"<html><p>Document officiel.</p></html>",
        *,
        status=200,
        content_type="text/html; charset=utf-8",
        headers=None,
        chunks=None,
    ):
        self.headers = CaseInsensitiveDict({"Content-Type": content_type, **(headers or {})})
        self.status_code = status
        self.chunks = chunks if chunks is not None else [content]
        self.closed = False
        self.chunks_read = 0

    def iter_content(self, chunk_size):
        assert chunk_size == live.STREAM_CHUNK_BYTES
        for chunk in self.chunks:
            self.chunks_read += 1
            if isinstance(chunk, Exception):
                raise chunk
            yield chunk

    def close(self):
        self.closed = True


class StreamSession:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def get(self, url, **kwargs):
        assert kwargs["stream"] is True
        assert kwargs["allow_redirects"] is False
        assert kwargs["timeout"] > 0
        self.calls.append((url, kwargs))
        result = self.responses[url]
        if isinstance(result, Exception):
            raise result
        return result


def reader(response, url=URL):
    session = StreamSession({url: response})
    return live.LiveOfficialResearch(sources=source_map(), session=session), session


def pdf_bytes(texts, *, encrypt=False):
    """Tiny locally generated PDF, with text on each requested page and no third-party data."""
    writer = PdfWriter()
    for text in texts:
        page = writer.add_blank_page(width=300, height=300)
        font = DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
        page[NameObject("/Resources")] = DictionaryObject(
            {
                NameObject("/Font"): DictionaryObject({NameObject("/F1"): font}),
            }
        )
        stream = DecodedStreamObject()
        stream.set_data(f"BT /F1 12 Tf 10 100 Td ({text}) Tj ET".encode("ascii"))
        page[NameObject("/Contents")] = writer._add_object(stream)
    if encrypt:
        writer.encrypt("test-password")
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


@pytest.mark.parametrize(
    "url",
    [
        "http://official.test/report",
        "https://official.test.evil.test/",
        "https://evilofficial.test/",
        "https://user:password@official.test/",
        "https://official.test:444/",
        "https://official.test:invalid/",
        "https://[broken",
        "https://official.test/\nreport",
        "https://official.test\\@evil.test/",
    ],
)
def test_invalid_urls_rejected_before_network(url):
    research, session = reader(StreamResponse())
    with pytest.raises(live.SourceNotAllowed):
        research.open(url)
    assert session.calls == []


def test_empty_allowlist_does_not_restore_default_sources():
    research = live.LiveOfficialResearch(sources={}, session=StreamSession({}))
    with pytest.raises(live.SourceNotAllowed):
        research.open("https://www.insee.fr/")


def test_relative_redirect_keeps_final_provenance_and_closes_responses():
    redirect = StreamResponse(status=302, headers={"Location": "/final"})
    response = StreamResponse()
    session = StreamSession({URL: redirect, "https://official.test/final": response})
    research = live.LiveOfficialResearch(sources=source_map(), session=session)
    doc = research.open(URL)
    assert doc.url == "https://official.test/final"
    assert redirect.closed and redirect.chunks_read == 0
    assert response.closed


@pytest.mark.parametrize(
    "location", ["https://evil.test/", "http://official.test/", "https://[bad"]
)
def test_redirect_refused_before_destination_is_requested(location):
    response = StreamResponse(status=302, headers={"Location": location})
    research, session = reader(response)
    with pytest.raises(live.SourceNotAllowed):
        research.open(URL)
    assert [call[0] for call in session.calls] == [URL]
    assert response.closed and response.chunks_read == 0


def test_redirect_loop_is_bounded():
    response = StreamResponse(status=302, headers={"Location": URL})
    research, session = reader(response)
    with pytest.raises(live.LiveResearchError, match="redirections"):
        research.open(URL)
    assert len(session.calls) == live.MAX_REDIRECTS + 1
    assert response.closed


def test_redirect_without_destination_is_not_read():
    response = StreamResponse(status=302)
    research, _ = reader(response)
    with pytest.raises(live.LiveResearchError, match="destination"):
        research.open(URL)
    assert response.closed and response.chunks_read == 0


@pytest.mark.parametrize("status", [204, 206, 404, 429, 500])
def test_http_failure_is_recoverable_and_creates_no_document(status):
    response = StreamResponse(status=status)
    research, _ = reader(response)
    with pytest.raises(live.LiveResearchError, match=f"HTTP {status}"):
        research.open(URL)
    with pytest.raises(live.LiveResearchError):
        research.document("D1")
    assert response.closed and response.chunks_read == 0


@pytest.mark.parametrize("error", [requests.Timeout(), requests.ConnectionError()])
def test_connection_failure_becomes_documentary_failure(error):
    research, _ = reader(error)
    with pytest.raises(live.LiveResearchError, match="indisponible"):
        research.open(URL)


@pytest.mark.parametrize(
    "chunks",
    [
        [b"<html>", requests.Timeout()],
        [b"<html>", requests.exceptions.ChunkedEncodingError()],
    ],
)
def test_interrupted_stream_is_closed_without_document(chunks):
    response = StreamResponse(chunks=chunks)
    research, _ = reader(response)
    with pytest.raises(live.LiveResearchError, match="interrompu"):
        research.open(URL)
    assert response.closed
    assert research._documents == {}


@pytest.mark.parametrize("length", ["bad", "-1", str(live.MAX_HTML_BYTES + 1)])
def test_announced_invalid_or_excessive_size_is_refused_without_reading(length):
    response = StreamResponse(headers={"Content-Length": length})
    research, _ = reader(response)
    with pytest.raises(live.LiveResearchError):
        research.open(URL)
    assert response.closed and response.chunks_read == 0


@pytest.mark.parametrize("headers", [{}, {"Content-Encoding": "gzip", "Content-Length": "2"}])
def test_stream_size_enforced_on_decoded_bytes_not_only_headers(monkeypatch, headers):
    monkeypatch.setattr(live, "MAX_HTML_BYTES", 10)
    response = StreamResponse(headers=headers, chunks=[b"<html>", b"too much", b"never read"])
    research, _ = reader(response)
    with pytest.raises(live.DocumentTooLarge):
        research.open(URL)
    assert response.chunks_read == 2
    assert response.closed


def test_short_response_is_not_accepted_as_complete():
    response = StreamResponse(headers={"Content-Length": "999"})
    research, _ = reader(response)
    with pytest.raises(live.LiveResearchError, match="incomplet"):
        research.open(URL)


def test_slow_continuous_stream_has_a_deadline(monkeypatch):
    ticks = iter([0, 1, 21])
    monkeypatch.setattr(live.time, "monotonic", lambda: next(ticks))
    response = StreamResponse(chunks=[b"<html>", b"slow"])
    research, _ = reader(response)
    with pytest.raises(live.LiveResearchError, match="délai"):
        research.open(URL)
    assert response.closed


@pytest.mark.parametrize(
    "content_type,content",
    [
        ("application/json", b'{"message":"not HTML"}'),
        ("application/octet-stream", b"binary"),
        ("text/html", b"not HTML"),
        ("text/html", b"<html><script>hidden()</script><p> </p></html>"),
        ("application/pdf", b"not a PDF"),
        ("application/pdf", b"%PDF-1.7\nbroken"),
    ],
)
def test_unreadable_content_creates_no_document(content_type, content):
    response = StreamResponse(content, content_type=content_type)
    research, _ = reader(response)
    with pytest.raises(live.LiveResearchError):
        research.open(URL)
    assert research._documents == {}
    assert response.closed


def test_pdf_contiguous_pages_keep_locators_and_source_order():
    response = StreamResponse(
        pdf_bytes(["Page one", "", "Page three", "Page four", "Page five"]),
        content_type="application/pdf",
    )
    research, _ = reader(response)
    doc = research.open(URL)
    assert [unit.locator for unit in doc.units] == ["pages 1-4", "page 5"]
    assert doc.units[0].text.index("Page one") < doc.units[0].text.index("Page three")
    assert research.read(doc.document_id, 2).text == "Page five"


@pytest.mark.parametrize("content", [pdf_bytes([""]), pdf_bytes(["secret"], encrypt=True)])
def test_scanned_or_encrypted_pdf_has_no_readable_evidence(content):
    research, _ = reader(StreamResponse(content, content_type="application/pdf"))
    with pytest.raises(live.LiveResearchError):
        research.open(URL)
    assert research._documents == {}


def test_pdf_page_limit_refuses_whole_document_without_truncation(monkeypatch):
    monkeypatch.setattr(live, "MAX_PDF_PAGES", 1)
    research, _ = reader(StreamResponse(pdf_bytes(["one", "two"]), content_type="application/pdf"))
    with pytest.raises(live.DocumentTooLarge, match="pages"):
        research.open(URL)
    assert research._documents == {}


@pytest.mark.parametrize(
    "content_type,content",
    [
        ("text/html", b"<p>Too much text</p>"),
        ("application/pdf", pdf_bytes(["Too much text"])),
    ],
)
def test_extracted_text_limit_refuses_instead_of_truncating(monkeypatch, content_type, content):
    monkeypatch.setattr(live, "MAX_EXTRACTED_CHARS", 5)
    research, _ = reader(StreamResponse(content, content_type=content_type))
    with pytest.raises(live.DocumentTooLarge):
        research.open(URL)


def test_html_segments_cover_all_text_in_order(monkeypatch):
    monkeypatch.setattr(live, "HTML_UNIT_CHARS", 20)
    text = "First paragraph.\nUnrelated passage.\nFinal conclusion."
    units = live._split_html_units(text)
    assert "".join(unit.text for unit in units).replace("\n", "") == text.replace("\n", "")
    assert [unit.locator for unit in units] == [f"segment {i}" for i in range(1, len(units) + 1)]


def test_discovery_redirect_url_is_decoded_once_and_snippets_are_discarded():
    target = URL + "?value=%26retained"
    html = f"""<a class="result__a" href="//duckduckgo.com/l/?uddg={quote(target, safe="")}">Titre</a>
      <div class="result__snippet">NEVER_EVIDENCE</div>
      <a class="result__a" href="https://[broken">Invalid</a>
      <a class="result__a" href="https://evil.test">External</a>"""
    response = StreamResponse(html.encode())
    research, _ = reader(response, live.DISCOVERY_URL)
    results = research.search("logement", source_ids=["official"])
    assert [result.url for result in results] == [target]
    assert "NEVER_EVIDENCE" not in str(results)
    assert response.closed


@pytest.mark.parametrize("status", [202, 302, 429, 503])
def test_discovery_failures_are_not_misreported_as_zero_results(status):
    response = StreamResponse(status=status)
    research, _ = reader(response, live.DISCOVERY_URL)
    with pytest.raises(live.LiveResearchError, match="index"):
        research.search("logement", source_ids=["official"])
    assert response.closed and response.chunks_read == 0


def test_discovery_download_is_bounded(monkeypatch):
    monkeypatch.setattr(live, "MAX_DISCOVERY_BYTES", 3)
    response = StreamResponse()
    research, _ = reader(response, live.DISCOVERY_URL)
    with pytest.raises(live.DocumentTooLarge):
        research.search("logement", source_ids=["official"])
    assert response.closed


def test_document_sessions_are_isolated_per_question(monkeypatch):
    monkeypatch.setattr(live.requests, "Session", lambda: StreamSession({URL: StreamResponse()}))
    parent = live.LiveOfficialResearch(sources=source_map())
    first, second = parent.spawn(), parent.spawn()
    assert first.open(URL).document_id == "D1"
    with pytest.raises(live.LiveResearchError):
        second.read("D1", 1)
    assert second.open(URL).document_id == "D1"
    assert parent._documents == {}


def test_shared_official_domain_keeps_specific_source_provenance():
    from acfpf.source_registry import Source

    def source(uid, base):
        return Source(
            id=uid,
            name=uid,
            base_url=base,
            priority="primary",
            themes=(),
            allowed_domains=("official.test",),
        )

    sources = {
        "statistics": source("statistics", "https://official.test/statistics/"),
        "decisions": source("decisions", "https://competition.official.test/decisions/"),
    }
    research = live.LiveOfficialResearch(sources=sources)
    assert research._source_for_url("https://official.test/statistics/report").id == "statistics"
    assert (
        research._source_for_url("https://competition.official.test/decisions/report").id
        == "decisions"
    )
    with pytest.raises(live.SourceNotAllowed, match="ambiguë"):
        research._source_for_url("https://official.test/unclassified")


@pytest.mark.parametrize("content_type", ["application/json", "application/pdf", ""])
def test_discovery_rejects_non_html_before_reading(content_type):
    response = StreamResponse(content_type=content_type)
    research, _ = reader(response, live.DISCOVERY_URL)
    with pytest.raises(live.LiveResearchError, match="HTML"):
        research.search("logement", source_ids=["official"])
    assert response.closed and response.chunks_read == 0


def test_discovery_timeout_is_a_recoverable_failure():
    research, _ = reader(requests.Timeout(), live.DISCOVERY_URL)
    with pytest.raises(live.LiveResearchError, match="index"):
        research.search("logement", source_ids=["official"])


def test_html_declared_encoding_and_title_entities_are_preserved():
    response = StreamResponse(
        "<html><title>État &amp; société</title><p>Décision publiée.</p></html>".encode(
            "iso-8859-1"
        ),
        content_type="text/html; charset=iso-8859-1",
    )
    research, _ = reader(response)
    document = research.open(URL)
    assert document.title == "État & société"
    assert "Décision publiée." in document.units[0].text
