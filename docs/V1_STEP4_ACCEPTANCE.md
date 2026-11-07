<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Étape 4 — Recette V1 du 7 novembre 2026

**Statut : recette exécutée, clôture non validée.** Les contrôles déterministes et
les garde-fous passent. Les essais IA réels ne permettent pas de déclarer tous les
parcours fiables : Gemini est indisponible et le scénario multi-documents Groq échoue.
Aucun échec réel n’est requalifié en réussite à partir d’un test simulé.

L’utilisateur a expressément demandé d’enchaîner les étapes 4 et 5 dans cette session,
en dérogation au découpage par défaut. Cela ne vaut autorisation ni de fusion ni de release.

## Environnement et changements

Linux ; environnement de développement Python 3.14.8 ; environnement vierge Python 3.11 ;
Chromium intégré, Flask/Jinja et scripts locaux. Branche `codex/v1-acceptance-delivery`,
sur `60784c6` (étape 3). Les PR #58 à #61 sont encore ouvertes à la vérification initiale.

Corrections liées aux essais :

- Le registre réseau dépendait du dossier courant et provoquait `FileNotFoundError`
  hors du checkout. Il est désormais embarqué comme ressource ; sa copie est comparée
  au registre canonique par test. Un fichier homonyme dans le dossier courant est ignoré.
- L’agent reçoit une consigne explicite d’ouvrir une URL fournie et d’exploiter les
  résultats déjà trouvés avant de multiplier les recherches.
- Les unités HTML passent de 12 000 à 4 000 caractères pour réduire le volume initial.
  La segmentation reste mécanique et contiguë ; les unités suivantes restent lisibles.
  Aucune sélection de pertinence, aucun paragraphe supprimé. Ce changement ne garantit
  pas que tous les documents tiennent dans les quotas d’un fournisseur.
- Un candidat rejeté par la validation des citations peut être corrigé **une seule fois**,
  dans les 14 étapes et le budget de reprises existants. La notice contient uniquement
  le diagnostic de validation, jamais le texte refusé. Toute réponse corrigée passe les
  mêmes contrôles et la vérification distincte. Une seconde erreur interrompt l’enquête.

Les tests ajoutés vérifient aussi deux documents et deux empreintes distincts, la
correction suivie d’une ouverture réelle dans le pipeline simulé, l’absence de fuite
des candidats refusés, et l’arrêt après le second candidat invalide.

## Matrice des dix scénarios

| # | Scénario | Sans réseau / contrôle déterministe | Résultat réel du 7 novembre |
| --- | --- | --- | --- |
| 1 | Politique publique, question libre | Pipeline Flask/recherche/lecture/synthèse dans `test_documentary_pipeline.py` | Question sur la protection des demandeurs de logement : 8 URL découvertes, puis recherches HTTP 202 et erreur Groq 429 après reprises. **Non validé** de bout en bout. |
| 2 | Question budgétaire | Séries, unités et routes testées | Groq a comparé le solde 2000/2025, cité S1 et passé le vérificateur. **Réussi pour ce cas limité.** |
| 3 | Textes en cours | Statuts/recherche/tri/filtres testés sans réseau | Inventaires réels, page installée « Textes en cours », 30 résultats et provenance visibles. **Réussi.** |
| 4 | Textes par thème | Recherche et parcours applicatif testés | Recherche stricte « logement », 30 résultats, filtre et ouverture du dossier. **Réussi.** |
| 5 | Dossier puis chat contextualisé | Contexte reconstruit côté serveur, substitution navigateur rejetée | Dossier DLR5L17N54628 ouvert ; page officielle lue et vérification lancée, puis 429 après attentes de 12 et 36 s. **Non validé cette session.** La réussite de l’étape 3 reste historique. |
| 6 | Plusieurs documents | Deux URL, identités et empreintes distinctes ; correction bornée testée | Essais AN + Sénat : rejet initial de citations, puis deux documents effectivement ouverts mais HTTP 413 ; essais suivants HTTP 400 ou E2 jamais lue rejetée. Dernier essai après ajout de la correction : HTTP 400 après ouverture de D1. **Non validé.** |
| 7 | Source absente/inaccessible | 404, timeout, coupure, taille, PDF invalide et redirection interdite simulés | URL officielle volontairement absente : HTTP 404 correctement rejeté par le lecteur. **Réussi au niveau transport ; scénario LLM complet non rejoué.** |
| 8 | Preuves insuffisantes | Résultat `insufficient` sans conclusion inventée ; contrôle navigateur avec fournisseur simulé explicitement | Petit appel réel Groq sans preuves : action `answer`, statut `insufficient`. Pas une enquête documentaire réelle complète. |
| 9 | Erreur/quota fournisseur | 401/403/429/413/503, timeout, JSON invalide, bornes et flux testés | Gemini 503 ; Groq 429, 413 et 400 observés. Diagnostics et réactivation des formulaires vérifiés. **Gestion d’erreur réussie ; disponibilité non acquise.** |
| 10 | Citation jamais lue | Citations inconnues, URL inline non lue, rejet du vérificateur et non-publication testés | Un essai réel multi-documents a cité E2 après seule lecture de E1 : refus backend, aucun candidat publié. État d’erreur aussi vérifié dans le navigateur avec E999 simulée. **Garde-fou réussi.** |

## Commandes et résultats

- `.venv/bin/ruff check .` : réussi.
- `.venv/bin/pytest -q` : **360 réussis, 19 ignorés**.
  Les 19 essais live ne sont pas activés dans la suite ordinaire.
- `node --test tests/js/*.test.js` : **17 réussis** ; syntaxe de tous les scripts contrôlée.
- `ACFPF_LIVE_SOURCES=1 pytest -q -s` sur les sept modules
  `test_live_official_{legislation,documents,votes,fulltext,actors,reports,debates}.py` :
  **7 réussis, 1 ignoré** (archive intégrale des débats non activée).
- `ACFPF_LIVE_DOCUMENTARY=1 pytest -q -s tests/test_live_documentary_pipeline.py` :
  **1 réussi**, découverte puis lecture réelle sans dossier.
- `ACFPF_LIVE_AI=1 pytest -q tests/test_live_ai_grounding.py`, Groq/GPT-OSS-120B :
  **8 réussis** sur le benchmark synthétique versionné. Il calibre le vérificateur,
  sans démontrer la fiabilité de l’agent sur toutes les questions.
- `ACFPF_LIVE_ACCEPTANCE=1 pytest -q -s tests/test_live_v1_acceptance.py`, Groq :
  **1 réussi (budget), 1 échec (deux documents)** lors du premier passage.
  Le cas multi-documents a été rejoué séparément après chaque correction pertinente ;
  le dernier résultat reste un échec HTTP 400, sans réponse publiée.
- Suite extraite de la distribution source et exécutée avec Python 3.11 : vérifiée
  à nouveau lors de l’étape 5 ; voir son rapport pour le résultat final.

Les appels fournisseurs chargent les clés exclusivement côté serveur, sans les
imprimer ni les committer. Gemini : liste des modèles HTTP 200, génération du preset
`gemini-3.8-flash` HTTP 503. Une comparaison explicite avec `gemini-2.5-flash`, annoncée
par la liste, a reçu HTTP 404 via la compatibilité OpenAI. Aucun preset ni fournisseur
n’a été changé silencieusement. Les autres fournisseurs, sans clés disponibles,
ne sont pas testés en direct.

Traces publiques temporaires hors dépôt : `/tmp/acfpf-v1-live-acceptance.log`,
`/tmp/acfpf-v1-live-two-documents-retest.log`,
`/tmp/acfpf-v1-live-two-documents-small-units.log`,
`/tmp/acfpf-v1-live-final-multi.log`, `/tmp/acfpf-v1-live-multi-repair.log` et
`/tmp/acfpf-v1-grounding-benchmark.log`. Elles contiennent les événements publics,
pas de corps brut fournisseur ni de raisonnement privé. Les résultats utiles sont
consignés ici pour ne pas dépendre de ces fichiers temporaires.

## Contrôles navigateur et limites

Application réelle avec Groq : accueil, saisie libre, progression, erreur/quota,
recherche logement et dossier. Application installée depuis la wheel, sans IA :
accueil, textes en cours et finances. Un second serveur de recette utilisant HTTP/LLM
simulés vérifie les états « preuves insuffisantes » et citation E999 refusée ; cette
vérification UI est distincte des essais réseau. Les formats et captures finaux sont
décrits dans le rapport de livraison.

La recette **ne peut pas être déclarée entièrement réussie**. Il reste à obtenir des
réponses documentaires libre, contextualisée et multi-documents de façon reproductible
avec une configuration fournisseur disponible. Le backend échoue explicitement et
préserve ses garde-fous ; cela ne remplace pas un parcours utile aboutissant.
L’étape 5 prépare une candidate installable et les instructions de reproduction, sans
masquer cette réserve ni publier une V1 stable. Aucun tag ni release n’est créé.
