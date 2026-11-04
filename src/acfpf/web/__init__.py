# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

"""Local web interface for ACFPF."""

from acfpf.ai import AnswerService
from acfpf.ai.legislation_query import LegislativeQueryPlanner
from acfpf.cofog import CofogService
from acfpf.legislation import LegislationService
from acfpf.legislation_detail import AmendmentService
from acfpf.legislative_versions import TextVersionService
from acfpf.macro import MacroService
from acfpf.web.amendments import register_amendment_routes
from acfpf.web.versions import register_version_routes
from acfpf.web.app import create_app as _create_app


def create_app(
    service: MacroService | None = None,
    answer_service: AnswerService | None = None,
    cofog_service: CofogService | None = None,
    legislation_service: LegislationService | None = None,
    legislation_query_planner: LegislativeQueryPlanner | None = None,
    amendment_service: AmendmentService | None = None,
    version_service: TextVersionService | None = None,
):
    """Create the ACFPF web app and register optional structured civic-data routes."""
    civic_service = legislation_service or LegislationService()
    app = _create_app(
        service,
        answer_service,
        cofog_service=cofog_service,
        legislation_service=civic_service,
        legislation_query_planner=legislation_query_planner,
    )
    register_amendment_routes(
        app,
        civic_service,
        amendment_service or AmendmentService(),
    )
    register_version_routes(app, civic_service, version_service or TextVersionService())
    return app


__all__ = ["create_app"]
