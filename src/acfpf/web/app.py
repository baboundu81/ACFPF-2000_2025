# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

from __future__ import annotations

import json

from flask import Flask, Response, jsonify, render_template, request, stream_with_context

from acfpf.ai import AnswerService, build_default_answer_service
from acfpf.ai.provider import AIError
from acfpf.cofog import CofogService
from acfpf.data.assemblee_legislation import ASSEMBLY_SOURCE_PAGE
from acfpf.data.eurostat import EurostatError, get_source_catalog
from acfpf.legislation import (
    LegislationError,
    LegislationService,
    LegislativeDossier,
    parse_legislative_search,
)
from acfpf.macro import MacroService
from acfpf.source_registry import load_sources

MAX_SCOPED_QUESTION_CHARS = 600
MAX_HISTORY_ITEMS = 2
MAX_HISTORY_ITEM_CHARS = 220


def _legislative_question(
    dossier: LegislativeDossier, question: str, history: list[dict[str, str]] | None = None
) -> str:
    """Add trusted dossier orientation while keeping official documents as the only evidence."""
    history_text = ""
    if history:
        compact = []
        for item in history[-MAX_HISTORY_ITEMS:]:
            role = "Utilisateur" if item.get("role") == "user" else "ACFPF"
            content = item.get("content", "")[:MAX_HISTORY_ITEM_CHARS]
            if content:
                compact.append(f"{role}: {content}")
        if compact:
            history_text = " Échanges récents: " + " | ".join(compact) + "."

    return (
        "Contexte de dossier législatif fourni par le backend ACFPF. "
        "Ce contexte sert uniquement à orienter la recherche et ne constitue pas une preuve. "
        f"Dossier: {dossier.title}. Identifiant: {dossier.id}. "
        f"URL officielle: {dossier.official_url}. "
        f"Statut indicatif: {dossier.status_label}."
        f"{history_text} "
        f"Question actuelle de l'utilisateur: {question}"
    )


def create_app(
    service: MacroService | None = None,
    answer_service: AnswerService | None = None,
    cofog_service: CofogService | None = None,
    legislation_service: LegislationService | None = None,
) -> Flask:
    app = Flask(__name__)
    macro_service = service or MacroService()
    functional_service = cofog_service or CofogService()
    civic_service = legislation_service or LegislationService()
    ai_service = answer_service or build_default_answer_service(
        macro_service,
        functional_service,
    )
    registered_sources = load_sources()
    live_sources = [source for source in registered_sources if source.live_research]

    @app.get("/")
    def home():
        query = request.args.get("q", "").strip()
        status = request.args.get("status") or None
        effective_status = parse_legislative_search(query, status=status).status
        refresh = request.args.get("refresh") == "1"
        try:
            dossiers = civic_service.search(query, status=status, refresh=refresh, limit=30)
            return render_template(
                "home.html",
                query=query,
                selected_status=effective_status,
                dossiers=[item.as_dict(include_events=False) for item in dossiers],
                legislation_error=None,
                legislation_source=ASSEMBLY_SOURCE_PAGE,
            )
        except LegislationError as exc:
            return render_template(
                "home.html",
                query=query,
                selected_status=effective_status,
                dossiers=[],
                legislation_error=str(exc),
                legislation_source=ASSEMBLY_SOURCE_PAGE,
            ), 503

    @app.get("/textes/<dossier_id>")
    def legislative_dossier(dossier_id: str):
        try:
            dossier = civic_service.get(dossier_id)
        except LegislationError as exc:
            return render_template(
                "dossier.html",
                dossier=None,
                error=str(exc),
                research_sources=[source.as_dict() for source in live_sources],
                ai_enabled=ai_service is not None,
            ), 503
        if dossier is None:
            return render_template(
                "dossier.html",
                dossier=None,
                error="Dossier législatif introuvable.",
                research_sources=[source.as_dict() for source in live_sources],
                ai_enabled=ai_service is not None,
            ), 404
        return render_template(
            "dossier.html",
            dossier=dossier.as_dict(),
            error=None,
            research_sources=[source.as_dict() for source in live_sources],
            ai_enabled=ai_service is not None,
        )

    @app.get("/finances")
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

    @app.get("/api/legislation")
    def legislation_api():
        query = request.args.get("q", "").strip()
        status = request.args.get("status") or None
        effective_status = parse_legislative_search(query, status=status).status
        refresh = request.args.get("refresh") == "1"
        try:
            limit = max(1, min(int(request.args.get("limit", "30")), 100))
        except ValueError:
            return jsonify({"error": "invalid_limit"}), 400
        try:
            dossiers = civic_service.search(query, status=status, refresh=refresh, limit=limit)
        except LegislationError as exc:
            return jsonify({"error": "legislation_unavailable", "message": str(exc)}), 503
        return jsonify(
            {
                "query": query,
                "status": effective_status,
                "source": ASSEMBLY_SOURCE_PAGE,
                "results": [item.as_dict(include_events=False) for item in dossiers],
            }
        )

    @app.get("/api/legislation/<dossier_id>")
    def legislation_dossier_api(dossier_id: str):
        try:
            dossier = civic_service.get(dossier_id)
        except LegislationError as exc:
            return jsonify({"error": "legislation_unavailable", "message": str(exc)}), 503
        if dossier is None:
            return jsonify({"error": "not_found"}), 404
        return jsonify(dossier.as_dict())

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
        question = question.strip()
        if not question:
            return None, (
                {"error": "invalid_question", "message": "La question ne peut pas être vide."},
                400,
            )

        dossier_id = payload.get("dossier_id")
        if dossier_id is None:
            return question, None
        if not isinstance(dossier_id, str) or not dossier_id.strip():
            return None, ({"error": "invalid_dossier"}, 400)
        if len(question) > MAX_SCOPED_QUESTION_CHARS:
            return None, (
                {
                    "error": "invalid_question",
                    "message": (
                        "Une question liée à un dossier est limitée à "
                        f"{MAX_SCOPED_QUESTION_CHARS} caractères."
                    ),
                },
                400,
            )
        history_payload = payload.get("history", [])
        if not isinstance(history_payload, list):
            return None, ({"error": "invalid_history"}, 400)
        history: list[dict[str, str]] = []
        for item in history_payload[-MAX_HISTORY_ITEMS:]:
            if not isinstance(item, dict):
                return None, ({"error": "invalid_history"}, 400)
            role = item.get("role")
            content = item.get("content")
            if role not in {"user", "assistant"} or not isinstance(content, str):
                return None, ({"error": "invalid_history"}, 400)
            history.append({"role": role, "content": content})

        try:
            dossier = civic_service.get(dossier_id.strip())
        except LegislationError as exc:
            return None, ({"error": "legislation_unavailable", "message": str(exc)}, 503)
        if dossier is None:
            return None, ({"error": "dossier_not_found"}, 404)
        return _legislative_question(dossier, question, history), None

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
            app.logger.exception("AI request failed")
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
            except EurostatError as exc:
                app.logger.exception("Data failure during streamed AI request")
                yield json.dumps(
                    {"type": "error", "message": str(exc)}, ensure_ascii=False
                ) + "\n"
            except AIError as exc:
                app.logger.exception("AI streaming request failed")
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
            "primary_experience": "civic_legislation",
        }

    return app
