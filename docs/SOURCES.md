<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Catalogue des sources

Ce document complète le registre machine-readable [`config/sources.yml`](../config/sources.yml).

La convention qui distingue **observation statistique, prévision, décision, exécution, évaluation et processus parlementaire** est décrite dans [`docs/EVIDENCE.md`](EVIDENCE.md).

Le registre de sources est aussi la **liste blanche de recherche live** : chaque entrée peut déclarer les domaines HTTPS que l'agent est autorisé à ouvrir. Une URL trouvée sur le Web n'est jamais une preuve avant validation du domaine et lecture effective par ACFPF.

## INSEE et Eurostat

Usage prioritaire :

- comptes nationaux et administrations publiques ;
- prélèvements obligatoires ;
- dépenses par fonction COFOG ;
- PIB, population, inflation ;
- comparaisons européennes harmonisées.

Eurostat alimente actuellement le dashboard macro et la première décomposition COFOG. L'INSEE reste prioritaire lorsqu'une série française primaire homogène et exploitable est disponible.

## Budget.gouv.fr et data.economie.gouv.fr

Usage :

- projets annuels de performances (PAP) ;
- rapports annuels de performances (RAP) ;
- lois/projets de finances et documents annexés ;
- exécution budgétaire par mission, programme, action, titre ou catégorie ;
- indicateurs de performance, prévisions et réalisations.

Attention : le budget de l'État ne représente qu'une partie de la dépense publique totale.

## Légifrance / DILA

Usage :

- lois et lois organiques ;
- décrets et règlements ;
- codes ;
- versions historiques des textes ;
- textes budgétaires et fiscaux promulgués.

La lecture publique live peut fonctionner directement sur les pages Légifrance. Un connecteur structuré vers l'API officielle PISTE pourra être ajouté en complément lorsque ses identifiants sont configurés ; il ne doit pas être requis pour lancer ACFPF.

## Assemblée nationale et Sénat

Usage :

- amendements et leur sort ;
- dossiers législatifs ;
- débats et travaux parlementaires ;
- votes et textes adoptés.

Un amendement proposé ou rejeté n'est jamais assimilé à une décision applicable. Le sort final du texte doit être conservé.

## Sécurité sociale et DREES

Usage :

- PLFSS et LFSS ;
- annexes et REPSS ;
- protection sociale, retraites, santé, famille, minima sociaux ;
- comptes et indicateurs sectoriels.

## Cour des comptes

Usage :

- contrôle de gestion publique ;
- certification ;
- évaluation de politiques publiques ;
- analyses de l'exécution budgétaire et de la Sécurité sociale ;
- estimations et constats sur les systèmes de contrôle et de fraude.

Une recommandation ou appréciation de la Cour doit être distinguée d'une donnée statistique brute.

## BOFiP-Impôts

Usage envisagé : doctrine et interprétation administrative de la fiscalité. Une doctrine administrative doit être distinguée de la loi elle-même et reliée, lorsque pertinent, au texte juridique correspondant.

## data.gouv.fr

Catalogue national de données publiques.

Usage envisagé :

- commande publique ;
- aides et subventions ;
- données administratives sectorielles ;
- jeux produits par les ministères et opérateurs publics.

Chaque jeu doit être relié à son producteur d'origine.

## OCDE et Commission européenne

Usage : comparaisons internationales, fiscalité, dépenses, emploi public et aides d'État.

## Découverte et preuve

La recherche d'URL peut s'appuyer sur un index externe, mais cet index ne sert qu'à la navigation. Les snippets, classements et résumés du moteur de découverte ne sont pas des sources ACFPF et ne sont pas transmis comme faits au modèle.

Seul le contenu récupéré depuis un domaine autorisé peut recevoir un identifiant de preuve `E…`.

## Règle de citation

Chaque analyse doit citer le producteur original et conserver suffisamment d'informations pour retrouver précisément le jeu de données, le document et le locator utilisé, ainsi que la date de consultation pour les sources live.
