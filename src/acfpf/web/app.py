# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

from __future__ import annotations

from flask import Flask, jsonify, render_template, request

from acfpf.ai import AnswerService, build_default_answer_service
from acfpf.ai.provider import AIError
from acfpf.data.eurostat import EurostatError, get_source_catalog
from acfpf.macro import MacroService


def create_app(
    service: MacroService | None = None,
    answer_service: AnswerService | None = None,
) -> Flask:
    app = Flask(__name__)
    macro_service = service or MacroService()
    ai_service = answer_service or build_default_answer_service(macro_service)

    @app.get("/")
    def dashboard():
        refresh = request.args.get("refresh") == "1"
        sources = get_source_catalog()
        try:
            model = macro_service.dashboard(refresh=refresh)
            payload = model.as_dict()
            return render_template(
                "dashboard.html",
                dashboard=payload,
                error=None,
                sources=payload["sources"],
                ai_enabled=ai_service is not None,
            )
        except EurostatError as exc:
            return render_template(
                "dashboard.html",
                dashboard=None,
                error=str(exc),
                sources=sources,
                ai_enabled=ai_service is not None,
            ), 503

    @app.get("/api/macro")
    def macro_api():
        refresh = request.args.get("refresh") == "1"
        try:
            return jsonify(macro_service.dashboard(refresh=refresh).as_dict())
        except EurostatError as exc:
            return jsonify(
                {
                    "error": str(exc),
                    "sources": get_source_catalog(),
                }
            ), 503

    @app.post("/api/ask")
    def ask_api():
        if ai_service is None:
            return jsonify(
                {
                    "error": "ai_not_configured",
                    "message": (
                        "La fonction IA n'est pas configurée. Définissez MISTRAL_API_KEY "
                        "côté serveur puis relancez ACFPF."
                    ),
                }
            ), 503

        payload = request.get_json(silent=True) or {}
        question = payload.get("question", "")
        if not isinstance(question, str):
            return jsonify({"error": "invalid_question"}), 400

        try:
            return jsonify(ai_service.ask(question).as_dict())
        except ValueError as exc:
            return jsonify({"error": "invalid_question", "message": str(exc)}), 400
        except EurostatError as exc:
            return jsonify({"error": "data_unavailable", "message": str(exc)}), 503
        except AIError as exc:
            return jsonify({"error": "ai_failure", "message": str(exc)}), 502

    @app.get("/healthz")
    def health():
        return {
            "status": "ok",
            "ai": "enabled" if ai_service is not None else "disabled",
        }

    return app
