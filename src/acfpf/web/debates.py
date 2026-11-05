# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors
"""Debate-stage references with explicit absence of transcript linkage."""

from flask import Flask, jsonify

from acfpf.legislation import LegislationError, LegislationService
from acfpf.legislative_debates import debate_references


def register_debate_routes(app: Flask, service: LegislationService) -> None:
    @app.get("/api/legislation/<dossier_id>/debates")
    def legislative_debates_api(dossier_id: str):
        try:
            dossier = service.get(dossier_id)
        except LegislationError as exc:
            return jsonify({"error": "legislation_unavailable", "message": str(exc)}), 503
        if dossier is None:
            return jsonify({"error": "dossier_not_found"}), 404
        return jsonify(debate_references(dossier))
