<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# ACFPF 2000–2025

**Analyse citoyenne des finances publiques françaises entre 2000 et 2025**

ACFPF est un projet public et reproductible visant à analyser l'évolution des finances publiques françaises à partir de **sources primaires, officielles et documentées**.

Le projet ne cherche pas à confirmer une conclusion politique prédéfinie. Il vise à tester quantitativement des hypothèses, documenter les limites des données et permettre à chacun de vérifier les sources utilisées.

## Questions de départ

Le projet cherchera notamment à répondre, données à l'appui, aux questions suivantes :

- Les prélèvements obligatoires ont-ils augmenté entre 2000 et 2025, en euros constants, par habitant et en part de PIB ?
- Comment la structure des dépenses publiques a-t-elle évolué ?
- Quels postes expliquent l'évolution globale des dépenses ?
- Les moyens consacrés aux grands services publics ont-ils augmenté ou diminué ?
- Comment leurs résultats et leur activité ont-ils évolué en parallèle ?
- Quelle est l'importance relative des retraites, de la santé, de l'éducation, de la sécurité, des intérêts de la dette et des autres grandes fonctions ?
- Quelle est l'importance mesurable des fraudes sociales et fiscales, en distinguant fraude estimée, détectée, redressée et effectivement recouvrée ?
- Quelles aides publiques sont accordées aux entreprises et sous quelles formes ?

## Principes méthodologiques

1. **Sources primaires d'abord** : INSEE, administrations, juridictions financières, organismes de Sécurité sociale, Eurostat, Légifrance, Assemblée nationale, Sénat, etc.
2. **Traçabilité** : toute donnée ou tout texte utilisé doit conserver sa source, sa date, son URL, son identifiant et son périmètre.
3. **Reproductibilité** : les traitements doivent être réalisés par code dès que possible.
4. **Pas de cherry-picking** : une hypothèse doit pouvoir être confirmée, nuancée ou réfutée.
5. **Comparaisons homogènes** : distinguer euros courants, euros constants, part de PIB, par habitant et autres unités pertinentes.
6. **Nature de la preuve explicite** : une prévision, une décision, une exécution, une observation statistique et une évaluation ne sont pas interchangeables.
7. **Fraîcheur documentaire** : les textes officiels sont consultés en direct lorsqu'une question le nécessite plutôt que maintenus dans un corpus local massif.

Voir [docs/METHODOLOGY.md](docs/METHODOLOGY.md), [docs/EVIDENCE.md](docs/EVIDENCE.md) et [AGENTS.md](AGENTS.md).

## Tableau de bord actuel

Le socle macro 2000–2025 utilise :

- `gov_10a_main` pour les dépenses publiques (`TE`), les recettes publiques (`TR`) et le solde public (`B9`) ;
- `gov_10dd_edpt1` pour la dette publique consolidée (`GD`) ;
- `gov_10a_exp` pour les dépenses des administrations publiques par fonction COFOG.

Les vues actuelles sont exprimées en pourcentage du PIB. Le tableau de bord affiche les dix grandes fonctions COFOG et leur variation depuis 2000. Une baisse en points de PIB n'est pas présentée comme une « économie » sans métrique complémentaire.

Les séries sont mises en cache localement pendant 24 heures et peuvent utiliser le dernier cache compatible si Eurostat devient temporairement inaccessible.

## Recherche documentaire live

ACFPF ne télécharge plus à l'avance un corpus exhaustif de lois, rapports et documents budgétaires.

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

L'application fonctionne sans IA. L'architecture IA reste indépendante du fournisseur.

### Option recommandée pour commencer : Groq

Créez une clé dans la console Groq puis :

```bash
export ACFPF_LLM_PROVIDER="groq"
export ACFPF_LLM_API_KEY="votre_clé"
acfpf
```

Le modèle par défaut peut être remplacé avec `ACFPF_LLM_MODEL`.

### Autres fournisseurs supportés

ACFPF supporte également `gemini`, `mistral`, `openai` et `openrouter`. La configuration reste la même : `ACFPF_LLM_PROVIDER`, `ACFPF_LLM_API_KEY` et éventuellement `ACFPF_LLM_MODEL`.

Le protocole d'enquête est provider-neutral : à chaque tour le modèle demande `search`, `open`, `read` ou `answer`. Le backend exécute l'action et garde le contrôle des sources accessibles.

Voir [docs/AI.md](docs/AI.md), [docs/PROVIDERS.md](docs/PROVIDERS.md) et [docs/EVIDENCE.md](docs/EVIDENCE.md).

## APIs locales

Une fois ACFPF lancé :

- `/api/macro` : agrégats macro ;
- `/api/cofog` : dépenses par grande fonction ;
- `/api/evidence` : registre et liste blanche des sources ;
- `/api/ask` : question IA sourcée (POST) ;
- `/api/ask/stream` : enquête IA avec progression NDJSON (POST).

## Tests

```bash
ruff check .
pytest
```

Les tests unitaires n'appellent pas les services externes en temps réel : clients HTTP, providers IA et recherche live sont simulés par des fixtures/fakes déterministes.

## Structure

```text
.
├── analyses/               # Analyses thématiques finales
├── config/
│   └── sources.yml         # Registre des producteurs et domaines autorisés
├── data/                   # Données locales, brutes/intermédiaires/traitées
├── docs/                   # Méthodologie, preuves, IA, UX/UI
├── notebooks/              # Exploration et contrôles ponctuels
├── src/acfpf/
│   ├── ai/                 # Providers LLM et boucle d'agent
│   ├── data/               # Acquisition et extraction déterministes
│   ├── evidence.py         # Sémantique commune des preuves
│   ├── live_research.py    # Recherche/lecture live avec liste blanche
│   └── web/                # Interface Flask locale
└── tests/                  # Tests déterministes
```

## Sources prioritaires

Le registre est dans [config/sources.yml](config/sources.yml). Il comprend notamment :

- INSEE et Eurostat ;
- budget.gouv.fr et data.economie.gouv.fr ;
- Légifrance / DILA ;
- Assemblée nationale et Sénat ;
- Sécurité sociale et DREES ;
- Cour des comptes ;
- BOFiP-Impôts ;
- OCDE et Commission européenne.

## État du projet

Le projet dispose maintenant d'un socle macro, d'une décomposition fonctionnelle COFOG, d'une sémantique de preuves et d'un agent de recherche live contraint aux sources officielles. Les prochaines étapes sont notamment l'intégration des prélèvements obligatoires, euros constants/par habitant, exécutions détaillées par mission/programme/action et des connecteurs officiels spécialisés lorsque ceux-ci améliorent la recherche.

## Licences

ACFPF utilise plusieurs licences selon la nature du contenu :

- **code source, scripts, tests et notebooks exécutables** : [PolyForm Noncommercial License 1.0.0](LICENSE) (`PolyForm-Noncommercial-1.0.0`) ;
- **documentation, textes d'analyse et créations éditoriales originales** : [Creative Commons Attribution 4.0 International](LICENSES/CC-BY-4.0.txt) (`CC-BY-4.0`) ;
- **données et documents tiers** : ils restent soumis aux licences et conditions de leurs producteurs respectifs et ne sont pas relicenciés par ACFPF.

Le logiciel est donc **source-available à usage non commercial**, et non « open source » au sens OSI. Un usage commercial du logiciel nécessite une **licence commerciale écrite distincte** : voir [COMMERCIAL-LICENSING.md](COMMERCIAL-LICENSING.md).

La portée détaillée des licences, les cas mixtes et l'historique de licence sont documentés dans [LICENSES/README.md](LICENSES/README.md).
