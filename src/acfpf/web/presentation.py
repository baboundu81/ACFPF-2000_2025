# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

"""Display-only dossier metadata; do not turn scheduled dates into completed activity."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from acfpf.legislative_stages import enrich_dossier_payload

PARIS = ZoneInfo("Europe/Paris")


def dossier_view(dossier, *, include_events=True, today: date | None = None):
    payload = enrich_dossier_payload(dossier, include_events=include_events)
    current = today or datetime.now(PARIS).date()

    def is_future(value):
        try:
            return date.fromisoformat(value[:10]) > current if value else False
        except ValueError:
            return False

    payload["activity_label"] = (
        "Date prévue dans la source"
        if is_future(dossier.last_activity)
        else "Dernière date renseignée"
    )
    retrieved = dossier.retrieved_at
    if retrieved:
        try:
            moment = datetime.fromisoformat(retrieved)
            retrieved = (
                moment.astimezone(PARIS).strftime("%d/%m/%Y à %H:%M (Paris)")
                if moment.tzinfo
                else retrieved
            )
        except ValueError:
            pass
    payload["freshness_label"] = retrieved or "date de récupération non renseignée"
    for event in payload.get("events", []):
        event["date_is_future"] = is_future(event.get("date"))
    return payload
