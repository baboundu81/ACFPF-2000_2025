# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

"""API for officially linked public ballots, excluding guesswork from titles."""

from collections.abc import Callable

from flask import Flask, jsonify, request

from acfpf.data.assemblee_votes import VoteSourceError, load_votes
from acfpf.legislation import LegislationError, LegislationService
from acfpf.web.amendments import _bounded_integer


def register_vote_routes(
    app: Flask, legislation_service: LegislationService, vote_loader: Callable = load_votes
) -> None:
    @app.get("/api/legislation/<dossier_id>/votes")
    def legislation_votes_api(dossier_id: str):
        try:
            limit = _bounded_integer("limit", default=25, minimum=1, maximum=100)
            offset = _bounded_integer("offset", default=0, minimum=0, maximum=100000)
            dossier = legislation_service.get(dossier_id)
        except ValueError as exc:
            return jsonify({"error": "invalid_filter", "message": str(exc)}), 400
        except LegislationError as exc:
            return jsonify({"error": "legislation_unavailable", "message": str(exc)}), 503
        if dossier is None:
            return jsonify({"error": "dossier_not_found"}), 404

        if not any(
            source.source_id == "assemblee_nationale_open_data" for source in dossier.sources
        ):
            return jsonify({
                "available": False, "reason": "Aucune référence Assemblée nationale liée.",
                "count": 0, "votes": [], "dossier_id": dossier.id,
            })

        try:
            ballots = vote_loader(
                dossier_uid=dossier.id, refresh=request.args.get("refresh") == "1"
            )
        except VoteSourceError as exc:
            return jsonify({"error": "votes_unavailable", "message": str(exc)}), 503
        return jsonify({
            "available": True,
            "dossier_id": dossier.id,
            "count": len(ballots),
            "offset": offset, "limit": limit,
            "votes": [item.as_dict() for item in ballots[offset : offset + limit]],
            "source_url": "https://data.assemblee-nationale.fr/travaux-parlementaires/votes",
            "linkage": "Uniquement sur objet.dossierLegislatif.dossierRef exact",
        })
