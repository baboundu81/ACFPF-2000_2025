<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Plan de développement — analyse citoyenne de l'action publique

## Vision

ACFPF devient en priorité un outil citoyen permettant de comprendre l'action publique française à partir de sources primaires et vérifiables. Les finances publiques restent un sous-outil spécialisé, réutilisable lorsqu'une décision ou une politique possède une dimension budgétaire.

Le parcours principal visé est :

1. retrouver ou découvrir un texte avec des mots courants ;
2. sélectionner le dossier législatif correspondant ;
3. comprendre son état d'avancement et ses différentes étapes ;
4. ouvrir un chat dédié à ce dossier ;
5. obtenir des réponses sourcées dans lesquelles projet initial, amendements, votes, texte adopté, promulgation et application ne sont jamais confondus ;
6. à terme, relier la décision aux moyens budgétaires, à l'exécution et aux évaluations a posteriori.

## Principes d'architecture

- Le LLM n'est pas une base de données législative. La liste des dossiers et leurs métadonnées proviennent de données officielles structurées.
- Une métadonnée de dossier sert à identifier et orienter une enquête ; elle ne prouve pas le contenu juridique d'un article.
- Toute affirmation sur le contenu d'un texte doit reposer sur un document officiel effectivement ouvert et lu par le moteur de recherche live.
- Les différentes versions d'un texte doivent être représentées explicitement avant de proposer des comparaisons automatiques.
- Les connecteurs Assemblée nationale, Sénat et Légifrance doivent converger vers un modèle métier commun sans effacer leur provenance.
- Les finances publiques restent déterministes côté Python pour les séries, calculs et comparaisons chiffrées.

## Phase 1 — verticale de découverte législative

Objectif : rendre le nouveau parcours utilisable de bout en bout sans attendre l'intégration de toutes les sources parlementaires.

- [x] Ajouter un connecteur structuré vers les dossiers législatifs de l'Assemblée nationale.
- [x] Ajouter un modèle `LegislativeDossier` et une chronologie minimale.
- [x] Permettre les recherches en langage courant telles que « quels textes sont en cours de vote ? » ou « quels textes concernent le logement ? ».
- [x] Faire de `/` l'accueil citoyen consacré aux textes et décisions.
- [x] Déplacer le dashboard financier existant sous `/finances`.
- [x] Ajouter `/textes/<id>` avec les repères du dossier et son chat dédié.
- [x] Ajouter `/api/legislation` et `/api/legislation/<id>`.
- [x] Conserver le dossier côté serveur lors des questions afin qu'un client ne puisse pas substituer silencieusement son titre ou son URL.
- [x] Ajouter des tests unitaires et web sans dépendance réseau réelle.

La couverture initiale limitée à l'Assemblée nationale a été levée lors de l'étape suivante avec l'intégration de DOSLEG au Sénat.

## Phase 2 — couverture parlementaire complète

- [x] Ajouter un connecteur structuré Sénat à partir de l'export officiel DOSLEG.
- [x] Dédupliquer les dossiers communs Assemblée/Sénat avec conservation des identifiants et URL de chaque chambre.
- [x] Normaliser une taxonomie d'étapes stable : dépôt, commission, séance/lecture, navette, CMP, Congrès, contrôle constitutionnel, adopté, promulgué, clos et inconnu.
- [x] Ajouter les filtres chambre, période, type de texte et thème à partir de facettes calculées sur l'inventaire officiel chargé.
- [x] Ajouter un filtre d'étape précis fondé sur la taxonomie normalisée.
- [ ] Ajouter une recherche assistée pour les formulations approximatives sans laisser le LLM inventer les candidats.
- [x] Conserver un comportement dégradé explicite si une seule source parlementaire est momentanément indisponible.
- [ ] Documenter les règles de classement et de tri pour éviter toute notion opaque de « texte important ».

### Règle de fusion inter-chambres

ACFPF ne fait pas de rapprochement flou automatique entre dossiers. Deux entrées Assemblée/Sénat sont regroupées uniquement lorsque leur titre canonique correspond exactement après normalisation mécanique (casse, accents et préfixe « projet/proposition de loi »). Les références de chaque chambre restent conservées dans `sources`. Cette règle privilégie les faux négatifs aux faux positifs : deux textes proches mais non identiques restent séparés tant qu'un identifiant officiel commun n'a pas été établi.

Pour les statuts terminaux, une information explicite de promulgation, adoption définitive ou clôture sans loi prime sur un dossier qui apparaît encore actif dans l'autre source. Toute panne partielle est exposée comme avertissement et ne provoque pas l'invention d'un résultat de remplacement.

### Règles de facettes et de période

Les facettes de chambre, étape, thème, type et période sont calculées sur l'inventaire effectivement chargé avant application des filtres. Elles ne sont pas générées par le LLM. La période correspond à l'année de dépôt ou de début du dossier ; si cette date n'est pas fournie par la source, ACFPF utilise l'année de dernière activité comme repli explicite.

### Taxonomie des étapes

Le champ `current_stage` conserve le libellé brut fourni par la source. ACFPF ajoute à côté un couple dérivé `stage` / `stage_label` afin de permettre des comparaisons et filtres cohérents entre les chambres. Cette classification est mécanique et conservatrice : lorsqu'un libellé ne permet pas d'établir une étape sans ambiguïté, `stage=unknown` et le libellé utilisateur devient « Étape à vérifier ». Une classification ACFPF ne remplace donc jamais la provenance ou le libellé officiel.

Les codes normalisés sont :

- `deposit` — dépôt ;
- `committee` — commission ;
- `plenary` — séance ou lecture ;
- `shuttle` — navette parlementaire ;
- `cmp` — commission mixte paritaire ;
- `congress` — Congrès du Parlement ;
- `constitutional_review` — contrôle constitutionnel ;
- `adopted` — adopté ;
- `promulgated` — promulgué ;
- `closed` — clos sans promulgation ;
- `unknown` — étape non déterminable sans ambiguïté.

## Phase 3 — dossier législatif riche

Introduire des objets structurés :

- `TextVersion` ;
- `Article` ;
- `Amendment` ;
- `Vote` ;
- `LegislativeEvent` ;
- `DebateReference` ;
- `ReportReference`.

Puis intégrer :

- [ ] versions successives du texte ;
- [ ] amendements, auteurs, objet et sort ;
- [ ] scrutins publics et positions de vote ;
- [ ] rapports de commission ;
- [ ] débats en séance ;
- [ ] texte définitivement adopté et, lorsqu'elle existe, décision du Conseil constitutionnel ;
- [ ] loi promulguée sur Légifrance.

## Phase 4 — analyse des transformations

- [ ] Comparer article par article les versions successives.
- [ ] Expliquer quelles dispositions ont été ajoutées, supprimées ou modifiées.
- [ ] Relier chaque changement aux amendements et étapes correspondants lorsque la donnée le permet.
- [ ] Afficher systématiquement la version et la date analysées.
- [ ] Ajouter les vues « ce que disait le texte initial » et « ce que dit la version actuelle ».
- [ ] Ajouter un mode « comprendre la controverse » séparant contenu du texte, arguments favorables, arguments opposés et éléments vérifiables.

## Phase 5 — de la loi à l'action publique

Faire évoluer le dossier législatif vers un `PublicActionDossier` capable de relier :

- annonce ou objectif déclaré ;
- texte proposé ;
- parcours parlementaire ;
- décision applicable ;
- textes réglementaires d'application ;
- financement prévu ;
- budget voté ;
- exécution constatée ;
- indicateurs de résultat ;
- évaluations officielles.

Le module finances publiques devient alors un moteur spécialisé appelé par ces dossiers pour remettre les montants en perspective et distinguer prévision, autorisation et exécution.

## Garde-fous IA

Le chat dédié à un dossier doit :

- considérer l'identité du dossier comme un contexte d'orientation fourni par le backend ;
- rechercher et lire les sources officielles avant toute affirmation juridique substantielle ;
- citer uniquement des preuves effectivement lues ;
- distinguer proposition, amendement, vote, décision, promulgation et mise en œuvre ;
- attribuer explicitement une affirmation à son auteur lorsqu'il s'agit d'un argument politique ;
- répondre `insufficient` lorsqu'une conclusion n'est pas établie ;
- ne jamais présenter la synthèse du modèle comme une source.

## Qualité et validation

Chaque phase doit conserver :

- tests unitaires sans réseau ;
- fixtures représentatives des formats officiels ;
- tests de non-régression sur la provenance et les statuts ;
- tests Flask du parcours accueil → dossier → chat ;
- validation des citations côté backend ;
- benchmark futur sur fidélité claim → preuve, version correcte du texte et refus correct ;
- `ruff check .` et `pytest` verts avant fusion.
