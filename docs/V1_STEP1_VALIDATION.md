<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# V1 — validation de l’étape 1, 6 novembre 2026

## Périmètre et résultat

L’étape 1 fiabilise le **moteur documentaire sans dossier obligatoire**.
Elle est validée sur les tests déterministes du parcours complet et sur des lectures
réelles, avec les limites fournisseurs explicitement décrites ci-dessous.
Ce statut ne valide pas les étapes 2 à 5 ni une livraison V1.

Branche : `codex/v1-step1-documentary-engine`, construite sur `1bd3226` (étape 0).
La PR #58 de l’audit était encore ouverte au début de cette session ; elle n’a pas
été fusionnée automatiquement. La contribution de l’étape 1 dépend de cet audit.
Aucun connecteur parlementaire avancé, nouveau fournisseur, formulaire ou refonte UI
n’est ajouté. Les fichiers locaux de clés sont exclus des commits et des rapports.

## Corrections et garanties vérifiées

- Téléchargement en flux, limites sur la taille annoncée et les octets décompressés
  reçus, fermeture des réponses y compris sur erreur, délai de lecture borné.
- HTTP complet requis ; refus des réponses partielles 206, des erreurs et redirections
  sans destination ou excessives. Chaque redirection officielle est revalidée avant requête.
- Validation des URL mal formées, identifiants, ports, domaines voisins trompeurs,
  schémas non HTTPS et caractères invalides avant tout appel réseau.
- Index Web borné, redirections refusées, résultats limités aux sources autorisées ;
  snippets exclus. HTTP 202 de l’index est distingué d’un résultat vide.
- Extraction HTML/PDF avec refus des types incompatibles, PDF invalides/chiffrés/sans texte,
  limites de pages et de texte ; aucune troncature ni présélection par pertinence.
- Provenance unique pour les producteurs partageant un domaine : utilisation du `base_url`
  le plus spécifique, refus en cas d’ambiguïté (notamment Eurostat/Commission européenne).
- Identifiants des documents/preuves, URL finale, titre, locator, date et SHA-256 conservés ;
  relecture sans duplication d’identifiant et isolation entre deux questions.
- Échecs et recherches vides visibles dans la progression **et au prochain tour de l’agent**
  via `RESEARCH_NOTICES`, sans devenir des preuves. Le modèle peut ainsi reformuler,
  essayer une autre source autorisée ou déclarer explicitement `insufficient`.

Les limites exactes sont documentées dans [AI.md](AI.md#transport-documentaire-borné-v1-étape-1).
Les invariants de citation existants n’ont pas été assouplis.

## Tests déterministes

Environnement local : Linux, Python 3.14.8 du `.venv` existant, Node 22.22.2.
Aucune nouvelle dépendance. Commandes et résultats :

| Contrôle | Résultat |
| --- | --- |
| `.venv/bin/ruff check .` | Réussi |
| `.venv/bin/pytest -q` | **273 passed, 9 skipped**, 4,11 s |
| `node --check` sur les scripts web locaux | Réussi |
| `node --test tests/js/*.test.js` | **3 passed** |
| `git diff --check` | Réussi |

72 tests supplémentaires sans réseau : 58 cas du lecteur/transport et 14 cas du
parcours Flask utilisant le vrai `LiveOfficialResearch` et le vrai agent avec HTTP/LLM
simulés. Ces derniers couvrent JSON et NDJSON, HTML long et PDF de cinq pages,
relecture d’une unité, absence de résultat, panne d’index, timeout, HTTP 404,
transfert interrompu, taille excessive, PDF invalide, redirection interdite,
citation d’un segment non lu et isolation entre questions. Les PDF sont générés
localement par le test, sans contenu tiers.

Le service de dossiers du test refuse tout accès : les requêtes `/api/ask` et
`/api/ask/stream` fonctionnent avec seulement `question`, sans `dossier_id`.
Le scénario positif vérifie le contenu réellement transmis au fournisseur factice,
les métadonnées de chaque citation et l’absence des snippets dans ses requêtes.
Les scénarios négatifs aboutissent à une absence de preuve explicite ou au refus
d’une citation inconnue ; aucun document rejeté ne reçoit d’identifiant citable.

## Réseau réel, distinct des simulations

`ACFPF_LIVE_DOCUMENTARY=1 .venv/bin/pytest -q -s tests/test_live_documentary_pipeline.py` :
**1 passed**, 2,42 s. Recherche « logement sollicitations sexuelles abusives » sur
`assemblee_nationale_open_data`, ouverture du premier résultat et lecture du premier
segment sans LLM ni service de dossiers. Résultat réellement lu :

- URL : `https://www.assemblee-nationale.fr/dyn/17/dossiers/DLR5L17N54628` ;
- titre officiel : proposition de loi visant à protéger les demandeurs de logement
  contre les sollicitations sexuelles abusives ;
- source `assemblee_nationale_open_data`, `segment 1`, 7 090 caractères ;
- SHA-256 : `b0b2cb54f737aa55929d2df568b97c0620d93634c7abd752c784ec79fe93b3dc`.

Une sonde directe antérieure a également retourné deux URL puis lu cette page.
Ces résultats prouvent le transport et l’extraction de la page, pas une interprétation
juridique du texte proposé.

La suite live préexistante des sept fichiers `tests/test_live_official_*.py` (hors nouvelle
sonde dédiée) a donné **6 passed, 1 failed, 1 skipped**, 20,08 s : l’échec reste le transfert
de l’index des amendements du dossier `54629`, déjà observé à l’étape 0. Le test de grosse
archive Syceron reste ignoré sans `ACFPF_LIVE_DEBATES_FULL=1`. Ce connecteur structuré
n’utilise pas `LiveOfficialResearch` ; aucune correction hors périmètre n’a été ajoutée.

## Boucle navigateur UX/UI et vrais fournisseurs

Les essais utilisent le formulaire existant sous `/finances` : son POST ne contient
pas de `dossier_id`. L’ajout de la question libre sur l’accueil reste à l’étape 3.
Les clés sont chargées uniquement dans les processus Flask temporaires côté serveur.

1. **Gemini réel, modèle par défaut du dépôt** : question générale sur les sollicitations
   sexuelles dans la recherche de logement. L’appel fournisseur s’arrête sur `ReadTimeout`
   après 30 secondes, avant recherche documentaire. L’interface affiche l’erreur et
   réactive le bouton. Ce n’est pas une analyse réelle réussie.
2. **Groq réel, modèle par défaut du dépôt** : même question. HTTP 400, validation JSON
   refusée par le fournisseur. L’erreur est visible et le formulaire redevient utilisable.
   Pas de changement de modèle ou de schéma dans cette étape.
3. **Rejeu de protocole local explicitement simulé + vrai réseau documentaire** : script
   temporaire hors dépôt (`/tmp/acfpf-step1-browser-harness.py`), fournisseur nommé
   `test-scripted / protocol-replay-no-llm`. La recherche reçoit cette fois HTTP 202 de
   l’index ; l’interface montre l’indisponibilité et une réponse « Preuves insuffisantes »
   sans citation. Ce résultat est distinct de la sonde réseau réussie précédente.
4. **Même rejeu, URL officielle fournie dans une question libre** : ouverture et lecture
   réseau du dossier cité ci-dessus, progression puis résultat technique avec citation
   E1, locator et date. Le résultat précise qu’il n’est pas une analyse par un vrai LLM.
   Contrôle du lien de preuve et inspection responsive à 390 × 844, puis retour au format normal.
   Le bloc de réponse/citation est lisible ; la largeur globale de la page finances atteint
   toutefois 425 px pour un viewport de 390 px (débordement horizontal à corriger à l’étape 3).
   Capture locale de ce contrôle : `/tmp/acfpf-step1-browser-mobile.jpg` (non versionnée).

Ce rejeu ne modifie ni les templates ni le comportement normal de l’application.
Il sépare la validation lecteur/stream/UI des erreurs des fournisseurs réels.
Aucune réponse documentaire avec un vrai LLM n’est déclarée réussie dans cette session.

## Limites et suite

- **Étape 2** : résoudre et vérifier les échecs des fournisseurs, fidélité assertion/preuve,
  comportements avec/sans dossier et progression réelle. Les tests présents ne démontrent
  pas que chaque affirmation d’une réponse serait correctement étayée.
- **Étape 3** : question libre sur l’accueil et UX globale ; le libellé du formulaire reste
  financier malgré l’API générale. Aucune validation WCAG AA exhaustive ici.
- L’index Web est une dépendance externe susceptible de bloquer ou limiter la recherche.
  Le lecteur accepte une URL officielle fournie même si cet index est indisponible.
- Les plafonds bornent les entrées et sorties du lecteur ; ils ne constituent pas une
  isolation CPU/mémoire du parseur PDF contre tout document hostile. Pas d’OCR ni de navigateur
  JavaScript documentaire. Un type MIME incorrect est refusé et signalé.
- La panne intermittente de l’index structuré des amendements reste à qualifier avant
  la recette des fonctionnalités concernées. Ni les tests ignorés ni les essais fournisseurs
  échoués ne sont comptés comme des réussites.

Arrêt après cette étape et préparation de sa PR ; aucune mise en œuvre de l’étape 2.
