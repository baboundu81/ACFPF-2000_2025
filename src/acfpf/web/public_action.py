# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors
"""Public-action coverage uses only exact official dossier source references."""

from flask import Flask, jsonify

from acfpf.legislation import LegislationError, LegislationService
from acfpf.public_action import public_action_coverage


def register_public_action_routes(app: Flask, service: LegislationService) -> None:
    @app.get("/api/legislation/<dossier_id>/public-action")
    def legislative_public_action_api(dossier_id: str):
        try:
            dossier = service.get(dossier_id)
        except LegislationError as exc:
            return jsonify({"error": "legislation_unavailable", "message": str(exc)}), 503
        if dossier is None:
            return jsonify({"error": "dossier_not_found"}), 404
        return jsonify(public_action_coverage(dossier))
