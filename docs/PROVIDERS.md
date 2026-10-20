<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Providers LLM

ACFPF utilise une configuration uniforme :

```bash
export ACFPF_LLM_PROVIDER="groq"
export ACFPF_LLM_API_KEY="..."
export ACFPF_LLM_MODEL="..."   # facultatif
```

Le provider par défaut est `groq`.

| Provider | Modèle par défaut | Endpoint |
| --- | --- | --- |
| `groq` | `openai/gpt-oss-120b` | `https://api.groq.com/openai/v1/chat/completions` |
| `gemini` | `gemini-3.8-flash` | `https://generativelanguage.googleapis.com/v1beta/openai/chat/completions` |
| `mistral` | `mistral-small-latest` | `https://api.mistral.ai/v1/chat/completions` |
| `openai` | `gpt-4.1-mini` | `https://api.openai.com/v1/chat/completions` |
| `openrouter` | `openrouter/free` | `https://openrouter.ai/api/v1/chat/completions` |

Les offres gratuites, modèles disponibles et quotas changent dans le temps. La présence d'un provider dans ce tableau signifie que l'intégration est supportée par ACFPF, pas qu'un quota gratuit est garanti indéfiniment.

Le choix du provider ne modifie pas les règles de grounding : aucun outil Web n'est transmis au modèle, le contexte vient d'ACFPF et les citations sont validées par le backend.
