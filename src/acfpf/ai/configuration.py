# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

"""Process-local AI configuration, shared by both AI entry points."""

from dataclasses import dataclass

from acfpf.ai.civic import CivicAnswerService
from acfpf.ai.legislation_query import LegislativeQueryPlanner
from acfpf.ai.registry import build_provider
from acfpf.ai.service import AnswerService
from acfpf.cofog import CofogService
from acfpf.live_research import LiveOfficialResearch
from acfpf.macro import MacroService

MAX_KEY_BYTES = 4096


class KeyFileError(ValueError):
    """An upload error safe to display without its contents."""


def read_key(raw: bytes) -> str:
    """Read a plain key, optionally with a BOM and a final newline."""
    if len(raw) > MAX_KEY_BYTES:
        raise KeyFileError("Le fichier de clé dépasse la taille maximale de 4 Kio.")
    try:
        key = raw.decode("utf-8-sig").strip()
    except UnicodeDecodeError:
        raise KeyFileError("Le fichier doit être un fichier texte UTF-8.") from None
    if not key or any(not 33 <= ord(char) <= 126 for char in key):
        raise KeyFileError("Le fichier doit contenir uniquement la clé, sur une seule ligne.")
    return key


@dataclass(frozen=True)
class AIServices:
    answer: AnswerService | None
    planner: LegislativeQueryPlanner | None
    imported: bool = False


class AIConfiguration:
    def __init__(self, initial: AIServices, macro: MacroService, cofog: CofogService):
        self._initial = self.current = initial
        self._macro = macro
        self._cofog = cofog

    def activate(self, provider_name: str, raw_key: bytes) -> None:
        provider = build_provider(provider_name, read_key(raw_key))
        answer = CivicAnswerService(
            AnswerService(provider, self._macro, self._cofog, LiveOfficialResearch())
        )
        # Replace the pair together. In-flight requests keep their previous service.
        self.current = AIServices(answer, LegislativeQueryPlanner(provider), imported=True)

    def reset(self) -> None:
        self.current = self._initial
