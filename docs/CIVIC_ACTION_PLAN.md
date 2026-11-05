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
- [x] Ajouter une recherche assistée pour les formulations approximatives sans laisser le LLM inventer les candidats.
- [x] Conserver un comportement dégradé explicite si une seule source parlementaire est momentanément indisponible.
- [x] Documenter les règles de classement et de tri pour éviter toute notion opaque de « texte important ».

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

- [x] Référencer les versions successives à partir des actes et notices officiels (identifiant, titre, provenance, date, étape) ;
- [ ] Récupérer et vérifier le contenu intégral des versions avant toute comparaison d'articles ;
- [x] Amendements Assemblée : index, auteur, article, sort et détail XML à la demande ;
- [ ] scrutins publics et positions de vote ;
- [x] notices de rapports de commission liées aux dossiers et consultation HTML Assemblée lorsque disponible ;
- [ ] couverture complète des rapports Sénat et des commissions hors notices Assemblée ;
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

### Garde-fou sur les versions documentaires (novembre 2026)

La source Assemblée nationale fournit des références `texteAssocie` au sein des actes et des notices
`json/document/<UID>.json` contenant titre, provenance et dates. Une notice documentaire ne contient
**pas** le texte des articles. ACFPF expose `full_text_available=false` et un lien vers le **dossier**
officiel plutôt que de construire une URL de document non confirmée.

Les changements entre articles, l'imputation certaine aux amendements et les résumés sur le fond
ne devront pas être annoncés avant la récupération et le contrôle des contenus de chaque version.

Validation réseau : `ACFPF_LIVE_SOURCES=1 pytest -q -s tests/test_live_official_legislation.py tests/test_live_official_documents.py`.

### Scrutins publics de l'Assemblée — première intégration (novembre 2026)

L'API `GET /api/legislation/<dossier_id>/votes` expose les scrutins de la XVIIe législature
uniquement lorsque l'archive JSON officielle contient un lien exact
`objet.dossierLegislatif.dossierRef` avec l'identifiant du dossier Assemblée.
Les scrutins sans cette référence explicite ne sont **pas** imputés au dossier par
similarité de titre : une liste vide ne prouve donc pas l'absence de votes.
Les décomptes sont des données de scrutin et ne constituent pas un relevé individuel
exhaustif des positions de chaque parlementaire.

Source : https://data.assemblee-nationale.fr/travaux-parlementaires/votes
(archive `Scrutins.json.zip`, XVIIe législature).

Validation : le test `tests/test_live_official_votes.py`, lancé avec
`ACFPF_LIVE_SOURCES=1`, vérifie le format réel et exerce le parseur de production
sur une référence de dossier présente dans l'archive. L'API est une première brique :
l'interface de consultation paginée des scrutins rattachés est désormais présente
sur la fiche dossier ; la couverture du Sénat, les scrutins sans référence explicite et
les votes nominatifs restent à développer et à valider.


### Consultation des textes HTML officiels — tranche initiale (novembre 2026)

L'Assemblée nationale documente la publication individuelle des textes en HTML et PDF
sur https://data.assemblee-nationale.fr/foire-aux-questions (section
« Récupérations au fil de l'eau »). Une page réelle de la XVIIe législature,
`PIONANR5L17B2562.html`, sert de contrôle d'intégration.

`GET /api/legislation/<dossier_id>/versions/<document_uid>/text` ne télécharge
un document que si son UID est **explicitement lié au dossier** par les actes de
l'archive structurée et qu'une notice officielle de ce document existe. Le contenu
HTML est récupéré à la demande par HTTPS sans redirection, avec contrôle du type
de réponse et une limite de 2 Mio. La réponse conserve l'URL consultée,
l'horodatage UTC et le SHA-256 des octets téléchargés. Les HTML absents,
trop volumineux, invalides ou non reconnus produisent une erreur explicite.

La conversion du HTML en texte demeure une extraction mécanique ; elle ne prouve
**pas** une segmentation juridique fiable par article, la présence exhaustive des
annexes ou l'identité entre HTML et version légalement applicable. Le document
HTML source doit être ouvert pour vérifier les détails. Le booléen
`article_structure_verified=false` interdit toute comparaison automatique
prématurée. Le champ `full_text_available=false` des notices reste volontairement
inchangé, car la disponibilité est vérifiée au moment de la consultation uniquement.

Cette première tranche **ne coche pas** la récupération complète de toutes
les versions : couverture Assemblée incomplète, formats PDF, Sénat et comparaison
des articles restent à valider.

Tests : `tests/test_legislative_fulltext.py` (déterministes) et
`ACFPF_LIVE_SOURCES=1 pytest -q -s tests/test_live_official_fulltext.py`.

### Lecture depuis la fiche dossier

Les notices du dossier affichent désormais un bouton « Afficher le texte officiel »
quand une notice officielle est disponible. Le navigateur appelle alors l'endpoint
borné, affiche la transcription textuelle du HTML, son empreinte, sa date de
consultation et le lien original. La lecture n'est pas déclenchée au chargement de
la page afin d'éviter des téléchargements non demandés. Les erreurs et absences
de HTML sont affichées sans présenter la notice comme un texte intégral.

L'absence de validation de la structure article par article reste explicite et
interdit de qualifier cet affichage de comparaison juridique entre versions.


### Classement et neutralité des résultats

Le moteur `browse_legislation` applique d'abord les filtres déterministes, sans
présélection par un modèle. Pour chaque terme lexical normalisé (minuscules,
accents supprimés), une occurrence dans le titre ajoute **10** au score ;
une occurrence ailleurs dans les champs indexés (titre, procédure, étape brute,
thèmes) ajoute **3**. Les termes sans occurrence sont exclus de la recherche
lorsqu'au moins un mot-clé a été extrait. La correspondance est actuellement
une inclusion de chaîne, sans analyse sémantique ni jugement d'intérêt public.

L'ordre est décroissant : score lexical, dernière activité connue (date ISO),
titre, puis UID du dossier comme départage stable. Sans mot-clé, tous les
scores valent zéro et la dernière activité détermine d'abord l'ordre. Les
filtres s'appliquent avant la limite de 100 résultats. Les facettes utilisent
l'inventaire réellement chargé avant application des filtres. En mode assisté,
le LLM ne peut que proposer une requête ou des filtres : cette même formule
déterministe classe les dossiers retenus. Aucun élément n'est présenté comme
« important » ou prioritaire pour des raisons éditoriales.


### Votes nominatifs — première tranche

L'API `GET /api/legislation/<dossier_id>/votes/<vote_uid>/positions`
expose les identifiants officiels `acteurRef`, `mandatRef`, `organeRef`,
la position nominative publiée (`pour`, `contre`, `abstention`,
`non_votant`) et le drapeau de délégation lorsque disponible.

Ce service ne s'appuie que sur les listes `ventilationVotes.organe.groupes.groupe
.vote.decompteNominatif` de l'archive JSON officielle de l'Assemblée
nationale. Il exige le rattachement exact du scrutin par
`objet.dossierLegislatif.dossierRef` et une identité de scrutin vérifiée ;
aucun nom de député n'est fabriqué à partir des références.
Un acteur absent des listes ne doit **jamais** être qualifié d'absent,
d'abstentionniste ou de non-votant par déduction. Les incohérences
contradictoires entraînent un refus de restitution.

Validation structure réelle : test live utilisant un scrutin lié à un dossier
et la ventilation nominative publiée par l'Assemblée (XVIIe législature).
La résolution des noms depuis le référentiel des acteurs, la couverture
historique et la consultation des positions dans l'UI restent à traiter.


### Consultation des positions nominatives depuis la fiche dossier

Chaque scrutin public explicitement rattaché possède désormais une vue
à la demande des positions nominatives, paginée par lots de 50. Les listes
reprennent les identifiants officiels `acteurRef` et `organeRef`, la
position déclarée et l'éventuelle délégation. Le navigateur valide les
UID de dossier et de scrutin renvoyés par l'API avant de présenter les
résultats ; aucune interprétation politique n'est déduite.

La résolution du nom de chaque acteur depuis l'annuaire **historique**
de l'Assemblée reste une tâche distincte. Jusqu'à sa validation, les
identifiants sont préférés à des identités ou affiliations supposées.


### Résolution exacte des députés — annuaire historique officiel

Pour les positions nominatives, l'API peut résoudre `acteurRef` en
`prenom nom` uniquement après vérification d'une correspondance **identique**
de l'UID dans `json/acteur/PA....json` du jeu historique AMO30.
Source : https://data.assemblee-nationale.fr/acteurs/historique-des-deputes
(XVIIe législature, export historique des acteurs depuis la XIe législature).

L'archive est limitée en taille et mise en cache durant 24 heures. Si la
source réseau est indisponible, un cache antérieur intact peut être utilisé.
En l'absence de source exploitable, les positions du scrutin restent
accessibles : le nom est inconnu, l'UID n'est jamais remplacé par une
recherche floue ou une identité présumée. Les fichiers d'état civil
contiennent d'autres informations personnelles qui ne sont pas exposées
par cette fonctionnalité. L'appartenance à un groupe au moment du scrutin
ne doit jamais être inférée depuis les mandats contemporains.

`GET /api/legislation/<dossier_id>/votes/<vote_uid>/positions?names=1`
ajoute facultativement `actor_name` à chaque entrée résolue,
`actors_source_url` et une indication de disponibilité ; sans `names=1`,
le comportement antérieur n'est pas modifié.

Validation : `tests/test_assemblee_actors.py` et
`ACFPF_LIVE_SOURCES=1 pytest -q -s tests/test_live_official_actors.py`.


### Notices de rapports parlementaires — tranche initiale

L'export JSON `Dossiers_Legislatifs.json.zip` de l'Assemblée nationale
contient les notices de rapports (`classification.type.code=RAPP`) avec
un `document.dossierRef` explicite. ACFPF ne rattache un rapport à un
dossier que sur correspondance **strictement identique** de cet UID et
vérification du dossier lui-même dans l'archive. Le test live a établi
l'existence de notices de rapports d'origine Assemblée et Sénat dans le
même export ; la provenance documentaire est conservée et ne doit pas
être confondue avec le producteur de l'archive.

L'endpoint `GET /api/legislation/<dossier>/reports` fournit la liste
paginée des notices et leurs dates renseignées, sans construire de lien
vers une ressource dont l'adresse n'a pas été vérifiée. L'endpoint
`GET /api/legislation/<dossier>/reports/<uid>/text` utilise le lecteur
HTML officiel déjà validé seulement pour les UID d'origine Assemblée
`RAPPANR...` correctement rattachés, et refuse une URL HTML inventée
pour les rapports d'origine Sénat. Une notice ne garantit pas que le
contenu HTML soit disponible. Aucun extrait de rapport n'est une preuve
juridique du contenu applicable d'une loi.

Sources :
https://data.assemblee-nationale.fr/travaux-parlementaires/dossiers-legislatifs ;
https://data.assemblee-nationale.fr/foire-aux-questions .
Validation : `tests/test_legislative_reports.py` et
`ACFPF_LIVE_SOURCES=1 pytest -q -s tests/test_live_official_reports.py`.

La couverture de tous les rapports de commission, leur interface dédiée
et les publications du Sénat indépendantes de l'archive Assemblée
restent à compléter : la case générale « rapports de commission » n'est
pas cochée sur cette seule tranche.


### Interface de consultation des rapports

La fiche `/textes/<id>` présente les rapports publiés dans l'inventaire
officiel avec leur UID, leur date, leur provenance et leur rattachement
exact au dossier. Le bouton « Lire le rapport HTML » n'est proposé que
pour les notices d'origine Assemblée `RAPPANR...`, et charge la source
à la demande. Une erreur de disponibilité laisse accessible le dossier
officiel ; le Sénat n'est pas assimilé artificiellement à une URL
Assemblée. La transcription HTML distingue clairement rapport et droit
applicable. La couverture exhaustive des rapports de commissions est
encore limitée aux notices présentes dans l'archive vérifiée.


### Débats : références d'étapes officielles, pas de transcriptions (novembre 2026)

`GET /api/legislation/<dossier_id>/debates` expose uniquement des
**références aux étapes de séance ou lecture** déjà présentes dans la
chronologie officielle de l'Assemblée. Les doublons exacts sont éliminés ;
les étapes Sénat ne sont pas transformées en séances de l'Assemblée.
L'interface du dossier permet également de retrouver ces étapes et de
rechercher les comptes rendus via le portail officiel :
https://www.assemblee-nationale.fr/dyn/17/comptes-rendus/seance .

La source indépendante des comptes rendus existe :
https://data.assemblee-nationale.fr/travaux-parlementaires/debats .
Cependant, aucun identifiant de transcription ou d'intervention n'est
encore lié par preuve structurée à ces étapes. L'API retourne donc
`transcripts_available=false` et `transcript_verified=false`.
Ni un événement de première lecture ni sa date ne permettent d'inférer
qu'une personne donnée a pris la parole. L'étape générale « débats en
séance » reste ouverte jusqu'au raccordement des comptes rendus XML
officiels et à la vérification du lien avec chaque dossier.
