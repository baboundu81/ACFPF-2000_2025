# Instructions spécifiques à la couche IA

Ce fichier complète le `AGENTS.md` racine et s'applique à `src/acfpf/ai/**`.

## Principe central

Le LLM n'est **jamais** la source de vérité d'ACFPF. Il formule une réponse à partir d'un contexte construit par le backend ACFPF à partir de données et documents autorisés.

## Fournisseurs

- La couche métier doit dépendre d'une abstraction `LLMProvider`, jamais directement d'un fournisseur concret.
- La configuration standard est `ACFPF_LLM_PROVIDER` + `ACFPF_LLM_API_KEY` + `ACFPF_LLM_MODEL` facultatif.
- Groq est le provider recommandé par défaut pour le développement tant que son free tier reste disponible, mais ce choix ne doit jamais contaminer la logique métier.
- Les providers actuellement supportés sont Groq, Gemini, Mistral, OpenAI et OpenRouter.
- Ajouter ou remplacer un provider ne doit pas modifier le RAG, le prompt métier ou la validation des citations.
- Les clés API restent côté serveur. Elles ne doivent jamais être envoyées au navigateur, commitées dans Git ou loggées.

## Sources et grounding

- Aucun accès Web libre n'est accordé au modèle par ACFPF.
- Le modèle ne reçoit que le contexte explicitement sélectionné par ACFPF.
- Le backend peut récupérer des documents sur Internet uniquement si leur URL exacte figure dans un manifeste ACFPF de sources officielles autorisées.
- Une réponse factuelle doit citer au moins une source fournie dans ce contexte.
- Une citation inconnue ou absente du contexte provoque un rejet de la réponse.
- Lorsque le contexte est insuffisant, le résultat attendu est `insufficient`, pas une extrapolation.
- Ne jamais utiliser le savoir pré-entraîné du modèle pour compléter silencieusement une lacune du corpus.
- Le contexte doit conserver le **stade de preuve** de chaque élément : observation, prévision, décision, exécution, évaluation, processus parlementaire ou interprétation.
- Le prompt doit rappeler qu'une prévision, une décision et une exécution ne sont pas interchangeables.

## RAG documentaire

Le premier corpus documentaire est volontairement limité et allow-listé.

Pipeline actuel :

1. lire le manifeste `config/evidence_documents.yml` ;
2. télécharger uniquement les entrées `status: seed` ;
3. extraire le texte visible et le mettre en cache local ;
4. découper en chunks traçables ;
5. effectuer une recherche lexicale simple ;
6. transmettre un nombre limité de passages au modèle ;
7. valider les identifiants de citation retournés.

Évolution attendue :

- extraction structurée PDF/HTML ;
- pages, sections et articles précis ;
- API Légifrance PISTE ;
- corpus PAP/RAP/exécution budgétaire ;
- amendements et dossiers législatifs Assemblée/Sénat ;
- `EmbeddingProvider` abstrait ;
- index vectoriel et reranking ;
- benchmark de retrieval.

Les embeddings servent à retrouver des passages ; ils ne constituent pas une source et ne remplacent pas la citation du document original.

## Réponses

- Répondre en français par défaut.
- Distinguer constat, calcul, décision, exécution et interprétation.
- Ne pas transformer une corrélation en causalité.
- Ne pas qualifier de « baisse des dépenses » une simple baisse de part de PIB sans préciser l'unité.
- Ne jamais traiter un amendement rejeté comme une règle applicable.
- Exposer les limites pertinentes et la couverture partielle du corpus.
- Préférer une réponse courte et vérifiable à une réponse longue comportant des inférences fragiles.

## Tests

- Aucun test CI ne doit appeler un fournisseur LLM réel ni une source documentaire externe.
- Tester les providers avec un faux client HTTP.
- Tester le registre de providers et les valeurs par défaut.
- Tester le service avec un provider factice.
- Tester le parsing COFOG, les stades de preuve, l'extraction/chunking documentaire et la récupération sur fixtures.
- Tester les cas de citations inconnues, réponse sans citation, contexte insuffisant et provider indisponible.
- Tout changement de modèle, prompt ou stratégie de retrieval important devra à terme être évalué sur un benchmark ACFPF versionné.

## Coût et gratuité

- L'architecture doit rester utilisable avec au moins un provider disposant d'un vrai free tier pour le développement.
- Ne pas supposer qu'un provider gratuit aujourd'hui le restera : documenter le choix, garder les alternatives fonctionnelles et centraliser les presets.
- Limiter la taille du contexte, le nombre de chunks et les appels inutiles.
- Avant un déploiement public, ajouter quotas, limitation de débit et suivi de consommation côté serveur.
