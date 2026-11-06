# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors
"""Debate references and exact vote-to-sitting links, never speech attribution."""

from collections.abc import Callable

from flask import Flask, jsonify, request

from acfpf.data.assemblee_debates import DebateArchiveError, download_debate_archive
from acfpf.data.assemblee_votes import VoteSourceError, load_votes
from acfpf.legislation import LegislationError, LegislationService
from acfpf.legislative_debate_sessions import DebateLinkError, link_sitting_transcripts
from acfpf.legislative_debates import debate_references
from acfpf.web.amendments import _bounded_integer


def register_debate_routes(
    app: Flask, service: LegislationService,
    vote_loader: Callable = load_votes,
    archive_loader: Callable = download_debate_archive,
) -> None:
    @app.get("/api/legislation/<dossier_id>/debates")
    def legislative_debates_api(dossier_id: str):
        try:
            dossier = service.get(dossier_id)
        except LegislationError as exc:
            return jsonify({"error": "legislation_unavailable", "message": str(exc)}), 503
        if dossier is None:
            return jsonify({"error": "dossier_not_found"}), 404
        return jsonify(debate_references(dossier))

    @app.get("/api/legislation/<dossier_id>/debates/linked-sessions")
    def legislative_debate_sessions_api(dossier_id: str):
        try:
            limit = _bounded_integer("limit", default=20, minimum=1, maximum=100)
            offset = _bounded_integer("offset", default=0, minimum=0, maximum=100000)
            dossier = service.get(dossier_id)
        except ValueError as exc:
            return jsonify({"error": "invalid_filter", "message": str(exc)}), 400
        except LegislationError as exc:
            return jsonify({"error": "legislation_unavailable", "message": str(exc)}), 503
        if dossier is None:
            return jsonify({"error": "dossier_not_found"}), 404
        if not any(
            s.source_id == "assemblee_nationale_open_data" for s in dossier.sources
        ):
            return jsonify({
                "available": False, "dossier_id": dossier.id,
                "count": 0, "sessions": [],
                "reason": "Aucune référence Assemblée nationale associée.",
            })
        refresh = request.args.get("refresh") == "1"
        try:
            votes = tuple(vote_loader(dossier_uid=dossier.id, refresh=refresh))
            if not any(vote.seance_ref for vote in votes):
                return jsonify({
                    "available": True, "dossier_id": dossier.id,
                    "count": 0, "sessions": [],
                    "reason": "Aucun scrutin lié ne fournit de référence de séance.",
                    "session_linkage_verified": False,
                })
            archive = archive_loader(refresh=refresh)
            result = link_sitting_transcripts(
                dossier_uid=dossier.id, votes=votes, archive=archive,
            )
        except (VoteSourceError, DebateArchiveError, DebateLinkError) as exc:
            return jsonify({"error": "debate_sessions_unavailable", "message": str(exc)}), 503
        result["limit"] = limit
        result["offset"] = offset
        result["sessions"] = result["sessions"][offset : offset + limit]
        result["session_linkage_verified"] = result["count"] > 0
        return jsonify(result)
