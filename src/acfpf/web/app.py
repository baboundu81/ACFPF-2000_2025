# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

from __future__ import annotations

from flask import Flask, jsonify, render_template, request

from acfpf.data.eurostat import EurostatError
from acfpf.macro import MacroService


def create_app(service: MacroService | None = None) -> Flask:
    app = Flask(__name__)
    macro_service = service or MacroService()

    @app.get("/")
    def dashboard():
        refresh = request.args.get("refresh") == "1"
        try:
            model = macro_service.dashboard(refresh=refresh)
            payload = model.as_dict()
            return render_template(
                "dashboard.html",
                dashboard=payload,
                error=None,
            )
        except EurostatError as exc:
            return render_template(
                "dashboard.html",
                dashboard=None,
                error=str(exc),
            ), 503

    @app.get("/api/macro")
    def macro_api():
        refresh = request.args.get("refresh") == "1"
        try:
            return jsonify(macro_service.dashboard(refresh=refresh).as_dict())
        except EurostatError as exc:
            return jsonify({"error": str(exc)}), 503

    @app.get("/healthz")
    def health():
        return {"status": "ok"}

    return app
