<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# UX/UI d'ACFPF

## Objectif

ACFPF est un outil d'analyse de données publiques. Son interface doit inspirer confiance sans imiter visuellement une institution ni un média en particulier.

Le design doit pouvoir évoluer rapidement sans réécrire les templates ou les composants.

## Architecture du design system

Le design est séparé en trois couches :

1. **tokens structurels** : échelles d'espacement, tailles, breakpoints et règles communes ;
2. **tokens sémantiques de thème** : surfaces, textes, accents, bordures, typographies, rayons, ombres ;
3. **composants** : cartes, navigation, boutons, tableaux et graphiques qui ne consomment que des tokens sémantiques.

Les composants ne doivent pas savoir si le thème est « institutionnel », « journalistique » ou autre.

## Thèmes initiaux

### Institutional

Intention : sérieux, calme, structuré, très lisible, adapté à la consultation de données de référence.

- typographie sans serif sobre ;
- faible décoration ;
- cartes et tableaux clairement séparés ;
- bordures présentes ;
- accent mesuré ;
- densité moyenne.

### Journalistic

Intention : lecture éditoriale, hiérarchie forte, mise en avant des constats et des explications.

- titres plus éditoriaux ;
- contraste typographique plus marqué ;
- surfaces plus discrètes ;
- graphiques et narratif davantage mis en avant ;
- densité légèrement plus aérée.

Ces thèmes sont des presets de démonstration. De nouveaux thèmes doivent pouvoir être ajoutés sans modifier l'HTML.

## Tokens

Exemples de tokens sémantiques :

```css
--font-body
--font-heading
--color-page
--color-surface
--color-surface-raised
--color-text-primary
--color-text-secondary
--color-border
--color-accent
--color-accent-strong
--color-positive
--color-negative
--radius-card
--shadow-card
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
- tooltips ou table de données quand pertinent ;
- palette non partisane ;
- pas d'effets 3D ;
- pas de décor qui masque la lecture ;
- graphiques utilisables sans dépendance CDN.

## Performance

L'interface doit rester légère. Une amélioration esthétique ne doit pas dégrader sensiblement le temps de démarrage, le temps d'affichage ou la fluidité.
