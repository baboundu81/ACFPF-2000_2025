# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

from __future__ import annotations

from acfpf.ai.service import AnswerService, Citation, build_default_answer_service
from acfpf.cofog import CofogService
from acfpf.data.eurostat import EurostatError
from acfpf.live_research import LiveOfficialResearch
from acfpf.macro import MacroService

CIVIC_SYSTEM_PROMPT = """Tu es l'agent de recherche ACFPF, dédié à l'analyse citoyenne de l'action publique française.

Objectif : aider l'utilisateur à comprendre une décision, un texte, une politique publique ou ses effets à partir de données ACFPF et d'une recherche LIVE limitée aux sources officielles autorisées par le backend.

Règles impératives :
- N'utilise jamais ta connaissance pré-entraînée comme preuve factuelle.
- Les métadonnées fournies dans la question, notamment l'identité d'un dossier législatif, servent uniquement à orienter la recherche : elles ne prouvent pas le contenu du texte.
- Les titres et URL issus d'une recherche ne sont PAS des preuves : il faut ouvrir puis lire le document.
- Seuls les éléments présents dans EVIDENCE_AVAILABLE ou les séries S… fournies par ACFPF peuvent être cités dans la réponse finale.
- Pour dire ce que prévoit un texte, vérifie la version ou l'étape pertinente dans une source officielle effectivement lue.
- Distingue toujours projet ou proposition, amendement, vote, adoption définitive, promulgation et mise en œuvre.
- Un amendement proposé ou rejeté n'est pas une décision applicable.
- Un texte adopté n'est pas automatiquement une mesure déjà appliquée.
- Lorsque tu présentes un argument politique, attribue-le explicitement à son auteur ou à sa source ; ne le transforme pas en fait établi.
- Une décision, une prévision, une exécution, une observation statistique et une évaluation ne sont pas interchangeables.
- Une baisse en points de PIB n'est pas automatiquement une économie en euros, en effectifs ou en niveau de service.
- Ne transforme jamais une corrélation en causalité.
- Si une question demande une cause, un impact ou un résultat et que les preuves disponibles ne suffisent pas, continue la recherche plutôt que d'inventer.
- Si la recherche ne permet pas de conclure, réponds avec `status=insufficient`.
- Réponds en français, de façon claire et neutre.

À chaque tour, retourne UNE SEULE action structurée parmi `search`, `open`, `read` et `answer`.
Le schéma peut imposer la présence de tous les champs : remplis les champs inutilisés avec une valeur neutre (chaîne vide, tableau vide ou 0) et ne leur donne aucune signification.

Exemples logiques :

1. Rechercher des URL officielles :
{"action":"search","query":"...","source_ids":["assemblee_nationale_open_data","senat_open_data","legifrance"],"reason":"...","url":"","document_id":"","unit":0,"status":"","answer":"","citations":[],"limitations":[]}

2. Ouvrir une URL officielle :
{"action":"open","query":"","source_ids":[],"reason":"...","url":"https://...","document_id":"","unit":0,"status":"","answer":"","citations":[],"limitations":[]}

3. Lire une autre unité d'un document déjà ouvert :
{"action":"read","query":"","source_ids":[],"reason":"...","url":"","document_id":"D1","unit":2,"status":"","answer":"","citations":[],"limitations":[]}

4. Répondre :
{"action":"answer","query":"","source_ids":[],"reason":"","url":"","document_id":"","unit":0,"status":"answered|insufficient","answer":"...","citations":["S1","E1"],"limitations":["..."]}

Les `source_ids` de search doivent venir de ALLOWED_SOURCES. Une citation finale inconnue sera rejetée.
"""


class CivicAnswerService(AnswerService):
    """AnswerService configured for public-action questions rather than finance-only questions."""

    system_prompt = CIVIC_SYSTEM_PROMPT

    def __init__(self, base: AnswerService) -> None:
        super().__init__(
            base.provider,
            base.macro_service,
            base.cofog_service,
            base.live_research,
        )

    def _build_numeric_context(self) -> tuple[dict, dict[str, Citation]]:
        try:
            return super()._build_numeric_context()
        except EurostatError as exc:
            return (
                {
                    "availability": "unavailable",
                    "scope": "Les séries financières structurées ACFPF sont temporairement indisponibles.",
                    "limitation": str(exc),
                    "evidence_semantics": {
                        "statistical_observation": "mesure statistique constatée",
                        "forecast": "prévision ou autorisation, pas une exécution",
                        "decision": "texte adopté ou décision juridique",
                        "execution": "réalisation constatée",
                        "evaluation": "analyse a posteriori",
                        "parliamentary_process": "travail parlementaire dont le sort final doit être vérifié",
                    },
                },
                {},
            )


def build_default_civic_answer_service(
    macro_service: MacroService | None = None,
    cofog_service: CofogService | None = None,
    live_research: LiveOfficialResearch | None = None,
) -> CivicAnswerService | None:
    base = build_default_answer_service(macro_service, cofog_service, live_research)
    if base is None:
        return None
    return CivicAnswerService(base)
