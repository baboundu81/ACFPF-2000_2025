# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors
"""Official Senate DOSLEG legislative outcomes, not verified normative texts."""

from flask import Flask, jsonify

from acfpf.legislation import LegislationError, LegislationService
from acfpf.legislative_outcomes import official_outcomes


def register_outcome_routes(app: Flask, service: LegislationService) -> None:
    @app.get("/api/legislation/<dossier_id>/outcomes")
    def legislative_outcomes_api(dossier_id: str):
        try:
            dossier = service.get(dossier_id)
        except LegislationError as exc:
            return jsonify({"error": "legislation_unavailable", "message": str(exc)}), 503
        if dossier is None:
            return jsonify({"error": "dossier_not_found"}), 404
        return jsonify(official_outcomes(dossier))
