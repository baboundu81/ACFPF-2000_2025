# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

"""Local-only form for configuring the application's AI provider."""

import re
from hmac import compare_digest
from secrets import token_urlsafe

from flask import (
    Flask,
    abort,
    current_app,
    make_response,
    redirect,
    render_template,
    request,
    url_for,
)
from werkzeug.exceptions import RequestEntityTooLarge

from acfpf.ai.configuration import MAX_KEY_BYTES, AIConfiguration, KeyFileError
from acfpf.ai.registry import DEFAULT_PROVIDER, PROVIDER_PRESETS

MAX_SETTINGS_BODY_BYTES = 16 * 1024
LOCAL_HOST = re.compile(r"(?:127\.0\.0\.1|localhost|\[::1\])(?::[0-9]{1,5})?", re.IGNORECASE)


def ai_settings_available() -> bool:
    return (
        current_app.config.get("AI_SETTINGS_ENABLED", True)
        and request.remote_addr in {"127.0.0.1", "::1"}
        and LOCAL_HOST.fullmatch(request.host) is not None
    )


def register_ai_settings(app: Flask, configuration: AIConfiguration) -> None:
    csrf_token = token_urlsafe(32)

    def page(error=None, status=200, selected=None):
        active = configuration.current
        provider = getattr(active.answer, "provider", None)
        provider_name = getattr(provider, "name", None)
        selected = selected or provider_name or DEFAULT_PROVIDER
        preset = PROVIDER_PRESETS.get(selected, PROVIDER_PRESETS[DEFAULT_PROVIDER])
        return make_response(
            render_template(
                "ai_settings.html",
                csrf_token=csrf_token,
                presets=PROVIDER_PRESETS.values(),
                selected=preset.name,
                default_model=preset.default_model,
                provider_name=provider_name,
                model=getattr(provider, "model", None),
                configured=active.answer is not None,
                imported=active.imported,
                error=error,
            ),
            status,
            {"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"},
        )

    @app.route("/configuration-ia", methods=["GET", "POST"])
    def ai_settings():
        if not ai_settings_available():
            abort(404)
        if request.method == "GET":
            return page()

        request.max_content_length = MAX_SETTINGS_BODY_BYTES
        request.max_form_memory_size = MAX_SETTINGS_BODY_BYTES
        request.max_form_parts = 4
        try:
            form = request.form
            if not compare_digest(form.get("csrf_token", "").encode(), csrf_token.encode()):
                return page("Le formulaire a expiré. Réessayez depuis cette page.", 403)
            operation = form.get("operation")
            if operation == "reset":
                configuration.reset()
            elif operation == "activate":
                selected = form.get("provider")
                if selected not in PROVIDER_PRESETS:
                    return page("Choisissez un fournisseur dans la liste.", 400)
                uploads = request.files.getlist("key_file")
                if len(uploads) != 1 or not uploads[0].filename:
                    return page("Sélectionnez un seul fichier contenant la clé.", 400, selected)
                try:
                    configuration.activate(selected, uploads[0].stream.read(MAX_KEY_BYTES + 1))
                except KeyFileError as exc:
                    return page(str(exc), 400, selected)
            else:
                return page("Action inconnue.", 400)
        except RequestEntityTooLarge:
            return page("Fichier trop volumineux. Utilisez un fichier texte de 4 Kio au plus.", 413)

        response = redirect(url_for("ai_settings"), code=303)
        response.headers["Cache-Control"] = "no-store"
        return response
