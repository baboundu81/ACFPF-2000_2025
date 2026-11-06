# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

import json

import pytest

from acfpf.ai.civic import CivicAnswerService
from acfpf.ai.grounding import REVIEW_PROMPT, REVIEW_SCHEMA, REVIEW_SCHEMA_NAME
from acfpf.ai.provider import AIGroundingError, AIProviderError
from acfpf.ai.service import SCOPED_LEGISLATION_MARKER, AnswerService
from tests.test_ai import FakeLiveResearch, FakeMacroService, FakeProvider

CANDIDATE = {
    "action": "answer",
    "status": "answered",
    "answer": "Le texte autorise des crédits.",
    "citations": ["E1"],
    "limitations": [],
}
OPEN = {
    "action": "open",
    "url": "https://www.legifrance.gouv.fr/test",
    "reason": "PRIVATE_MODEL_REASON",
}


class ReviewProvider(FakeProvider):
    def __init__(self, review, *actions):
        super().__init__(*(actions or (OPEN, CANDIDATE)))
        self.review = review

    def complete_json(self, request):
        if request.response_schema_name == REVIEW_SCHEMA_NAME:
            self.requests.append(request)
            assert request.system_prompt == REVIEW_PROMPT
            assert request.response_schema == REVIEW_SCHEMA
            if isinstance(self.review, Exception):
                raise self.review
            return self.review
        return super().complete_json(request)


def service(provider):
    return CivicAnswerService(
        AnswerService(provider, FakeMacroService(), live_research=FakeLiveResearch())
    )


@pytest.mark.parametrize("scoped", [False, True])
@pytest.mark.parametrize(
    "review",
    [
        {"supported": False, "citations": ["E1"], "issues": ["unsupported_claim"]},
        {"supported": True, "citations": ["E2"], "issues": []},
        {"supported": True, "citations": ["E1"], "issues": ["wrong_version"]},
    ],
)
def test_rejected_review_never_publishes_candidate_for_free_or_scoped_question(scoped, review):
    provider = ReviewProvider(review)
    events = list(
        service(provider).iter_ask(
            (SCOPED_LEGISLATION_MARKER if scoped else "") + "Que prévoit ce texte ?"
        )
    )
    answer = events[-1].answer
    assert answer.status == "insufficient" and answer.citations == ()
    assert CANDIDATE["answer"] not in answer.answer
    assert "PRIVATE_MODEL_REASON" not in json.dumps([e.as_dict() for e in events])
    state = json.loads(provider.requests[-1].user_prompt)
    assert state["EVIDENCE_AVAILABLE"]["E1"]["text"]
    assert state["CITATIONS_USED"][0]["sha256"] == "abc123"
    assert "SEARCH_RESULTS" not in state


@pytest.mark.parametrize(
    "review",
    [
        None,
        {},
        {"supported": "true", "citations": ["E1"], "issues": []},
        {"supported": True, "citations": ["E1"], "issues": ["invented_issue"]},
    ],
)
def test_invalid_review_does_not_release_candidate(review):
    with pytest.raises(AIGroundingError):
        service(ReviewProvider(review)).ask("Texte ?")


def test_verifier_outage_is_an_error_and_no_answer_is_emitted():
    events = []
    with pytest.raises(AIProviderError):
        for event in service(
            ReviewProvider(AIProviderError("verification indisponible", code="timeout"))
        ).iter_ask("Texte ?"):
            events.append(event)  # noqa: PERF402 - retain events emitted before the expected exception
    assert all(event.type != "answer" for event in events)
    assert events[-1].payload["message"].startswith("Vérification")


def test_initial_progress_precedes_numeric_loading_and_context_is_bounded():
    class HugeContext(AnswerService):
        def _build_numeric_context(self):
            return {"huge": "x" * 128000}, {}

    provider = FakeProvider()
    stream = HugeContext(provider, FakeMacroService()).iter_ask("Question")
    assert next(stream).type == "started"
    answer = next(stream).answer
    assert answer.status == "insufficient"
    assert provider.requests == []


def test_insufficient_payload_does_not_echo_unverified_assertions():
    provider = FakeProvider(
        {
            "action": "answer",
            "status": "insufficient",
            "answer": "FALSE_ASSERTION",
            "citations": [],
            "limitations": ["FALSE_LIMITATION"],
        }
    )
    result = service(provider).ask("Texte ?").as_dict()
    assert "FALSE_" not in json.dumps(result)


@pytest.mark.parametrize(
    "text",
    [
        "Affirmation [E99]",
        "Affirmation [E1, E99]",
        "Voir https://evil.test/unread",
        "Voir [un autre document](https://www.legifrance.gouv.fr/never-read)",
    ],
)
def test_inline_unread_references_are_refused_even_with_a_known_citation(text):
    candidate = {**CANDIDATE, "answer": text}
    provider = ReviewProvider(
        {"supported": True, "citations": ["E1"], "issues": []}, OPEN, candidate
    )
    with pytest.raises(AIGroundingError):
        service(provider).ask("Texte ?")
    assert not any(
        request.response_schema_name == REVIEW_SCHEMA_NAME for request in provider.requests
    )


def test_quota_retry_resumes_same_request_and_is_visible(monkeypatch):
    from acfpf.ai import service as service_module

    waits = []
    monkeypatch.setattr(service_module.time, "sleep", waits.append)

    class RateLimitedOnce(FakeProvider):
        def __init__(self):
            super().__init__(OPEN, CANDIDATE)
            self.first = True

        def complete_json(self, request):
            if self.first:
                self.first = False
                raise AIProviderError("Quota", code="rate_limited", retry_after=7)
            return super().complete_json(request)

    events = list(service(RateLimitedOnce()).iter_ask("Texte ?"))
    assert waits == [7]
    assert events[-1].answer.status == "answered"
    assert any("reprise dans 7" in event.payload.get("message", "") for event in events)


def test_persistent_quota_is_not_retried_indefinitely(monkeypatch):
    from acfpf.ai import service as service_module

    waits = []
    monkeypatch.setattr(service_module.time, "sleep", waits.append)

    class AlwaysLimited:
        name = "fake"
        model = "fake"

        def complete_json(self, request):
            raise AIProviderError("Quota", code="rate_limited", retry_after=1)

    with pytest.raises(AIProviderError):
        service(AlwaysLimited()).ask("Texte ?")
    assert len(waits) == service_module.MAX_QUOTA_RETRIES


def test_long_quota_wait_is_reported_without_blocking(monkeypatch):
    from acfpf.ai import service as service_module

    monkeypatch.setattr(service_module.time, "sleep", lambda _: pytest.fail("Must not wait"))

    class LongWait:
        name = "fake"
        model = "fake"

        def complete_json(self, request):
            raise AIProviderError("Quota", code="rate_limited", retry_after=600)

    with pytest.raises(AIProviderError):
        service(LongWait()).ask("Texte ?")


def test_scoped_backend_context_can_exceed_free_question_limit():
    provider = FakeProvider(
        {
            "action": "answer",
            "status": "insufficient",
            "answer": "Non établi.",
            "citations": [],
            "limitations": [],
        }
    )
    assert service(provider).ask(SCOPED_LEGISLATION_MARKER + "x" * 1600).status == "insufficient"
