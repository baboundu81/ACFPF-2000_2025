# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

"""Nominative ballot tests: never deduce an actor's position from absence."""

import json
import zipfile

import pytest

from acfpf.data.assemblee_votes import VoteSourceError
from acfpf.legislative_vote_positions import (
    NominalVoteCollection,
    load_nominal_positions,
    parse_nominal_positions,
)
from acfpf.web import create_app
from tests.test_web import FakeCofogService, FakeLegislationService, FakeMacroService

DOSSIER = "DLR123456"
SCRUTIN = "VTANR5L17V1234"


def ballot(*, dossier=DOSSIER, groups=None):
    if groups is None:
        groups = [
            {"organeRef": "PO123", "vote": {"decompteNominatif": {
                "pours": {"votant": [
                    {"acteurRef": "PA1", "mandatRef": "PM1", "parDelegation": "true"},
                    {"acteurRef": "PA2", "mandatRef": "PM2", "parDelegation": "false"},
                ]},
                "contres": {"votant": {
                    "acteurRef": "PA3", "mandatRef": "PM3", "parDelegation": "false",
                }},
                "abstentions": None, "nonVotants": None,
            }}}
        ]
    return {"scrutin": {
        "uid": SCRUTIN, "numero": "1234", "dateScrutin": "2026-11-05",
        "objet": {"dossierLegislatif": {"dossierRef": dossier}},
        "ventilationVotes": {"organe": {"groupes": {"groupe": groups}}},
    }}


def payload(**kwargs):
    return json.dumps(ballot(**kwargs)).encode()


def test_parses_official_nested_nominal_votes_without_guessing_absentees():
    result = parse_nominal_positions(payload(), dossier_uid=DOSSIER, vote_uid=SCRUTIN)
    assert result.available
    assert len(result.positions) == 3
    assert [item.actor_ref for item in result.positions] == ["PA1", "PA2", "PA3"]
    assert [item.position for item in result.positions] == ["pour", "pour", "contre"]
    assert result.positions[0].by_delegation is True
    assert result.positions[1].by_delegation is False
    assert "absence de mention" in result.as_dict()["interpretation"].lower()


def test_refuses_cross_dossier_and_wrong_ballot_identity():
    with pytest.raises(VoteSourceError, match="does not reference"):
        parse_nominal_positions(payload(dossier="DLR999999"), dossier_uid=DOSSIER, vote_uid=SCRUTIN)
    with pytest.raises(VoteSourceError, match="ballot UID mismatch"):
        parse_nominal_positions(payload(), dossier_uid=DOSSIER, vote_uid="VTANR5L17V9999")


def test_conflicting_actor_positions_fail_closed():
    conflict = [{"organeRef": "PO123", "vote": {"decompteNominatif": {
        "pours": {"votant": {"acteurRef": "PA1"}},
        "contres": {"votant": {"acteurRef": "PA1"}},
    }}}]
    with pytest.raises(VoteSourceError, match="Conflicting"):
        parse_nominal_positions(payload(groups=conflict), dossier_uid=DOSSIER, vote_uid=SCRUTIN)


def test_missing_nominal_data_is_not_claimed_to_be_zero_votes():
    record = ballot(groups=[{"organeRef": "PO123", "vote": {"decompteNominatif": None}}])
    data = json.dumps(record).encode()
    result = parse_nominal_positions(data, dossier_uid=DOSSIER, vote_uid=SCRUTIN)
    assert result.available is False
    assert result.reason


def test_load_requires_scrutin_present_in_official_archive_cache(tmp_path):
    cache = tmp_path / "votes.zip"
    with zipfile.ZipFile(cache, "w") as archive:
        archive.writestr(f"json/{SCRUTIN}.json", payload())
    result = load_nominal_positions(dossier_uid=DOSSIER, vote_uid=SCRUTIN, cache_path=cache)
    assert len(result.positions) == 3
    with pytest.raises(VoteSourceError, match="non lié"):
        load_nominal_positions(
            dossier_uid="DLR999999", vote_uid=SCRUTIN, cache_path=cache,
        )


def test_api_paginates_nominative_positions_and_preserves_dossier_scope():
    official = parse_nominal_positions(payload(), dossier_uid=DOSSIER, vote_uid=SCRUTIN)
    def loader(**kwargs):
        assert kwargs["dossier_uid"] == "DLR1"
        assert kwargs["vote_uid"] == SCRUTIN
        return NominalVoteCollection("DLR1", SCRUTIN, True, official.positions)
    app = create_app(
        service=FakeMacroService(),
        cofog_service=FakeCofogService(),
        legislation_service=FakeLegislationService(),
        vote_position_loader=loader,
    )
    client = app.test_client()
    assert client.get(f"/api/legislation/UNKNOWN/votes/{SCRUTIN}/positions").status_code == 404
    response = client.get(f"/api/legislation/DLR1/votes/{SCRUTIN}/positions?limit=1&offset=1")
    assert response.status_code == 200
    document = response.get_json()
    assert document["count"] == 3
    assert [item["actor_ref"] for item in document["positions"]] == ["PA2"]
    assert document["dossier_id"] == "DLR1"
