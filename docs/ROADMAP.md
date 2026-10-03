# Feuille de route

## Phase 0 — Socle méthodologique

- [x] définir les principes de reproductibilité ;
- [x] définir la hiérarchie des sources ;
- [x] séparer données brutes, intermédiaires et traitées ;
- [x] initialiser l'environnement Python et les tests ;
- [ ] figer le schéma de métadonnées des jeux de données.

## Phase 1 — Socle macro 2000–2025

Construire une table annuelle commune contenant au minimum :

- PIB nominal ;
- population ;
- indice de prix utilisé pour les conversions en euros constants ;
- recettes publiques ;
- dépenses publiques ;
- prélèvements obligatoires ;
- déficit / excédent ;
- dette publique ;
- intérêts de la dette.

Pour chaque variable, conserver la valeur brute, l'unité, la source et les transformations.

Livrables :

- `data/processed/macro_2000_2025.parquet` généré par script ;
- tableau de contrôle ;
- graphiques en euros courants, euros constants, par habitant et en % du PIB ;
- analyse `analyses/macro/`.

## Phase 2 — Décomposition fonctionnelle des dépenses

Étudier la ventilation COFOG :

- protection sociale ;
- santé ;
- enseignement ;
- défense ;
- ordre et sécurité publics ;
- affaires économiques ;
- services généraux ;
- logement et équipements collectifs ;
- environnement ;
- culture et loisirs.

Objectif : identifier les postes qui expliquent l'évolution de la dépense totale.

## Phase 3 — Services publics

Analyses séparées avec indicateurs de ressources **et** de service rendu :

- éducation ;
- santé ;
- police / gendarmerie ;
- justice ;
- services publics de proximité.

## Phase 4 — Protection sociale

Décomposer les prestations :

- retraites ;
- santé ;
- famille ;
- chômage ;
- logement ;
- minima sociaux ;
- invalidité et autres risques.

## Phase 5 — Fraudes et contrôle

Construire des séries séparées pour :

- fraude fiscale ;
- fraude aux prestations ;
- fraude aux cotisations ;
- montants estimés ;
- montants détectés / redressés ;
- recouvrements effectifs ;
- coûts de contrôle lorsqu'ils sont disponibles.

Aucune comparaison ne sera faite entre concepts non homogènes sans avertissement explicite.

## Phase 6 — Aides aux entreprises

Construire une taxonomie avant agrégation :

- subventions ;
- dépenses fiscales ;
- allègements de cotisations ;
- prêts et avances ;
- garanties ;
- participations ;
- aides locales ;
- aides européennes.

Les marchés publics seront analysés séparément.

## Phase 7 — Comparaisons internationales

Comparer la France avec des pays pertinents via Eurostat et l'OCDE, avec des définitions harmonisées autant que possible.

## Phase 8 — Synthèse

Répondre aux questions de départ à partir des analyses précédentes, sans score politique ni classement normatif.

Chaque conclusion devra pointer vers les données et scripts permettant de la reproduire.
