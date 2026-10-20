<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# ACFPF 2000–2025

**Analyse citoyenne des finances publiques françaises entre 2000 et 2025**

ACFPF est un projet public et reproductible visant à analyser l'évolution des finances publiques françaises sur la période 2000–2025 à partir de **sources primaires, officielles et documentées**.

Le projet ne cherche pas à confirmer une conclusion politique prédéfinie. Il vise à tester quantitativement des hypothèses, à documenter les limites des données et à permettre à chacun de reproduire les calculs.

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
- Que représentent ces phénomènes par rapport aux masses budgétaires totales ?

## Principes méthodologiques

1. **Sources primaires d'abord** : INSEE, administrations, juridictions financières, organismes de Sécurité sociale, Eurostat, Légifrance, Assemblée nationale, Sénat, etc.
2. **Traçabilité** : toute donnée ou tout texte utilisé doit conserver sa source, sa date, son URL, son identifiant et son périmètre.
3. **Reproductibilité** : les traitements doivent être réalisés par code dès que possible.
4. **Pas de cherry-picking** : une hypothèse doit pouvoir être confirmée, nuancée ou réfutée.
5. **Comparaisons homogènes** : distinguer euros courants, euros constants, part de PIB, par habitant et autres unités pertinentes.
6. **Nature de la preuve explicite** : une prévision, une décision, une exécution, une observation statistique et une évaluation ne sont pas interchangeables.
7. **Incertitude visible** : toute limite, rupture de série, changement de périmètre ou corpus documentaire incomplet doit être documenté.

Voir [docs/METHODOLOGY.md](docs/METHODOLOGY.md), [docs/EVIDENCE.md](docs/EVIDENCE.md) et [AGENTS.md](AGENTS.md).

## Tableau de bord actuel

Le socle macro 2000–2025 utilise :

- `gov_10a_main` pour les dépenses publiques (`TE`), les recettes publiques (`TR`) et le solde public (`B9`) ;
- `gov_10dd_edpt1` pour la dette publique consolidée (`GD`) ;
- `gov_10a_exp` pour les dépenses des administrations publiques par fonction COFOG.

Les vues actuelles sont exprimées en pourcentage du PIB. Le tableau de bord affiche désormais les dix grandes fonctions COFOG et leur variation depuis 2000. Une baisse en points de PIB n'est pas présentée comme une « économie » sans métrique complémentaire.

Les séries sont mises en cache localement pendant 24 heures et peuvent utiliser le dernier cache compatible si Eurostat devient temporairement inaccessible.

## Couche de preuves

ACFPF commence à relier les chiffres aux textes qui peuvent les expliquer.

`config/sources.yml` catalogue les familles de sources officielles et leur nature : statistiques, budget, lois, exécution, amendements, évaluations, etc.

`config/evidence_documents.yml` contient un premier manifeste de documents ou collections officielles. Le corpus automatique ne télécharge que les entrées explicitement marquées `status: seed` ; il n'effectue aucune recherche Web libre.

Le premier pipeline documentaire :

1. télécharge une URL officielle allow-listée ;
2. extrait son texte visible ;
3. le conserve dans le cache local ;
4. le découpe en passages traçables ;
5. recherche les passages pertinents pour la question ;
6. transmet uniquement ces passages et les données ACFPF au LLM ;
7. valide les identifiants de citation avant affichage.

Le corpus est encore volontairement petit. Les prochaines intégrations documentaires prioritaires sont Légifrance/PISTE, PAP/RAP, exécution détaillée du budget de l'État, Assemblée nationale, Sénat, LFSS/REPSS et Cour des comptes.

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

L'application fonctionne sans IA. L'IA est indépendante du fournisseur : le backend ACFPF prépare le contexte autorisé, le fournisseur LLM génère une réponse structurée, puis ACFPF valide les citations avant affichage.

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

La clé n'est jamais envoyée au navigateur. Le modèle ne reçoit aucun outil de navigation Web. Le backend lui fournit actuellement les séries macro, la décomposition COFOG et jusqu'à quelques passages récupérés dans le corpus officiel allow-listé. Les réponses factuelles sans citation connue sont refusées.

Voir [docs/AI.md](docs/AI.md), [docs/PROVIDERS.md](docs/PROVIDERS.md) et [docs/EVIDENCE.md](docs/EVIDENCE.md).

## APIs locales

Une fois ACFPF lancé :

- `/api/macro` : agrégats macro ;
- `/api/cofog` : dépenses par grande fonction ;
- `/api/evidence` : catalogue des sources et documents officiels ;
- `/api/ask` : question IA sourcée (POST).

## Tests

```bash
ruff check .
pytest
```

Les tests unitaires n'appellent pas les services externes en temps réel : les parseurs, routes, corpus documentaire et providers IA utilisent des fixtures ou faux clients déterministes.

## Structure

```text
.
├── analyses/               # Analyses thématiques finales
├── config/
│   ├── sources.yml         # Registre des producteurs/sources
│   └── evidence_documents.yml # Manifeste documentaire allow-listé
├── data/                   # Données locales, brutes/intermédiaires/traitées
├── docs/                   # Méthodologie, preuves, IA, UX/UI
├── notebooks/              # Exploration et contrôles ponctuels
├── src/acfpf/
│   ├── ai/                 # Providers LLM et grounding
│   ├── data/               # Acquisition et extraction
│   ├── evidence.py         # Modèle commun de preuve
│   ├── document_corpus.py  # Corpus local et retrieval documentaire
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

Le projet dispose maintenant d'un socle macro, d'une première décomposition fonctionnelle COFOG, d'une couche de preuves et d'un mini-corpus documentaire officiel. Les prochaines étapes sont l'intégration systématique des prélèvements obligatoires, euros constants/par habitant, exécutions détaillées par mission/programme/action et l'élargissement du corpus juridique et budgétaire.

## Licences

ACFPF utilise plusieurs licences selon la nature du contenu :

- **code source, scripts, tests et notebooks exécutables** : [PolyForm Noncommercial License 1.0.0](LICENSE) (`PolyForm-Noncommercial-1.0.0`) ;
- **documentation, textes d'analyse et créations éditoriales originales** : [Creative Commons Attribution 4.0 International](LICENSES/CC-BY-4.0.txt) (`CC-BY-4.0`) ;
- **données et documents tiers** : ils restent soumis aux licences et conditions de leurs producteurs respectifs et ne sont pas relicenciés par ACFPF.

Le logiciel est donc **source-available à usage non commercial**, et non « open source » au sens OSI. Un usage commercial du logiciel nécessite une **licence commerciale écrite distincte** : voir [COMMERCIAL-LICENSING.md](COMMERCIAL-LICENSING.md).

La portée détaillée des licences, les cas mixtes et l'historique de licence sont documentés dans [LICENSES/README.md](LICENSES/README.md).
