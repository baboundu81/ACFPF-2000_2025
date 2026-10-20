# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

from __future__ import annotations

import os

from acfpf.ai.openai_compatible import OpenAICompatibleProvider

API_URL = "https://api.mistral.ai/v1/chat/completions"
DEFAULT_MODEL = "mistral-small-latest"


class MistralProvider(OpenAICompatibleProvider):
    """Backward-compatible wrapper around the generic OpenAI-compatible provider."""

    def __init__(self, api_key: str, *, model: str = DEFAULT_MODEL, **kwargs) -> None:
        super().__init__(
            name="mistral",
            api_key=api_key,
            model=model,
            api_url=API_URL,
            **kwargs,
        )

    @classmethod
    def from_env(cls) -> MistralProvider:
        api_key = os.getenv("ACFPF_LLM_API_KEY") or os.getenv("MISTRAL_API_KEY", "")
        model = os.getenv("ACFPF_LLM_MODEL", DEFAULT_MODEL)
        return cls(api_key, model=model)
