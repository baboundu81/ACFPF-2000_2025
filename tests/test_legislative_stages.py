# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

from types import SimpleNamespace

from acfpf.legislative_stages import (
    classify_assembly_stage,
    classify_dossier_stage,
    classify_senate_stage,
    enrich_dossier_payload,
)


def test_assembly_stage_mapping_is_conservative_and_ordered() -> None:
    assert classify_assembly_stage("Dépôt à l'Assemblée nationale").code == "deposit"
    assert classify_assembly_stage("Examen en commission").code == "committee"
    assert classify_assembly_stage("Discussion en séance publique").code == "plenary"
    assert classify_assembly_stage("Deuxième lecture au Sénat").code == "shuttle"
    assert classify_assembly_stage("Commission mixte paritaire").code == "cmp"
    assert classify_assembly_stage("Saisine du Conseil constitutionnel").code == "constitutional_review"
    assert classify_assembly_stage("Promulgation de la loi").code == "promulgated"
    assert classify_assembly_stage("Étape interne non documentée").code == "unknown"


def test_assembly_cmp_is_not_misclassified_as_generic_committee() -> None:
    result = classify_assembly_stage("Réunion de la commission mixte paritaire")

    assert result.code == "cmp"
    assert result.label == "Commission mixte paritaire"


def test_senate_documented_states_map_to_stable_stages() -> None:
    assert classify_senate_stage("Première lecture au Sénat").code == "plenary"
    assert classify_senate_stage("Deuxième lecture à l'Assemblée nationale").code == "shuttle"
    assert classify_senate_stage("Nouvelle lecture au Sénat").code == "shuttle"
    assert classify_senate_stage("Commission mixte paritaire").code == "cmp"
    assert classify_senate_stage("Congrès du Parlement").code == "congress"
    assert classify_senate_stage("Lecture définitive (AN)").code == "plenary"
    assert classify_senate_stage("adopté").code == "adopted"
    assert classify_senate_stage("non adopté").code == "closed"
    assert classify_senate_stage("caduc").code == "closed"
    assert classify_senate_stage("non conforme").code == "constitutional_review"
    assert classify_senate_stage("promulgué").code == "promulgated"


def test_senate_explicit_dates_can_establish_terminal_stage() -> None:
    assert classify_senate_stage(None, promulgation_date="2026-10-01").code == "promulgated"
    assert classify_senate_stage(None, constitutional_date="2026-09-20").code == "constitutional_review"


def test_unknown_senate_state_stays_unknown() -> None:
    result = classify_senate_stage("État futur non reconnu")

    assert result.code == "unknown"
    assert result.label == "Étape à vérifier"


def test_terminal_dossier_status_has_priority_over_ambiguous_raw_stage() -> None:
    dossier = SimpleNamespace(status="promulgated", current_stage="Étape interne non documentée")

    assert classify_dossier_stage(dossier).code == "promulgated"


def test_closed_non_conformity_keeps_constitutional_review_as_last_stage() -> None:
    dossier = SimpleNamespace(status="closed_without_law", current_stage="non conforme")

    assert classify_dossier_stage(dossier).code == "constitutional_review"


def test_dossier_stage_does_not_guess_unrecognized_active_label() -> None:
    dossier = SimpleNamespace(status="active", current_stage="Étape future non documentée")

    assert classify_dossier_stage(dossier).code == "unknown"


def test_enrich_payload_adds_stage_without_replacing_raw_source_label() -> None:
    event = SimpleNamespace(label="Examen en commission", code="COM")

    class FakeDossier:
        status = "active"
        current_stage = "Deuxième lecture au Sénat"
        events = (event,)

        def as_dict(self, *, include_events=True):
            payload = {"current_stage": self.current_stage}
            if include_events:
                payload["events"] = [{"label": event.label, "code": event.code}]
            return payload

    payload = enrich_dossier_payload(FakeDossier())

    assert payload["current_stage"] == "Deuxième lecture au Sénat"
    assert payload["stage"] == "shuttle"
    assert payload["stage_label"] == "Navette parlementaire"
    assert payload["events"][0]["stage"] == "committee"
