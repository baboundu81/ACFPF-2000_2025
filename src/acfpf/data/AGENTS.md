# Instructions spécifiques aux données et documents

Ce fichier complète le `AGENTS.md` racine et s'applique à `src/acfpf/data/**`.

## Sources

- Utiliser uniquement des endpoints ou documents officiels explicitement documentés.
- Ne pas ajouter de scraping généraliste ou de moteur de recherche Web dans cette couche.
- Les URLs récupérées automatiquement doivent être fixes, issues d'un manifeste ou construites à partir d'une API officielle documentée.

## Provenance

Chaque import doit permettre de retrouver au minimum : producteur, URL, identifiant de jeu/document, date de récupération, unité/type, période et licence lorsque connue.

## Sémantique

Ne jamais perdre la distinction entre observation, prévision, décision, exécution, évaluation et processus parlementaire lors d'une transformation.

## Cache

- Les réponses distantes peuvent être mises en cache localement.
- Un changement de structure du cache doit incrémenter sa version.
- Un cache périmé peut être utilisé comme repli hors-ligne si sa structure reste compatible et si ce comportement est visible dans les métadonnées.

## Tests

Les tests CI utilisent des fixtures et faux clients HTTP. Aucun test unitaire ne doit dépendre de la disponibilité d'Eurostat, Légifrance, budget.gouv.fr ou d'une autre source externe.
