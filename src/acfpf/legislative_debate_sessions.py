# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors
"""Join Assembly ballots to sitting transcripts by *identical* seanceRef.

A vote concerns an official dossier, and a session contains that vote; this
does NOT establish which speeches within the sitting concern that dossier.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
import zipfile
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from acfpf.data.assemblee_debates import DebateArchive
from acfpf.data.assemblee_votes import Vote

_XML_MEMBER = re.compile(r"xml/compteRendu/(CRSANR5L17S[A-Z0-9]+)\.xml\Z")
_SESSION_REF = re.compile(r"RUANR5L17S[A-Z0-9]+\Z")
_MAX_METADATA_BYTES = 64 * 1024
_MAX_XML_BYTES = 20 * 1024 * 1024


class DebateLinkError(RuntimeError):
    """Session reference or official XML source could not be verified."""


def _metadata(xml_file: Any) -> dict[str, str]:
    result: dict[str, str] = {}
    parser = ET.XMLPullParser(events=("end",))
    bytes_read = 0
    try:
        while bytes_read < _MAX_METADATA_BYTES:
            payload = xml_file.read(min(4096, _MAX_METADATA_BYTES - bytes_read))
            if not payload:
                break
            bytes_read += len(payload)
            parser.feed(payload)
            for _, element in parser.read_events():
                tag = element.tag.split("}")[-1]
                if tag in {"uid", "seanceRef", "sessionRef", "dateSeance"} and tag not in result:
                    result[tag] = (element.text or "").strip()
                element.clear()
            if all(name in result for name in ("uid", "seanceRef", "dateSeance")):
                break
    except (ET.ParseError, OSError, RuntimeError) as exc:
        raise DebateLinkError("Official sitting XML metadata unreadable") from exc
    return result


def _source_date(raw: str | None) -> str | None:
    if not isinstance(raw, str) or not re.fullmatch(r"\d{8}\d{0,9}", raw):
        return None
    try:
        return datetime.strptime(raw[:8], "%Y%m%d").date().isoformat()
    except ValueError:
        return None


def link_sitting_transcripts(
    *, dossier_uid: str, votes: tuple[Vote, ...], archive: DebateArchive,
) -> dict[str, Any]:
    """Match only official ballot session UIDs, not titles, dates or keywords."""
    vote_refs: dict[str, set[str]] = defaultdict(set)
    for vote in votes:
        if vote.dossier_id != dossier_uid:
            raise DebateLinkError("Ballot is not linked to requested dossier")
        if vote.seance_ref:
            if not _SESSION_REF.fullmatch(vote.seance_ref):
                raise DebateLinkError("Invalid official ballot session reference")
            vote_refs[vote.seance_ref].add(vote.uid)
    linked: list[dict[str, Any]] = []
    matched_refs: set[str] = set()
    if vote_refs:
        try:
            with zipfile.ZipFile(archive.path) as source:
                for info in source.infolist():
                    match = _XML_MEMBER.fullmatch(info.filename)
                    if not match:
                        continue
                    if info.file_size > _MAX_XML_BYTES:
                        raise DebateLinkError("Official sitting XML exceeds size bound")
                    with source.open(info) as reader:
                        meta = _metadata(reader)
                    ref = meta.get("seanceRef")
                    if ref not in vote_refs:
                        continue
                    report_uid = match.group(1)
                    if meta.get("uid") != report_uid:
                        raise DebateLinkError("Official sitting XML UID mismatch")
                    matched_refs.add(ref)
                    linked.append({
                        "dossier_id": dossier_uid,
                        "session_ref": ref,
                        "transcript_uid": report_uid,
                        "session_ref_source": "compteRendu.seanceRef",
                        "vote_refs_source": "scrutin.seanceRef",
                        "dossier_link_source": "scrutin.objet.dossierLegislatif.dossierRef",
                        "linked_vote_uids": sorted(vote_refs[ref]),
                        "date": _source_date(meta.get("dateSeance")),
                        "source_url": archive.source_url,
                        "archive_retrieved_at": archive.retrieved_at,
                        "archive_from_cache": archive.from_cache,
                        "transcript_document_identified": True,
                        "debate_topic_verified": False,
                        "speech_attribution_verified": False,
                    })
        except (OSError, zipfile.BadZipFile) as exc:
            raise DebateLinkError("Official debate archive could not be read") from exc

    linked.sort(key=lambda item: (item["date"] or "", item["transcript_uid"]))
    return {
        "dossier_id": dossier_uid,
        "available": True,
        "count": len(linked),
        "sessions": linked,
        "unmatched_session_refs": sorted(set(vote_refs) - matched_refs),
        "source_url": archive.source_url,
        "linkage": "Dossier → scrutin exact → seanceRef identique dans le compte rendu XML",
        "warning": (
            "Le compte rendu identifié correspond à une séance comportant au moins "
            "un scrutin lié au dossier. La séance peut porter sur plusieurs textes. "
            "Aucun discours individuel n'est automatiquement attribué à ce dossier."
        ),
    }
