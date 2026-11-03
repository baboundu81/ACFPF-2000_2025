# Planner borné de recherche législative

Le planner traduit une formulation citoyenne approximative en critères de recherche structurés utilisables par le moteur déterministe ACFPF.

Il ne recherche pas les textes lui-même et ne reçoit aucun identifiant, titre ou URL de dossier candidat. Il ne peut retourner que :

- une requête textuelle courte ;
- un statut ;
- une chambre ;
- une étape normalisée ;
- un thème ;
- un type de texte ;
- une période.

Les facettes possibles sont construites à partir de l'inventaire officiel déjà chargé depuis l'Assemblée nationale et le Sénat. Toute valeur produite par le modèle qui n'appartient pas à ces facettes est rejetée côté backend.

Le planner est donc un composant d'interprétation de requête, pas une source de vérité. Les résultats restent exclusivement issus de l'inventaire structuré officiel, et le contenu juridique continue d'exiger la lecture de sources primaires avant toute réponse factuelle.
