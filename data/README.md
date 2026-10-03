<!-- SPDX-License-Identifier: CC-BY-4.0 -->

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

## Licences des données

Le fait qu'un fichier soit téléchargé, transformé ou référencé par ACFPF ne modifie pas sa licence d'origine.

Chaque jeu de données doit, lorsque l'information est disponible, conserver dans ses métadonnées :

- la licence ou les conditions de réutilisation du producteur ;
- l'URL de la licence ;
- le producteur ;
- l'URL source ;
- la date de récupération.

Les licences `PolyForm-Noncommercial-1.0.0` et `CC-BY-4.0` du projet ne s'appliquent pas automatiquement aux données tierces.
