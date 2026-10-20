# Instructions spécifiques à la couche IA

Ce fichier complète le `AGENTS.md` racine et s'applique à `src/acfpf/ai/**`.

## Principe central

Le LLM n'est **jamais** la source de vérité d'ACFPF. Il choisit les recherches à mener et formule une synthèse à partir de données structurées ACFPF et de preuves officielles effectivement lues pendant la session.

## Fournisseurs

- La couche métier doit dépendre d'une abstraction `LLMProvider`, jamais directement d'un fournisseur concret.
- La configuration standard est `ACFPF_LLM_PROVIDER` + `ACFPF_LLM_API_KEY` + `ACFPF_LLM_MODEL` facultatif.
- Gemini est le provider recommandé par défaut pour le développement tant que son free tier reste disponible, mais ce choix ne doit jamais contaminer la logique métier.
- Les providers actuellement supportés sont Gemini, Groq, Claude, Mistral, OpenAI et OpenRouter.
- Ajouter ou remplacer un provider ne doit pas modifier le protocole de recherche, les règles métier ou la validation des citations.
- Les providers capables de Structured Outputs doivent utiliser le schéma commun `AGENT_ACTION_SCHEMA` plutôt qu'un JSON libre.
- Claude utilise l'API native Anthropic pour conserver la garantie de schéma ; ne pas basculer silencieusement sur sa couche OpenAI-compatible tant que `response_format` y est ignoré.
- Les clés API restent côté serveur. Elles ne doivent jamais être envoyées au navigateur, commitées dans Git ou loggées.

## Agent de recherche live

Le protocole d'agent est provider-neutral. À chaque tour, le modèle renvoie exactement une action JSON parmi :

- `search` : rechercher des URL sur une ou plusieurs sources ACFPF autorisées ;
- `open` : ouvrir une URL officielle ;
- `read` : lire une autre unité contiguë d'un document ouvert ;
- `answer` : répondre avec citations ou déclarer `insufficient`.

Le modèle n'obtient pas un navigateur libre. Le backend exécute chaque action et contrôle les domaines.

## Sources et grounding

- Le registre `config/sources.yml` est la liste blanche réseau.
- Toute URL doit être HTTPS et appartenir à un domaine autorisé ; les redirections doivent être revalidées.
- Un index Web peut être utilisé pour la découverte d'URL uniquement. Ses snippets et résumés ne doivent jamais devenir des preuves.
- Une URL trouvée mais non ouverte n'est pas citable.
- Une unité de document n'est citable que si elle a effectivement été fournie au modèle pendant la session.
- Le backend attribue les identifiants `E…`; le modèle ne choisit pas lui-même des identifiants arbitraires.
- Les séries déterministes utilisent des identifiants `S…`.
- Une citation inconnue provoque un rejet de la réponse.
- Lorsque les preuves sont insuffisantes, le résultat attendu est `insufficient`, pas une extrapolation.
- Ne jamais utiliser le savoir pré-entraîné du modèle pour compléter silencieusement une lacune.

## Lecture documentaire

- Ne pas classer ou supprimer des paragraphes par pertinence avant lecture du modèle.
- Le texte visible doit être conservé dans son ordre source.
- La segmentation HTML doit être mécanique et contiguë.
- Les PDF peuvent être regroupés en blocs de pages contiguës.
- Le modèle peut demander les unités suivantes ; le nombre total d'étapes reste plafonné.
- Les documents sont éphémères par question. Ne pas recréer un corpus local persistant par défaut.
- Conserver dans la citation live : URL, source, titre, locator, date de consultation et empreinte SHA-256.

## Sémantique des preuves

Le prompt et la réponse doivent distinguer :

- `statistical_observation` ;
- `forecast` ;
- `decision` ;
- `execution` ;
- `evaluation` ;
- `parliamentary_process` ;
- `interpretation`.

Une prévision, une décision et une exécution ne sont jamais interchangeables. Une baisse en points de PIB ne suffit pas à établir une économie en euros ou en moyens.

## Réponses

- Répondre en français par défaut.
- Distinguer constat, calcul, décision, exécution et interprétation.
- Ne pas transformer une corrélation en causalité.
- Ne jamais traiter un amendement rejeté comme une règle applicable.
- Exposer les limites pertinentes et les recherches qui n'ont pas abouti.
- Préférer une réponse vérifiable à une réponse longue comportant des inférences fragiles.

## UX et progression

Le backend peut exposer des événements de progression `started`, `search`, `open`, `read`, `notice`, `answer`.

Ces événements doivent décrire les actions observables de l'agent, jamais son raisonnement privé. L'interface doit montrer les sources ouvertes et les locators lus sans afficher de chaîne de pensée.

## Tests

- Aucun test CI ne doit appeler un fournisseur LLM réel ni une source externe.
- Tester les providers avec un faux client HTTP.
- Tester l'agent avec des séquences de réponses factices.
- Tester la liste blanche, les redirections, les documents longs et les unités mécaniques.
- Tester les cas de citation jamais lue, réponse sans citation, preuve insuffisante et provider indisponible.
- Tester le flux NDJSON de progression.
- Tout changement de modèle, prompt ou stratégie d'agent important devra être évalué sur un benchmark ACFPF versionné.

## Coût et gratuité

- L'architecture doit rester utilisable avec au moins un provider disposant d'un free tier pour le développement.
- Ne pas supposer qu'un provider gratuit aujourd'hui le restera : garder les alternatives fonctionnelles et centraliser les presets.
- Plafonner le nombre d'étapes d'enquête et la taille des documents lus.
- Avant un déploiement public, ajouter quotas, limitation de débit, suivi de consommation et budgets de tokens côté serveur.
