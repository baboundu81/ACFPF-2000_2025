# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

from __future__ import annotations

import os
from dataclasses import dataclass

from acfpf.ai.openai_compatible import OpenAICompatibleProvider
from acfpf.ai.provider import AIProviderNotConfigured, LLMProvider

DEFAULT_PROVIDER = "groq"


@dataclass(frozen=True)
class ProviderPreset:
    name: str
    api_url: str
    default_model: str
    legacy_key_env: str


PROVIDER_PRESETS: dict[str, ProviderPreset] = {
    "groq": ProviderPreset(
        name="groq",
        api_url="https://api.groq.com/openai/v1/chat/completions",
        default_model="openai/gpt-oss-120b",
        legacy_key_env="GROQ_API_KEY",
    ),
    "gemini": ProviderPreset(
        name="gemini",
        api_url="https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        default_model="gemini-3.8-flash",
        legacy_key_env="GEMINI_API_KEY",
    ),
    "mistral": ProviderPreset(
        name="mistral",
        api_url="https://api.mistral.ai/v1/chat/completions",
        default_model="mistral-small-latest",
        legacy_key_env="MISTRAL_API_KEY",
    ),
    "openai": ProviderPreset(
        name="openai",
        api_url="https://api.openai.com/v1/chat/completions",
        default_model="gpt-4.1-mini",
        legacy_key_env="OPENAI_API_KEY",
    ),
    "openrouter": ProviderPreset(
        name="openrouter",
        api_url="https://openrouter.ai/api/v1/chat/completions",
        default_model="openrouter/free",
        legacy_key_env="OPENROUTER_API_KEY",
    ),
}


def available_providers() -> tuple[str, ...]:
    return tuple(PROVIDER_PRESETS)


def build_provider_from_env() -> LLMProvider:
    provider_name = os.getenv("ACFPF_LLM_PROVIDER", DEFAULT_PROVIDER).strip().lower()
    preset = PROVIDER_PRESETS.get(provider_name)
    if preset is None:
        supported = ", ".join(available_providers())
        raise AIProviderNotConfigured(
            f"Unsupported ACFPF_LLM_PROVIDER={provider_name!r}. Supported providers: {supported}"
        )

    api_key = os.getenv("ACFPF_LLM_API_KEY", "").strip()
    if not api_key:
        api_key = os.getenv(preset.legacy_key_env, "").strip()
    if not api_key:
        raise AIProviderNotConfigured(
            "No LLM API key configured. Set ACFPF_LLM_API_KEY or "
            f"{preset.legacy_key_env}."
        )

    model = os.getenv("ACFPF_LLM_MODEL", preset.default_model).strip() or preset.default_model
    return OpenAICompatibleProvider(
        name=preset.name,
        api_key=api_key,
        model=model,
        api_url=preset.api_url,
    )
