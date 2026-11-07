<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Étape 5 — Candidate installable du 7 novembre 2026

**Résultat : préparation de livraison testable réalisée, version `1.0.0rc1`.**
La [recette de l’étape 4](V1_STEP4_ACCEPTANCE.md) conserve des échecs réels. Ce rapport
ne déclare donc pas une V1 stable validée ni une publication accomplie.

L’enchaînement 4 → 5 a été explicitement demandé par l’utilisateur. Aucun merge,
aucun tag, aucune release, aucun téléchargement de clé vers un autre service.

## Correctifs et éléments livrables

- Le registre de sources est fourni dans la wheel et chargé avec `importlib.resources`,
  indépendamment du dossier courant. Un test le compare au canonique `config/sources.yml`
  et vérifie qu’un registre homonyme local ne peut pas remplacer la liste blanche.
- La version déclarée par `acfpf.__version__` et les métadonnées Python utilisent une
  seule définition ; l’écart préexistant 0.1.0 / 0.3.0 est supprimé. La désignation
  `1.0.0rc1` indique explicitement une candidate, sans tag ni publication sur PyPI.
- `MANIFEST.in` inclut guides, licences, registre canonique et fixtures nécessaires
  aux tests de la distribution source. La wheel conserve templates, CSS et JS.
- Les artefacts de build et les deux fichiers locaux de clés sont ignorés par Git.
  Les clés et les pièces jointes ne sont jamais ajoutées aux artefacts.
- La CI comporte un job distinct : construire sdist/wheel, installer la wheel dans
  un environnement vierge et vérifier le démarrage hors checkout avec Python `-I`.
- Le [guide de prise en main](QUICKSTART.md) couvre installation, configuration,
  variables, deux parcours, finances, diagnostics, limites, essais live et reconstruction.
  README et roadmap indiquent l’état réel de la candidate.

## Installation propre réellement exécutée

Environnement dédié `/tmp/acfpf-v1-clean`, créé avec `/usr/bin/python3.11` (sans
`--system-site-packages`). Les dépendances ont été téléchargées par pip, pas reprises
du venv de développement. Vérifications :

1. Construire sdist et wheel avec `python -m build`.
2. Installer la wheel avec `python -m pip install /tmp/acfpf-v1-artifacts/acfpf-1.0.0rc1-py3-none-any.whl`.
3. `python -m pip check` : aucune dépendance incohérente.
4. Depuis `/tmp`, `python -I tests/check_installed_distribution.py` avec le chemin absolu
   du script : version, sources, accueil, santé, catalogue et assets HTTP 200.
5. Depuis `/tmp`, `acfpf --no-browser --port 5062` : démarrage réel, accès dans Chromium
   à l’accueil, aux textes en cours et aux finances.
6. Avec des services réels et **caches temporairement vides distincts** : accueil,
   recherche logement, dossier DLR5L17N54628 et finances HTTP 200 ; caches AN/Sénat/macro/COFOG créés.
7. Extraire la sdist, puis lancer ses tests avec Python 3.11 : **360 réussis, 19 ignorés**.
   La première vérification, avant la correction bornée finale, comptait 358 réussis ;
   seul le résultat final est retenu comme contrôle de la candidate.

Un premier lancement sur le port 5060 a été refusé par Chromium (`ERR_UNSAFE_PORT`) ;
le serveur a été arrêté et relancé sur 5062. Aucun contournement de sécurité navigateur.
Un essai de sonde a utilisé à tort `/api/health` (404) ; le bon endpoint `/healthz`
a ensuite été testé avec succès. Ces corrections concernent la procédure de test.

Contrôles de développement : Ruff, **360 tests Python réussis / 19 ignorés**, **17 tests
JavaScript réussis**, syntaxe de tous les scripts et `git diff --check`. Les contrôles
réseau et fournisseur restent détaillés séparément dans le rapport de l’étape 4.
Le lien PR et le résultat CI exacts sont donnés dans le compte rendu de session.

## Contrôle visuel et portée

Navigateur Chromium intégré, version installée sans IA : accueil, liste réelle de
textes en cours, navigation vers les finances et données/sources affichées. Contrôles
responsive à 390 et 768 px, sans débordement global, puis retour au viewport normal.
Capture locale de l’application installée conservée hors dépôt pour le compte rendu.
Les états IA du rapport d’étape 4 utilisent un autre processus avec clé côté serveur,
ou un fournisseur explicitement simulé pour les états déterministes.

Windows, macOS, lecteurs d’écran et installation hors ligne ne sont pas testés.
Le premier lancement nécessitant des données non mises en cache dépend d’Internet.
La distribution ne contient aucun corpus documentaire massif ni cache utilisateur.

## Artefacts et état Git

Artefacts locaux : `/tmp/acfpf-v1-artifacts/acfpf-1.0.0rc1-py3-none-any.whl` et
`/tmp/acfpf-v1-artifacts/acfpf-1.0.0rc1.tar.gz`. Ils ont été contrôlés pour la présence
du registre/fixtures/assets et l’absence de fichiers de clés ou pièces jointes.
`SHA256SUMS` dans ce même dossier identifie les derniers artefacts reconstruits.
Ces fichiers restent temporaires : les reconstruire depuis le commit de livraison.

Branche : `codex/v1-acceptance-delivery`, empilée sur les PR #58–#61 non fusionnées.
La PR vers `main` documente cette dépendance. La préparation technique est terminée ;
la **clôture de l’étape 4 et la décision de publier restent ouvertes**. Une nouvelle clé
ou une activation de facturation n’est pas présentée comme une solution démontrée.
