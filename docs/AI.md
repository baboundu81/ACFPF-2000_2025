<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Intelligence artificielle dans ACFPF

## Objectif

Permettre à un utilisateur de poser une question en langage naturel sur les finances publiques françaises et d'obtenir une réponse **strictement appuyée sur les données et documents validés par ACFPF**, avec citations explicites.

L'IA ne remplace ni la collecte des données, ni leur validation, ni les calculs reproductibles. Elle constitue une couche d'interrogation et d'explication au-dessus de ces éléments.

## Architecture cible

```text
question utilisateur
        ↓
ACFPF
        ↓
recherche / sélection dans les données et documents autorisés
        ↓
contexte traçable + identifiants de source
        ↓
LLMProvider
        ↓
Mistral (par défaut aujourd'hui)
        ↓
réponse structurée
        ↓
validation des citations par ACFPF
        ↓
affichage de la réponse + sources + limites
```

Le fournisseur du modèle doit rester interchangeable.

## Premier jalon

Le premier jalon ne constitue **pas encore un RAG documentaire complet**.

L'IA reçoit uniquement :

- les séries macroéconomiques actuellement chargées par ACFPF ;
- leurs unités ;
- les années disponibles ;
- les métadonnées des jeux Eurostat associés.

Elle peut donc répondre à des questions simples sur les dépenses publiques, les recettes, le solde et la dette pour les années présentes dans ce socle.

Elle doit refuser de conclure sur un domaine pour lequel ACFPF n'a pas encore fourni les données nécessaires, par exemple l'éducation, les retraites ou la fiscalité d'un ménage.

## Fournisseur initial : Mistral

Le fournisseur par défaut est Mistral via l'endpoint `POST /v1/chat/completions`.

Configuration locale :

```bash
export MISTRAL_API_KEY="..."
acfpf
```

Le modèle est configurable avec :

```bash
export ACFPF_LLM_MODEL="mistral-small-latest"
```

La clé reste exclusivement côté serveur Flask. Elle n'est jamais exposée au navigateur.

Si aucune clé n'est configurée, l'application principale reste utilisable ; seule la fonction de questions IA est désactivée.

## Contraintes de réponse

Le prompt système impose notamment :

- utilisation exclusive du contexte ACFPF fourni ;
- aucune recherche Web ;
- aucune utilisation volontaire du savoir général du modèle pour combler un manque ;
- réponse `insufficient` si le contexte ne permet pas de répondre ;
- citations obligatoires pour une réponse factuelle ;
- distinction entre constat, calcul et interprétation ;
- absence de causalité non démontrée.

Le fournisseur renvoie un objet JSON. ACFPF valide ensuite les identifiants de citation et refuse une réponse qui cite une source non fournie.

Cette validation limite certaines hallucinations mais **ne garantit pas à elle seule qu'une phrase est factuellement exacte**. C'est pourquoi un benchmark spécifique ACFPF devra être construit avant de présenter cette couche comme hautement fiable.

## Étape suivante : RAG documentaire

Lorsque le corpus aura suffisamment grandi :

1. téléchargement ou ingestion des documents autorisés ;
2. extraction du texte avec conservation des pages/sections ;
3. découpage en passages traçables ;
4. embeddings, initialement avec un provider abstrait ;
5. index vectoriel local ou serveur ;
6. recherche des passages pertinents ;
7. reranking éventuel ;
8. génération d'une réponse à partir des seuls passages récupérés ;
9. citations vers le document, la page et la source originale.

Le modèle d'embeddings peut être `mistral-embed` au départ, mais ce choix doit rester interchangeable comme celui du LLM.

## Gratuité et déploiement

Pour le développement et la bêta locale, ACFPF vise le mode gratuit de l'API Mistral.

Pour un service public hébergé, la gratuité pour l'utilisateur ne signifie pas nécessairement l'absence de coût d'infrastructure. Avant une ouverture publique, il faudra mettre en place :

- quotas par utilisateur/IP ;
- limitation de débit ;
- suivi des tokens et du coût ;
- cache de certaines réponses ou recherches ;
- protection de la clé serveur ;
- politique de confidentialité ;
- éventuellement possibilité pour un utilisateur avancé de fournir sa propre clé.

## Benchmark ACFPF

Le choix final du modèle ne doit pas reposer uniquement sur des benchmarks généraux.

ACFPF devra disposer de son propre jeu de tests :

- questions dont la réponse est présente dans les données ;
- questions volontairement impossibles avec le corpus ;
- questions ambiguës ;
- calculs simples ;
- comparaisons temporelles ;
- tentatives d'obtenir une réponse politique ou causale non supportée ;
- vérification des citations.

Mesures minimales : exactitude, refus correct, qualité des citations, hallucinations, qualité du français, latence et coût en tokens.
