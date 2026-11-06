<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Audit V1 — étape 0, 6 novembre 2026

## Conclusion et périmètre figé

L’étape 0 est validée comme **audit et recentrage**, pas comme recette du produit.
Aucune fonctionnalité applicative n’est ajoutée, supprimée ou masquée dans cette étape.
Les étapes 1 à 5 de [V1_ROADMAP.md](V1_ROADMAP.md) restent non validées.

Le périmètre de livraison est : question libre sans dossier obligatoire, recherche sur les
sources autorisées, ouverture et lecture réelles, réponse IA traçable ; découverte déterministe
d’un dossier et chat contextualisé ; maintien des finances sous `/finances`.
Python/Flask, rendu serveur, tokens sémantiques et abstraction des fournisseurs sont conservés.
L’exhaustivité parlementaire et la chaîne loi → application → financement → résultats
ne sont pas des prérequis de cette livraison.

## Référence Git et CI

Audit du checkout local après `git fetch origin` : `main` et `origin/main` valent
`287075de78231fd1bb4863439b355574c3520553`. Branche d’audit : `codex/v1-step0-audit`.
Les fichiers non suivis préexistants (dont des fichiers de clés et les métadonnées
`src/acfpf.egg-info/`) ne sont ni lus pour leurs secrets, ni inclus dans la contribution.

Contrôles GitHub effectués via le connecteur, sur les collections REST `pulls?state=all`,
`pulls?state=open` et `actions/runs` :

- 49 PR historiques retournées, toutes fermées ; 46 fusionnées et 3 fermées sans fusion
  (#25, #43 et #46), remplacées respectivement par #26, #44 et #47.
- Aucune PR ouverte au début de l’audit. Beaucoup de branches distantes restent présentes
  après squash : leur absence de l’ascendance Git de `main` ne prouve pas un travail absent.
- [CI de main, run 42190176598](https://github.com/baboundu81/ACFPF-2000_2025/actions/runs/42190176598) :
  terminée avec succès sur `287075d`. Les deux runs précédents de main sont aussi verts.
- `origin/feature/debate-vote-session-bridge` pointe sur
  `7043533f6105bdfb565889f72b2a00e876b43f9b` : **six commits absents de main**,
  336 insertions et 5 suppressions dans six fichiers par rapport à l’ancêtre commun.
  La branche ajoute `legislative_debate_sessions.py`, la jointure exacte des `seanceRef`
  de scrutins et les routes de consultation de séances. Aucune PR associée et aucun run
  Actions sur cette branche n’ont été retournés. Ses tests n’ont pas été exécutés ici.
  Elle n’est ni fusionnée ni reprise dans l’étape 0 : à conserver au backlog post-V1.
- Le transport résilient des archives de débats (#57, `95546e8`) est déjà dans main ;
  il ne faut pas le confondre avec la jointure séance/dossier de la branche précédente.

Reproduction : `git log --oneline main..origin/feature/debate-vote-session-bridge`,
`git diff --stat main...origin/feature/debate-vote-session-bridge`, puis vérification
GitHub des PR (incluant `merged_at`) et runs associés aux SHA. Ne pas déduire une
fusion de la seule existence d’une branche ou d’un message de commit.

## Cartographie et niveau de validation

« Opérationnel observé » désigne uniquement le scénario effectivement essayé.
« Simulé » désigne un test avec fixtures, faux clients HTTP ou fournisseur factice.
Aucune de ces catégories ne vaut validation exhaustive.

| Composant / parcours | Implémentation et preuves vérifiables | État à cette date |
| --- | --- | --- |
| Lancement | `cli.py`, `web/__init__.py`, commande `acfpf --no-browser --port 5050` | Opérationnel observé ; installation propre non testée |
| Accueil et découverte | `web/app.py`, `home.html`, `legislation.py`, `legislation_browse.py`, connecteurs Assemblée et Sénat | Recherche « logement » et ouverture d’un dossier observées dans le navigateur, inventaires réels ; parseurs/statuts/filtres également testés sur fixtures |
| Reformulation assistée | `legislation_assisted.py`, `ai/legislation_query.py` | Intégrée, testée par mocks ; vrai fournisseur non validé dans cette session |
| Question libre | POST `/api/ask` et `/api/ask/stream`, `ai/civic.py`, `ai/service.py` | API sans `dossier_id` intégrée et simulée dans `test_web.py` ; formulaire absent de l’accueil, présent sous finances si IA configurée ; parcours A partiellement intégré |
| Chat dossier | identité rechargée côté serveur par `_question_from_request`, `dossier_chat.js` | Parcours et refus de substitution simulés dans `test_web.py` ; message « IA non configurée » observé ; conversation réelle non validée |
| Découverte live d’URL | `LiveOfficialResearch.search`, index DuckDuckGo, `config/sources.yml` | Sonde réelle « logement » sur `assemblee_nationale_open_data` : deux URL autorisées ; ce ne sont pas des preuves lues |
| Ouverture et lecture | `live_research.py`, `data/documents.py`, HTML/PDF, segmentation contiguë | Lecture HTML réelle d’un dossier officiel (voir ci-dessous) ; PDF, redirections et refus principalement simulés dans `test_evidence.py`/tests IA ; robustesse à compléter |
| Preuves et citations | `evidence.py`, `ai/service.py`, `test_ai.py`, `test_civic_grounding_gate.py` | Identifiants E/S, URL, locator, date, SHA et refus d’identifiants inconnus testés par mocks ; pas de validation sémantique assertion par assertion |
| Fournisseurs | `ai/provider.py`, `registry.py`, `openai_compatible.py`, `anthropic.py`, `mistral.py` | Gemini par défaut ; Groq, Claude, Mistral, OpenAI, OpenRouter conservés ; schémas/diagnostics testés avec faux HTTP, aucun appel LLM réel dans cet audit |
| Progression | `iter_ask`, NDJSON, `ask.js`, `dossier_chat.js` | Test serveur simulé ; progression réelle avec fournisseur non validée |
| Dossier enrichi | modules `legislative_*`, routes spécialisées et JS locaux | Versions, rapports, votes, amendements partiellement validés en live ; erreur réseau des amendements reproduite ; limites détaillées ci-dessous |
| Finances | `macro.py`, `cofog.py`, connecteur Eurostat, `/finances` | Dashboard réel observé : KPI, graphique, tableaux, unités, sources ; calculs déterministes testés ; pas d’audit économique exhaustif |
| Légifrance PISTE | `data/legifrance_piste.py`, `test_legifrance_piste.py` | Transport testé par mocks, non branché au parcours public ; habilitation et validation juridique réelles manquantes |
| Couverture action publique / diff / articles | `public_action.py`, `legislative_text_diff.py`, `legislative_articles.py` | Socles intégrés avec tests ; couverture de métadonnées et fonctions expérimentales, pas de chaîne normative/budgétaire ni comparaison juridique certifiée |

## Vérifications exécutées et limites

Environnement : Linux, Python **3.14.8** du `.venv` existant, Node local,
Flask lancé sans clé IA configurée ; navigateur intégré contrôlé via CUA.
La CI de main utilise Python 3.11. Pas de nouvelle dépendance installée.

| Commande / vérification | Résultat |
| --- | --- |
| `.venv/bin/ruff check .` | Réussi |
| `.venv/bin/pytest -q` | **201 passed, 8 skipped**, 5,31 s ; tests réseau désactivés par défaut |
| `node --check` sur chaque fichier `src/acfpf/web/static/js/*.js` | Réussi |
| `node --test tests/js/*.test.js` | **3 passed** (comportement du lecteur de rapports seulement) |
| `ACFPF_LIVE_SOURCES=1 .venv/bin/pytest -q -s tests/test_live_official_{legislation,documents,votes,fulltext,actors,reports,debates}.py` | **6 passed, 1 failed, 1 skipped**, 19,71 s |

Le test live en échec est `test_live_assembly_dossier_amendments_and_xml` : transfert
incomplet de l’index des amendements du dossier `54629`, `ChunkedEncodingError` /
`IncompleteRead` (1 671 475 octets reçus, 9 164 106 encore attendus), converti en
`LegislativeDetailError`. Les six succès portent sur notices documentaires, scrutins,
HTML officiel, acteurs historiques, rapports et transport léger Syceron. Le test
ignoré est l’audit complet de la grosse archive, soumis à `ACFPF_LIVE_DEBATES_FULL=1`.
Le succès CI antérieur ne fait pas disparaître cet échec réseau local.

La [CI de la PR #58 sur le commit efd3ed0](https://github.com/baboundu81/ACFPF-2000_2025/actions/runs/42263647545)
a ensuite reproduit l’échec du même test live des amendements : **6 passed, 1 failed,
1 skipped**, 8,17 s. Installation, lint, syntaxe/comportement JavaScript et tests Python
déterministes ont réussi en CI. **La PR ne doit pas être fusionnée avec cette CI rouge.**
Le statut validé de l’étape 0 qualifie l’audit documenté, pas une livraison ni une
autorisation de fusion ; la panne observée reste à traiter dans le périmètre approprié.

Sondes directes de `LiveOfficialResearch(timeout=15)` :

- `search('logement', source_ids=['assemblee_nationale_open_data'], limit=2)` : deux
  résultats officiels retournés ; aucune interprétation du contenu des snippets.
- `open('https://www.assemblee-nationale.fr/dyn/17/dossiers/DLR5L17N54628')`,
  puis `read(document_id, 1)` : HTML, une unité de 7 090 caractères,
  SHA-256 `b0b2cb54f737aa55929d2df568b97c0620d93634c7abd752c784ec79fe93b3dc`.
  Cette lecture par le backend ne constitue pas une synthèse validée par un LLM.

### Boucle navigateur UX/UI

1. Accueil réel : hiérarchie journalistique, navigation active « Textes & décisions »,
   recherche et filtres visibles ; pas de champ de question libre documentaire.
2. Saisie et soumission de « logement » : titre « Résultats pour “logement” »,
   30 résultats limités, critères de tri exposés, liens vers les dossiers.
3. Ouverture du dossier `DLR5L17N54628` : identité, statut, date, provenance des deux
   chambres et limites visibles ; chat indiquant explicitement « IA non configurée ».
4. Après interruption du premier serveur de test, les requêtes JS affichaient
   `Failed to fetch`. Relance du serveur et reprise dans un onglet neuf : **2 versions,
   1 rapport**, aucun scrutin explicitement rattaché, erreur d’index des amendements
   du dossier `54628`. On distingue ainsi l’interruption locale de la panne documentaire.
5. Inspection visuelle du dossier en **390 × 844**, puis retour au viewport normal :
   navigation et titre se replient ; largeur du document 375 px pour 390 px de viewport,
   sans débordement horizontal constaté. Vue initiale également inspectée sur grand écran.
6. `/finances` : page réelle affichée, source et fraîcheur, unités, KPI, tableaux et
   graphique présents. L’IA désactivée n’empêche pas cette consultation.

Constats à traiter à l’étape 3 : chat précédé de nombreuses sections secondaires et
requêtes automatiques ; texte « Aucune comparaison automatique n’est encore proposée »
contredisant le comparateur expérimental juste dessous ; dernière activité pouvant être
future sans distinction visuelle entre séance prévue et activité réalisée ; provenance
Sénat parfois en HTTP dans les liens des notices, à distinguer du lecteur live HTTPS.

Non exécutés : conversation et streaming avec vrai fournisseur (aucun fournisseur activé
pour cet audit limité), authentification PISTE (pas de compte habilité configuré),
installation propre, archive Syceron complète, audit WCAG AA exhaustif, navigation
clavier complète, tablette, matrice complète des dix scénarios de recette. Ces contrôles
restent ouverts ; la présence de fichiers de clés locaux ne vaut pas test d’une clé.

## Risques et travaux restants vérifiables

| Étape future | Points à vérifier / corriger et critère de sortie |
| --- | --- |
| 1 | `live_research.py` télécharge actuellement via `requests.get` sans streaming et contrôle la taille après réception ; `raise_for_status()` hors conversion peut laisser échapper `HTTPError`, alors que l’agent capture `LiveResearchError`. Borner les transferts, traiter contenus invalides/erreurs, tester le parcours libre complet sans réseau et sonder le vrai moteur |
| 2 | Recette Gemini réelle et alternatives, quota/timeouts/JSON/contexte ; fidélité des citations aux affirmations, progression ; le garde-fou documentaire spécifique aux dossiers ne couvre pas de la même façon les questions libres. Les séries financières sont encore préparées avant toute enquête documentaire : mesurer l’impact et confirmer le mode dégradé |
| 3 | Question libre sur l’accueil, chat dossier accessible plus tôt, erreurs/chargement/vide, suppression des formulations contradictoires et distinction des dates prévues ; vérifier les deux parcours sur desktop/tablette/mobile et au clavier |
| 4 | Exécuter la matrice de dix scénarios de V1_ROADMAP, distinguer mocks/live/LLM/navigateur ; reproduire puis qualifier la panne des amendements si toujours exposés, aucune recette globale cochée avant résolution des blocages V1 |
| 5 | Installation propre Python >=3.11, variables provider, commande `acfpf`, documentation des limites, CI de la livraison ; pas de tag/release sans accord |

### Composants à reléguer sans suppression (décision de périmètre)

À l’étape 3, placer en vues avancées ou sections repliées les index d’amendements,
positions nominatives, inventaires de rapports/versions, jalons détaillés et carte
complète `PublicActionDossier`. Garder un accès immédiat à l’identité, au statut,
aux sources essentielles et au chat. Masquer par défaut le diff HTML et les intitulés
candidats d’articles tant qu’ils distraient du parcours V1 ; conserver modules, API et tests.
La mise en œuvre de ces changements d’interface ne fait pas partie de l’étape 0.

### Backlog post-V1 et prérequis

- Jointure débats/scrutins/séances : préserver la branche `feature/debate-vote-session-bridge`,
  examiner et tester séparément ses six commits ; valider la jointure exacte sur sources
  réelles avant exposition, sans attribuer un discours à un texte par simple co-présence.
- Couverture complète des chambres, rapports et interventions : schémas et identifiants
  vérifiés, transport borné, tests représentatifs, limites de couverture visibles.
- Structure normative et comparaison article par article : contenus complets, versions
  et dates contrôlées ; un diff HTML ou un intitulé heuristique ne suffit pas.
- Décisions constitutionnelles et Légifrance : habilitation PISTE si ce transport est retenu,
  références exactes et lecture réelle des textes ; ne pas fabriquer de JORFTEXT.
- Application, financement, exécution et effets : preuves et identifiants distincts,
  aucun rapprochement causal ou budgétaire implicite.
- Finances avancées : euros constants/habitant et exécution détaillée, sans bloquer la V1.

Les phases historiques de `CIVIC_ACTION_PLAN.md` restent conservées. Les documents
directeurs renvoient désormais à la roadmap V1 pour l’ordre des travaux. Fin de
l’étape 0 ; aucune étape suivante n’est commencée par cette contribution.
