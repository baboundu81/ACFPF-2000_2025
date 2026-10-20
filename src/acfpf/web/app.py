# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

from __future__ import annotations

import json

from flask import Flask, Response, jsonify, render_template, request, stream_with_context

from acfpf.ai import AnswerService, build_default_answer_service
from acfpf.ai.provider import AIError
from acfpf.cofog import CofogService
from acfpf.data.eurostat import EurostatError, get_source_catalog
from acfpf.macro import MacroService
from acfpf.source_registry import load_sources


def create_app(
    service: MacroService | None = None,
    answer_service: AnswerService | None = None,
    cofog_service: CofogService | None = None,
) -> Flask:
    app = Flask(__name__)
    macro_service = service or MacroService()
    functional_service = cofog_service or CofogService()
    ai_service = answer_service or build_default_answer_service(
        macro_service,
        functional_service,
    )
    registered_sources = load_sources()
    live_sources = [source for source in registered_sources if source.live_research]

    @app.get("/")
    def dashboard():
        refresh = request.args.get("refresh") == "1"
        sources = get_source_catalog()
        cofog_payload = None
        cofog_error = None
        try:
            cofog_payload = functional_service.analysis(refresh=refresh).as_dict()
        except EurostatError as exc:
            cofog_error = str(exc)

        try:
            model = macro_service.dashboard(refresh=refresh)
            payload = model.as_dict()
            return render_template(
                "dashboard.html",
                dashboard=payload,
                cofog=cofog_payload,
                cofog_error=cofog_error,
                error=None,
                sources=payload["sources"],
                research_sources=[source.as_dict() for source in live_sources],
                ai_enabled=ai_service is not None,
            )
        except EurostatError as exc:
            return render_template(
                "dashboard.html",
                dashboard=None,
                cofog=cofog_payload,
                cofog_error=cofog_error,
                error=str(exc),
                sources=sources,
                research_sources=[source.as_dict() for source in live_sources],
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

    @app.get("/api/cofog")
    def cofog_api():
        refresh = request.args.get("refresh") == "1"
        try:
            return jsonify(functional_service.analysis(refresh=refresh).as_dict())
        except EurostatError as exc:
            return jsonify({"error": str(exc)}), 503

    @app.get("/api/evidence")
    def evidence_api():
        return jsonify(
            {
                "mode": "live_official_research",
                "persistent_document_corpus": False,
                "sources": [source.as_dict() for source in registered_sources],
            }
        )

    def _question_from_request() -> tuple[str | None, tuple[dict[str, str], int] | None]:
        payload = request.get_json(silent=True) or {}
        question = payload.get("question", "")
        if not isinstance(question, str):
            return None, ({"error": "invalid_question"}, 400)
        return question, None

    @app.post("/api/ask")
    def ask_api():
        if ai_service is None:
            return jsonify(
                {
                    "error": "ai_not_configured",
                    "message": (
                        "La fonction IA n'est pas configurée. Définissez ACFPF_LLM_PROVIDER "
                        "et ACFPF_LLM_API_KEY côté serveur puis relancez ACFPF."
                    ),
                }
            ), 503

        question, error = _question_from_request()
        if error is not None:
            payload, status = error
            return jsonify(payload), status

        try:
            return jsonify(ai_service.ask(question or "").as_dict())
        except ValueError as exc:
            return jsonify({"error": "invalid_question", "message": str(exc)}), 400
        except EurostatError as exc:
            return jsonify({"error": "data_unavailable", "message": str(exc)}), 503
        except AIError as exc:
            return jsonify({"error": "ai_failure", "message": str(exc)}), 502

    @app.post("/api/ask/stream")
    def ask_stream_api():
        if ai_service is None:
            return jsonify(
                {
                    "error": "ai_not_configured",
                    "message": "La fonction IA n'est pas configurée côté serveur.",
                }
            ), 503

        question, error = _question_from_request()
        if error is not None:
            payload, status = error
            return jsonify(payload), status

        @stream_with_context
        def generate():
            try:
                for event in ai_service.iter_ask(question or ""):
                    yield json.dumps(event.as_dict(), ensure_ascii=False) + "\n"
            except ValueError as exc:
                yield json.dumps(
                    {"type": "error", "message": str(exc)}, ensure_ascii=False
                ) + "\n"
            except (EurostatError, AIError) as exc:
                yield json.dumps(
                    {"type": "error", "message": str(exc)}, ensure_ascii=False
                ) + "\n"

        return Response(generate(), mimetype="application/x-ndjson")

    @app.get("/healthz")
    def health():
        return {
            "status": "ok",
            "ai": "enabled" if ai_service is not None else "disabled",
            "research_mode": "live_official_sources",
        }

    return app
