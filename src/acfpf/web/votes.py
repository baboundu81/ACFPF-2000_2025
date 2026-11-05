# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

"""API for officially linked public ballots, excluding guesswork from titles."""

from collections.abc import Callable

from flask import Flask, jsonify, request

from acfpf.data.assemblee_actors import (
    ACTORS_SOURCE,
    ActorDirectoryError,
    resolve_actor_names,
)
from acfpf.data.assemblee_votes import VoteSourceError, load_votes
from acfpf.legislation import LegislationError, LegislationService
from acfpf.legislative_vote_positions import load_nominal_positions
from acfpf.web.amendments import _bounded_integer


def register_vote_routes(
    app: Flask, legislation_service: LegislationService, vote_loader: Callable = load_votes,
    position_loader: Callable = load_nominal_positions,
    actor_resolver: Callable = resolve_actor_names,
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

    @app.get("/api/legislation/<dossier_id>/votes/<vote_uid>/positions")
    def legislative_nominal_vote_api(dossier_id: str, vote_uid: str):
        try:
            limit = _bounded_integer("limit", default=50, minimum=1, maximum=200)
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
                "count": 0, "positions": [], "dossier_id": dossier.id,
            })
        try:
            collection = position_loader(
                dossier_uid=dossier.id, vote_uid=vote_uid,
                refresh=request.args.get("refresh") == "1",
            )
        except VoteSourceError as exc:
            return jsonify({"error": "vote_positions_unavailable", "message": str(exc)}), 503
        payload = collection.as_dict()
        page = collection.positions[offset:offset + limit]
        entries = [item.as_dict() for item in page]
        payload["actor_names_available"] = False
        if request.args.get("names") == "1" and entries:
            try:
                resolved = actor_resolver([item.actor_ref for item in page])
            except ActorDirectoryError:
                payload["actor_names_warning"] = (
                    "Annuaire historique indisponible : identifiants officiels conservés."
                )
            else:
                payload["actor_names_available"] = True
                payload["actors_source_url"] = ACTORS_SOURCE
                for item in entries:
                    item["actor_name"] = resolved.get(item["actor_ref"])
        payload.update({
            "offset": offset, "limit": limit,
            "positions": entries,
            "source_url": "https://data.assemblee-nationale.fr/travaux-parlementaires/votes",
        })
        return jsonify(payload)
