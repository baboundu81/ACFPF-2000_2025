# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

from dataclasses import replace
from datetime import date
from html.parser import HTMLParser

from acfpf.ai.civic import CivicAnswerService
from acfpf.ai.service import SCOPED_LEGISLATION_MARKER, AnswerService
from acfpf.legislation import LegislativeEvent
from acfpf.web import create_app
from acfpf.web.presentation import dossier_view
from tests.test_ai import FakeLiveResearch, FakeProvider
from tests.test_web import (
    FailingLegislationService,
    FakeAnswerService,
    FakeCofogService,
    FakeLegislationService,
    FakeMacroService,
    make_app,
    sample_dossier,
)


class Page(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.stack = []
        self.ids = []
        self.advanced_roots = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if any(
            key.startswith("data-") and key.endswith("-dossier-id") and key != "data-dossier-id"
            for key in attrs
        ):
            self.advanced_roots.append((attrs, tuple(self.stack)))
        if tag not in {"input", "meta", "link", "br", "hr"}:
            self.stack.append((tag, attrs))

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                self.stack = self.stack[:index]
                break


def test_home_does_not_wait_for_parliamentary_network_and_keeps_free_question():
    client = make_app(FakeAnswerService(), FailingLegislationService()).test_client()
    response = client.get("/")
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'id="ask-form"' in html and "Retrouver un texte" in html
    assert "Impossible d'afficher" not in html
    browsing = client.get("/?status=active")
    assert browsing.status_code == 503
    assert 'id="ask-form"' in browsing.get_data(as_text=True)


def test_dossier_chat_precedes_secondary_tools_and_data_are_collapsed():
    html = make_app(FakeAnswerService()).test_client().get("/textes/DLR1").get_data(as_text=True)
    assert html.index('id="dossier-chat-form"') < html.index('id="versions"')
    page = Page(html)
    assert len(page.ids) == len(set(page.ids))
    assert len(page.advanced_roots) == 4
    for _attrs, parents in page.advanced_roots:
        details = [attrs for tag, attrs in parents if tag == "details"]
        assert details and "open" not in details[-1]
    assert "comparaison automatique n'est encore proposée" not in html
    assert "date de récupération non renseignée" in html


def test_home_and_dashboard_share_free_question_form_without_dossier_binding():
    client = make_app(FakeAnswerService()).test_client()
    for url in ["/", "/finances"]:
        html = client.get(url).get_data(as_text=True)
        assert 'id="ask-form"' in html
        assert "data-dossier-id=" not in html
        assert 'aria-describedby="ask-hint"' in html
        assert "js/research_stream.js" in html
        assert len(Page(html).ids) == len(set(Page(html).ids))


def test_disabled_ai_does_not_block_entry_or_discovery(monkeypatch):
    monkeypatch.setattr("acfpf.web.app.build_default_civic_answer_service", lambda *args: None)
    client = make_app().test_client()
    for url in ["/", "/?status=active", "/textes/DLR1"]:
        response = client.get(url)
        assert response.status_code == 200
        assert "IA non configurée" in response.get_data(as_text=True)
    assert "Projet de loi relatif au logement" in client.get("/?status=active").get_data(
        as_text=True
    )


def test_scheduled_date_and_freshness_are_explicit_without_mutating_source():
    dossier = replace(
        sample_dossier(),
        last_activity="2026-11-20",
        retrieved_at="2026-11-06T12:00:00+00:00",
        from_cache=True,
        events=(LegislativeEvent("2026-11-20", "Séance prévue"),),
    )
    view = dossier_view(dossier, today=date(2026, 11, 6))
    assert view["activity_label"] == "Date prévue dans la source"
    assert view["events"][0]["date_is_future"] is True
    assert view["freshness_label"] == "06/11/2026 à 13:00 (Paris)"
    assert dossier.last_activity == "2026-11-20"
    assert (
        dossier_view(dossier, today=date(2026, 11, 21))["activity_label"]
        == "Dernière date renseignée"
    )


def test_home_discovery_dossier_chat_route_preserves_backend_identity():
    provider = FakeProvider(
        {"action": "open", "url": "https://www.legifrance.gouv.fr/test"},
        {
            "action": "answer",
            "status": "answered",
            "answer": "Le texte autorise les crédits.",
            "citations": ["E1"],
            "limitations": [],
        },
    )
    macro, cofog = FakeMacroService(), FakeCofogService()
    answer = CivicAnswerService(AnswerService(provider, macro, cofog, FakeLiveResearch()))
    client = create_app(
        service=macro,
        cofog_service=cofog,
        legislation_service=FakeLegislationService(),
        answer_service=answer,
    ).test_client()
    assert 'id="ask-form"' in client.get("/").get_data(as_text=True)
    assert 'href="/textes/DLR1"' in client.get("/?q=logement&assist=0").get_data(as_text=True)
    assert 'data-dossier-id="DLR1"' in client.get("/textes/DLR1").get_data(as_text=True)
    response = client.post(
        "/api/ask",
        json={
            "question": "Que prévoit ce texte ?",
            "dossier_id": "DLR1",
            "title": "INVENTED_CLIENT_TITLE",
            "official_url": "https://evil.test",
        },
    )
    assert response.status_code == 200 and response.json["citations"][0]["evidence_id"] == "E1"
    prompt = provider.requests[0].user_prompt
    assert SCOPED_LEGISLATION_MARKER in prompt and "Projet de loi relatif au logement" in prompt
    assert "INVENTED_CLIENT_TITLE" not in prompt and "evil.test" not in prompt
