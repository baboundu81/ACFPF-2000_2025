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
