# ACFPF — Instructions permanentes pour les agents

Ce fichier définit la ligne directrice du projet. Toute modification du dépôt doit respecter ces règles, sauf décision explicite documentée dans une PR et dans ce fichier.

## 1. Mission

ACFPF est un outil citoyen, reproductible et non partisan d'analyse des finances publiques françaises, principalement sur la période 2000–2025.

Le projet ne doit jamais être conçu pour confirmer une opinion prédéfinie. Une hypothèse peut être confirmée, nuancée ou réfutée.

## 2. Données, documents et méthode

- Privilégier les sources primaires : INSEE, administrations, juridictions financières, organismes de Sécurité sociale, Eurostat, OCDE, Commission européenne, Légifrance, Assemblée nationale, Sénat, etc.
- Conserver pour chaque donnée ou document la provenance, le millésime/publication, l'unité ou le type de texte, le périmètre et les transformations appliquées.
- Toute preuve doit être qualifiée par son stade : `statistical_observation`, `forecast`, `decision`, `execution`, `evaluation`, `parliamentary_process` ou `interpretation`.
- Ne jamais présenter une prévision ou une autorisation budgétaire comme une dépense exécutée.
- Ne jamais présenter un amendement proposé ou rejeté comme une décision applicable.
- Une évolution statistique ne démontre pas à elle seule la cause de cette évolution.
- Une baisse en points de PIB ne doit pas être appelée « économie » sans métrique complémentaire permettant de justifier ce terme.
- Ne jamais mélanger silencieusement deux bases statistiques ou deux définitions différentes.
- Distinguer clairement données définitives, semi-définitives, provisoires et estimées.
- Ne jamais coder en dur un chiffre analytique dans un template ou un composant UI : les chiffres affichés doivent provenir de la couche de données.
- Toute conclusion importante doit pouvoir être reproduite par le code et reliée à ses sources.
- Une série de référence versionnée est acceptable pour permettre un fonctionnement local déterministe, à condition que sa source, sa date et sa méthode de construction soient documentées.
- Pour les documents textuels, la stratégie par défaut est **live-first** : consulter la source officielle au moment de la question plutôt que maintenir un corpus local exhaustif.
- La recherche live est limitée aux domaines explicitement autorisés dans `config/sources.yml`. Toute URL et toute redirection doivent être revalidées par le backend avant lecture.
- Un moteur ou index Web peut servir uniquement à découvrir des URL officielles ; ses snippets et résumés ne constituent jamais des preuves et ne doivent pas être fournis au LLM comme faits.
- Une URL n'est citable qu'après ouverture et lecture effective par ACFPF. Conserver autant que possible l'URL, le titre, le locator (page/segment), la date de consultation et l'empreinte du document.
- Ne pas présélectionner des paragraphes par score lexical/vectoriel avant lecture par le modèle. Toute segmentation doit être mécanique, contiguë et conserver l'ordre de la source.

Voir `docs/EVIDENCE.md` pour la convention de preuve.

## 3. Architecture

- Python >= 3.11.
- Une seule commande utilisateur doit suffire pour lancer l'application après installation : `acfpf`.
- Le point d'entrée doit rester stable même si l'architecture interne évolue.
- L'application locale utilise Flask et du rendu serveur tant qu'une architecture plus complexe n'est pas justifiée par un besoin réel.
- Éviter une SPA ou un framework frontend lourd sans bénéfice démontré.
- Séparer strictement : acquisition/normalisation des données, recherche live officielle, validation des preuves, logique d'analyse et présentation web.
- Les routes Flask ne doivent pas contenir la logique métier ou de calcul substantielle.
- Les séries structurées doivent rester traitées par des fonctions déterministes ; le LLM sert à piloter la recherche et à synthétiser les preuves.
- La couche IA doit rester indépendante du fournisseur de modèle.
- Éviter les dépendances réseau côté navigateur pour les fonctions essentielles : l'interface doit rester utilisable localement sans CDN.

## 4. UX/UI

ACFPF possède son propre langage visuel. Ne pas copier le design d'un autre projet.

Le style courant est **journalistique** : lecture éditoriale, hiérarchie typographique forte, mise en avant des chiffres, des constats, des sources et du contexte. Il n'existe pas de sélecteur de thème dans l'interface.

Principes :

- respecter les conventions d'interfaces web connues avant d'inventer de nouveaux patterns ;
- hiérarchie visuelle claire et densité adaptée à un outil d'analyse ;
- navigation active unique et non ambiguë ;
- contraste lisible et accessibilité visée au minimum WCAG AA ;
- responsive desktop/tablette/mobile ;
- états hover, focus, active, disabled, loading et error explicites ;
- animations rares, courtes et fonctionnelles ;
- priorité à la lisibilité, à la rapidité et à la compréhension des données ;
- pour l'enquête IA, rendre visibles les étapes significatives (recherche, ouverture, lecture, réponse) sans exposer de raisonnement privé du modèle ;
- permettre à l'utilisateur d'ouvrir les sources officielles effectivement consultées.

### Design system

Les composants ne doivent pas contenir de couleurs, typographies, ombres, rayons ou espacements de marque codés en dur.

Ils doivent consommer des **design tokens sémantiques** (CSS custom properties) centralisés. Le set de valeurs actuel produit le style journalistique.

L'objectif est de pouvoir refaire entièrement la direction visuelle plus tard en modifiant principalement ce set de tokens, sans réécrire les templates ni les composants. Il ne faut toutefois pas construire de mécanisme de changement de thème tant qu'il n'est pas demandé.

Les tokens peuvent piloter notamment :

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
- tests des métadonnées et stades de preuve ;
- tests de la liste blanche réseau, des redirections et de la lecture documentaire sans appel réseau réel ;
- tests de l'agent multi-étapes et du refus des citations jamais lues ;
- tests des routes/API Flask et du flux de progression ;
- tests de non-régression pour quelques valeurs de référence officielles ;
- `ruff check .` et `pytest` verts avant fusion.

Les tests ne doivent pas dépendre d'un serveur externe disponible en temps réel. Les appels live sont des tests d'intégration distincts.

## 7. Performance

- Le démarrage local doit rester rapide.
- Ne pas recharger/recalculer inutilement les mêmes données à chaque requête.
- Ne pas maintenir par défaut un entrepôt documentaire local massif.
- Les documents lus pendant une question doivent rester éphémères et isolés à cette session ; un éventuel cache HTTP court terme devra être borné, invalidable et ne pas devenir une source de vérité.
- Préférer HTML/CSS/JS léger et local.
- Toute dépendance importante doit apporter une valeur fonctionnelle claire.

## 8. Licence

- Code et éléments logiciels : `PolyForm-Noncommercial-1.0.0` sauf mention contraire.
- Documentation et contenu éditorial original : `CC-BY-4.0`.
- Données et documents tiers : licence du producteur ; ne jamais les relicencier implicitement.
- Respecter le CLA et la politique décrits dans `CONTRIBUTING.md` et `LICENSES/README.md`.

## 9. Workflow Git

- Développer les évolutions significatives sur une branche dédiée.
- Faire une PR vers `main`.
- Vérifier le diff et la CI avant fusion.
- Privilégier un squash merge pour garder un historique lisible.
- Documenter dans la PR les décisions d'architecture ou de méthodologie importantes.

## 10. Évolution de ces règles

Si une décision structurante change (stack, méthodologie, conventions UX/UI, politique de données, politique de preuve, licence), mettre à jour le ou les `AGENTS.md` concernés dans la même PR.
