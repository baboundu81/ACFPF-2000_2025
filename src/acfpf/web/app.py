# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

from __future__ import annotations

import json

from flask import Flask, Response, jsonify, render_template, request, stream_with_context

from acfpf.ai import AnswerService
from acfpf.ai.civic import build_default_civic_answer_service
from acfpf.ai.legislation_query import (
    LegislativeQueryPlanner,
    build_default_legislative_query_planner,
)
from acfpf.ai.provider import AIError, AIProviderError
from acfpf.ai.service import MAX_QUESTION_CHARS
from acfpf.cofog import CofogService
from acfpf.data.assemblee_legislation import ASSEMBLY_SOURCE_PAGE
from acfpf.data.eurostat import EurostatError, get_source_catalog
from acfpf.data.senat_legislation import SENATE_SOURCE_PAGE
from acfpf.legislation import (
    LegislationError,
    LegislationService,
    LegislativeDossier,
    parse_legislative_search,
)
from acfpf.legislation_assisted import assisted_browse_legislation
from acfpf.legislative_stages import classify_dossier_stage, enrich_dossier_payload
from acfpf.macro import MacroService
from acfpf.public_action import public_action_coverage
from acfpf.source_registry import load_sources

MAX_SCOPED_QUESTION_CHARS = 600
MAX_HISTORY_ITEMS = 2
MAX_HISTORY_ITEM_CHARS = 220
LEGISLATION_SOURCE_PAGES = (
    {"name": "Assemblée nationale", "url": ASSEMBLY_SOURCE_PAGE},
    {"name": "Sénat", "url": SENATE_SOURCE_PAGE},
)
EMPTY_FACETS = {
    "chambers": [],
    "stages": [],
    "themes": [],
    "text_types": [],
    "min_year": None,
    "max_year": None,
}


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

    source_urls = [source.official_url for source in dossier.sources] or [dossier.official_url]
    normalized_stage = classify_dossier_stage(dossier)
    return (
        "Contexte de dossier législatif fourni par le backend ACFPF. "
        "Ce contexte sert uniquement à orienter la recherche et ne constitue pas une preuve. "
        f"Dossier: {dossier.title}. Identifiant: {dossier.id}. "
        f"Dossiers officiels connus: {', '.join(source_urls)}. "
        f"Statut indicatif: {dossier.status_label}. "
        f"Étape normalisée indicative: {normalized_stage.label} ({normalized_stage.code}). "
        f"Libellé source de l'étape: {dossier.current_stage or 'non renseigné'}."
        f"{history_text} "
        f"Question actuelle de l'utilisateur: {question}"
    )


def _legislation_warnings(service: object) -> list[str]:
    getter = getattr(service, "warnings", None)
    if callable(getter):
        return list(getter())
    return []


def _optional_year(value: str | None, label: str) -> int | None:
    if value is None or not value.strip():
        return None
    try:
        year = int(value)
    except ValueError as exc:
        raise ValueError(f"{label} doit être une année entière.") from exc
    if year < 1900 or year > 2100:
        raise ValueError(f"{label} doit être comprise entre 1900 et 2100.")
    return year


def _browse_filters_from_request() -> dict[str, str | int | None]:
    return {
        "chamber": request.args.get("chamber", "").strip() or None,
        "stage": request.args.get("stage", "").strip() or None,
        "theme": request.args.get("theme", "").strip() or None,
        "text_type": request.args.get("text_type", "").strip() or None,
        "from_year": _optional_year(request.args.get("from_year"), "L'année de début"),
        "to_year": _optional_year(request.args.get("to_year"), "L'année de fin"),
    }


def _empty_selected_filters() -> dict[str, str | int | None]:
    return {
        "chamber": None,
        "stage": None,
        "theme": None,
        "text_type": None,
        "from_year": None,
        "to_year": None,
    }


def _assist_enabled_from_request() -> bool:
    return request.args.get("assist", "1").strip().lower() not in {"0", "false", "off", "no"}


def create_app(
    service: MacroService | None = None,
    answer_service: AnswerService | None = None,
    cofog_service: CofogService | None = None,
    legislation_service: LegislationService | None = None,
    legislation_query_planner: LegislativeQueryPlanner | None = None,
) -> Flask:
    app = Flask(__name__)
    macro_service = service or MacroService()
    functional_service = cofog_service or CofogService()
    civic_service = legislation_service or LegislationService()
    ai_service = answer_service or build_default_civic_answer_service(
        macro_service,
        functional_service,
    )
    query_planner = legislation_query_planner or build_default_legislative_query_planner()
    registered_sources = load_sources()
    live_sources = [source for source in registered_sources if source.live_research]

    @app.get("/")
    def home():
        query = request.args.get("q", "").strip()
        status = request.args.get("status") or None
        fallback_status = parse_legislative_search(query, status=status).status
        refresh = request.args.get("refresh") == "1"
        assist_enabled = _assist_enabled_from_request()
        try:
            selected_filters = _browse_filters_from_request()
            assisted = assisted_browse_legislation(
                civic_service,
                query,
                planner=query_planner,
                assist=assist_enabled,
                status=status,
                refresh=refresh,
                limit=30,
                **selected_filters,
            )
            browse = assisted.browse
            interpretation = assisted.as_meta_dict() if query else None
            return render_template(
                "home.html",
                query=query,
                selected_status=assisted.effective_status,
                selected_filters=assisted.effective_filters,
                facets=browse.facets.as_dict(),
                dossiers=[
                    enrich_dossier_payload(item, include_events=False) for item in browse.results
                ],
                legislation_error=None,
                legislation_warnings=_legislation_warnings(civic_service),
                legislation_sources=LEGISLATION_SOURCE_PAGES,
                legislation_source=ASSEMBLY_SOURCE_PAGE,
                search_interpretation=interpretation,
                planner_available=query_planner is not None,
                assist_enabled=assist_enabled,
            )
        except ValueError as exc:
            return render_template(
                "home.html",
                query=query,
                selected_status=fallback_status,
                selected_filters=_empty_selected_filters(),
                facets=EMPTY_FACETS,
                dossiers=[],
                legislation_error=str(exc),
                legislation_warnings=_legislation_warnings(civic_service),
                legislation_sources=LEGISLATION_SOURCE_PAGES,
                legislation_source=ASSEMBLY_SOURCE_PAGE,
                search_interpretation=None,
                planner_available=query_planner is not None,
                assist_enabled=assist_enabled,
            ), 400
        except LegislationError as exc:
            return render_template(
                "home.html",
                query=query,
                selected_status=fallback_status,
                selected_filters=_empty_selected_filters(),
                facets=EMPTY_FACETS,
                dossiers=[],
                legislation_error=str(exc),
                legislation_warnings=_legislation_warnings(civic_service),
                legislation_sources=LEGISLATION_SOURCE_PAGES,
                legislation_source=ASSEMBLY_SOURCE_PAGE,
                search_interpretation=None,
                planner_available=query_planner is not None,
                assist_enabled=assist_enabled,
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
                legislation_warnings=_legislation_warnings(civic_service),
                research_sources=[source.as_dict() for source in live_sources],
                ai_enabled=ai_service is not None,
            ), 503
        if dossier is None:
            return render_template(
                "dossier.html",
                dossier=None,
                error="Dossier législatif introuvable.",
                legislation_warnings=_legislation_warnings(civic_service),
                research_sources=[source.as_dict() for source in live_sources],
                ai_enabled=ai_service is not None,
            ), 404
        return render_template(
            "dossier.html",
            dossier=enrich_dossier_payload(dossier),
            public_action=public_action_coverage(dossier),
            error=None,
            legislation_warnings=_legislation_warnings(civic_service),
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
        refresh = request.args.get("refresh") == "1"
        assist_enabled = _assist_enabled_from_request()
        try:
            limit = max(1, min(int(request.args.get("limit", "30")), 100))
            selected_filters = _browse_filters_from_request()
            assisted = assisted_browse_legislation(
                civic_service,
                query,
                planner=query_planner,
                assist=assist_enabled,
                status=status,
                refresh=refresh,
                limit=limit,
                **selected_filters,
            )
            browse = assisted.browse
        except ValueError as exc:
            return jsonify({"error": "invalid_filter", "message": str(exc)}), 400
        except LegislationError as exc:
            return jsonify({"error": "legislation_unavailable", "message": str(exc)}), 503
        return jsonify(
            {
                "query": query,
                "status": assisted.effective_status,
                "filters": assisted.effective_filters,
                "assistance": assisted.as_meta_dict(),
                "assist_enabled": assist_enabled,
                "planner_available": query_planner is not None,
                "facets": browse.facets.as_dict(),
                "sources": list(LEGISLATION_SOURCE_PAGES),
                "warnings": _legislation_warnings(civic_service),
                "results": [
                    enrich_dossier_payload(item, include_events=False) for item in browse.results
                ],
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
        payload = enrich_dossier_payload(dossier)
        payload["warnings"] = _legislation_warnings(civic_service)
        return jsonify(payload)

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
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return None, ({"error": "invalid_request", "message": "Un objet JSON est requis."}, 400)
        question = payload.get("question", "")
        if not isinstance(question, str):
            return None, ({"error": "invalid_question"}, 400)
        question = question.strip()
        if len(question) > MAX_QUESTION_CHARS:
            return None, (
                {
                    "error": "invalid_question",
                    "message": "La question est limitée à 1500 caractères.",
                },
                400,
            )
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
            app.logger.warning("AI request failed (%s)", type(exc).__name__)
            details = (
                exc.as_dict()
                if isinstance(exc, AIProviderError)
                else {"code": "grounding_rejected", "message": str(exc)}
            )
            return jsonify({"error": "ai_failure", **details}), 502

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
                yield json.dumps({"type": "error", "message": str(exc)}, ensure_ascii=False) + "\n"
            except EurostatError as exc:
                app.logger.exception("Data failure during streamed AI request")
                yield json.dumps({"type": "error", "message": str(exc)}, ensure_ascii=False) + "\n"
            except AIError as exc:
                app.logger.warning("AI streaming request failed (%s)", type(exc).__name__)
                details = (
                    exc.as_dict()
                    if isinstance(exc, AIProviderError)
                    else {"code": "grounding_rejected", "message": str(exc)}
                )
                yield json.dumps({"type": "error", **details}, ensure_ascii=False) + "\n"

        return Response(
            generate(),
            mimetype="application/x-ndjson",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.get("/healthz")
    def health():
        return {
            "status": "ok",
            "ai": "enabled" if ai_service is not None else "disabled",
            "research_mode": "live_official_sources",
            "primary_experience": "civic_legislation",
        }

    return app
