<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Prendre en main la candidate V1

Cette version est une candidate `1.0.0rc1`, destinée aux essais locaux. Le statut de
recette et les limites constatées figurent dans [V1_STEP4_ACCEPTANCE.md](V1_STEP4_ACCEPTANCE.md).
Elle n’est pas une release publiée. Le logiciel est réservé aux usages autorisés par
la [licence PolyForm Noncommercial](../LICENSE).

## Installer et démarrer

Prérequis : Python 3.11 ou supérieur, `pip`, accès Internet pour installer les dépendances
et consulter les sources. Les contrôles de cette livraison utilisent Linux avec Python
3.11 et 3.14 ; Windows et macOS ne sont pas vérifiés dans cette session.

Depuis un checkout de la branche de livraison :

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install .
acfpf
```

Sous PowerShell, créer l’environnement avec `py -3 -m venv .venv`, puis l’activer
avec `.venv\Scripts\Activate.ps1`. Les commandes `python -m pip install .` et `acfpf`
sont ensuite identiques. Il s’agit d’instructions proposées, pas d’un essai Windows réalisé.

`acfpf` ouvre l’accueil sur `http://127.0.0.1:5000`. Après installation, cette commande
fonctionne aussi depuis un autre dossier. Pour éviter l’ouverture automatique du navigateur :

```sh
acfpf --no-browser --port 5050
```

Arrêter le serveur avec `Ctrl+C`. Une seconde option de lancement est `python -m acfpf`.
Le serveur fourni est destiné à cet usage local. Aucun déploiement public n’est préparé ici.

Une wheel construite par le projet peut être installée avec
`python -m pip install /chemin/acfpf-1.0.0rc1-py3-none-any.whl`. Le nom `acfpf` seul sur
PyPI ne constitue pas la procédure de cette candidate, qui n’a pas été publiée.

## Configurer l’IA côté serveur

Sans clé, la recherche de dossiers et les finances restent utilisables. La question
libre et le chat indiquent que l’IA n’est pas configurée.

Dans l’application locale, ouvrez **Configuration IA**. Choisissez un fournisseur,
puis sélectionnez ou déposez un fichier texte UTF-8 contenant uniquement sa clé sur
une ligne (4 Kio maximum). Le modèle par défaut est indiqué dans le formulaire.
Cliquez sur **Activer l’IA** : le changement est immédiat pour le chat et la recherche
assistée. L’import ne déclenche aucun appel fournisseur ; la clé sera utilisée quand
vous lancerez une enquête ou une recherche assistée.

Le fichier n’est pas sauvegardé. La clé reste en mémoire côté serveur pour ce
lancement d’ACFPF ; **Rétablir le réglage de démarrage** annule l’import. Les variables
d’environnement servent toujours au démarrage et permettent de choisir un modèle
explicite. Le menu d’import est disponible sur l’interface locale, pas lorsque le
lanceur est configuré pour écouter sur le réseau.

Gemini reste le fournisseur par défaut :

```sh
export ACFPF_LLM_PROVIDER="gemini"
export ACFPF_LLM_API_KEY="votre_cle"
acfpf
```

La clé se gère dans [Google AI Studio](https://aistudio.google.com/api-keys).
Le test du 7 novembre a constaté un HTTP 503 sur la génération Gemini ; une clé acceptée
ne garantit pas que le service de génération réponde. Voir le rapport de recette avant
de conclure à un défaut de clé.

Pour choisir explicitement Groq :

```sh
export ACFPF_LLM_PROVIDER="groq"
export ACFPF_LLM_API_KEY="votre_cle_groq"
acfpf
```

Le scénario budgétaire et le benchmark ont fonctionné avec Groq lors de cette recette,
mais des quotas et refus de génération ont aussi été observés. Il n’y a aucune bascule
automatique de fournisseur ou de modèle en cas d’échec.

Sous PowerShell, remplacer par exemple `export ACFPF_LLM_PROVIDER="groq"` par
`$env:ACFPF_LLM_PROVIDER="groq"`, et définir la clé de la même façon.

| Variable | Rôle |
| --- | --- |
| `ACFPF_LLM_PROVIDER` | `gemini` par défaut ; aussi `groq`, `claude`, `mistral`, `openai`, `openrouter` |
| `ACFPF_LLM_API_KEY` | Clé du fournisseur choisi, exclusivement côté serveur |
| `ACFPF_LLM_MODEL` | Modèle explicite facultatif ; défauts dans [PROVIDERS.md](PROVIDERS.md) |
| `GEMINI_API_KEY`, `GROQ_API_KEY`, `ANTHROPIC_API_KEY`, `MISTRAL_API_KEY`, `OPENAI_API_KEY`, `OPENROUTER_API_KEY` | Variables spécifiques acceptées si la clé commune est absente |

Relancer ACFPF après modification des variables. Un fichier `.env` ou un fichier de clé
n’est **pas chargé automatiquement** : définir les variables dans le terminal qui lance
le serveur. Ne pas versionner les clés. Le registre réseau embarqué est indépendant du
fournisseur ; une clé IA ne donne pas au modèle accès à tout le Web.

## Essayer les parcours

1. Sur l’accueil, poser une question précise. Observer recherche, ouverture, lecture et
   vérification. Une réponse peut être refusée si les preuves manquent ; une erreur ne
   constitue pas une réponse sur le fond.
2. Ouvrir les liens de preuves affichés dans la réponse. Une citation documentaire
   identifie le document et son segment/page ; une citation `S…` renvoie à une série structurée.
3. Dans « Retrouver un texte », chercher « logement » ou parcourir les textes en cours.
   Le mode strict reste disponible sans IA. Les filtres portent sur l’inventaire officiel.
4. Ouvrir un dossier, lire son statut et sa fraîcheur, puis poser une question dans son chat.
   Les rubriques de détail sont repliées et se chargent à la demande.
5. Ouvrir « Finances publiques » pour les séries, unités, tableaux et sources.

Les inventaires sont mis en cache quelques heures dans `~/.cache/acfpf` et les séries
financières pendant une journée. Un cache peut être utilisé en repli lorsque la source
est inaccessible ; sa provenance et sa fraîcheur restent à examiner. La lecture de
textes pendant une enquête reste éphémère et isolée par question. Sans réseau, un
premier chargement de données non mises en cache peut échouer explicitement.

## Comprendre un échec

| Message | Action utile |
| --- | --- |
| IA non configurée | Définir la clé et le fournisseur côté serveur, puis relancer |
| HTTP 401 / 403 | Vérifier la clé et les droits du fournisseur sélectionné |
| HTTP 429 | Attendre le délai indiqué ; les reprises automatiques sont bornées à deux par question |
| HTTP 413 / contexte trop volumineux | Réduire le périmètre ou utiliser un modèle dont le quota couvre la requête |
| HTTP 503 | Réessayer ultérieurement ; le service du fournisseur est indisponible |
| Index HTTP 202 / source indisponible | La découverte est temporairement empêchée ; fournir une URL officielle connue peut permettre la lecture directe |
| Preuves insuffisantes / citation refusée | Aucun résultat non vérifié n’est publié ; préciser la question ou la source |
| Adresse déjà utilisée | Arrêter l’autre serveur ou choisir `acfpf --port 5050` |

Une citation invalide peut donner lieu à une seule correction interne, sans afficher
la réponse refusée. Chaque nouveau candidat est contrôlé à nouveau et soumis à la
vérification distincte de ses appuis. Cela ne garantit pas une réussite du fournisseur.

Les modules versions, amendements, scrutins, rapports, débats et comparaison textuelle
restent partiels ou expérimentaux. Ils ne garantissent ni couverture exhaustive, ni
comparaison juridique certifiée, ni établissement du droit applicable.

## Reproduire les contrôles

Depuis les sources :

```sh
python -m pip install -e ".[dev]"
ruff check .
pytest -q
node --test tests/js/*.test.js
```

Node est requis pour les contrôles JavaScript, pas pour lancer l’application.
Les tests par défaut simulent HTTP et LLM. Les essais réels sont séparés :

```sh
ACFPF_LIVE_DOCUMENTARY=1 pytest -q -s tests/test_live_documentary_pipeline.py
ACFPF_LIVE_AI=1 pytest -q tests/test_live_ai_grounding.py
ACFPF_LIVE_ACCEPTANCE=1 pytest -q -s tests/test_live_v1_acceptance.py
```

Les deux dernières commandes nécessitent une clé définie dans les variables ci-dessus,
consomment le quota du fournisseur et peuvent échouer. Les résultats publiés sont
ceux du [rapport de recette](V1_STEP4_ACCEPTANCE.md), pas une promesse de disponibilité.

Pour construire les artefacts locaux :

```sh
python -m pip install build
python -m build
```

Le registre canonique reste `config/sources.yml`. Après une modification, synchroniser
sa copie embarquée `src/acfpf/resources/sources.yml` ; un test interdit leur divergence.
Le chargement par défaut utilise cette copie versionnée et ne dépend jamais d’un fichier
`config/sources.yml` trouvé dans le dossier courant.
