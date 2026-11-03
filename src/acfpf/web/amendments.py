# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

from __future__ import annotations

from flask import Flask, jsonify, request

from acfpf.legislation import LegislationError, LegislationService
from acfpf.legislation_detail import AmendmentService, LegislativeDetailError

MAX_AMENDMENTS_PAGE_SIZE = 200


def _bounded_integer(name: str, *, default: int, minimum: int, maximum: int) -> int:
    raw = request.args.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if value < minimum or value > maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return value


def register_amendment_routes(
    app: Flask,
    legislation_service: LegislationService,
    amendment_service: AmendmentService,
) -> None:
    @app.get("/api/legislation/<dossier_id>/amendments")
    def legislation_amendments_api(dossier_id: str):
        try:
            dossier = legislation_service.get(dossier_id)
        except LegislationError as exc:
            return jsonify({"error": "legislation_unavailable", "message": str(exc)}), 503
        if dossier is None:
            return jsonify({"error": "dossier_not_found"}), 404

        try:
            limit = _bounded_integer(
                "limit",
                default=50,
                minimum=1,
                maximum=MAX_AMENDMENTS_PAGE_SIZE,
            )
            offset = _bounded_integer("offset", default=0, minimum=0, maximum=1_000_000)
            collection = amendment_service.for_dossier(
                dossier,
                refresh=request.args.get("refresh") == "1",
            )
        except ValueError as exc:
            return jsonify({"error": "invalid_filter", "message": str(exc)}), 400
        except LegislativeDetailError as exc:
            return jsonify({"error": "amendments_unavailable", "message": str(exc)}), 503

        fate = request.args.get("fate", "").strip()
        items = collection.amendments
        if fate:
            items = tuple(item for item in items if item.fate == fate)
        total_filtered = len(items)
        page = items[offset : offset + limit]
        payload = collection.as_dict()
        payload.update(
            {
                "count": len(collection.amendments),
                "filtered_count": total_filtered,
                "offset": offset,
                "limit": limit,
                "fate": fate or None,
                "amendments": [item.as_dict() for item in page],
            }
        )
        return jsonify(payload)

    @app.get("/api/legislation/<dossier_id>/amendments/<amendment_id>")
    def legislation_amendment_detail_api(dossier_id: str, amendment_id: str):
        try:
            dossier = legislation_service.get(dossier_id)
        except LegislationError as exc:
            return jsonify({"error": "legislation_unavailable", "message": str(exc)}), 503
        if dossier is None:
            return jsonify({"error": "dossier_not_found"}), 404

        try:
            detail = amendment_service.detail_for(
                dossier,
                amendment_id,
                refresh=request.args.get("refresh") == "1",
            )
        except LegislativeDetailError as exc:
            return jsonify({"error": "amendment_unavailable", "message": str(exc)}), 503
        if detail is None:
            return jsonify({"error": "amendment_not_found"}), 404
        return jsonify(detail.as_dict())
