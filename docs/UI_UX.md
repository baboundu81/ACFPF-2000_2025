<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# UX/UI d'ACFPF

## Objectif

ACFPF est un outil d'analyse de données publiques. Son interface doit inspirer confiance, rendre les chiffres lisibles et donner envie d'explorer les sources sans imiter visuellement une institution ou un média existant.

La direction actuelle est **journalistique** : forte hiérarchie éditoriale, chiffres mis en avant, textes explicatifs courts, sources visibles et lecture fluide.

Il n'existe pas de sélecteur de thème. Le design doit toutefois pouvoir être refondu facilement plus tard sans réécrire les templates ou les composants.

## Architecture du design system

Le design est séparé en trois couches :

1. **tokens structurels** : échelles d'espacement, tailles et règles communes ;
2. **tokens sémantiques** : surfaces, textes, accents, bordures, typographies, rayons et ombres ;
3. **composants** : navigation, indicateurs, tableaux, graphiques, appels de source et contenus éditoriaux qui ne consomment que des tokens sémantiques.

Le set de tokens actuel correspond au style journalistique. Un futur changement de direction visuelle doit principalement modifier ce set, pas l'HTML.

## Direction journalistique

Intention : donner le sentiment de consulter une publication de données sérieuse plutôt qu'un logiciel d'administration ou un dashboard d'entreprise générique.

Principes :

- titres éditoriaux avec contraste typographique marqué ;
- typographie de lecture sobre pour le corps ;
- grands chiffres utilisés avec parcimonie ;
- séparation des sections principalement par rythme, bordures et espace plutôt que par accumulation de cartes ;
- graphiques intégrés dans le récit ;
- textes de contexte et sources immédiatement accessibles ;
- palette réduite et non partisane ;
- densité suffisamment aérée pour lire, suffisamment compacte pour comparer.

## Tokens

Exemples de tokens sémantiques :

```css
--font-body
--font-heading
--font-data
--color-page
--color-surface
--color-text-primary
--color-text-secondary
--color-border
--color-accent
--color-accent-strong
--color-positive
--color-negative
--radius-control
--shadow-overlay
--content-max-width
```

Les composants ne doivent pas utiliser des variables liées à une couleur précise du type `--blue-700`.

## Navigation

Architecture cible :

- Tableau de bord ;
- Finances publiques ;
- Prélèvements ;
- Services publics ;
- Protection sociale ;
- Fraudes ;
- Aides aux entreprises ;
- Sources & méthodologie.

Au démarrage du projet, seules les sections réellement disponibles sont actives. Les fonctionnalités futures ne doivent pas être présentées comme fonctionnelles.

## Dashboard

Le tableau de bord doit répondre rapidement à trois questions :

1. qu'est-ce que je regarde ?
2. qu'est-ce qui a changé ?
3. d'où viennent les chiffres ?

Structure recommandée :

- titre et période ;
- état des données / millésime ;
- indicateurs clés ;
- graphique principal ;
- premier constat descriptif ;
- source et limites ;
- accès au détail.

## Expérience d'enquête IA

L'assistant n'est pas présenté comme un chatbot omniscient. L'expérience doit ressembler à une **enquête vérifiable** menée sur les données et sites officiels.

Avant la question, l'interface explique quatre garanties :

- les domaines accessibles sont bornés par ACFPF ;
- les documents sont consultés en direct lorsque nécessaire ;
- les calculs structurés sont effectués par le backend ;
- une source ne devient citable qu'après lecture effective.

Pendant l'enquête, afficher progressivement les actions observables :

- préparation ;
- recherche de documents ;
- ouverture d'une source officielle ;
- lecture d'une page ou d'un segment supplémentaire ;
- avertissement si une recherche échoue ;
- fin de l'enquête.

Ne pas afficher la chaîne de pensée privée du modèle. Une justification opérationnelle courte comme « vérifier l'exécution budgétaire » est acceptable ; un raisonnement interne détaillé ne l'est pas.

À la fin :

- distinguer visuellement une réponse sourcée d'un état « preuves insuffisantes » ;
- rendre chaque preuve cliquable vers la source officielle ;
- afficher le locator disponible (page ou segment) ;
- exposer les limites pertinentes ;
- ne pas présenter les résultats de recherche non ouverts comme des sources utilisées.

La progression doit être utile même si l'enquête prend plusieurs secondes : l'utilisateur doit comprendre que l'outil consulte réellement des sources plutôt que d'attendre devant un spinner opaque.

## Accessibilité

- contraste minimum WCAG AA visé ;
- navigation clavier ;
- focus visible ;
- ne jamais utiliser uniquement la couleur pour transmettre une information ;
- tableaux accessibles pour les séries importantes ;
- support de `prefers-reduced-motion`.

## Graphiques

- source toujours associée ;
- légende explicite ;
- unités visibles ;
- table de données disponible lorsque pertinent ;
- palette non partisane ;
- pas d'effets 3D ;
- pas de décor qui masque la lecture ;
- graphiques utilisables sans dépendance CDN.

## Performance

L'interface doit rester légère. Une amélioration esthétique ne doit pas dégrader sensiblement le temps de démarrage, le temps d'affichage ou la fluidité.

Pour l'enquête IA, le flux de progression est diffusé en NDJSON et traité progressivement ; le navigateur ne doit pas recevoir ni conserver les contenus complets des documents lus par le backend.
