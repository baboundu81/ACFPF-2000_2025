<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Intelligence artificielle dans ACFPF

## Objectif

Permettre à un utilisateur de poser une question en langage naturel sur les finances publiques françaises et d'obtenir une réponse **strictement appuyée sur les données et documents validés par ACFPF**, avec citations explicites.

L'IA ne remplace ni la collecte des données, ni leur validation, ni les calculs reproductibles. Elle constitue une couche d'interrogation et d'explication au-dessus de ces éléments.

## Architecture actuelle

```text
question utilisateur
        ↓
ACFPF
        ├── séries macro
        ├── décomposition COFOG
        └── retrieval dans un corpus officiel allow-listé
        ↓
contexte traçable + stades de preuve + identifiants de citation
        ↓
LLMProvider
        ↓
provider configuré
        ↓
réponse JSON structurée
        ↓
validation des citations par ACFPF
        ↓
affichage de la réponse + sources + limites
```

Le fournisseur et le modèle sont interchangeables. Les règles de grounding, le retrieval et la validation des citations appartiennent à ACFPF, pas au fournisseur LLM.

## Données actuellement fournies au modèle

Le contexte peut contenir :

- dépenses, recettes, solde et dette des administrations publiques ;
- dix grandes fonctions COFOG et leur variation depuis 2000 ;
- passages textuels récupérés dans le premier corpus documentaire officiel ;
- métadonnées indiquant si un élément est une observation, une prévision, une décision, une exécution, une évaluation ou un élément de processus parlementaire.

L'IA doit toujours refuser de conclure lorsque ce contexte ne suffit pas.

## Corpus documentaire contrôlé

Le corpus n'est pas un moteur de recherche Web.

`config/evidence_documents.yml` constitue l'allow-list. Seules les entrées explicitement marquées `status: seed` peuvent être téléchargées automatiquement par le premier moteur documentaire.

Lors d'une question :

1. ACFPF lit le manifeste ;
2. les documents autorisés sont chargés depuis le cache ou leur URL officielle ;
3. le texte visible est extrait et découpé en chunks ;
4. une recherche lexicale sélectionne quelques passages ;
5. ces passages sont envoyés au LLM avec leur provenance ;
6. les citations retournées sont vérifiées côté backend.

Le corpus de départ est volontairement limité. L'absence d'un passage pertinent signifie donc souvent « corpus encore incomplet », pas « ce texte n'existe pas ».

Voir [EVIDENCE.md](EVIDENCE.md).

## Providers LLM

La configuration générique repose sur :

```bash
export ACFPF_LLM_PROVIDER="groq"
export ACFPF_LLM_API_KEY="..."
export ACFPF_LLM_MODEL="..."  # facultatif
```

Providers intégrés : Groq, Gemini, Mistral, OpenAI et OpenRouter. Les presets et instructions sont documentés dans [PROVIDERS.md](PROVIDERS.md).

La clé reste exclusivement côté serveur Flask. Elle n'est jamais exposée au navigateur.

Si aucune clé n'est configurée, le dashboard reste utilisable ; seule la fonction de questions IA est désactivée.

## Contraintes de réponse

Le prompt système impose notamment :

- utilisation exclusive du contexte ACFPF fourni ;
- aucune recherche Web ou appel d'outil par le LLM ;
- aucune utilisation volontaire du savoir général du modèle pour combler un manque ;
- réponse `insufficient` si le contexte ne permet pas de répondre ;
- citations obligatoires pour une réponse factuelle ;
- distinction entre observation, prévision, décision, exécution et évaluation ;
- absence de causalité non démontrée ;
- interdiction d'appeler automatiquement « économie » une baisse exprimée seulement en points de PIB.

ACFPF rejette une citation qui n'existe pas dans le contexte transmis au modèle.

Cette validation réduit certaines hallucinations mais **ne garantit pas à elle seule la vérité de chaque phrase**. Le benchmark ACFPF reste indispensable.

## Prochaines étapes du RAG

Le moteur lexical actuel valide le pipeline, mais il n'est pas la cible finale.

Évolutions prioritaires :

1. ingestion structurée Légifrance via l'API PISTE ;
2. PAP/RAP et données d'exécution du budget de l'État ;
3. amendements et dossiers législatifs de l'Assemblée nationale et du Sénat ;
4. LFSS, annexes et REPSS ;
5. rapports de la Cour des comptes ;
6. extraction PDF avec page/section ;
7. `EmbeddingProvider` abstrait ;
8. index vectoriel et reranking ;
9. benchmark du retrieval et des réponses.

## Gratuité et déploiement

Pour le développement local, ACFPF privilégie un provider disposant d'un free tier. Pour un service public hébergé, la gratuité pour l'utilisateur ne signifie pas nécessairement l'absence de coût d'infrastructure.

Avant une ouverture publique, il faudra notamment : quotas, limitation de débit, suivi des tokens/coûts, protection de la clé serveur, politique de confidentialité et éventuellement prise en charge d'une clé utilisateur.

## Benchmark ACFPF

Le choix final du modèle ne doit pas reposer uniquement sur des benchmarks généraux.

Le benchmark devra couvrir :

- questions dont la réponse est présente dans les données ;
- questions nécessitant chiffres + documents ;
- questions volontairement impossibles avec le corpus ;
- distinction prévision/décision/exécution ;
- calculs simples et comparaisons temporelles ;
- tentatives d'obtenir une causalité non démontrée ;
- citations valides, invalides ou absentes.

Mesures minimales : exactitude, refus correct, qualité des citations, hallucinations, qualité du français, rappel du retrieval, latence et coût en tokens.
