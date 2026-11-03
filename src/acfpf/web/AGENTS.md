# Instructions spécifiques à l'interface web

Ce fichier complète le `AGENTS.md` racine et s'applique à tout `src/acfpf/web/**`.

## Stack

- Flask + Jinja pour le rendu serveur.
- JavaScript vanilla pour les interactions simples.
- Pas de framework SPA sans décision d'architecture documentée.
- Pas de CDN requis pour une fonctionnalité essentielle.

## Navigation produit

- L'accueil `/` est l'expérience principale d'analyse citoyenne : découverte et recherche de textes/décisions.
- Un dossier législatif est ouvert sous `/textes/<id>` et possède son espace d'analyse et son chat contextualisé.
- Les finances publiques sont un sous-outil spécialisé sous `/finances`.
- Un seul élément de navigation principale doit être actif à la fois.
- L'utilisateur ne doit pas être obligé de connaître le nom officiel d'un texte pour le retrouver.

## Design system

- `static/css/tokens.css` contient l'ensemble des tokens sémantiques du design courant.
- `static/css/app.css` contient les composants et layouts ; il doit consommer les tokens de `tokens.css`.
- Les styles spécialisés peuvent être séparés dans des fichiers dédiés comme `static/css/ai.css` ou `static/css/legislation.css`, mais doivent eux aussi consommer les tokens sémantiques.
- Une valeur de marque (couleur, typo, rayon, ombre, densité) ne doit pas être répétée directement dans les composants.
- Le design courant est **journalistique**.
- Il n'y a pas de sélecteur de thème ni de mécanisme de bascule à chaud.
- Si la direction visuelle change un jour, le changement doit pouvoir être réalisé principalement en modifiant `tokens.css` et, si nécessaire, quelques règles structurelles ciblées, sans réécrire les templates.

## Direction visuelle

- hiérarchie éditoriale forte ;
- grands chiffres utilisés avec sobriété ;
- sources et contexte visibles ;
- séparation par rythme, espace et bordures plutôt que par empilement systématique de cartes ;
- palette courte et non partisane ;
- lecture confortable des tableaux, chronologies et graphiques.

## Composants

- Les résultats de recherche législative doivent afficher au minimum le titre, le statut dérivé, la dernière activité disponible et la provenance.
- Les critères de tri et de filtre doivent rester compréhensibles et reproductibles.
- Une fiche dossier doit distinguer les métadonnées d'orientation des documents qui constituent effectivement des preuves.
- Les KPI affichent valeur, unité, période/comparaison et contexte minimal.
- Les tableaux restent disponibles lorsque le graphique est la représentation principale d'une série.
- Les composants interactifs doivent avoir un focus visible et être utilisables au clavier.

## Données

- Les templates reçoivent des view-models ; ils ne réalisent aucun calcul financier ou législatif substantiel.
- Les endpoints JSON lisent la même couche de données que les pages HTML.
- Ne jamais dupliquer une série ou une liste de dossiers dans le JavaScript ou l'HTML.
- Les sources et millésimes doivent être visibles dans l'interface.
- Les métadonnées d'un dossier envoyées au modèle doivent être récupérées à nouveau côté serveur depuis l'identifiant du dossier ; ne pas faire confiance à un titre ou une URL fournis par le navigateur.

## IA et enquête dans l'interface

- La clé API d'un fournisseur LLM reste exclusivement côté serveur et ne doit jamais apparaître dans le HTML, le JavaScript ou une réponse API.
- `/api/ask` fournit la réponse finale JSON ; `/api/ask/stream` expose la progression de l'enquête en NDJSON.
- Un chat de dossier peut envoyer l'identifiant du dossier et un historique court, mais le backend reste responsable de reconstruire le contexte de confiance.
- La progression peut afficher uniquement des actions observables : préparation, recherche, ouverture d'une source, lecture d'une unité, avertissement, réponse.
- Ne jamais afficher ni demander la chaîne de pensée privée du modèle. Le champ `reason` d'une action doit rester une justification opérationnelle brève, pas un raisonnement détaillé.
- Les résultats de recherche qui n'ont pas été ouverts ne doivent pas être présentés comme des sources utilisées.
- Les liens affichés comme preuves doivent correspondre exclusivement aux citations validées par `acfpf.ai`.
- Pour chaque preuve live, afficher le locator disponible et permettre d'ouvrir la source officielle.
- L'interface doit expliquer clairement que la recherche est live et limitée à la liste blanche ACFPF ; elle ne doit pas laisser croire que le LLM possède un navigateur Web libre.
- L'absence de configuration IA ne doit pas bloquer la découverte des dossiers ni les autres fonctions déterministes.
- En cas de preuves insuffisantes, afficher clairement `insufficient` et les limites plutôt qu'une réponse approximative.

## Performance

- Éviter les bibliothèques graphiques lourdes tant que des SVG légers suffisent.
- Le navigateur ne doit pas refaire des calculs métier.
- Charger uniquement les assets nécessaires à la page.
- Le flux NDJSON doit être consommé progressivement sans conserver des copies inutiles des documents consultés dans le navigateur.
