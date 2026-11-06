<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Étape 3 — Interface et parcours V1

Contrôles effectués le 6 novembre 2026, Linux, Python 3.11, Node et navigateur
Chromium intégré. Étape 3 uniquement ; la recette globale de l’étape 4 n’est pas engagée.

## Résultat et décisions

L’accueil réunit désormais question libre et découverte des textes. Le formulaire
d’enquête est partagé avec les finances et reste disponible si les inventaires
parlementaires échouent. Sans critères explicites, l’accueil n’attend aucun téléchargement
de ces inventaires. La recherche explicite conserve les filtres et le tri déterministes.

Le dossier présente identité, statut, provenance, fraîcheur, limites et accès au chat,
puis huit rubriques avancées repliées. Les modules existants et leurs API sont conservés.
Versions, scrutins, rapports et amendements ne téléchargent leurs notices qu’à la première
ouverture de leur rubrique ; les boutons et filtres continuent de fonctionner ensuite.
Les dates futures sont qualifiées de prévues dans la source sans modifier les données,
les statuts ni l’ordre des résultats. Les timestamps avec fuseau sont affichés en heure
de Paris. Les métadonnées restent distinctes des preuves documentaires.

Les états occupé, erreur et preuves insuffisantes sont explicites ; les formulaires
se réactivent après le flux. Le chat respecte la préférence de réduction du mouvement.
Des liens d’évitement et le focus visible sont disponibles. Les changements visuels
consomment des tokens sémantiques ; aucun framework ni dépendance n’est ajouté.

Fichiers principaux : `web/app.py`, `web/presentation.py`, les templates d’accueil,
de dossier et le formulaire partagé, les CSS et scripts locaux, ainsi que
`tests/test_v1_user_journeys.py` et `tests/js/dossier_lazy_sections.test.js`.

## Vérifications sans réseau

- `.venv/bin/ruff check .` : réussi.
- `.venv/bin/pytest -q` : **354 réussis, 17 ignorés** (tests live à activation explicite).
- `node --check` sur tous les scripts de `src/acfpf/web/static/js` : réussi.
- `node --test tests/js/*.test.js` : **17 réussis**.
- `git diff --check` : réussi.

Les nouveaux tests couvrent accueil indépendant des inventaires, accueil et finances
sans dossier obligatoire, navigation sans IA, chat avant les outils avancés, IDs uniques,
fraîcheur et dates futures sans mutation, et parcours accueil → recherche → dossier →
chat via le véritable service civique avec fournisseur et HTTP simulés. Une tentative
de substitution du titre/URL par le navigateur conserve le contexte officiel du backend.
Les quatre scripts de notices sont exécutés en VM : aucune requête au rendu ou à la
fermeture, un premier chargement à l’ouverture, sans second chargement au toggle suivant.
Ces tests ne constituent pas une validation de fournisseur réel.

## Réseau et navigateur réels

Commande live :

```sh
ACFPF_LIVE_SOURCES=1 .venv/bin/pytest -q \
  tests/test_live_official_legislation.py tests/test_live_official_documents.py \
  tests/test_live_official_votes.py tests/test_live_official_fulltext.py \
  tests/test_live_official_actors.py tests/test_live_official_reports.py \
  tests/test_live_official_debates.py
```

Résultat : **7 réussis, 1 ignoré** (archive complète des débats non activée).

Navigateur sur Flask local, avec puis sans IA :

- Accueil desktop 1265 px : deux parcours identifiables, formulaire libre visible à
  côté de l’introduction. Une première disposition plaçait le formulaire trop bas :
  correction en deux colonnes desktop puis nouvelle capture vérifiée.
- Formats 768, 390 et 320 px : accueil, formulaire et navigation lisibles, vérification
  des largeurs DOM sans débordement global. Finances vérifiées à 390 et 320 px ;
  le retour à la ligne de la navigation corrige le débordement constaté au premier passage.
- Recherche stricte « logement » : 30 résultats officiels et filtres. Parcours sans IA
  rejoué au clavier/formulaire, puis clic du résultat jusqu’à `/textes/DLR5L17N54628`.
- Dossier : chat placé avant les outils ; rubriques initialement fermées. Ouverture de
  « Versions du texte et comparaison expérimentale » : chargement puis deux notices
  réelles, limites expérimentales et liens officiels visibles.
- Clavier : passage du champ libre au bouton avec focus visible. Rubriques natives
  utilisables sans contrôle personnalisé. Pas d’audit exhaustif au lecteur d’écran.
- Sans configuration IA : message explicite, découverte et dossier accessibles.
- Question libre réelle demandant le titre d’une page officielle : ouverture de la page
  observée, puis échec 429 à la vérification finale après deux reprises. Diagnostic
  visible et bouton réactivé ; aucun candidat non vérifié publié.
- Chat contextualisé réel : question limitée au titre officiel du dossier ci-dessus.
  Page officielle ouverte et lue ; deux attentes de quota de 20 puis 40 secondes.
  Réponse finale correcte avec lien **E1 / segment 1**, fournisseur Groq,
  modèle `openai/gpt-oss-120b`, et formulaire réactivé. Cette réussite limitée ne vaut
  pas recette générale des questions législatives ou budgétaires.

Captures locales de contrôle : `/tmp/acfpf-step3-home-desktop.jpg` et
`/tmp/acfpf-step3-home-mobile.jpg` (temporaires, hors dépôt).
Contrastes calculés des tokens sur la surface page : texte 16,34:1, texte secondaire
6,20:1, liens 7,52:1, bouton blanc sur accent fort 11,74:1, focus 5,82:1.
Ce contrôle ciblé ne constitue pas une certification WCAG complète.

## Limites et suite

Gemini n’est pas retesté ici : les échecs 503 réels de l’étape 2 restent ouverts.
Le benchmark IA complet et la matrice de dix scénarios ne sont pas répétés : ils
relèvent de la recette de l’étape 4. Les quotas Groq peuvent interrompre une enquête
malgré les reprises bornées ; la disponibilité des sources reste externe au produit.

Branche : `codex/v1-step3-user-journeys`, construite sur `3266a6f` (étape 2).
La PR vers `main` dépend des étapes précédentes non fusionnées (#58, #59, #60).
Aucune fusion, aucun tag, aucune release. Le compte rendu de session donne le commit,
le lien de PR et le résultat CI après publication. Les fichiers de clés utilisateur
et les pièces jointes restent hors commit.

**Étape 3 validée pour son périmètre UI**, avec les limites ci-dessus.
Il reste **deux étapes** : 4 (recette fonctionnelle réelle), puis 5 (livraison testable).
Arrêt obligatoire avant l’étape 4.
