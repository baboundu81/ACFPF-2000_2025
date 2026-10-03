<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Méthodologie

## 1. Objectif

ACFPF vise à produire des analyses quantitatives reproductibles sur les finances publiques françaises entre 2000 et 2025.

Une analyse ne doit pas être conçue pour démontrer une opinion. Elle doit être formulée comme une **hypothèse testable**.

Exemple :

> Hypothèse : les prélèvements obligatoires supportés par l'économie française ont augmenté entre 2000 et 2025.

Cette hypothèse doit ensuite être testée avec plusieurs métriques pertinentes, et non avec un chiffre isolé.

## 2. Hiérarchie des sources

Ordre de préférence :

1. données administratives ou statistiques primaires ;
2. publications méthodologiques des producteurs de données ;
3. juridictions et organismes publics de contrôle ;
4. organismes internationaux harmonisant les statistiques ;
5. études académiques ;
6. presse et sources secondaires uniquement pour identifier une question ou une source primaire.

Les articles de presse ne doivent pas être utilisés comme source finale d'un chiffre lorsque la source primaire est disponible.

## 3. Unités de comparaison

Une évolution monétaire doit, lorsque cela a du sens, être présentée au minimum selon plusieurs axes :

- euros courants ;
- euros constants ;
- part du PIB ;
- montant par habitant ;
- éventuellement montant par bénéficiaire ou par unité de service.

Une augmentation en euros courants n'implique pas nécessairement une augmentation en volume.

## 4. Périmètres

Toujours distinguer :

- État ;
- administrations publiques centrales ;
- administrations publiques locales ;
- administrations de sécurité sociale ;
- ensemble des administrations publiques.

Les transferts internes aux administrations publiques doivent être consolidés lorsqu'on cherche à mesurer la dépense publique totale.

## 5. Séries temporelles

Pour chaque série, documenter :

- producteur ;
- identifiant ou tableau source ;
- URL ;
- date de récupération ;
- unité ;
- périmètre ;
- fréquence ;
- années disponibles ;
- changement de base ou de nomenclature ;
- ruptures de série connues.

Les révisions statistiques doivent être considérées comme normales : les scripts doivent permettre de régénérer les résultats avec les données les plus récentes.

## 6. Fraudes

Ne jamais assimiler :

- fraude potentielle estimée ;
- fraude détectée ;
- montant redressé ;
- montant effectivement recouvré ;
- erreur non frauduleuse.

Le dénominateur doit toujours être précisé : prestations versées, impôts théoriques, population contrôlée, etc.

## 7. Aides aux entreprises

Distinguer au minimum :

- subventions directes ;
- dépenses fiscales / crédits d'impôt ;
- exonérations ou réductions de cotisations ;
- prêts et avances ;
- garanties ;
- prises de participation ;
- aides locales ;
- aides européennes ;
- marchés publics, qui ne sont pas des subventions.

Les agrégations ne doivent être réalisées qu'après vérification des risques de double comptage.

## 8. Mesure des services publics

Une analyse de l'efficacité d'un service public ne doit pas se limiter à son budget.

Selon le domaine, rapprocher :

- ressources financières ;
- effectifs ;
- population ou public couvert ;
- activité produite ;
- délais ;
- accessibilité ;
- qualité ou résultats mesurables.

## 9. Reproductibilité

Les données brutes ne doivent jamais être modifiées manuellement.

Pipeline recommandé :

```text
source -> data/raw -> nettoyage documenté -> data/interim
       -> normalisation -> data/processed -> analyse -> résultats
```

Chaque transformation significative doit être réalisée par un script versionné.

## 10. Contrôle des biais

Avant de publier une conclusion :

- rechercher les métriques qui pourraient la contredire ;
- vérifier si le résultat dépend du choix de l'année de départ ;
- tester l'effet de l'inflation, de la population et du PIB ;
- identifier les ruptures de série ;
- rechercher les doubles comptes ;
- distinguer corrélation et causalité ;
- expliciter ce que les données ne permettent pas de conclure.

## 11. Format d'une analyse

Chaque analyse thématique devrait contenir :

1. question ;
2. hypothèses ;
3. sources ;
4. définitions ;
5. méthode ;
6. résultats ;
7. tests de robustesse ;
8. limites ;
9. conclusion strictement supportée par les données ;
10. commandes permettant de reproduire les résultats.
