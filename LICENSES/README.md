<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Licences du projet

ACFPF est un dépôt **multi-licence**.

## Logiciel — PolyForm Noncommercial 1.0.0

Le code logiciel original du projet est distribué sous **PolyForm Noncommercial License 1.0.0** (`PolyForm-Noncommercial-1.0.0`).

Cela couvre notamment :

- `src/**` ;
- `scripts/**` lorsqu'ils contiennent du code ;
- `tests/**` ;
- les notebooks exécutables (`*.ipynb`) ;
- les fichiers de code placés sous `analyses/**` ;
- le code d'une éventuelle application ou API ACFPF.

Le texte officiel est fourni dans [../LICENSE](../LICENSE) et [PolyForm-Noncommercial-1.0.0.md](PolyForm-Noncommercial-1.0.0.md).

Cette licence autorise l'utilisation, la modification et la distribution du logiciel pour des usages non commerciaux selon ses termes. Elle autorise notamment certains usages personnels ainsi que les usages par des organisations non commerciales, établissements d'enseignement, organismes publics de recherche, de sécurité ou de santé publique, organismes de protection de l'environnement et institutions gouvernementales dans les conditions prévues par la licence.

**Elle n'accorde pas de droit d'utilisation commerciale.** Toute utilisation commerciale nécessite une licence séparée : voir [../COMMERCIAL-LICENSING.md](../COMMERCIAL-LICENSING.md).

PolyForm Noncommercial est une licence **source-available**, mais elle n'est pas une licence open source approuvée par l'OSI. Contrairement à l'AGPL, elle n'impose pas à elle seule une obligation générale de publier le code source de toute modification privée ou déployée en réseau.

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

- un notebook `.ipynb` est traité par défaut comme du logiciel et placé sous PolyForm Noncommercial ;
- un rapport Markdown contenant de courts extraits de code reste traité comme documentation sous CC BY 4.0, sauf mention contraire ;
- une mention SPDX explicite dans le fichier prime sur cette règle générale.

## SPDX

Les nouveaux fichiers devraient utiliser, lorsque possible, l'un des identifiants :

```
SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
SPDX-License-Identifier: CC-BY-4.0
```

## Contributions et licences commerciales

Les contributeurs conservent la propriété de leurs contributions, mais les contributions de code doivent être accompagnées du grant prévu dans [CONTRIBUTOR_LICENSE_AGREEMENT.md](../CONTRIBUTOR_LICENSE_AGREEMENT.md). Ce mécanisme permet au propriétaire du projet de proposer, en parallèle de la licence non commerciale publique, une licence commerciale distincte.

## Historique

Le changement de licence n'annule pas les droits déjà accordés sur les versions antérieurement publiées. Voir [LICENSE_HISTORY.md](LICENSE_HISTORY.md).
