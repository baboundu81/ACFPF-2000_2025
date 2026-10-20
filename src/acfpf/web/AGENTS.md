# Instructions spécifiques à l'interface web

Ce fichier complète le `AGENTS.md` racine et s'applique à tout `src/acfpf/web/**`.

## Stack

- Flask + Jinja pour le rendu serveur.
- JavaScript vanilla pour les interactions simples.
- Pas de framework SPA sans décision d'architecture documentée.
- Pas de CDN requis pour une fonctionnalité essentielle.

## Design system

- `static/css/tokens.css` contient les échelles et tokens communs.
- `static/css/theme-*.css` contient les valeurs des thèmes.
- `static/css/app.css` contient les composants et layouts ; il doit consommer des tokens sémantiques.
- Une valeur de marque (couleur, typo, rayon, ombre) ne doit pas être répétée directement dans les composants.
- Ajouter un nouveau thème doit se limiter principalement à un nouveau fichier `theme-*.css` et à son enregistrement dans le sélecteur/configuration.

## Thèmes

Thèmes initiaux :

- `institutional` : sobre, structuré, données de référence ;
- `journalistic` : plus éditorial, hiérarchie typographique marquée.

Aucun thème ne doit changer la sémantique, l'ordre ou le contenu des données.

## Composants

- Un seul élément de navigation est actif à la fois.
- Les cartes KPI affichent valeur, unité, période/comparaison et contexte minimal.
- Les tableaux restent disponibles lorsque le graphique est la représentation principale d'une série.
- Les composants interactifs doivent avoir un focus visible et être utilisables au clavier.

## Données

- Les templates reçoivent des view-models ; ils ne réalisent aucun calcul financier.
- Les endpoints JSON lisent la même couche de données que les pages HTML.
- Ne jamais dupliquer une série dans le JavaScript ou l'HTML.
- Les sources et millésimes doivent être visibles dans l'interface.

## Performance

- Éviter les bibliothèques graphiques lourdes tant que des SVG légers suffisent.
- Le navigateur ne doit pas refaire des calculs métier.
- Charger uniquement les assets nécessaires à la page.
