# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

"""Local web interface for ACFPF."""

from collections.abc import Callable

from acfpf.ai import AnswerService
from acfpf.ai.legislation_query import LegislativeQueryPlanner
from acfpf.cofog import CofogService
from acfpf.legislation import LegislationService
from acfpf.legislation_detail import AmendmentService
from acfpf.legislative_reports import ReportsService
from acfpf.legislative_versions import TextVersionService
from acfpf.macro import MacroService
from acfpf.web.amendments import register_amendment_routes
from acfpf.web.app import create_app as _create_app
from acfpf.web.debates import register_debate_routes
from acfpf.web.outcomes import register_outcome_routes
from acfpf.web.public_action import register_public_action_routes
from acfpf.web.reports import register_report_routes
from acfpf.web.versions import register_version_routes
from acfpf.web.votes import register_vote_routes


def create_app(
    service: MacroService | None = None,
    answer_service: AnswerService | None = None,
    cofog_service: CofogService | None = None,
    legislation_service: LegislationService | None = None,
    legislation_query_planner: LegislativeQueryPlanner | None = None,
    amendment_service: AmendmentService | None = None,
    version_service: TextVersionService | None = None,
    report_service: ReportsService | None = None,
    vote_loader: Callable | None = None,
    vote_position_loader: Callable | None = None,
    vote_actor_resolver: Callable | None = None,
    debate_archive_loader: Callable | None = None,
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
    register_report_routes(app, civic_service, report_service or ReportsService())
    if vote_loader is None and debate_archive_loader is None:
        register_debate_routes(app, civic_service)
    else:
        from acfpf.data.assemblee_debates import download_debate_archive
        from acfpf.data.assemblee_votes import load_votes

        register_debate_routes(
            app, civic_service,
            vote_loader=vote_loader or load_votes,
            archive_loader=debate_archive_loader or download_debate_archive,
        )
    register_outcome_routes(app, civic_service)
    register_public_action_routes(app, civic_service)
    if vote_loader is None and vote_position_loader is None and vote_actor_resolver is None:
        register_vote_routes(app, civic_service)
    else:
        from acfpf.data.assemblee_actors import resolve_actor_names
        from acfpf.data.assemblee_votes import load_votes
        from acfpf.legislative_vote_positions import load_nominal_positions

        register_vote_routes(
            app, civic_service,
            vote_loader=vote_loader or load_votes,
            position_loader=vote_position_loader or load_nominal_positions,
            actor_resolver=vote_actor_resolver or resolve_actor_names,
        )
    return app


__all__ = ["create_app"]
