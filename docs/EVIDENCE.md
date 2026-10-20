<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Modèle de preuves ACFPF

## Pourquoi une couche de preuves

ACFPF ne doit pas mélanger des éléments qui n'ont pas la même portée. Une loi votée, une prévision budgétaire, une dépense exécutée et un rapport de la Cour des comptes peuvent parler du même sujet sans démontrer la même chose.

Chaque élément utilisé par une analyse ou par l'IA doit donc être qualifié avant d'être interprété.

## Stades de preuve

| Stade | Sens |
| --- | --- |
| `statistical_observation` | mesure publiée dans une source statistique officielle |
| `forecast` | prévision, objectif ou autorisation budgétaire |
| `decision` | texte adopté, promulgué ou décision juridiquement pertinente |
| `execution` | dépense, recette, effectif ou résultat réellement constaté |
| `evaluation` | analyse a posteriori, audit ou contrôle |
| `parliamentary_process` | amendement, débat, proposition ou vote à replacer dans son sort final |
| `interpretation` | doctrine ou interprétation administrative officielle |

## Règles d'interprétation

- Une **prévision** ne doit jamais être présentée comme une exécution.
- Une **décision** peut autoriser ou imposer une mesure sans démontrer son coût réellement exécuté.
- Un **amendement rejeté** n'est pas une décision applicable.
- Une baisse d'une dépense **en points de PIB** n'est pas automatiquement une économie en euros courants ou constants.
- Une évolution chiffrée n'établit pas à elle seule la cause de cette évolution.
- Une explication causale doit être appuyée par des textes, données d'exécution ou évaluations compatibles avec la période et le périmètre étudiés.

## Sources officielles prioritaires

Le registre `config/sources.yml` catalogue notamment :

- INSEE et Eurostat pour les séries statistiques ;
- budget.gouv.fr et data.economie.gouv.fr pour les PAP, RAP, données d'exécution et indicateurs de performance ;
- Légifrance/DILA pour les lois, décrets, codes et textes réglementaires ;
- Assemblée nationale et Sénat pour les amendements, dossiers législatifs, débats et votes ;
- securite-sociale.fr pour les PLFSS, LFSS, annexes et REPSS ;
- Cour des comptes pour le contrôle et l'évaluation ;
- DREES pour les séries et études de santé/protection sociale.

Les données Légifrance seront à terme récupérées via l'API officielle PISTE lorsqu'une configuration d'accès est disponible. Le corpus local ne doit jamais contourner cette politique par du scraping indiscriminé.

## Corpus documentaire

`config/evidence_documents.yml` contient un premier manifeste de documents et collections officielles.

Les entrées `status: seed` peuvent être récupérées automatiquement par le premier corpus local. Le backend :

1. télécharge uniquement l'URL explicitement déclarée ;
2. extrait le texte visible ;
3. conserve une copie locale en cache ;
4. découpe le texte en passages ;
5. attache à chaque passage son identifiant de document, sa source, son stade de preuve et son URL ;
6. recherche les passages pertinents avant d'appeler le LLM.

Il n'y a donc pas de moteur de recherche Web général caché derrière l'IA.

## Évolution vers le RAG complet

Le moteur lexical actuel est volontairement simple. Il sert à valider le pipeline de provenance et de citation.

La suite prévue est :

- extraction PDF/HTML plus précise ;
- conservation des pages, sections et articles ;
- ingestion structurée Légifrance ;
- ingestion des amendements et dossiers parlementaires ;
- ingestion systématique PAP/RAP et exécution budgétaire ;
- embeddings via une abstraction `EmbeddingProvider` ;
- index vectoriel ;
- reranking ;
- benchmark de rappel documentaire et de qualité des citations.

## Principe de prudence

Lorsque plusieurs preuves se contredisent ou ne couvrent pas le même périmètre, ACFPF doit exposer la divergence au lieu de choisir silencieusement la version qui conforte une hypothèse.
