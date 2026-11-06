# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

"""Free questions through Flask, real agent/reader/extraction; only HTTP and LLM are faked."""

import hashlib
import json

import pytest
import requests

from acfpf import live_research as live
from acfpf.ai.civic import CivicAnswerService
from acfpf.ai.service import AnswerService
from acfpf.web import create_app
from tests.test_ai import FakeProvider
from tests.test_evidence import source_map
from tests.test_live_research import URL, StreamResponse, StreamSession, pdf_bytes
from tests.test_web import FakeCofogService, FakeMacroService

QUESTION = "Quelles mesures publiques concernent le logement ?"
SEARCH = {"action": "search", "query": "logement", "source_ids": ["official"]}
OPEN = {"action": "open", "url": URL}
READ = {"action": "read", "document_id": "D1", "unit": 2}
INSUFFICIENT = {
    "action": "answer",
    "status": "insufficient",
    "answer": "L’information n’est pas établie.",
    "citations": [],
    "limitations": ["Aucun passage officiel lisible ne permet de conclure."],
}


class NoDossierService:
    def get(self, *args, **kwargs):
        raise AssertionError("Une question libre ne doit pas charger un dossier.")


def pipeline(monkeypatch, responses, actions):
    sessions = []

    def session_factory():
        session = StreamSession(responses)
        sessions.append(session)
        return session

    monkeypatch.setattr(live.requests, "Session", session_factory)
    macro, cofog = FakeMacroService(), FakeCofogService()
    provider = FakeProvider(*actions)
    research = live.LiveOfficialResearch(sources=source_map())
    answer_service = CivicAnswerService(AnswerService(provider, macro, cofog, research))
    app = create_app(
        service=macro,
        cofog_service=cofog,
        answer_service=answer_service,
        legislation_service=NoDossierService(),
    )
    app.testing = True
    return app.test_client(), provider, sessions


def search_response():
    return StreamResponse(
        f'''<a class="result__a" href="{URL}">Titre de navigation</a>
        <div class="result__snippet">NEVER_USE_SEARCH_SNIPPET</div>'''.encode()
    )


@pytest.mark.parametrize("stream", [False, True])
@pytest.mark.parametrize("kind", ["html", "pdf"])
def test_free_question_search_open_read_answer_keeps_read_evidence(monkeypatch, stream, kind):
    if kind == "pdf":
        content = pdf_bytes(["First", "Second", "Third", "Fourth", "Fifth"])
        content_type = "application/pdf"
        locators = ["pages 1-4", "page 5"]
    else:
        content = (
            "<html><title>Rapport &amp; contexte</title>"
            + "<p>Paragraphe de contexte sans le mot recherché.</p>" * 400
            + "<p>Conclusion.</p></html>"
        ).encode()
        content_type = "text/html; charset=utf-8"
        locators = ["segment 1", "segment 2"]
    answer = {
        "action": "answer",
        "status": "answered",
        "answer": "Le document indique… [E1][E2]",
        "citations": ["E1", "E2"],
        "limitations": ["Document de test, aucune conclusion juridique."],
    }
    document_response = StreamResponse(content, content_type=content_type)
    client, provider, sessions = pipeline(
        monkeypatch,
        {live.DISCOVERY_URL: search_response(), URL: document_response},
        [SEARCH, OPEN, READ, READ, answer],
    )
    route = "/api/ask/stream" if stream else "/api/ask"
    response = client.post(route, json={"question": QUESTION})
    assert response.status_code == 200
    if stream:
        events = [json.loads(line) for line in response.data.splitlines()]
        assert [event["type"] for event in events] == [
            "started",
            "search",
            "open",
            "read",
            "read",
            "answer",
        ]
        payload = events[-1]["answer"]
    else:
        payload = response.json
    assert payload["status"] == "answered"
    assert [c["evidence_id"] for c in payload["citations"]] == ["E1", "E2"]
    assert [c["locator"] for c in payload["citations"]] == locators
    for citation in payload["citations"]:
        assert citation["source_url"] == URL
        assert citation["source_id"] == "official"
        assert citation["sha256"] == hashlib.sha256(content).hexdigest()
        assert citation["retrieved_at"]
    states = [json.loads(request.user_prompt) for request in provider.requests]
    assert all(state["QUESTION"] == QUESTION for state in states)
    assert states[1]["EVIDENCE_AVAILABLE"] == {}  # search alone is never evidence
    assert set(states[2]["EVIDENCE_AVAILABLE"]) == {"E1"}
    assert set(states[-1]["EVIDENCE_AVAILABLE"]) == {"E1", "E2"}  # re-read keeps identity
    assert "NEVER_USE_SEARCH_SNIPPET" not in str(states)
    expected_text = "First" if kind == "pdf" else "Paragraphe de contexte"
    assert expected_text in states[2]["EVIDENCE_AVAILABLE"]["E1"]["text"]
    assert document_response.closed
    assert [call[0] for call in sessions[-1].calls] == [live.DISCOVERY_URL, URL]


@pytest.mark.parametrize(
    "failure",
    [
        StreamResponse(status=404),
        requests.Timeout(),
        StreamResponse(chunks=[b"<html>", requests.exceptions.ChunkedEncodingError()]),
        StreamResponse(b"%PDF-1.7\nbroken", content_type="application/pdf"),
        StreamResponse(headers={"Content-Length": str(live.MAX_HTML_BYTES + 1)}),
        StreamResponse(status=302, headers={"Location": "https://evil.test/unread"}),
    ],
)
def test_source_failure_informs_agent_and_stream_ends_insufficient(monkeypatch, failure):
    client, provider, sessions = pipeline(monkeypatch, {URL: failure}, [OPEN, INSUFFICIENT])
    response = client.post("/api/ask/stream", json={"question": QUESTION})
    events = [json.loads(line) for line in response.data.splitlines()]
    assert [event["type"] for event in events] == ["started", "notice", "answer"]
    assert events[-1]["answer"]["status"] == "insufficient"
    assert events[-1]["answer"]["citations"] == []
    state = json.loads(provider.requests[-1].user_prompt)
    assert state["EVIDENCE_AVAILABLE"] == {}
    assert state["OPEN_DOCUMENTS"] == []
    assert state["RESEARCH_NOTICES"][0]["message"] == events[1]["message"]
    assert [call[0] for call in sessions[-1].calls] == [URL]


@pytest.mark.parametrize(
    "response", [StreamResponse(b"<html>No results</html>"), StreamResponse(status=503)]
)
def test_empty_or_unavailable_discovery_is_explicit_without_evidence(monkeypatch, response):
    client, provider, _ = pipeline(
        monkeypatch, {live.DISCOVERY_URL: response}, [SEARCH, INSUFFICIENT]
    )
    result = client.post("/api/ask", json={"question": QUESTION}).json
    assert result["status"] == "insufficient" and result["citations"] == []
    state = json.loads(provider.requests[-1].user_prompt)
    assert state["RESEARCH_NOTICES"][0]["message"]
    assert state["EVIDENCE_AVAILABLE"] == {} and state["SEARCH_RESULTS"] == []


def test_unread_next_segment_cannot_be_cited_after_open(monkeypatch):
    answer = {
        "action": "answer",
        "status": "answered",
        "answer": "Unfounded assertion",
        "citations": ["E2"],
        "limitations": [],
    }
    client, _, _ = pipeline(monkeypatch, {URL: StreamResponse()}, [OPEN, answer])
    response = client.post("/api/ask", json={"question": QUESTION})
    assert response.status_code == 502
    assert response.json["error"] == "ai_failure"
    assert "E2" in response.json["message"]


def test_question_cannot_reuse_previous_questions_document(monkeypatch):
    client, provider, sessions = pipeline(
        monkeypatch,
        {URL: StreamResponse()},
        [OPEN, INSUFFICIENT, {"action": "read", "document_id": "D1", "unit": 1}, INSUFFICIENT],
    )
    assert client.post("/api/ask", json={"question": QUESTION}).status_code == 200
    response = client.post("/api/ask", json={"question": QUESTION})
    assert response.json["status"] == "insufficient"
    state = json.loads(provider.requests[-1].user_prompt)
    assert state["EVIDENCE_AVAILABLE"] == {}
    assert state["RESEARCH_NOTICES"][0]["action"] == "read"
    assert sessions[-1].calls == []
