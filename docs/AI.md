<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Intelligence artificielle dans ACFPF

## Objectif

Permettre à un utilisateur de poser une question en langage naturel sur les finances publiques françaises et d'obtenir une réponse **strictement appuyée sur les données ACFPF et des sources officielles consultées en direct**, avec citations vérifiables.

Le LLM n'est jamais une source de vérité. Il choisit quoi chercher et quoi lire ; ACFPF contrôle où il peut aller, fournit les données structurées, exécute les calculs et valide les preuves citées.

## Architecture actuelle

```text
question utilisateur
        ↓
agent LLM
        ↓
choix d'une action
  ├── répondre avec les données déjà disponibles
  ├── rechercher dans une ou plusieurs sources officielles
  ├── ouvrir une URL officielle
  └── lire la suite d'un document
        ↓
backend ACFPF
  ├── vérifie la liste blanche de domaines
  ├── récupère la source live
  ├── conserve l'ordre du document
  ├── attribue des identifiants E… aux unités effectivement lues
  └── fournit les séries S… calculées de façon déterministe
        ↓
agent LLM (tour suivant)
        ↓
réponse finale JSON + citations S… / E…
        ↓
validation backend
        ↓
affichage + trace de recherche + liens officiels
```

Le fournisseur et le modèle restent interchangeables. Le protocole d'agent est un échange JSON standard au-dessus de `LLMProvider`, sans dépendre des mécanismes propriétaires de tool-calling d'un fournisseur.

## Recherche live contrôlée

ACFPF ne maintient plus un corpus documentaire exhaustif et ne fait pas de retrieval lexical/vectoriel avant de transmettre des passages au modèle.

Le registre `config/sources.yml` contient la liste des sources autorisées et leurs domaines. L'agent reçoit cette liste puis peut demander une recherche sur certaines sources.

La découverte d'URL peut utiliser un index Web public. Cet index sert uniquement d'annuaire :

- les snippets et résumés de l'index ne sont jamais transmis comme preuves ;
- seuls les résultats dont l'URL appartient à une source autorisée sont conservés ;
- l'URL est à nouveau contrôlée au moment de l'ouverture ;
- toute redirection vers un domaine non autorisé est refusée.

Une URL trouvée n'est jamais citable par elle-même.

## Lecture des documents

Lorsqu'un document officiel est ouvert :

- le HTML visible est extrait dans l'ordre de la page ;
- les PDF sont extraits page par page puis regroupés en blocs de pages contiguës ;
- aucune phrase n'est supprimée parce qu'elle paraît lexicalement ou sémantiquement éloignée de la question ;
- la segmentation est uniquement mécanique pour respecter les limites de contexte ;
- le modèle peut demander les unités suivantes d'un document.

Chaque unité effectivement lue reçoit un identifiant `E1`, `E2`, etc. La preuve conserve : URL, source, titre, date de consultation, locator (page/segment) et SHA-256 du document récupéré.

Les contenus documentaires sont éphémères et isolés par question ; ils ne constituent pas un entrepôt local persistant.

## Données chiffrées

Les séries macro et COFOG restent récupérées et normalisées par la couche de données ACFPF. Elles sont exposées à l'agent avec des identifiants `S…`.

Le principe reste :

- données et calculs déterministes en Python ;
- LLM pour choisir la recherche, mettre en relation les preuves et expliquer ;
- pas de chiffre substitué depuis la mémoire du modèle lorsqu'une donnée officielle est nécessaire.

## Boucle d'enquête

À chaque tour le modèle doit produire exactement une action JSON :

- `search` : requête + `source_ids` autorisés ;
- `open` : URL HTTPS officielle ;
- `read` : unité suivante d'un document déjà ouvert ;
- `answer` : réponse finale sourcée ou statut `insufficient`.

Le contrat commun est défini par `AGENT_ACTION_SCHEMA` dans `src/acfpf/ai/schema.py`. Les providers qui supportent des sorties structurées doivent utiliser ce schéma au niveau de l'API, plutôt que compter uniquement sur le prompt.

Le nombre d'étapes est plafonné afin d'éviter les boucles et les coûts incontrôlés. Si la limite est atteinte sans preuve suffisante, ACFPF renvoie une réponse insuffisante plutôt que de forcer une conclusion.

## Validation des citations

Une réponse `answered` doit citer au moins une preuve connue.

ACFPF rejette :

- une citation vers un identifiant inconnu ;
- une citation vers une URL simplement trouvée mais jamais ouverte ;
- une citation vers une partie d'un document qui n'a jamais été fournie au modèle ;
- une réponse factuelle sans citation.

La validation d'identité et de provenance ne garantit pas à elle seule que le texte de la réponse est parfaitement fidèle à la source. Le benchmark ACFPF doit donc également mesurer l'entailment entre affirmation et preuve.

## Providers LLM

La configuration générique reste :

```bash
export ACFPF_LLM_PROVIDER="gemini"
export ACFPF_LLM_API_KEY="..."
export ACFPF_LLM_MODEL="..."  # facultatif
```

Gemini est le provider par défaut. Le modèle par défaut est `gemini-3.8-flash`. Les autres providers intégrés sont Groq, Claude, Mistral, OpenAI et OpenRouter. Les presets et particularités d'intégration sont documentés dans [PROVIDERS.md](PROVIDERS.md).

Gemini et Groq/GPT-OSS utilisent le schéma structuré via leur endpoint compatible OpenAI. Claude utilise l'API native Anthropic, car sa couche OpenAI-compatible ne garantit pas actuellement `response_format` ; l'API native permet d'imposer `output_config.format=json_schema`.

La clé reste exclusivement côté serveur Flask et n'est jamais exposée au navigateur.

## Streaming vers l'interface

`POST /api/ask/stream` renvoie un flux NDJSON afin que l'interface puisse afficher les étapes au fur et à mesure : préparation, recherche, ouverture, lecture, puis réponse.

L'objectif UX est que l'utilisateur puisse comprendre **comment** ACFPF a construit sa réponse et ouvrir lui-même les sources consultées.

## Évolutions prioritaires

Le live-first ne signifie pas qu'un seul mécanisme de découverte doit tout faire. Des connecteurs spécialisés pourront améliorer la recherche sans constituer de corpus local massif :

1. API Légifrance / PISTE en option ;
2. API/open data Budget et data.economie.gouv.fr ;
3. recherche structurée Assemblée nationale / Sénat ;
4. outils déterministes supplémentaires pour les séries INSEE, DREES et Sécurité sociale ;
5. vérification automatique claim → preuve ;
6. benchmark de recherche, de fidélité aux sources et de refus correct ;
7. quotas, timeouts, budget maximal de tokens et observabilité avant déploiement public.

Les embeddings et index vectoriels ne sont plus une dépendance architecturale prévue par défaut. Ils pourraient être ajoutés un jour comme aide facultative pour une source spécifique si leur bénéfice est démontré, mais ils ne doivent pas décider silencieusement quels paragraphes sont exclus de l'analyse.

## Benchmark ACFPF

Le benchmark devra couvrir notamment :

- questions purement chiffrées ;
- questions nécessitant plusieurs sources officielles ;
- décision versus exécution ;
- textes contradictoires ou périmètres différents ;
- reformulation de requêtes lorsqu'une première recherche échoue ;
- documents longs nécessitant plusieurs lectures ;
- tentative d'ouverture d'un domaine interdit ;
- citation d'une preuve jamais lue ;
- questions pour lesquelles la bonne réponse est `insufficient`.

Mesures minimales : exactitude, taux de refus correct, qualité et fidélité des citations, hallucinations, couverture de recherche, latence, nombre d'étapes et consommation de tokens.

Voir aussi [EVIDENCE.md](EVIDENCE.md).

## Transport documentaire borné (V1, étape 1)

`LiveOfficialResearch` utilise des réponses HTTP en flux, sans suivre automatiquement
les redirections. Chaque destination officielle est revalidée avant requête ; l’index
de découverte, distinct des preuves, refuse les redirections et les réponses non HTML.
Une réponse HTTP 202/429 de l’index est une indisponibilité, pas une recherche réussie sans résultat.

Les limites courantes sont centralisées dans `live_research.py` :

- index de découverte : 1 000 000 octets ;
- HTML officiel : 3 000 000 octets ; PDF : 12 000 000 octets ;
- texte extrait : 1 000 000 caractères ; PDF : au plus 400 pages ;
- blocs réseau : 32 768 octets ; délai réseau et de lecture du flux : 20 secondes par défaut ;
- au plus cinq redirections officielles ; 14 actions d’agent comme auparavant.

La taille annoncée et les octets décompressés reçus sont contrôlés. Le flux est fermé
sur succès comme sur échec. Une limite dépassée, une réponse partielle, une erreur HTTP,
un PDF invalide/chiffré ou sans texte, ou un contenu non HTML/PDF ne crée aucun document
ni preuve. Le lecteur ne tronque pas le texte pour contourner une limite. Les PDF
nécessitant un OCR et les pages exigeant une exécution JavaScript ne sont pas pris en charge.
Les types MIME acceptés sont `text/html`, `application/xhtml+xml`, `application/pdf`.
Un document mal étiqueté est refusé plutôt qu’interprété silencieusement comme du HTML.

Lorsque plusieurs producteurs partagent un domaine autorisé, le lecteur utilise l’hôte
et le chemin de leur `base_url` pour déterminer une provenance unique, ou refuse l’ambiguïté.
Le périmètre réseau reste défini par `allowed_domains` ; aucune URL fournie par un moteur
n’étend cette liste blanche.

Les erreurs et recherches vides sont exposées par les événements `notice`, conservées
dans la trace et fournies au prochain tour via `RESEARCH_NOTICES`. Ce sont des observations
opérationnelles : elles ne rejoignent jamais `EVIDENCE_AVAILABLE`. Les unités effectivement
transmises gardent leur identifiant `E…`, leur locator, URL finale, titre, source, date et SHA-256.
La relecture d’une même unité réutilise son identifiant ; les documents restent isolés par question.

Tests sans réseau : `tests/test_live_research.py` et `tests/test_documentary_pipeline.py`
(le vrai lecteur et l’agent sont utilisés, seuls HTTP et le fournisseur sont simulés).
Sonde séparée, sans LLM ni sélection de dossier :

```bash
ACFPF_LIVE_DOCUMENTARY=1 pytest -q -s tests/test_live_documentary_pipeline.py
```

Cette sonde dépend de l’index Web et reste exclue de la CI standard. Un succès ne constitue
pas une recette de fournisseur IA ; voir [le rapport de l’étape 1](V1_STEP1_VALIDATION.md).

## Validation des réponses et robustesse IA (V1, étape 2)

Une réponse candidate `answered` reste interne jusqu’à deux contrôles :

1. Contrôles déterministes : citations connues, segment effectivement lu, référence inline
   présente dans la liste validée, URL affichée appartenant aux sources citées ; une question
   de dossier nécessite une preuve documentaire E…, même si des séries S… sont disponibles.
2. Une seconde requête au même fournisseur, avec un prompt et un schéma de vérification
   distincts (`acfpf_grounding_review`), reçoit la question, les passages déjà lus, les séries
   déterministes et la réponse candidate. Elle vérifie les appuis, les dates/versions,
   les confusions de stade et les inférences causales. Les snippets ne lui sont pas fournis.

Le contrôle doit retourner un booléen, exactement les références utilisées et aucun code
d’anomalie pour accepter. Un rejet devient `insufficient` sans publier la réponse candidate.
Une panne ou un résultat de contrôle invalide produit une erreur explicite, sans publier le candidat.
Une réponse `insufficient` du modèle est remplacée par un message backend prudent : ses éventuelles
assertions et limites non vérifiées ne sont pas recopiées. Le champ libre `reason` de l’action
n’est plus exposé dans la progression ; les étapes affichées décrivent les opérations exécutées.

**Cette seconde passe est un garde-fou probabiliste, pas une preuve supplémentaire ni une
certification juridique.** Le LLM reste faillible ; les sources et les contrôles déterministes
restent nécessaires. Le benchmark de calibration est versionné dans
`tests/fixtures/ai_grounding_benchmark.json` : huit cas synthétiques, deux positifs et six négatifs
(proposition/droit applicable, prévision/exécution, version, passage sans rapport, causalité,
instruction malveillante dans une source). Il ne mesure pas la fidélité sur tout le corpus officiel.

Le contexte total est limité à 128 000 caractères par requête, sans tronquer ni sélectionner
les paragraphes ; un dépassement du contexte d’enquête aboutit à une réponse insuffisante.
Une réponse fournisseur dépassement/troncature/JSON invalide est refusée. Les sorties sont
plafonnées à 4 096 tokens, ou 2 048 pour Groq/GPT-OSS, avec effort faible pour Gemini 3 et Groq/GPT-OSS.
Les questions libres restent limitées à 1 500 caractères, et les questions de dossier à 600
côté route ; le contexte officiel assemblé peut atteindre 6 000 caractères.

Un quota HTTP 429 avec `Retry-After` numérique peut être repris au même point : **deux reprises
au maximum pour toute la question**, vérification comprise, et au plus 60 secondes par attente.
La progression annonce l’attente ; les sources lues restent conservées dans cette question.
Un délai plus long, un quota persistant, un timeout ou une indisponibilité 503 produit une erreur
explicite. Aucun changement silencieux de fournisseur/modèle ni augmentation de quota/facturation.

Les deux chats partagent un lecteur NDJSON local (`research_stream.js`) qui gère les caractères
UTF-8 et lignes découpés entre chunks, exige un unique événement final et refuse un flux incomplet
ou incohérent. Le résultat final est affiché après fermeture correcte du flux ; les erreurs finales,
y compris sans saut de ligne, réactivent le formulaire. Les en-têtes Flask empêchent le cache et
l’accumulation du flux par un reverse proxy qui respecte `X-Accel-Buffering`.

Évaluation LLM distincte, opt-in (clé uniquement dans l’environnement serveur) :

```bash
ACFPF_LIVE_AI=1 pytest -q tests/test_live_ai_grounding.py
```

Voir [le rapport de validation de l’étape 2](V1_STEP2_VALIDATION.md) pour distinguer tests simulés,
benchmark avec vrai fournisseur, essais navigateur et indisponibilité Gemini constatée.
