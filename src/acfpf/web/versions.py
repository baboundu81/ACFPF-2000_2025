# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

"""Bounded API for official text-version notices (not the full text)."""

from flask import Flask, jsonify, request

from acfpf.legislation import LegislationError, LegislationService
from acfpf.legislative_fulltext import OfficialTextError, fetch_official_text
from acfpf.legislative_text_diff import TextComparisonError, compare_official_texts
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

    @app.get("/api/legislation/<dossier_id>/versions/<document_uid>/text")
    def legislative_version_fulltext_api(dossier_id: str, document_uid: str):
        """Never fetch arbitrary UIDs: require a notice linked in the official archive."""
        try:
            dossier = legislation_service.get(dossier_id)
        except LegislationError as exc:
            return jsonify({"error": "legislation_unavailable", "message": str(exc)}), 503
        if dossier is None:
            return jsonify({"error": "dossier_not_found"}), 404
        try:
            collection = version_service.for_dossier(dossier)
        except TextVersionsError as exc:
            return jsonify({"error": "versions_unavailable", "message": str(exc)}), 503
        version = next(
            (item for item in collection.versions
             if item.uid == document_uid and item.notice_available),
            None,
        )
        if version is None:
            return jsonify({"error": "document_not_linked"}), 404
        try:
            document = fetch_official_text(document_uid)
        except OfficialTextError as exc:
            return jsonify({"error": "official_text_unavailable", "message": str(exc)}), 503
        payload = document.as_dict()
        payload["dossier_id"] = dossier.id
        payload["version"] = version.as_dict()
        return jsonify(payload)

    @app.get("/api/legislation/<dossier_id>/versions/compare")
    def legislative_text_diff_api(dossier_id: str):
        before_uid = request.args.get("before", "")
        after_uid = request.args.get("after", "")
        if not before_uid or not after_uid or before_uid == after_uid:
            return jsonify({
                "error": "invalid_versions", "message": "Sélectionnez deux versions distinctes."
            }), 400
        try:
            dossier = legislation_service.get(dossier_id)
        except LegislationError as exc:
            return jsonify({"error": "legislation_unavailable", "message": str(exc)}), 503
        if dossier is None:
            return jsonify({"error": "dossier_not_found"}), 404
        try:
            collection = version_service.for_dossier(dossier)
        except TextVersionsError as exc:
            return jsonify({"error": "versions_unavailable", "message": str(exc)}), 503
        notice_by_uid = {
            version.uid: version
            for version in collection.versions
            if version.notice_available
        }
        if before_uid not in notice_by_uid or after_uid not in notice_by_uid:
            return jsonify({
                "error": "document_not_linked",
                "message": "Les deux documents doivent être liés à ce dossier officiel.",
            }), 404
        try:
            before = fetch_official_text(before_uid)
            after = fetch_official_text(after_uid)
            diff = compare_official_texts(before, after)
        except OfficialTextError as exc:
            return jsonify({"error": "official_text_unavailable", "message": str(exc)}), 503
        except TextComparisonError as exc:
            return jsonify({"error": "comparison_unavailable", "message": str(exc)}), 422
        diff["dossier_id"] = dossier.id
        diff["before"]["version"] = notice_by_uid[before_uid].as_dict()
        diff["after"]["version"] = notice_by_uid[after_uid].as_dict()
        return jsonify(diff)
