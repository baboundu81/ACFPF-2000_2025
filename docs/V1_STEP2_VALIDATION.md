<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# V1 — étape 2 : IA, citations et robustesse (6 novembre 2026)

## Résultat et périmètre

Les contrôles de l’étape 2 sont implémentés et validés sur tests déterministes,
benchmark avec un vrai fournisseur et parcours navigateur réels **avec et sans dossier**.
Groq a produit des réponses sourcées après lecture officielle et contrôle distinct des appuis.
**Gemini reste indisponible en génération (HTTP 503)** : aucun succès Gemini n’est déclaré.
Cette limite externe ne doit pas être confondue avec une clé invalide ni avec une recette V1 complète.

Branche `codex/v1-step2-ai-grounding`, issue de `e5d21cd` (étape 1). Les PR #58 et #59
étaient encore ouvertes au démarrage. Aucune fusion automatique, aucun changement de preset
par défaut, nouveau connecteur ou refonte de l’accueil. L’étape 3 n’est pas commencée.

## Corrections et décisions

- Groq/GPT-OSS : activation explicite du mode JSON Schema strict, effort faible et
  plafond de 2 048 tokens de sortie. Les autres sorties restent bornées à 4 096 tokens.
  Le mode strict est documenté par [Groq](https://console.groq.com/docs/structured-outputs),
  les paramètres par son [contrat d’API](https://console.groq.com/docs/api-reference).
  Gemini conserve le schéma commun et l’effort faible ; Claude conserve le transport natif.
  Mistral, OpenAI et OpenRouter conservent leurs interfaces compatibles.
- Les réponses tronquées, refusées, trop longues ou mal formées sont rejetées ; contexte
  fournisseur limité à 128 000 caractères sans sélection de passages ni troncature documentaire.
- Diagnostics partagés, typés et sûrs : catégorie, code HTTP, délai de reprise et identifiant
  de requête validé. Pas de corps d’erreur, `failed_generation`, prompt ou raisonnement privé
  dans le navigateur ou les logs. Les exceptions HTTP brutes ne sont plus journalisées en chaîne.
- Contrôles des citations renforcés : références E/S connues, unités réellement lues,
  références affichées inline déclarées et URL affichées appartenant aux preuves citées.
  La règle documentaire propre au dossier est maintenue. Une insuffisance ne recopie plus
  les conclusions ou limites non vérifiées proposées par le modèle.
- Une seconde passe `acfpf_grounding_review` examine le candidat avant publication : preuves
  effectivement lues, contexte numérique déterministe et provenance, sans snippets. Elle vérifie
  les appuis, versions, stades et inférences. Rejet → insuffisance backend ; panne ou résultat
  invalide → erreur, sans publication du candidat. Le prompt de contrôle et son schéma restent
  distincts du prompt civique : l’ancien wrapper ne doit plus les remplacer silencieusement.
- Le premier événement de progression précède le chargement numérique. Le champ libre `reason`
  du modèle n’est plus exposé comme progression. Les actions publiques décrivent les opérations.
- Reprise d’un HTTP 429 uniquement avec `Retry-After` numérique : deux reprises au maximum pour
  toute la question, contrôle final compris, au plus 60 secondes par attente. Chaque attente est
  annoncée et la lecture déjà effectuée est conservée. Au-delà : erreur explicite. Pas de bascule
  silencieuse ni de modification de facturation. Timeout et 503 ne sont pas retentés implicitement.
- Lecteur NDJSON commun aux deux chats : UTF-8 et lignes fragmentées, événement terminal unique,
  fin sans saut de ligne, refus du flux incomplet/incohérent, réactivation du formulaire.
  Le candidat reste interne et le résultat final n’est affiché qu’après un flux terminé correctement.
- JSON non objet refusé par les routes ; limite utilisateur libre 1 500 caractères, dossier 600.
  Le contexte officiel assemblé côté backend peut atteindre 6 000 caractères sans empêcher
  l’utilisation des titres longs. L’identité officielle demeure rechargée côté serveur.

**Limite du contrôle sémantique :** la seconde passe utilise encore un LLM, actuellement le même
fournisseur. C’est un garde-fou probabiliste, pas une nouvelle source, une preuve de vérité ou une
certification juridique. Les huit cas du benchmark ne prouvent pas une fidélité universelle.
Les règles correspondantes sont ajoutées aux AGENTS racine, IA et web.

## Boucles déterministes et réseau

Environnement : Linux, Python 3.14.8 du `.venv` existant, Node 22.22.2 ; aucune nouvelle dépendance.
Avant modification : Ruff vert, 273 tests Python réussis. Après correction et dernière vérification :

| Commande | Résultat |
| --- | --- |
| `.venv/bin/ruff check .` | Réussi |
| `.venv/bin/pytest -q` | **348 passed, 17 skipped**, 4,50 s |
| `node --test tests/js/*.test.js` | **13 passed** |
| `node --check` sur chaque script local | Réussi |
| `git diff --check` | Réussi |
| Suite live préexistante, `ACFPF_LIVE_SOURCES=1` sur les sept fichiers officiels | **7 passed, 1 skipped**, 35,30 s |

Les 75 nouveaux cas Python couvrent notamment les six interfaces fournisseur, réseau/timeout,
quota/authentification, limites entrée/sortie, JSON/enveloppes invalides, troncature même avec JSON
valide, refus de preuve, contrôle rejeté/invalide/indisponible, références inline/URL jamais lues,
absence de fuite du candidat, limites de reprises et API JSON/stream avec/sans dossier.
Les dix nouveaux tests JavaScript couvrent le transport NDJSON avec de vrais `ReadableStream`.
Les anciens faux fournisseurs disposent d’un contrôle permissif explicite pour leurs scénarios ;
les nouveaux tests de contrôle utilisent séparément des réponses de rejet ou invalides.

Les 17 tests ignorés par défaut sont les neuf sondes réseau précédentes et les huit cas LLM opt-in.
Les simulations ne sont pas comptées comme des validations des services externes.
Le test profond de l’archive Syceron reste ignoré sans opt-in spécifique ; la panne intermittente
d’amendements du dossier `54628` demeure visible dans la fiche navigateur, même si la suite live
sur le dossier `54629` a réussi cette fois-ci.

## Benchmark LLM versionné

`tests/fixtures/ai_grounding_benchmark.json`, version `2026-11-06-v1`, huit cas synthétiques :
proposition correctement décrite, proposition présentée comme loi applicable, prévision présentée
comme exécution, mauvaise version, citation sans rapport, causalité non établie, constat descriptif
correct et instruction malveillante dans la source. Deux acceptations et six refus attendus.
Empreinte du fichier : `0b7e988938919095a1478f549dd6868320328008fb6d19e83f0fbd16a3fd2362`.

Exécution séparée avec Groq et clé chargée uniquement dans l’environnement serveur :
`ACFPF_LIVE_AI=1 pytest -q tests/test_live_ai_grounding.py`.
Premier passage : **8 passed**, 7,52 s. Passage final après réglage du budget de sortie :
**8 passed**, 7,95 s. Ce benchmark ne fournit aucun fait au produit :
les contenus sont des fixtures synthétiques sans attribution à un document réel.

## Fournisseurs réellement appelés et diagnostic Gemini

- Liste des modèles Gemini : **HTTP 200** avec la clé locale. La correspondance avec le suffixe
  visible sur la capture fournie par l’utilisateur a été vérifiée sans afficher la clé.
- Génération minimale Gemini 3.8 via compatibilité : **HTTP 503**, environ 3,6 s.
- Génération minimale Gemini 3.8 via API native : **HTTP 503 UNAVAILABLE**, environ 4 s.
  La variante native Gemini 2.5 a répondu 404 ; aucun remplacement silencieux du preset.
- L’essai navigateur final avec le vrai Gemini affiche « HTTP 503 — fournisseur temporairement
  indisponible », termine la progression et réactive le formulaire. Pas de génération Gemini réussie.
- [Google documente le 503](https://ai.google.dev/gemini-api/docs/generate-content/api-errors) comme
  une indisponibilité ou un manque temporaire de capacité. Les résultats observés n’établissent
  pas un problème de clé ou de facturation. Aucun réglage du compte n’a été modifié.
- Groq : appel minimal strict réussi, benchmark réussi, puis parcours réels ci-dessous.
  Une sonde quantitative du contexte documentaire a également réussi avec 5 888 tokens d’entrée
  et 202 de sortie ; cela explique pourquoi les quotas d’un compte gratuit peuvent être atteints
  entre plusieurs tours même si chaque requête est valide.
- Claude, Mistral, OpenAI et OpenRouter : interfaces testées avec faux HTTP uniquement, faute
  de clés configurées pour ces fournisseurs. Aucune validation réelle n’est inventée.

## Boucle navigateur réelle

Application Flask normale avec fournisseur Groq réel, sans mode simulé :

1. `/finances` → question libre avec URL officielle, sans `dossier_id` : ouverture de
   `https://www.assemblee-nationale.fr/dyn/17/dossiers/DLR5L17N54628`, lecture du segment 1,
   réponse et contrôle des appuis. Avant la reprise bornée, le second tour échouait sur quota.
   Après correction : attentes annoncées de 16 puis 14 secondes, réponse finale avec citation E1,
   titre et distinction entre dossier parlementaire et droit applicable. Bouton réactivé.
2. `/textes/DLR5L17N54628` → question contextualisée demandant le titre : identité fournie
   par le backend, ouverture officielle, attentes annoncées de 20 puis 41 secondes, contrôle,
   réponse avec citation E1. La source n’est pas remplacée par les champs du navigateur.
3. Inspection visuelle de ce chat à 390 × 844 : réponse et citation lisibles, largeur du document
   375 px pour un viewport 390 px ; retour au format normal. Le défaut horizontal du dashboard
   financier relevé à l’étape 1 n’est pas corrigé ici (étape 3).
4. Retour au formulaire avec Gemini réel : erreur 503 explicite et formulaire utilisable après échec.

Captures locales non versionnées : `/tmp/acfpf-step2-real-answer.jpg` et
`/tmp/acfpf-step2-real-chat-mobile.jpg`. Les serveurs temporaires sont arrêtés en fin de validation.
Aucune capture fournie par l’utilisateur, clé ou métadonnée d’installation locale n’entre dans le commit.

## Limites et suite

La disponibilité de Gemini reste un risque externe connu, annoncé sans requalifier l’essai en succès.
La seconde passe augmente coût et latence ; les reprises peuvent ajouter au plus 120 secondes par
question. Les quotas gratuits ne sont pas une garantie de service. Le benchmark sémantique doit être
élargi lors de la recette, notamment aux réponses longues, multi-documents et cas juridiques difficiles.
La terminologie d’une réponse peut encore être imparfaite : un contrôle LLM ne garantit pas chaque mot.
Installation propre, recette exhaustive des dix scénarios et audit WCAG AA restent aux étapes prévues.
Aucun tag, release, merge ou démarrage de l’étape 3 dans cette session.
