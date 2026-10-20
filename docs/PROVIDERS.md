<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Providers LLM

ACFPF utilise une configuration uniforme :

```bash
export ACFPF_LLM_PROVIDER="gemini"
export ACFPF_LLM_API_KEY="..."
export ACFPF_LLM_MODEL="..."   # facultatif
```

Le provider par défaut est `gemini`.

| Provider | Modèle par défaut | Endpoint | Sortie structurée |
| --- | --- | --- | --- |
| `gemini` | `gemini-3.8-flash` | `https://generativelanguage.googleapis.com/v1beta/openai/chat/completions` | JSON Schema |
| `groq` | `openai/gpt-oss-120b` | `https://api.groq.com/openai/v1/chat/completions` | JSON Schema |
| `claude` | `claude-haiku-5-5` | `https://api.anthropic.com/v1/messages` | JSON Schema natif |
| `mistral` | `mistral-small-latest` | `https://api.mistral.ai/v1/chat/completions` | JSON object |
| `openai` | `gpt-4.1-mini` | `https://api.openai.com/v1/chat/completions` | JSON object |
| `openrouter` | `openrouter/free` | `https://openrouter.ai/api/v1/chat/completions` | JSON object |

Les offres gratuites, modèles disponibles et quotas changent dans le temps. La présence d'un provider dans ce tableau signifie que l'intégration est supportée par ACFPF, pas qu'un quota gratuit est garanti indéfiniment.

## Gemini : choix recommandé pour commencer

Gemini est le provider par défaut car Google propose actuellement un Free Tier de la Gemini Developer API, et `gemini-3.8-flash` prend en charge les sorties structurées et les workflows agentiques. La clé se crée dans [Google AI Studio](https://aistudio.google.com/app/apikey).

Configuration minimale :

```bash
export ACFPF_LLM_PROVIDER="gemini"
export ACFPF_LLM_API_KEY="votre_clé_gemini"
acfpf
```

Pour les modèles Gemini 3.x, ACFPF demande un effort de raisonnement faible pour les tours de contrôle `search/open/read/answer`, afin de limiter la latence et la consommation de tokens. Cela ne change pas les contrôles de sources ni la validation des preuves.

## Claude

Claude est supporté via l'API native Anthropic, et non via la couche de compatibilité OpenAI. La raison est importante : la compatibilité OpenAI d'Anthropic ignore actuellement `response_format`, alors que l'API native prend en charge `output_config.format=json_schema` et garantit la structure de sortie.

```bash
export ACFPF_LLM_PROVIDER="claude"
export ACFPF_LLM_API_KEY="votre_clé_anthropic"
acfpf
```

`ANTHROPIC_API_KEY` est aussi accepté comme variable spécifique au provider. Claude n'est pas présenté comme le provider gratuit par défaut ; sa présence sert surtout à comparer la qualité des modèles et à offrir une alternative payante.

## Pourquoi une API reste nécessaire

ACFPF a besoin d'un **endpoint d'inférence programmable** pour exécuter la boucle de recherche `search → open → read → answer`. Un abonnement à une interface grand public de type ChatGPT, Gemini ou Claude ne constitue pas automatiquement un accès API utilisable par le serveur ACFPF. Si un fournisseur propose un jour une authentification officielle permettant à une application tierce d'utiliser le quota d'un compte grand public, elle pourra être ajoutée comme nouveau mode d'authentification sans modifier la logique métier.

Le choix du provider ne modifie pas les règles de grounding : aucun navigateur ni moteur de recherche n'est fourni directement au modèle. Le backend ACFPF exécute les actions, limite les domaines accessibles et valide les citations.

## Sorties structurées

ACFPF utilise le même schéma logique pour les quatre actions de l'agent : `search`, `open`, `read`, `answer`.

- Gemini et Groq/GPT-OSS utilisent `response_format=json_schema` sur leur API compatible OpenAI.
- Claude utilise les Structured Outputs natifs Anthropic avec `output_config.format=json_schema`.
- Les autres providers restent en mode `json_object` tant que leur prise en charge d'un schéma strict n'est pas explicitement activée et testée dans ACFPF.

Le schéma est centralisé dans `src/acfpf/ai/schema.py` afin que les différents providers appliquent exactement le même contrat.

## Diagnostic des erreurs

Les erreurs HTTP des providers doivent rester exploitables sans exposer les secrets. ACFPF remonte donc, lorsqu'ils existent :

- le code HTTP ;
- une catégorie lisible (`429` quota/rate limit, `401` authentification, `403` permission, etc.) ;
- `retry-after` ;
- les compteurs et délais de rate limit fournis par l'API ;
- l'identifiant de requête du fournisseur ;
- le message d'erreur structuré du fournisseur, tronqué à une taille raisonnable ;
- lorsque Groq retourne `failed_generation`, la raison structurée si elle est disponible, sans recopier automatiquement la génération fautive complète.

La clé API et les en-têtes d'authentification ne doivent jamais apparaître dans l'interface ni dans les logs.
