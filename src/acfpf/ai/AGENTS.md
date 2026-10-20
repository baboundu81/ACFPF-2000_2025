# Instructions spécifiques à la couche IA

Ce fichier complète le `AGENTS.md` racine et s'applique à `src/acfpf/ai/**`.

## Principe central

Le LLM n'est **jamais** la source de vérité d'ACFPF. Il formule une réponse à partir d'un contexte construit par le backend ACFPF à partir de données et documents autorisés.

## Fournisseurs

- La couche métier doit dépendre d'une abstraction `LLMProvider`, jamais directement de Mistral.
- Mistral est le fournisseur par défaut actuel, mais doit rester remplaçable sans modifier la logique de recherche ou de validation.
- Les clés API restent côté serveur. Elles ne doivent jamais être envoyées au navigateur, commitées dans Git ou loggées.

## Sources et grounding

- Aucun accès Web libre n'est accordé au modèle par ACFPF.
- Le modèle ne reçoit que le contexte explicitement sélectionné par ACFPF.
- Une réponse factuelle doit citer au moins une source fournie dans ce contexte.
- Une citation inconnue ou absente du contexte provoque un rejet de la réponse.
- Lorsque le contexte est insuffisant, le résultat attendu est `insufficient`, pas une extrapolation.
- Ne jamais utiliser le savoir pré-entraîné du modèle pour compléter silencieusement une lacune du corpus.

## RAG documentaire

Lorsque le corpus documentaire sera ajouté :

1. ingérer uniquement des sources autorisées et documentées ;
2. conserver URL, producteur, date, licence, page/section et identifiant stable ;
3. découper les documents en chunks traçables ;
4. indexer les chunks pour la recherche ;
5. récupérer un nombre limité de passages pertinents ;
6. transmettre uniquement ces passages au modèle ;
7. valider les citations retournées avant affichage.

Les embeddings servent à retrouver des passages ; ils ne constituent pas une source et ne remplacent pas la citation du document original.

## Réponses

- Répondre en français par défaut.
- Distinguer constat, calcul et interprétation.
- Ne pas transformer une corrélation en causalité.
- Exposer les limites pertinentes.
- Préférer une réponse courte et vérifiable à une réponse longue comportant des inférences fragiles.

## Tests

- Aucun test CI ne doit appeler un fournisseur LLM réel.
- Tester les providers avec un faux client HTTP.
- Tester le service avec un provider factice.
- Tester les cas de citations inconnues, réponse sans citation, contexte insuffisant et provider indisponible.
- Tout changement de modèle ou de prompt important devra à terme être évalué sur un benchmark ACFPF versionné.

## Coût et gratuité

- L'architecture doit fonctionner avec le mode gratuit de Mistral pour le développement et la bêta.
- Limiter la taille du contexte et le nombre d'appels inutiles.
- Avant un déploiement public, ajouter quotas, limitation de débit et suivi de consommation côté serveur.
