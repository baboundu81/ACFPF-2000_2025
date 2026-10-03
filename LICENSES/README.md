# Licences du projet

ACFPF est un dépôt **multi-licence**.

## Logiciel — AGPL-3.0-or-later

Le code logiciel original du projet est distribué sous **GNU Affero General Public License version 3, ou toute version ultérieure au choix du licencié** (`AGPL-3.0-or-later`).

Cela couvre notamment :

- `src/**` ;
- `scripts/**` lorsqu'ils contiennent du code ;
- `tests/**` ;
- les notebooks exécutables (`*.ipynb`) ;
- les fichiers de code placés sous `analyses/**` ;
- le code d'une éventuelle application ou API ACFPF.

Le texte de l'AGPLv3 est fourni dans [../LICENSE](../LICENSE) et [AGPL-3.0-or-later.txt](AGPL-3.0-or-later.txt).

En pratique, une version modifiée distribuée doit rester sous AGPL et fournir son code source correspondant. Lorsqu'une version modifiée permet à des utilisateurs d'interagir avec elle à distance via un réseau, ces utilisateurs doivent aussi pouvoir obtenir le code source correspondant conformément à la section 13 de l'AGPLv3.

## Documentation et analyses — CC BY 4.0

Les contenus éditoriaux originaux sont distribués sous **Creative Commons Attribution 4.0 International** (`CC-BY-4.0`), sauf mention contraire.

Cela couvre notamment :

- `README.md` ;
- `docs/**` ;
- les fichiers Markdown d'analyse ;
- les textes de rapports ;
- les graphiques et illustrations originaux créés par le projet, lorsqu'ils ne contiennent pas d'éléments tiers soumis à d'autres conditions.

La CC BY 4.0 permet la copie, la modification et l'utilisation commerciale avec attribution, lien vers la licence et indication des modifications.

## Données et contenus tiers

**Les données tierces ne sont pas relicenciées par ACFPF.**

Les fichiers provenant de l'INSEE, d'Eurostat, de la Cour des comptes, de data.gouv.fr ou de tout autre producteur restent soumis à leur licence ou à leurs conditions de réutilisation propres.

Un fichier dérivé peut également rester soumis à des obligations attachées aux données sources. La provenance et la licence doivent donc être suivies dans les métadonnées.

## Fichiers mixtes

Lorsqu'un fichier contient à la fois du code et du contenu éditorial :

- un notebook `.ipynb` est traité par défaut comme du logiciel et placé sous AGPL ;
- un rapport Markdown contenant de courts extraits de code reste traité comme documentation sous CC BY 4.0, sauf mention contraire ;
- une mention SPDX explicite dans le fichier prime sur cette règle générale.

## SPDX

Les nouveaux fichiers devraient utiliser, lorsque possible, l'un des identifiants :

```
SPDX-License-Identifier: AGPL-3.0-or-later
SPDX-License-Identifier: CC-BY-4.0
```

## Copyright

Sauf mention contraire, les contributions restent la propriété de leurs auteurs respectifs. La licence accordée au projet permet leur redistribution selon les termes ci-dessus.
