# ACFPF — Instructions permanentes pour les agents

Ce fichier définit la ligne directrice du projet. Toute modification du dépôt doit respecter ces règles, sauf décision explicite documentée dans une PR et dans ce fichier.

## 1. Mission

ACFPF est un outil citoyen, reproductible et non partisan d'analyse des finances publiques françaises, principalement sur la période 2000–2025.

Le projet ne doit jamais être conçu pour confirmer une opinion prédéfinie. Une hypothèse peut être confirmée, nuancée ou réfutée.

## 2. Données et méthode

- Privilégier les sources primaires : INSEE, administrations, juridictions financières, organismes de Sécurité sociale, Eurostat, OCDE, Commission européenne, etc.
- Conserver pour chaque donnée la provenance, le millésime/publication, l'unité, le périmètre et les transformations appliquées.
- Ne jamais mélanger silencieusement deux bases statistiques ou deux définitions différentes.
- Distinguer clairement données définitives, semi-définitives, provisoires et estimées.
- Ne jamais coder en dur un chiffre analytique dans un template ou un composant UI : les chiffres affichés doivent provenir de la couche de données.
- Toute conclusion importante doit pouvoir être reproduite par le code et reliée à ses sources.
- Une série de référence versionnée est acceptable pour permettre un fonctionnement local déterministe, à condition que sa source, sa date et sa méthode de construction soient documentées.

## 3. Architecture

- Python >= 3.11.
- Une seule commande utilisateur doit suffire pour lancer l'application après installation : `acfpf`.
- Le point d'entrée doit rester stable même si l'architecture interne évolue.
- L'application locale utilise Flask et du rendu serveur tant qu'une architecture plus complexe n'est pas justifiée par un besoin réel.
- Éviter une SPA ou un framework frontend lourd sans bénéfice démontré.
- Séparer strictement : acquisition/normalisation des données, logique d'analyse, présentation web.
- Les routes Flask ne doivent pas contenir la logique métier ou de calcul substantielle.
- Éviter les dépendances réseau côté navigateur pour les fonctions essentielles : l'interface doit rester utilisable localement sans CDN.

## 4. UX/UI

ACFPF possède son propre langage visuel. Ne pas copier le design d'un autre projet.

Principes :

- respecter les conventions d'interfaces web connues avant d'inventer de nouveaux patterns ;
- hiérarchie visuelle claire et densité adaptée à un outil d'analyse ;
- navigation active unique et non ambiguë ;
- contraste lisible et accessibilité visée au minimum WCAG AA ;
- responsive desktop/tablette/mobile ;
- états hover, focus, active, disabled, loading et error explicites ;
- animations rares, courtes et fonctionnelles ;
- priorité à la lisibilité, à la rapidité et à la compréhension des données.

### Design system et thèmes

Les composants ne doivent pas contenir de couleurs, typographies, ombres, rayons ou espacements de marque codés en dur.

Ils doivent consommer des **design tokens sémantiques** (CSS custom properties). Les valeurs sont définies dans des fichiers de thème séparés.

Objectif : pouvoir passer facilement d'un rendu, par exemple, `institutional` à `journalistic` sans modifier les templates ni les composants.

Les thèmes peuvent modifier notamment :

- familles et échelles typographiques ;
- couleurs de surfaces, textes, accent et états ;
- rayon des composants ;
- ombres ;
- densité/espacements ;
- traitement des bordures ;
- style des graphiques.

Les noms de tokens doivent exprimer un rôle (`--color-text-primary`) et non une couleur (`--blue-700`).

Voir `docs/UI_UX.md` et, pour l'implémentation web, `src/acfpf/web/AGENTS.md`.

## 5. Graphiques et interprétation

- Axes, unités, période et source doivent être visibles.
- Ne pas tronquer un axe de façon susceptible de tromper sans justification explicite.
- Le choix des couleurs ne doit pas porter implicitement un jugement politique ou moral.
- Une variation doit être présentée avec son unité : points de PIB, %, euros constants, euros/habitant, etc.
- Différencier corrélation, constat descriptif et causalité.
- Afficher les limites de données quand elles peuvent changer l'interprétation.

## 6. Tests et qualité

Toute fonctionnalité non triviale doit être testée.

Minimum attendu :

- tests unitaires de la logique de données ;
- tests de cohérence des séries (années, doublons, unités, identités simples) ;
- tests des routes/API Flask ;
- tests de non-régression pour quelques valeurs de référence officielles ;
- `ruff check .` et `pytest` verts avant fusion.

Les tests ne doivent pas dépendre d'un serveur externe disponible en temps réel. Les téléchargements live sont des tests d'intégration distincts.

## 7. Performance

- Le démarrage local doit rester rapide.
- Ne pas recharger/recalculer inutilement les mêmes données à chaque requête.
- Préférer HTML/CSS/JS léger et local.
- Toute dépendance importante doit apporter une valeur fonctionnelle claire.

## 8. Licence

- Code et éléments logiciels : `PolyForm-Noncommercial-1.0.0` sauf mention contraire.
- Documentation et contenu éditorial original : `CC-BY-4.0`.
- Données tierces : licence du producteur ; ne jamais les relicencier implicitement.
- Respecter le CLA et la politique décrits dans `CONTRIBUTING.md` et `LICENSES/README.md`.

## 9. Workflow Git

- Développer les évolutions significatives sur une branche dédiée.
- Faire une PR vers `main`.
- Vérifier le diff et la CI avant fusion.
- Privilégier un squash merge pour garder un historique lisible.
- Documenter dans la PR les décisions d'architecture ou de méthodologie importantes.

## 10. Évolution de ces règles

Si une décision structurante change (stack, méthodologie, conventions UX/UI, politique de données, licence), mettre à jour le ou les `AGENTS.md` concernés dans la même PR.
