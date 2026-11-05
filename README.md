<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# ACFPF

**Analyse citoyenne de l'action publique française à partir de sources primaires et vérifiables**

ACFPF est un projet public et reproductible visant à aider chacun à comprendre ce que les pouvoirs publics proposent, votent, mettent en œuvre, financent et évaluent.

Le projet ne cherche pas à confirmer une conclusion politique prédéfinie. Il cherche au contraire à rendre les affirmations vérifiables en distinguant notamment :

- ce qui est annoncé ;
- ce qui est proposé dans un texte ;
- ce qui est amendé ou rejeté ;
- ce qui est adopté et promulgué ;
- ce qui est budgété ;
- ce qui est effectivement exécuté ;
- ce qui est observé statistiquement ;
- ce qui est évalué a posteriori.

Le LLM n'est jamais utilisé comme source de vérité : il peut piloter une recherche et expliquer des preuves, mais les faits doivent provenir de données ou documents officiels.

## Expérience principale : textes et décisions

La page d'accueil permet de découvrir ou retrouver des dossiers législatifs sans connaître leur nom officiel.

Exemples de recherches :

- « Quels sont les textes en cours de vote ? »
- « Quels textes concernent le logement ? »
- « Quels textes ont été adoptés récemment ? »

La première verticale structurée utilise le jeu open data des dossiers législatifs de l'Assemblée nationale. ACFPF récupère les métadonnées officielles, dérive un statut de navigation et affiche la chronologie disponible.

Lorsqu'un dossier est sélectionné, `/textes/<id>` ouvre un espace dédié avec :

- identité et statut du dossier ;
- activité récente ;
- lien vers la source officielle ;
- questions suggérées ;
- chat contextualisé sur le dossier.

Le contexte du dossier est reconstruit côté serveur à partir de son identifiant. Les métadonnées servent uniquement à orienter l'enquête : elles ne sont pas traitées comme preuve du contenu juridique. Le moteur doit ouvrir et lire les documents officiels avant d'affirmer ce que prévoit un texte.

Cette première verticale n'est pas encore une couverture exhaustive de tout le Parlement : le connecteur Sénat et la fusion des identifiants des deux chambres font partie des prochaines étapes.

Voir [docs/CIVIC_ACTION_PLAN.md](docs/CIVIC_ACTION_PLAN.md).

## Sous-outil : finances publiques

L'ancien tableau de bord principal reste disponible sous `/finances`.

Le socle actuel utilise notamment :

- `gov_10a_main` pour les dépenses publiques (`TE`), les recettes publiques (`TR`) et le solde public (`B9`) ;
- `gov_10dd_edpt1` pour la dette publique consolidée (`GD`) ;
- `gov_10a_exp` pour les dépenses des administrations publiques par fonction COFOG.

Les vues actuelles sont exprimées en pourcentage du PIB. Une baisse en points de PIB n'est pas présentée comme une « économie » sans métrique complémentaire.

À terme, ce moteur financier pourra être appelé depuis un dossier d'action publique afin de confronter coût annoncé, financement prévu, budget voté et exécution constatée.

## Principes méthodologiques

1. **Sources primaires d'abord** : Assemblée nationale, Sénat, Légifrance, INSEE, administrations, juridictions financières, organismes de Sécurité sociale, Eurostat, etc.
2. **Traçabilité** : toute donnée ou tout texte utilisé doit conserver sa provenance, sa date, son URL, son identifiant et son périmètre.
3. **Reproductibilité** : les traitements doivent être réalisés par code dès que possible.
4. **Pas de cherry-picking** : une hypothèse doit pouvoir être confirmée, nuancée ou réfutée.
5. **Nature de la preuve explicite** : proposition, processus parlementaire, décision, prévision, exécution, observation statistique et évaluation ne sont pas interchangeables.
6. **Versions explicites** : lorsque plusieurs versions d'un texte existent, l'étape ou la version analysée doit être identifiable.
7. **Fraîcheur documentaire** : les textes officiels sont consultés en direct lorsqu'une question le nécessite plutôt que maintenus dans un corpus local massif.
8. **LLM non souverain** : l'IA choisit quoi chercher et aide à expliquer ; le backend contrôle les sources et valide les citations.

Voir [docs/METHODOLOGY.md](docs/METHODOLOGY.md), [docs/EVIDENCE.md](docs/EVIDENCE.md), [docs/AI.md](docs/AI.md) et [AGENTS.md](AGENTS.md).

## Recherche documentaire live

ACFPF ne télécharge pas à l'avance un corpus exhaustif de lois, rapports et documents budgétaires.

Lorsqu'une question nécessite des textes :

1. le LLM choisit quelles familles de sources officielles interroger ;
2. ACFPF cherche des URL uniquement sur les domaines autorisés dans `config/sources.yml` ;
3. les résultats de recherche servent uniquement à la navigation : leurs snippets ne sont jamais utilisés comme preuves ;
4. le modèle choisit une URL à ouvrir ;
5. le backend revalide l'URL et toute redirection ;
6. le document officiel est lu dans son ordre d'origine, par unités contiguës mécaniques ;
7. chaque unité effectivement lue reçoit un identifiant `E…` ;
8. la réponse finale ne peut citer que ces preuves `E…` ou les séries déterministes `S…`.

Une URL simplement trouvée mais jamais ouverte n'est donc pas citable.

Les documents consultés sont éphémères et isolés par question. La trace de réponse conserve seulement les éléments utiles à l'audit : URL, source, locator, date de consultation et empreinte SHA-256.

## Installation

Python 3.11 ou supérieur.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Sous Windows :

```powershell
.venv\Scripts\activate
```

## Lancer ACFPF

```bash
acfpf
```

Le serveur local démarre sur `http://127.0.0.1:5000` et le navigateur s'ouvre automatiquement.

Options utiles :

```bash
acfpf --no-browser
acfpf --port 5050
acfpf --debug
```

Il est également possible de lancer l'application avec :

```bash
python -m acfpf
```

## Activer l'IA

L'application reste utilisable sans IA pour ses fonctions déterministes.

Gemini est actuellement le provider par défaut :

```bash
export ACFPF_LLM_PROVIDER="gemini"
export ACFPF_LLM_API_KEY="votre_clé"
acfpf
```

`ACFPF_LLM_PROVIDER=gemini` peut être omis sur une installation neuve. Le modèle par défaut est configurable avec `ACFPF_LLM_MODEL`.

ACFPF supporte également Groq, Claude, Mistral, OpenAI et OpenRouter derrière la même abstraction de provider. Les clés restent exclusivement côté serveur.

Voir [docs/AI.md](docs/AI.md) et [docs/PROVIDERS.md](docs/PROVIDERS.md).

## APIs locales

Une fois ACFPF lancé :

- `/api/legislation` : recherche et découverte des dossiers législatifs ;
- `/api/legislation/<id>` : métadonnées et chronologie d'un dossier ;
- `/api/legislation/<id>/versions` : notices des versions documentaires ;
- `/api/legislation/<id>/versions/<uid>/text` : récupération HTML officielle à la demande ;
- `/api/legislation/<id>/amendments` : index des amendements ;
- `/api/legislation/<id>/votes` : scrutins explicitement rattachés ;
- `/api/legislation/<id>/votes/<uid>/positions` : positions nominatives, noms historiques facultatifs avec `?names=1` ;
- `/api/legislation/<id>/reports` : notices officielles des rapports rattachés ;
- `/api/legislation/<id>/reports/<uid>/text` : HTML officiel d'un rapport Assemblée lié ;
- `/api/macro` : agrégats macro ;
- `/api/cofog` : dépenses par grande fonction ;
- `/api/evidence` : registre et liste blanche des sources ;
- `/api/ask` : question IA sourcée (POST) ;
- `/api/ask/stream` : enquête IA avec progression NDJSON (POST).

Pour un chat dédié, `/api/ask` et `/api/ask/stream` acceptent un `dossier_id`. Le backend recharge alors le dossier officiel et ajoute son identité au contexte de recherche.

## Tests

```bash
ruff check .
pytest
```

Les tests unitaires n'appellent pas les services externes en temps réel : clients HTTP, providers IA, données législatives et recherche live sont simulés par des fixtures/fakes déterministes.

## Structure

```text
.
├── analyses/               # Analyses thématiques finales
├── config/
│   └── sources.yml         # Registre des producteurs et domaines autorisés
├── data/                   # Données locales, brutes/intermédiaires/traitées
├── docs/                   # Méthodologie, preuves, IA, roadmap produit
├── notebooks/              # Exploration et contrôles ponctuels
├── src/acfpf/
│   ├── ai/                 # Providers LLM et boucle d'agent
│   ├── data/               # Acquisition structurée et extraction déterministe
│   ├── legislation.py      # Modèle et recherche des dossiers législatifs
│   ├── evidence.py         # Sémantique commune des preuves
│   ├── live_research.py    # Recherche/lecture live avec liste blanche
│   └── web/                # Interface Flask locale
└── tests/                  # Tests déterministes
```

## Sources prioritaires

Le registre est dans [config/sources.yml](config/sources.yml). Il comprend notamment :

- Assemblée nationale et Sénat ;
- Légifrance / DILA ;
- INSEE et Eurostat ;
- budget.gouv.fr et data.economie.gouv.fr ;
- Sécurité sociale et DREES ;
- Cour des comptes ;
- BOFiP-Impôts ;
- OCDE et Commission européenne.

## Prochaines étapes

La trajectoire est détaillée dans [docs/CIVIC_ACTION_PLAN.md](docs/CIVIC_ACTION_PLAN.md). Les prochaines briques prioritaires sont :

- consolider les contenus complets de toutes les versions et leur structure juridique ;
- documenter et consulter les rapports, débats et décisions constitutionnelles ;
- comparer article par article les versions vérifiées sans imputation approximative ;
- relier la promulgation, les textes d'application et les publications Légifrance ;
- établir les liens vérifiables entre décisions, budgets et évaluations ;
- compléter le sous-outil finances : prélèvements obligatoires, euros constants/par habitant et exécution détaillée.

## Licences

ACFPF utilise plusieurs licences selon la nature du contenu :

- **code source, scripts, tests et notebooks exécutables** : [PolyForm Noncommercial License 1.0.0](LICENSE) (`PolyForm-Noncommercial-1.0.0`) ;
- **documentation, textes d'analyse et créations éditoriales originales** : [Creative Commons Attribution 4.0 International](LICENSES/CC-BY-4.0.txt) (`CC-BY-4.0`) ;
- **données et documents tiers** : ils restent soumis aux licences et conditions de leurs producteurs respectifs et ne sont pas relicenciés par ACFPF.

Le logiciel est donc **source-available à usage non commercial**, et non « open source » au sens OSI. Un usage commercial du logiciel nécessite une licence commerciale écrite distincte : voir [COMMERCIAL-LICENSING.md](COMMERCIAL-LICENSING.md).
