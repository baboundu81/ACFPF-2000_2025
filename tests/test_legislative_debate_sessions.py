# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors
"""A sitting transcript is linked only through a verified ballot session UID."""

import zipfile
from io import BytesIO

import pytest

from acfpf.data.assemblee_debates import DebateArchive, DEBATES_ARCHIVE_URL
from acfpf.data.assemblee_votes import Vote
from acfpf.legislative_debate_sessions import DebateLinkError, link_sitting_transcripts
from acfpf.web import create_app
from tests.test_web import FakeCofogService, FakeLegislationService, FakeMacroService

DOSSIER = "DLR123456"
SESSION = "RUANR5L17S2027IDS30918"
OTHER_SESSION = "RUANR5L17S2027IDS30919"
UID = "CRSANR5L17S2027O1N001"


def vote(ref=DOSSIER, session=SESSION, uid="VTANR5L17V1234"):
    return Vote(
        uid=uid, number="1234", date="2026-10-01",
        title="Scrutin officiel", result="adopté",
        pour=15, contre=4, abstentions=1,
        dossier_id=ref, seance_ref=session,
    )


def xml(uid=UID, session=SESSION, *, date="20261001090000000"):
    return (
        f"<compteRendu><uid>{uid}</uid><seanceRef>{session}</seanceRef>"
        f"<sessionRef>SCR5A2027O1</sessionRef>"
        f"<metadonnees><dateSeance>{date}</dateSeance></metadonnees>"
        "<contenu><paragraphe>Autre débat indépendant</paragraphe></contenu>"
        "</compteRendu>"
    ).encode()


def archive(tmp_path, *, xml_blob=None, uid=UID):
    path = tmp_path / "sessions.zip"
    with zipfile.ZipFile(path, "w") as file:
        file.writestr(
            f"xml/compteRendu/{uid}.xml",
            xml_blob if xml_blob is not None else xml(uid=uid),
        )
        file.writestr(
            "xml/compteRendu/CRSANR5L17S2027O1N002.xml",
            xml(uid="CRSANR5L17S2027O1N002", session=OTHER_SESSION),
        )
    return DebateArchive(
        path=path, source_url=DEBATES_ARCHIVE_URL,
        bytes_downloaded=path.stat().st_size,
        retrieved_at="2026-11-06T00:30:00+00:00", from_cache=True,
    )


def test_ballot_to_transcript_link_requires_matching_official_session_ref(tmp_path):
    result = link_sitting_transcripts(
        dossier_uid=DOSSIER,
        votes=(vote(), vote(uid="VTANR5L17V5678")),
        archive=archive(tmp_path),
    )
    assert result["count"] == 1
    item = result["sessions"][0]
    assert item["transcript_uid"] == UID
    assert item["session_ref"] == SESSION
    assert item["date"] == "2026-10-01"
    assert item["linked_vote_uids"] == ["VTANR5L17V1234", "VTANR5L17V5678"]
    assert item["transcript_document_identified"] is True
    assert item["debate_topic_verified"] is False
    assert item["speech_attribution_verified"] is False
    assert result["unmatched_session_refs"] == []


def test_different_session_is_not_claimed_as_debate_on_dossier(tmp_path):
    result = link_sitting_transcripts(
        dossier_uid=DOSSIER,
        votes=(vote(session="RUANR5L17S2025IDS99999"),),
        archive=archive(tmp_path),
    )
    assert result["count"] == 0
    assert result["unmatched_session_refs"] == ["RUANR5L17S2025IDS99999"]


def test_cross_dossier_vote_is_rejected_before_any_xml_link(tmp_path):
    with pytest.raises(DebateLinkError, match="not linked"):
        link_sitting_transcripts(
            dossier_uid=DOSSIER, votes=(vote(ref="DLR999999"),),
            archive=archive(tmp_path),
        )


def test_report_uid_mismatch_is_rejected(tmp_path):
    bad = archive(tmp_path, xml_blob=xml(uid="CRSANR5L17S2027O1N003"))
    with pytest.raises(DebateLinkError, match="UID mismatch"):
        link_sitting_transcripts(dossier_uid=DOSSIER, votes=(vote(),), archive=bad)


def test_linked_sessions_endpoint_pages_without_fetching_when_no_ballot_reference(tmp_path):
    checked = []
    source = archive(tmp_path)
    app = create_app(
        service=FakeMacroService(), cofog_service=FakeCofogService(),
        legislation_service=FakeLegislationService(),
        vote_loader=lambda **kwargs: (vote(ref="DLR1"),),
        debate_archive_loader=lambda **kwargs: checked.append(kwargs) or source,
    )
    client = app.test_client()
    assert client.get("/api/legislation/UNKNOWN/debates/linked-sessions").status_code == 404
    assert client.get("/api/legislation/DLR1/debates/linked-sessions?limit=invalid").status_code == 400
    response = client.get("/api/legislation/DLR1/debates/linked-sessions?limit=1")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["count"] == 1
    assert payload["sessions"][0]["session_ref"] == SESSION
    assert payload["session_linkage_verified"] is True
    assert checked == [{"refresh": False}]

    no_reference = create_app(
        service=FakeMacroService(), cofog_service=FakeCofogService(),
        legislation_service=FakeLegislationService(),
        vote_loader=lambda **kwargs: (vote(ref="DLR1", session=None),),
        debate_archive_loader=lambda **kwargs: pytest.fail("Archive must not be downloaded"),
    )
    result = no_reference.test_client().get("/api/legislation/DLR1/debates/linked-sessions")
    assert result.status_code == 200
    assert result.get_json()["session_linkage_verified"] is False
