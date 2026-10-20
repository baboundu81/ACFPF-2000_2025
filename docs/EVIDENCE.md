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

## Acquisition documentaire : live-first

ACFPF ne maintient pas par défaut une copie locale exhaustive des documents publics et ne présélectionne pas des passages par score lexical ou vectoriel avant de les montrer au modèle.

Le fonctionnement cible est :

1. l'utilisateur pose une question ;
2. l'agent détermine quelles familles de sources officielles peuvent être utiles ;
3. le backend recherche des URL appartenant uniquement aux domaines autorisés dans `config/sources.yml` ;
4. le modèle choisit les documents à ouvrir ;
5. ACFPF revalide le domaine, télécharge le document au moment de la question et en extrait le texte ;
6. le document est exposé au modèle dans son ordre d'origine, par unités contiguës mécaniques ;
7. le modèle peut demander à lire les unités suivantes ;
8. chaque unité effectivement lue reçoit un identifiant de preuve `E…` ;
9. la réponse finale ne peut citer que ces identifiants ou les séries chiffrées `S…` déjà validées par ACFPF.

Aucun classement lexical ou embedding ne décide quel paragraphe d'un document est suffisamment important pour être transmis. La seule segmentation sert à respecter les limites de contexte des modèles et conserve l'ordre du document.

## Découverte d'URL versus preuve

Un index Web peut être utilisé comme **annuaire** pour trouver des URL sur les domaines autorisés. Ses extraits, snippets ou résumés ne sont jamais transmis au LLM comme information factuelle et ne sont jamais citables.

Une URL trouvée n'est donc pas encore une preuve. Elle le devient seulement après :

- validation du domaine par ACFPF ;
- ouverture effective du document ;
- lecture d'une unité par le modèle ;
- attribution d'un identifiant `E…` par le backend.

Une redirection vers un domaine non autorisé est refusée.

## Sources officielles prioritaires

Le registre `config/sources.yml` définit la liste blanche et catalogue notamment :

- INSEE et Eurostat pour les séries statistiques ;
- budget.gouv.fr et data.economie.gouv.fr pour les PAP, RAP, données d'exécution et indicateurs de performance ;
- Légifrance/DILA pour les lois, décrets, codes et textes réglementaires ;
- Assemblée nationale et Sénat pour les amendements, dossiers législatifs, débats et votes ;
- securite-sociale.fr pour les PLFSS, LFSS, annexes et REPSS ;
- Cour des comptes pour le contrôle et l'évaluation ;
- DREES pour les séries et études de santé/protection sociale.

Des connecteurs officiels spécialisés pourront être ajoutés lorsque cela améliore la recherche. Par exemple, l'API Légifrance via PISTE peut compléter la recherche Web publique, sans modifier la règle de provenance.

## Stockage et fraîcheur

Les documents consultés ne constituent pas un entrepôt documentaire persistant. Une session de recherche est isolée par question et les contenus lus sont conservés uniquement le temps nécessaire à cette session.

La trace de réponse peut conserver des métadonnées légères :

- URL officielle ;
- source ACFPF ;
- date et heure de consultation ;
- titre ;
- page ou segment lu ;
- empreinte SHA-256 du document récupéré.

Cela permet d'auditer une réponse sans maintenir plusieurs centaines de gigaoctets de documents synchronisés.

## Données chiffrées

Pour les données structurées, ACFPF continue de privilégier des appels déterministes aux API officielles et des calculs Python reproductibles. Le LLM peut décider qu'il a besoin d'une série, mais il ne doit pas recalculer librement une série ou substituer un chiffre issu de sa mémoire à une donnée officielle.

## Principe de prudence

Lorsque plusieurs preuves se contredisent ou ne couvrent pas le même périmètre, ACFPF doit exposer la divergence au lieu de choisir silencieusement la version qui conforte une hypothèse.
