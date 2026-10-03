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

1. **Sources primaires d'abord** : INSEE, administrations, juridictions financières, organismes de Sécurité sociale, Eurostat, OCDE, Commission européenne, etc.
2. **Traçabilité** : toute donnée utilisée doit conserver sa source, sa date de récupération et, autant que possible, son URL et son identifiant.
3. **Reproductibilité** : les traitements doivent être réalisés par code dès que possible.
4. **Pas de cherry-picking** : une hypothèse doit pouvoir être confirmée, nuancée ou réfutée.
5. **Comparaisons homogènes** : distinguer euros courants, euros constants, part de PIB, par habitant et autres unités pertinentes.
6. **Définitions explicites** : ne pas confondre par exemple dépense de l'État et dépense publique totale, fraude estimée et fraude détectée, subvention et marché public.
7. **Incertitude visible** : toute limite, rupture de série, changement de périmètre ou estimation doit être documenté.

Voir [docs/METHODOLOGY.md](docs/METHODOLOGY.md).

## Structure

```text
.
├── analyses/               # Analyses thématiques finales
├── config/                 # Registre des sources et configuration
├── data/
│   ├── raw/                # Données sources non modifiées (non versionnées par défaut)
│   ├── interim/            # Données intermédiaires
│   └── processed/          # Jeux normalisés prêts pour l'analyse
├── docs/                   # Méthodologie, sources et documentation
├── notebooks/              # Exploration et contrôles ponctuels
├── scripts/                # Scripts d'import / automatisation
├── src/acfpf/              # Bibliothèque Python commune
└── tests/                  # Tests
```

## Sources prioritaires

Le registre initial est dans [config/sources.yml](config/sources.yml). Les principales familles de sources sont :

- INSEE : comptes nationaux et comptes des administrations publiques ;
- budget.gouv.fr : budget et exécution de l'État ;
- data.gouv.fr : jeux de données publics ;
- Cour des comptes : audits et rapports de contrôle ;
- DREES et organismes de Sécurité sociale ;
- DGFiP et administrations fiscales ;
- Eurostat et OCDE pour les comparaisons internationales ;
- Commission européenne pour certaines aides d'État.

## Installation

Python 3.11 ou supérieur.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

Sous Windows :

```powershell
.venv\Scripts\activate
```

## État du projet

Le dépôt est en phase d'initialisation. La première étape sera de construire un **socle macroéconomique 2000–2025** : PIB, population, inflation, dépenses publiques, recettes publiques, prélèvements obligatoires, déficit et dette.

Les analyses thématiques viendront ensuite.

## Licences

ACFPF utilise plusieurs licences selon la nature du contenu :

- **code source, scripts, tests et notebooks exécutables** : [PolyForm Noncommercial License 1.0.0](LICENSE) (`PolyForm-Noncommercial-1.0.0`) ;
- **documentation, textes d'analyse et créations éditoriales originales** : [Creative Commons Attribution 4.0 International](LICENSES/CC-BY-4.0.txt) (`CC-BY-4.0`) ;
- **données tierces** : elles restent soumises aux licences et conditions de leurs producteurs respectifs et ne sont pas relicenciées par ACFPF.

Le logiciel est donc **source-available à usage non commercial**, et non « open source » au sens OSI. Un usage commercial du logiciel nécessite une **licence commerciale écrite distincte** : voir [COMMERCIAL-LICENSING.md](COMMERCIAL-LICENSING.md).

La portée détaillée des licences, les cas mixtes et l'historique de licence sont documentés dans [LICENSES/README.md](LICENSES/README.md).
