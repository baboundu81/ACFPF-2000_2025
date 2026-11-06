<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# ACFPF — Roadmap V1 : recherche documentaire et analyse IA sourcée

**Statut :** périmètre V1 confronté au code lors de l’étape 0 ; livraison non validée.
**Décision produit :** recentrage sur une première version utilisable et testable.  
**Périmètre :** application locale Python/Flask, découverte des textes, recherche documentaire live, chat IA et sous-outil finances existant.

## 1. Objectif V1

ACFPF est un outil citoyen, neutre et vérifiable pour comprendre l'action publique française.

**La V1 est d'abord un moteur de recherche et d'analyse documentaire assisté par IA.** L'utilisateur peut poser une question libre ; ACFPF découvre des documents sur des sources autorisées, ouvre et lit leurs contenus, puis produit une réponse traçable et citée. L'utilisateur peut également chercher et sélectionner un dossier législatif pour poursuivre l'analyse dans un chat contextualisé.

Le parcours principal est :

**Question → recherche sur les sources autorisées → ouverture/lecture → constitution des preuves → analyse IA → réponse sourcée.**

La sélection d'un dossier législatif est facultative pour les questions générales. Les métadonnées structurées du dossier servent à découvrir, identifier et contextualiser les textes ; elles ne remplacent jamais la lecture des documents officiels.

### Parcours utilisateurs indispensables

- **A — Question libre :** accueil → question → recherche IA → réponse → consultation des preuves et sources.
- **B — Recherche d'un texte :** accueil → recherche en langage courant (ex. « textes en cours de discussion », « textes sur le logement ») → résultats fondés sur l'inventaire officiel → sélection du dossier → chat dédié → réponse sourcée.
- **C — Finances :** accès secondaire au sous-outil existant sous `/finances`.

La V1 n'exige **pas** la reconstitution exhaustive de la chaîne proposition → débats → votes → promulgation → application → financement → résultats.

## 2. Périmètre et règles de conservation

### Dans le périmètre V1

- Recherche documentaire live à partir des domaines explicitement autorisés par `config/sources.yml`.
- Validation des URL, redirections, réponses et limites de téléchargement par le backend.
- Lecture réelle de documents officiels ; traçabilité par URL, titre, date de consultation, locator et, si possible, empreinte.
- Analyse et synthèse par un fournisseur IA configurable, Gemini par défaut.
- Citations uniquement issues de preuves effectivement lues (ou des séries déterministes existantes, identifiées séparément).
- Recherche/découverte des dossiers législatifs, vue de leurs informations essentielles et chat contextualisé.
- États d'erreur lisibles, installation reproductible, tests et documentation.
- Conservation du sous-outil finances.

### Préserver sans imposer à la V1

Les fonctions déjà réalisées et stables (versions, amendements, scrutins, rapports, débats, différences expérimentales, etc.) restent dans le dépôt, avec leurs tests. Elles peuvent être masquées, reléguées dans des vues avancées ou désactivées de manière réversible si elles brouillent les deux parcours centraux.

Ne pas supprimer du code uniquement pour simplifier l'interface. Ne pas engager de refonte complète ni ajouter de nouveaux raccordements parlementaires avancés avant la recette V1. Les fonctionnalités inachevées ou non validées ne doivent pas être exposées comme fiables.

**Hors périmètre V1 :** rapprochement exhaustif des discours avec les textes, couverture intégrale des scrutins et rapports des deux chambres, comparaison juridique certifiée article par article, lien systématique entre lois, application réglementaire, budget et résultats. Ces axes restent dans le backlog post-V1.

## 3. Garde-fous permanents

1. Respecter les `AGENTS.md` du dépôt, les licences, le CLA et les règles de contribution.
2. Sources primaires et officielles en priorité. Ne jamais inventer URL, référence, source, fait ou validation.
3. Un résultat de moteur de recherche, son snippet ou une métadonnée non lue ne constitue pas une preuve sur le fond d'un texte.
4. Ne citer un document qu'après ouverture et lecture effective par ACFPF. Le backend valide l'appartenance à la liste blanche, les redirections et la provenance.
5. Ne pas confondre projet, amendement, scrutin, adoption, promulgation et application ; ni budget prévu, voté et exécuté.
6. En cas de sources insuffisantes, répondre explicitement que l'information n'est pas établie.
7. Le LLM aide à chercher, comprendre et synthétiser ; il n'est jamais une source de vérité. La découverte structurée des dossiers reste déterministe.
8. Gemini est le fournisseur par défaut, sans couplage bloquant à un seul provider. Ne jamais exposer ni committer une clé.
9. Conserver Python/Flask et le design system existant. Priorité aux corrections ciblées, sans grosse nouvelle dépendance.
10. Les tests sans réseau ne prouvent pas le fonctionnement en conditions réelles : distinguer simulations, tests d'intégration live et validation navigateur.

## 4. Étapes Codex

**Règle fondamentale : une seule étape par session Codex.** Une fois cette étape traitée, documenter, produire le bilan et **s'arrêter**, même si la suivante semble facile.

### Étape 0 — Audit et recentrage

**État :** [x] Validée le 6 novembre 2026 — audit uniquement, pas recette V1.

Rapport : [V1_STEP0_AUDIT.md](V1_STEP0_AUDIT.md) (Git/CI, cartographie,
tests simulés et live, boucle navigateur, limites et travaux restants).

**Objectif :** établir ce qui existe réellement et figer le périmètre V1.

Travail attendu :
- Examiner `main`, les PR/branches et la CI ; vérifier en particulier le devenir éventuel de `feature/debate-vote-session-bridge` sans présumer de son état actuel.
- Cartographier les parcours exécutables et les composants IA, recherche, lecture documentaire et UI.
- Distinguer : fonction opérationnelle ; testée uniquement par mocks ; partiellement intégrée ; non validée.
- Identifier les fonctionnalités secondaires à masquer plutôt qu'à supprimer.
- Vérifier et harmoniser `docs/V1_ROADMAP.md`, `docs/CIVIC_ACTION_PLAN.md`, `README.md` et les `AGENTS.md` si nécessaire, sans effacer l'historique technique.
- Conserver les travaux non-V1 dans un backlog post-V1 et signaler les prérequis ou risques.

**Critère d'acceptation :** état réel audité, périmètre V1 explicite, documentation sans instruction contradictoire, liste vérifiable des étapes restantes.

### Étape 1 — Moteur documentaire de bout en bout

**État :** [ ] Non validée

**Objectif :** une question libre permet de rechercher, ouvrir et lire des documents officiels, avec preuves, sans imposer de dossier législatif.

Travail attendu :
- Auditer et corriger le pipeline existant de recherche sur domaines autorisés, validation des URL et redirections, ouverture, extraction HTML/PDF déjà prise en charge, segmentation et lecture.
- Préserver les identifiants, locators et métadonnées des preuves effectivement lues.
- Gérer timeouts, téléchargements trop volumineux, contenu invalide, source indisponible et absence de résultat.
- Ajouter des tests déterministes couvrant le parcours complet et les refus de sources non autorisées.
- Éviter de développer de nouveaux connecteurs parlementaires détaillés sans nécessité démontrée.

**Critère d'acceptation :** des questions générales aboutissent à des contenus effectivement lus ou à une absence de preuve explicite ; parcours testé sans sélection de dossier.

### Étape 2 — IA, citations et robustesse

**État :** [ ] Non validée

**Objectif :** réponses utiles, vérifiables, résistantes aux erreurs de fournisseurs.

Travail attendu :
- Vérifier les interfaces des fournisseurs IA, Gemini en priorité, avec conservation des autres fournisseurs existants.
- Tester erreurs API, quota, timeouts, réponses invalides et tailles de contexte.
- Vérifier les contrôles backend interdisant les citations jamais lues et les conclusions infondées.
- S'assurer du fonctionnement avec et sans `dossier_id`.
- Vérifier ou corriger le flux de progression/streaming et le diagnostic des erreurs.

**Critère d'acceptation :** réponses fondées sur des preuves et correctement citées ; refus explicite si preuve insuffisante ; erreurs compréhensibles et testées.

### Étape 3 — Interface et parcours V1

**État :** [ ] Non validée

**Objectif :** navigation compréhensible sans connaissance préalable de l'architecture ACFPF.

Travail attendu :
- Mettre au premier plan la recherche libre et la découverte de textes.
- Finaliser le parcours « question → sources → réponse » et le parcours « textes → dossier → chat sourcé ».
- Afficher clairement titre, statut, provenance, dates, liens et limites des informations législatives lorsqu'ils sont connus.
- Masquer ou reléguer les modules complexes ou expérimentaux, sans supprimer leurs implémentations stables.
- Maintenir les finances dans la navigation secondaire.
- Soigner chargement, erreurs, absence de résultats, contraste, accessibilité et formats mobiles.
- Tester le parcours accueil → dossier → chat dans les tests de l'application.

**Critère d'acceptation :** les deux parcours essentiels sont identifiables et utilisables ; les fonctions accessoires ne perturbent pas la V1.

### Étape 4 — Recette fonctionnelle et validation réelle

**État :** [ ] Non validée

**Objectif :** vérifier les parcours V1 en conditions représentatives, sans confondre mocks et vrai réseau.

Matrice de scénarios à couvrir :
1. Question générale sur une politique publique.
2. Question sur un sujet budgétaire.
3. Recherche de textes législatifs en cours.
4. Recherche de textes par thème.
5. Ouverture d'un dossier et question contextualisée.
6. Question mobilisant plusieurs documents.
7. Document officiel absent ou inaccessible.
8. Question sans preuves suffisantes.
9. Erreur ou quota du fournisseur IA.
10. Tentative de citation d'une URL non lue.

Exécuter `ruff check .`, `pytest`, les tests live prévus par le dépôt si le réseau est accessible, des essais avec un vrai fournisseur IA uniquement si une clé est disponible, et des tests navigateur si l'environnement le permet.

Consigner dans un rapport les commandes, résultats, limites, dates et environnements. Les éléments non vérifiables doivent être notés « non testés », jamais « réussis ».

**Critère d'acceptation :** aucun blocage critique connu sur les parcours V1 ; matrice de recette documentée et vérifications manquantes identifiées.

### Étape 5 — Livraison V1 testable

**État :** [ ] Non validée

**Objectif :** permettre une installation et une prise en main autonomes.

Travail attendu :
- Tester l'installation propre (Python >= 3.11), la configuration, `acfpf` et les principaux parcours.
- Rendre explicites les variables d'environnement et le paramétrage du fournisseur IA.
- Mettre à jour README, guide de démarrage, limites connues et fonctions expérimentales.
- Vérifier l'état CI et préparer les éléments d'une livraison.
- Ne créer de tag ou release qu'après validation des critères et accord explicite de l'utilisateur.

**Critère d'acceptation :** version installable, démarrable, utilisable et accompagnée d'instructions de test.

## 5. Workflow Codex économe en quotas

À chaque session :

1. Lire `AGENTS.md`, les instructions locales pertinentes et cette roadmap.
2. Vérifier l'état Git, les éventuels changements non committés et les travaux déjà effectués.
3. Identifier l'étape explicitement demandée. Si aucune n'est précisée, proposer la prochaine étape non validée ; pour la première exécution, traiter **uniquement l'étape 0**.
4. Limiter le périmètre de la session à cette étape. Réutiliser le code existant.
5. Ajouter ou corriger les tests directement pertinents ; exécuter les contrôles adaptés, dont `ruff check .` et `pytest` avant toute demande de fusion.
6. Corriger les problèmes directement liés à l'étape, sans engager une refonte hors périmètre. En cas de blocage majeur ou de risque de consommation excessive, documenter et arrêter.
7. Mettre à jour le statut de l'étape uniquement si ses critères sont **effectivement** vérifiés.
8. Travailler sur une branche dédiée et préparer une PR vers `main` pour une modification significative. Ne pas fusionner une PR rouge.
9. **Ne pas merger automatiquement sans autorisation explicite.**
10. Émettre un compte rendu court et **s'arrêter obligatoirement avant l'étape suivante**.

### Compte rendu obligatoire

- **Étape traitée :**
- **Travail réalisé :**
- **Fichiers principaux modifiés :**
- **Tests exécutés et résultats :**
- **Tests non exécutés et pourquoi :**
- **Branche / commit / PR :**
- **Points bloquants ou risques :**
- **Prochaine étape recommandée :**

## 6. Instruction de démarrage pour Codex

> Lis les `AGENTS.md` et `docs/V1_ROADMAP.md`. Commence uniquement par l'étape 0 : audit et recentrage. Vérifie d'abord l'état réel de `main`, des branches et des tests. Ne développe pas de nouvelle fonctionnalité. Mets à jour la documentation et prépare la PR correspondante. Fournis le compte rendu prévu puis arrête-toi. Ne lance pas automatiquement l'étape 1.

## 7. Backlog post-V1

Conserver en dehors des critères de livraison V1 les objectifs de `docs/CIVIC_ACTION_PLAN.md` liés à : couverture complète des débats, scrutins et rapports ; identification des interventions ; textes définitifs et consolidation juridique exhaustive ; comparaison certifiée article par article ; rattachement de chaque modification à son amendement ; textes d'application ; liens formels vers financement, exécution et évaluation des résultats.

Ces améliorations pourront être reprises après une V1 réellement utilisable, sur la base de besoins constatés lors des tests.

Le détail des composants à reléguer, des prérequis et du travail non fusionné
`feature/debate-vote-session-bridge` est conservé dans l’[audit de l’étape 0](V1_STEP0_AUDIT.md).
