# Données

## Principe

Les données sont séparées selon leur état de transformation.

- `raw/` : copie fidèle de la source ;
- `interim/` : données intermédiaires ;
- `processed/` : données propres et normalisées utilisées par les analyses.

Les fichiers volumineux ne sont pas versionnés par défaut.

## Traçabilité minimale

Toute acquisition de données doit permettre de retrouver :

- le producteur ;
- l'URL source ;
- la date de récupération ;
- le nom ou identifiant du jeu ;
- l'unité ;
- le périmètre ;
- si possible un hash du fichier téléchargé.

Les données brutes ne doivent pas être corrigées manuellement.
