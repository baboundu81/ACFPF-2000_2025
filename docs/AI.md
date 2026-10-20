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
export ACFPF_LLM_PROVIDER="groq"
export ACFPF_LLM_API_KEY="..."
export ACFPF_LLM_MODEL="..."  # facultatif
```

Providers intégrés : Groq, Gemini, Mistral, OpenAI et OpenRouter. Les presets sont documentés dans [PROVIDERS.md](PROVIDERS.md).

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
