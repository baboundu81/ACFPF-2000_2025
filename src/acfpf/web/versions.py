# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

"""Bounded API for official text-version notices (not the full text)."""

from flask import Flask, jsonify, request

from acfpf.legislation import LegislationError, LegislationService
from acfpf.legislative_versions import TextVersionsError, TextVersionService
from acfpf.web.amendments import _bounded_integer


def register_version_routes(
    app: Flask, legislation_service: LegislationService, version_service: TextVersionService
) -> None:
    @app.get("/api/legislation/<dossier_id>/versions")
    def legislation_versions_api(dossier_id: str):
        try:
            limit = _bounded_integer("limit", default=30, minimum=1, maximum=100)
            offset = _bounded_integer("offset", default=0, minimum=0, maximum=100000)
            dossier = legislation_service.get(dossier_id)
        except ValueError as exc:
            return jsonify({"error": "invalid_filter", "message": str(exc)}), 400
        except LegislationError as exc:
            return jsonify({"error": "legislation_unavailable", "message": str(exc)}), 503
        if dossier is None:
            return jsonify({"error": "dossier_not_found"}), 404

        try:
            collection = version_service.for_dossier(
                dossier, refresh=request.args.get("refresh") == "1"
            )
        except TextVersionsError as exc:
            return jsonify({"error": "versions_unavailable", "message": str(exc)}), 503

        payload = collection.as_dict()
        payload.update({
            "offset": offset,
            "limit": limit,
            "versions": [item.as_dict() for item in collection.versions[offset:offset + limit]],
        })
        return jsonify(payload)
