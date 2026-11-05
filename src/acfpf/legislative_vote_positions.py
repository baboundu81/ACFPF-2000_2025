# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

"""Nominative positions on one *explicitly linked* Assembly public ballot.

An absent actor in the official lists is not assumed absent or abstaining.
"""

from __future__ import annotations

import json
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from acfpf.data.assemblee_votes import (
    VOTE_CACHE,
    VoteSourceError,
    load_votes,
)

_UID = re.compile(r"VTANR5L17V[0-9]+\Z")
_ACTOR = re.compile(r"PA[0-9]+\Z")
_MANDATE = re.compile(r"PM[0-9]+\Z")
_GROUP = re.compile(r"PO[0-9]+\Z")
_CATEGORIES = {
    "pours": "pour",
    "contres": "contre",
    "abstentions": "abstention",
    "nonVotants": "non_votant",
}


@dataclass(frozen=True)
class NominalPosition:
    actor_ref: str
    mandate_ref: str | None
    group_ref: str
    position: str
    by_delegation: bool | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "actor_ref": self.actor_ref,
            "mandate_ref": self.mandate_ref,
            "group_ref": self.group_ref,
            "position": self.position,
            "by_delegation": self.by_delegation,
        }


@dataclass(frozen=True)
class NominalVoteCollection:
    dossier_id: str
    vote_uid: str
    available: bool
    positions: tuple[NominalPosition, ...]
    reason: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "dossier_id": self.dossier_id,
            "vote_uid": self.vote_uid,
            "available": self.available,
            "reason": self.reason,
            "count": len(self.positions),
            "positions": [item.as_dict() for item in self.positions],
            "source_id": "assemblee_nationale_open_data",
            "interpretation": "Positions nominatives publiées ; absence de mention ≠ absence au vote",
        }


def _items(value: Any) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _flag(value: Any) -> bool | None:
    if value is True or value == "true":
        return True
    if value is False or value == "false":
        return False
    return None


def parse_nominal_positions(
    raw: bytes, *, dossier_uid: str, vote_uid: str
) -> NominalVoteCollection:
    if not _UID.fullmatch(vote_uid):
        raise VoteSourceError("Invalid official ballot UID")
    try:
        scrutin = json.loads(raw.decode("utf-8-sig")).get("scrutin")
    except (UnicodeError, json.JSONDecodeError, AttributeError) as exc:
        raise VoteSourceError("Invalid official ballot JSON") from exc
    if not isinstance(scrutin, dict) or scrutin.get("uid") != vote_uid:
        raise VoteSourceError("Official ballot UID mismatch")
    obj = scrutin.get("objet")
    dossier = obj.get("dossierLegislatif") if isinstance(obj, dict) else None
    if not isinstance(dossier, dict) or dossier.get("dossierRef") != dossier_uid:
        raise VoteSourceError("Official ballot does not reference this dossier")
    vent = scrutin.get("ventilationVotes")
    organe = vent.get("organe") if isinstance(vent, dict) else None
    groups = organe.get("groupes") if isinstance(organe, dict) else None
    entries = groups.get("groupe") if isinstance(groups, dict) else None
    if not entries:
        return NominalVoteCollection(dossier_uid, vote_uid, False, (),
                                     "Aucune ventilation nominative publiée.")
    found: dict[str, NominalPosition] = {}
    has_lists = False
    for group in _items(entries):
        if not isinstance(group, dict):
            raise VoteSourceError("Invalid official group data")
        group_ref = group.get("organeRef")
        if not isinstance(group_ref, str) or not _GROUP.fullmatch(group_ref):
            raise VoteSourceError("Missing official group identity")
        vote = group.get("vote")
        decompte = vote.get("decompteNominatif") if isinstance(vote, dict) else None
        if not isinstance(decompte, dict):
            continue
        for key, position in _CATEGORIES.items():
            category = decompte.get(key)
            voters = category.get("votant") if isinstance(category, dict) else None
            for voter in _items(voters):
                has_lists = True
                if not isinstance(voter, dict):
                    raise VoteSourceError("Invalid official voter record")
                actor_ref = voter.get("acteurRef")
                mandate_ref = voter.get("mandatRef")
                if not isinstance(actor_ref, str) or not _ACTOR.fullmatch(actor_ref):
                    raise VoteSourceError("Invalid official voter identity")
                if mandate_ref is not None and (
                    not isinstance(mandate_ref, str) or not _MANDATE.fullmatch(mandate_ref)
                ):
                    raise VoteSourceError("Invalid official mandate identity")
                item = NominalPosition(
                    actor_ref=actor_ref,
                    mandate_ref=mandate_ref,
                    group_ref=group_ref,
                    position=position,
                    by_delegation=_flag(voter.get("parDelegation")),
                )
                if actor_ref in found and found[actor_ref] != item:
                    raise VoteSourceError("Conflicting official positions for one actor")
                found[actor_ref] = item
    return NominalVoteCollection(
        dossier_id=dossier_uid, vote_uid=vote_uid, available=has_lists,
        positions=tuple(sorted(found.values(), key=lambda item: item.actor_ref)),
        reason=None if has_lists else "Aucun vote nominatif exploitable dans la source.",
    )


def load_nominal_positions(
    *, dossier_uid: str, vote_uid: str, cache_path: Path = VOTE_CACHE,
    refresh: bool = False,
) -> NominalVoteCollection:
    # The existing validated connector checks the dossier association using
    # the exact dossierRef. Reuse its cache and network policy.
    ballots = load_votes(dossier_uid=dossier_uid, cache_path=cache_path, refresh=refresh)
    if not any(ballot.uid == vote_uid for ballot in ballots):
        raise VoteSourceError("Scrutin non lié explicitement au dossier")
    if not _UID.fullmatch(vote_uid):
        raise VoteSourceError("Invalid official ballot UID")
    try:
        with zipfile.ZipFile(cache_path) as archive:
            member = f"json/{vote_uid}.json"
            if archive.getinfo(member).file_size > 2 * 1024 * 1024:
                raise VoteSourceError("Official ballot is too large")
            raw = archive.read(member)
    except (OSError, KeyError, zipfile.BadZipFile, RuntimeError) as exc:
        raise VoteSourceError("Official ballot unavailable in archive") from exc
    return parse_nominal_positions(raw, dossier_uid=dossier_uid, vote_uid=vote_uid)
