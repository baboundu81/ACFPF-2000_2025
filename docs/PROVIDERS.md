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

ACFPF a besoin d'un **endpoint d'inférence programmable** pour exécuter la boucle de recherche `search → open → read → answer`. Un abonnement à une interface grand public de type ChatGPT, Gemini ou autre ne constitue pas automatiquement un accès API utilisable par le serveur ACFPF. Si un fournisseur propose un jour une authentification officielle permettant à une application tierce d'utiliser le quota d'un compte grand public, elle pourra être ajoutée comme nouveau mode d'authentification sans modifier la logique métier.

Le choix du provider ne modifie pas les règles de grounding : aucun outil Web n'est transmis au modèle, le contexte vient d'ACFPF et les citations sont validées par le backend.

## Diagnostic des erreurs

Les erreurs HTTP des providers doivent rester exploitables sans exposer les secrets. ACFPF remonte donc, lorsqu'ils existent :

- le code HTTP ;
- une catégorie lisible (`429` quota/rate limit, `401` authentification, `403` permission, etc.) ;
- `retry-after` ;
- les compteurs et délais de rate limit fournis par l'API ;
- l'identifiant de requête du fournisseur ;
- le message d'erreur structuré du fournisseur, tronqué à une taille raisonnable.

La clé API et les en-têtes d'authentification ne doivent jamais apparaître dans l'interface ni dans les logs.
