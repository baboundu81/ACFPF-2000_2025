# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

"""A dossier answer must cite a passage of an opened official document."""

from acfpf.ai.civic import CivicAnswerService
from acfpf.ai.service import AnswerService, SCOPED_LEGISLATION_MARKER
from tests.test_ai import FakeLiveResearch, FakeMacroService, FakeProvider


SCOPED = (
    SCOPED_LEGISLATION_MARKER
    + " Dossier: Projet de loi. Identifiant: DLR1. "
    + "Question actuelle de l'utilisateur: Que prévoit ce texte ?"
)


def test_dossier_answer_with_only_numeric_citation_is_not_established():
    provider = FakeProvider({
        "action": "answer", "status": "answered",
        "answer": "Ce projet de loi impose une obligation.",
        "citations": ["S1"], "limitations": [],
    })
    service = CivicAnswerService(AnswerService(provider, FakeMacroService()))
    answer = service.ask(SCOPED)
    assert answer.status == "insufficient"
    assert answer.citations == ()
    assert "document officiel" in answer.answer
    assert "métadonnées de dossier" in answer.limitations[0]


def test_dossier_answer_with_live_read_official_evidence_is_allowed():
    provider = FakeProvider(
        {
            "action": "open",
            "url": "https://www.legifrance.gouv.fr/test",
            "reason": "Lire le passage officiel.",
        },
        {
            "action": "answer", "status": "answered",
            "answer": "Le texte publié indique une disposition concernant les crédits.",
            "citations": ["E1"], "limitations": [],
        },
    )
    service = CivicAnswerService(AnswerService(
        provider, FakeMacroService(), live_research=FakeLiveResearch(),
    ))
    answer = service.ask(SCOPED)
    assert answer.status == "answered"
    assert len(answer.citations) == 1
    assert answer.citations[0].evidence_id == "E1"
    assert answer.citations[0].sha256 == "abc123"


def test_finance_question_can_still_use_statistical_series_alone():
    provider = FakeProvider({
        "action": "answer", "status": "answered",
        "answer": "Le ratio observé a augmenté.",
        "citations": ["S1"], "limitations": [],
    })
    service = CivicAnswerService(AnswerService(provider, FakeMacroService()))
    answer = service.ask("Quelle est l'évolution des dépenses publiques ?")
    assert answer.status == "answered"
    assert [citation.id for citation in answer.citations] == ["S1"]


def test_insufficient_without_live_citations_is_preserved():
    provider = FakeProvider({
        "action": "answer", "status": "insufficient",
        "answer": "Le texte applicable n'a pas été vérifié.",
        "citations": [], "limitations": ["Aucun texte officiel lu."],
    })
    service = CivicAnswerService(AnswerService(provider, FakeMacroService()))
    answer = service.ask(SCOPED)
    assert answer.status == "insufficient"
    assert answer.limitations == ("Aucun texte officiel lu.",)
