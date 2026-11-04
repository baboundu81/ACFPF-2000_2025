# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

"""Scrutins publics reliés aux dossiers par une référence officielle explicite."""

from __future__ import annotations

import json
import re
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path

import requests

VOTE_ZIP = ("https://data.assemblee-nationale.fr/static/openData/repository/"
            "17/loi/scrutins/Scrutins.json.zip")
VOTE_SOURCE = "https://data.assemblee-nationale.fr/travaux-parlementaires/votes"
VOTE_CACHE = Path.home() / ".cache/acfpf/assembly_votes17.zip"


class VoteSourceError(RuntimeError):
    pass


@dataclass(frozen=True)
class Vote:
    uid: str
    number: str
    date: str | None
    title: str
    result: str | None
    pour: int | None
    contre: int | None
    abstentions: int | None
    dossier_id: str

    def as_dict(self):
        return {
            "uid": self.uid, "number": self.number, "date": self.date,
            "title": self.title, "result": self.result,
            "pour": self.pour, "contre": self.contre, "abstentions": self.abstentions,
            "dossier_id": self.dossier_id, "linked_by": "objet.dossierLegislatif.dossierRef",
            "official_url": f"https://www.assemblee-nationale.fr/dyn/17/scrutins/{self.number}",
            "source_id": "assemblee_nationale_open_data",
        }


def _count(value):
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return value
    if isinstance(value, str) and value.isdecimal():
        return int(value)
    return None


def parse_votes_archive(blob: bytes, *, dossier_uid: str) -> tuple[Vote, ...]:
    if not re.fullmatch(r"DLR[A-Za-z0-9_-]{5,100}", dossier_uid):
        raise VoteSourceError("Invalid official dossier UID")
    found = {}
    try:
        with zipfile.ZipFile(BytesIO(blob)) as archive:
            for name in archive.namelist():
                if not name.endswith(".json"):
                    continue
                raw = archive.read(name)
                if dossier_uid.encode("ascii") not in raw:
                    continue
                try:
                    scrutin = json.loads(raw).get("scrutin", {})
                except (UnicodeError, json.JSONDecodeError):
                    continue
                if not isinstance(scrutin, dict):
                    continue
                obj = scrutin.get("objet") or {}
                dossier = obj.get("dossierLegislatif") if isinstance(obj, dict) else None
                if not isinstance(dossier, dict) or dossier.get("dossierRef") != dossier_uid:
                    continue
                uid, number = scrutin.get("uid"), scrutin.get("numero")
                if not isinstance(uid, str) or not str(number).isdecimal():
                    continue
                summary = scrutin.get("syntheseVote") or {}
                counts = summary.get("decompte") or {} if isinstance(summary, dict) else {}
                outcome = scrutin.get("sort") or {}
                vote = Vote(
                    uid=uid, number=str(number), date=scrutin.get("dateScrutin"),
                    title=scrutin.get("titre") or obj.get("libelle") or "Scrutin public",
                    result=outcome.get("libelle") if isinstance(outcome, dict) else None,
                    pour=_count(counts.get("pour")),
                    contre=_count(counts.get("contre")),
                    abstentions=_count(counts.get("abstentions")),
                    dossier_id=dossier_uid,
                )
                found[uid] = vote
    except (OSError, zipfile.BadZipFile) as exc:
        raise VoteSourceError("Unreadable official voting archive") from exc
    return tuple(sorted(found.values(), key=lambda vote: (vote.date or "", int(vote.number))))


def load_votes(*, dossier_uid: str, cache_path: Path = VOTE_CACHE, refresh=False):
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    if cache_path.exists() and not refresh:
        if datetime.now(UTC).timestamp() - cache_path.stat().st_mtime <= 21600:
            return parse_votes_archive(cache_path.read_bytes(), dossier_uid=dossier_uid)
    try:
        response = requests.get(VOTE_ZIP, timeout=(15, 90))
        response.raise_for_status()
        payload = bytes(response.content)
        votes = parse_votes_archive(payload, dossier_uid=dossier_uid)
        cache_path.write_bytes(payload)
        return votes
    except (requests.RequestException, VoteSourceError) as exc:
        if cache_path.exists():
            return parse_votes_archive(cache_path.read_bytes(), dossier_uid=dossier_uid)
        raise VoteSourceError("Official vote source unavailable") from exc
