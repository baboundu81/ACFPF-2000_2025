# Instructions spécifiques aux données et documents

Ce fichier complète le `AGENTS.md` racine et s'applique à `src/acfpf/data/**`.

## Sources

- Utiliser uniquement des endpoints, jeux ou documents officiels documentés dans le registre ACFPF.
- Les données structurées peuvent utiliser des APIs officielles, exports ou URL stables.
- La recherche documentaire live appartient à `acfpf.live_research`, pas à la couche de données structurées.
- L'extraction de texte doit rester indépendante de la sélection de pertinence : ne pas supprimer des paragraphes parce qu'ils semblent éloignés de la requête.

## Provenance

Chaque import structuré doit permettre de retrouver au minimum : producteur, URL, identifiant de jeu/document, date de récupération, unité/type, période et licence lorsque connue.

Pour une lecture documentaire live, conserver au minimum : source ACFPF, URL finale, titre, date de consultation, locator et empreinte SHA-256.

## Sémantique

Ne jamais perdre la distinction entre observation, prévision, décision, exécution, évaluation et processus parlementaire lors d'une transformation.

## Cache

- Les séries et réponses d'API structurées peuvent être mises en cache localement avec version de schéma et métadonnées de fraîcheur.
- Les documents textuels consultés par l'agent ne doivent pas devenir par défaut un corpus persistant.
- Un éventuel cache HTTP documentaire futur doit être court, borné et considéré comme une optimisation de transport, jamais comme une source de vérité.

## Tests

Les tests CI utilisent des fixtures et faux clients HTTP. Aucun test unitaire ne doit dépendre de la disponibilité d'Eurostat, Légifrance, budget.gouv.fr, d'un moteur de découverte ou d'une autre source externe.
