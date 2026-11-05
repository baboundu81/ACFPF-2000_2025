# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors
"""Report metadata API and on-demand official HTML, never fuzzy dossier matching."""

from flask import Flask, jsonify, request

from acfpf.legislation import LegislationError, LegislationService
from acfpf.legislative_fulltext import OfficialTextError, fetch_official_text
from acfpf.legislative_reports import ReportsError, ReportsService
from acfpf.web.amendments import _bounded_integer


def register_report_routes(
    app: Flask, legislation_service: LegislationService, service: ReportsService
) -> None:
    @app.get("/api/legislation/<dossier_id>/reports")
    def reports_api(dossier_id: str):
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
        try:
            collection = service.for_dossier(dossier, refresh=request.args.get("refresh") == "1")
        except ReportsError as exc:
            return jsonify({"error": "reports_unavailable", "message": str(exc)}), 503
        payload = collection.as_dict()
        payload.update({
            "offset": offset, "limit": limit,
            "reports": [item.as_dict() for item in collection.reports[offset:offset + limit]],
            "linkage": "Uniquement par document.dossierRef exact",
        })
        return jsonify(payload)

    @app.get("/api/legislation/<dossier_id>/reports/<report_uid>/text")
    def report_text_api(dossier_id: str, report_uid: str):
        try:
            dossier = legislation_service.get(dossier_id)
        except LegislationError as exc:
            return jsonify({"error": "legislation_unavailable", "message": str(exc)}), 503
        if dossier is None:
            return jsonify({"error": "dossier_not_found"}), 404
        try:
            collection = service.for_dossier(dossier)
        except ReportsError as exc:
            return jsonify({"error": "reports_unavailable", "message": str(exc)}), 503
        report = next((item for item in collection.reports if item.uid == report_uid), None)
        if report is None:
            return jsonify({"error": "report_not_linked"}), 404
        if not report.uid.startswith("RAPPANR"):
            return jsonify({
                "error": "unverified_report_html",
                "message": "URL HTML Assemblée non vérifiée pour cette provenance.",
            }), 422
        try:
            document = fetch_official_text(report.uid)
        except OfficialTextError as exc:
            return jsonify({"error": "report_html_unavailable", "message": str(exc)}), 503
        payload = document.as_dict()
        payload.update({"dossier_id": dossier.id, "report": report.as_dict()})
        return jsonify(payload)
