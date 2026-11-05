# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

"""Actor identity enrichment is exclusively UID-based, not fuzzy names."""

import json
import zipfile

import pytest
import requests

from acfpf.data.assemblee_actors import (
    ActorDirectoryError,
    parse_actor_identity,
    resolve_actor_names,
)
from acfpf.legislative_vote_positions import NominalVoteCollection, NominalPosition
from acfpf.web import create_app
from tests.test_web import FakeCofogService, FakeLegislationService, FakeMacroService


def actor(uid="PA123", first="Alice", last="Durand"):
    return json.dumps({"acteur": {
        "uid": {"#text": uid},
        "etatCivil": {"ident": {"prenom": first, "nom": last}},
    }}).encode()


def write_archive(path):
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("json/acteur/PA123.json", actor())
        archive.writestr("json/acteur/PA999.json", actor("PA999", "Bob", "Martin"))


def test_actor_id_matches_official_json_and_is_not_approximated():
    assert parse_actor_identity(actor(), actor_ref="PA123") == "Alice Durand"
    with pytest.raises(ActorDirectoryError, match="UID mismatch"):
        parse_actor_identity(actor("PA999"), actor_ref="PA123")
    with pytest.raises(ActorDirectoryError, match="Malformed"):
        parse_actor_identity(b"{", actor_ref="PA123")
    assert parse_actor_identity(actor(first="", last="Durand"), actor_ref="PA123") is None


def test_directory_reads_only_exact_members_with_missing_left_unknown(tmp_path):
    cache = tmp_path / "actors.zip"
    write_archive(cache)
    names = resolve_actor_names(["PA999", "PA123", "PA000", "PA123"], cache_path=cache)
    assert names == {"PA999": "Bob Martin", "PA123": "Alice Durand", "PA000": None}
    with pytest.raises(ActorDirectoryError, match="Invalid"):
        resolve_actor_names(["../PA123"], cache_path=cache)
    with pytest.raises(ActorDirectoryError, match="Invalid"):
        resolve_actor_names(["PA123"] * 201 + [f"PA{i}" for i in range(201)], cache_path=cache)


def test_source_down_does_not_invent_actor_data(tmp_path):
    def failed_http(*args, **kwargs):
        raise requests.ConnectionError("simulated outage")

    with pytest.raises(ActorDirectoryError, match="unavailable"):
        resolve_actor_names(["PA123"], cache_path=tmp_path / "missing.zip", http_get=failed_http)


def test_directory_validates_download_and_does_not_follow_redirect(tmp_path):
    source = tmp_path / "source.zip"
    write_archive(source)
    class FakeResponse:
        status_code = 200
        content = source.read_bytes()

    calls = []
    def fake_http(url, **kwargs):
        calls.append((url, kwargs))
        return FakeResponse()

    names = resolve_actor_names(["PA123"], cache_path=tmp_path / "cache.zip", http_get=fake_http)
    assert names == {"PA123": "Alice Durand"}
    assert calls[0][1]["allow_redirects"] is False


def test_positions_api_enriches_name_and_survives_directory_failure():
    position = NominalPosition(
        actor_ref="PA123", mandate_ref="PM1", group_ref="PO2",
        position="pour", by_delegation=False,
    )
    votes = NominalVoteCollection("DLR1", "VTANR5L17V1234", True, (position,))

    def loader(**kwargs):
        assert kwargs["dossier_uid"] == "DLR1"
        return votes

    app = create_app(
        service=FakeMacroService(), cofog_service=FakeCofogService(),
        legislation_service=FakeLegislationService(), vote_position_loader=loader,
        vote_actor_resolver=lambda refs: {"PA123": "Alice Durand"},
    )
    path = "/api/legislation/DLR1/votes/VTANR5L17V1234/positions?names=1"
    payload = app.test_client().get(path).get_json()
    assert payload["positions"][0]["actor_name"] == "Alice Durand"
    assert payload["positions"][0]["actor_ref"] == "PA123"
    assert payload["actor_names_available"] is True

    def unavailable(_refs):
        raise ActorDirectoryError("Unavailable")

    bad = create_app(
        service=FakeMacroService(), cofog_service=FakeCofogService(),
        legislation_service=FakeLegislationService(), vote_position_loader=loader,
        vote_actor_resolver=unavailable,
    )
    response = bad.test_client().get(path)
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["positions"][0]["actor_ref"] == "PA123"
    assert "actor_name" not in payload["positions"][0]
    assert payload["actor_names_available"] is False
    assert payload["actor_names_warning"]


def test_actor_zip_no_identity_mixup(tmp_path):
    path = tmp_path / "actors.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("json/acteur/PA123.json", actor("PA999"))
    with pytest.raises(ActorDirectoryError, match="UID mismatch"):
        resolve_actor_names(["PA123"], cache_path=path)
