# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

from acfpf.ai.registry import PROVIDER_PRESETS


def test_all_provider_presets_define_secure_https_endpoints() -> None:
    assert set(PROVIDER_PRESETS) == {"groq", "gemini", "mistral", "openai", "openrouter"}
    for preset in PROVIDER_PRESETS.values():
        assert preset.api_url.startswith("https://")
        assert preset.default_model
        assert preset.legacy_key_env.endswith("_API_KEY")
