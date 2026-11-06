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
- [x] Scrutins publics Assemblée rattachés par référence exacte et positions nominatives avec identités historiques vérifiées ;
- [ ] Couverture des scrutins et positions du Sénat, et des scrutins sans référence explicite au dossier ;
- [x] notices de rapports de commission liées aux dossiers et consultation HTML Assemblée lorsque disponible ;
- [ ] couverture complète des rapports Sénat et des commissions hors notices Assemblée ;
- [x] Références aux étapes de lecture de l'Assemblée dans la chronologie, sans attribution de discours ;
- [ ] Comptes rendus intégraux des débats : identification exacte des séances et interventions associées ;
- [x] Jalons Sénat de contrôle constitutionnel et de promulgation avec références et dates officielles ;
- [ ] Texte définitivement adopté et décision intégrale du Conseil constitutionnel, lorsque publiés ;
- [ ] Texte de la loi promulguée et versions consolidées sur Légifrance (client PISTE préparé, validation réelle et habilitation manquantes).

## Phase 4 — analyse des transformations

- [x] Diff textuel expérimental de deux transcriptions HTML officielles vérifiées (sans équivalence juridique) ;
- [x] Repérage expérimental de lignes candidates d'intitulés d'articles (sans segmentation juridique certifiée) ;
- [ ] Comparer article par article les versions successives après vérification de la structure normative.
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


### Comparaison textuelle expérimentale de deux HTML officiels

`GET /api/legislation/<dossier>/versions/compare?before=<uid>&after=<uid>`
vérifie d'abord que **les deux** UID différents correspondent à des
notices existantes du même dossier structuré. Aucune URL arbitraire n'est
acceptée. Les deux sources HTML officielles sont téléchargées et validées
indépendamment ; le résultat inclut les deux URL, horodatages et SHA-256
des octets sources, ainsi qu'un diff unifié par lignes.

La comparaison est bornée (longueur, nombre de lignes et sortie). Si
les limites empêchent un diff complet, l'API refuse la comparaison plutôt
que d'en présenter une version tronquée. La fiche dossier propose un
sélecteur des versions déjà affichées et montre le diff ainsi que les
liens vers les deux documents originaux.

**Ce n'est pas une comparaison juridique article par article.** Une
différence apparente peut résulter du HTML, de sa conversion en texte ou
de sections non normatives ; aucun alignement des articles n'est
certifié, pas plus que le droit applicable. Les cases générales de la
phase 4 restent ouvertes jusqu'à validation du modèle `Article` et
du rapprochement fiable des contenus.


### Jalons vérifiés de contrôle constitutionnel et de promulgation

Les champs officiels de DOSLEG (Sénat) renseignent le résultat et la date
de la décision constitutionnelle, la date de promulgation et, le cas
échéant, le numéro de loi. ACFPF les convertit déjà en événements de
chronologie avec `source_id=senat_open_data`. L'API
`GET /api/legislation/<dossier_id>/outcomes` isole ces événements
uniquement sur les codes structurés `CONSTITUTIONAL_COUNCIL` et
`PROMULGATION`, élimine les doublons et conserve l'URL du dossier Sénat
comme provenance. La fiche dossier présente ces jalons et rappelle leur
périmètre exact.

Aucun `JORFTEXT` n'est généré par calcul à partir du numéro de loi,
ni aucune décision constitutionnelle reconstituée depuis sa date.
`legifrance_text_verified=false` et
`constitutional_decision_text_verified=false` demeurent vrais jusqu'à
la consultation directe des documents. Le statut final d'application,
les éventuelles censures partielles et les versions consolidées
demeurent **non déterminés** par ce seul export.

La consultation de Légifrance via API officielle suppose un accès
PISTE enregistré (voir https://www.data.gouv.fr/dataservices/legifrance).
Les cases générales d'intégration des décisions constitutionnelles et
du texte Légifrance restent ouvertes.


### Connecteur PISTE/Légifrance : transport préparé, contenu juridique non validé

`acfpf.data.legifrance_piste` implémente OAuth2 client_credentials, la
recherche exacte d'un numéro de loi dans le fonds LODA_ETAT à une date
donnée, des délais d'attente, des hôtes HTTPS fixes, aucune redirection
et des limites de réponse. Secrets et jetons ne sont pas retournés ;
le jeton est gardé temporairement en mémoire.

Cette brique est **optionnelle et non branchée au parcours public**
jusqu'à la validation réelle avec un compte PISTE habilité. Les réponses
brutes restent des candidats : `match_verified=false` et
`legal_text_verified=false`. La validation du LEGITEXT exact,
la consultation du texte et le suivi de sa version restent ouverts.
Les tests déterministes sont dans `tests/test_legifrance_piste.py`.
Aucun test réseau PISTE n'a été réalisé faute d'identifiants.

Sources techniques :
https://www.legifrance.gouv.fr/contenu/pied-de-page/foire-aux-questions-api ;
https://www.data.gouv.fr/dataservices/legifrance .


### Repérage expérimental des intitulés d'articles

`GET /api/legislation/<dossier>/versions/<uid>/article-candidates`
contrôle d'abord que l'UID du document possède une notice officielle
rattachée au dossier. Le HTML de l'Assemblée est téléchargé et vérifié
par le lecteur officiel existant. La réponse signale seulement les lignes
entières correspondant à un motif conservateur « Article 1er »,
« Article 2 bis », « Article unique », etc. avec leur numéro de ligne
dans la transcription textuelle et l'empreinte SHA-256 des octets source.
Le nombre de lignes et de candidats est borné ; une entrée trop longue
entraîne une erreur plutôt qu'une liste tronquée.

Le bouton de la fiche dossier propose ces repères à la demande.
`article_structure_verified=false` et
`article_verified=false` restent explicites : une rubrique peut
se trouver dans l'exposé des motifs ou une annexe, des articles peuvent
être manqués, et une ressemblance d'intitulé n'établit pas l'identité
juridique entre deux versions. Aucune comparaison article par article
ne découle encore de ce repérage.

Test sur HTML officiel réel :
`tests/test_live_official_fulltext.py` (article unique du texte
PIONANR5L17B2562) ; tests déterministes :
`tests/test_legislative_articles.py`.


### Garde-fou déterministe des réponses aux dossiers législatifs

Le backend marque les questions de chat rattachées à un dossier avec le
contexte de confiance `Contexte de dossier législatif fourni par le backend ACFPF.`.
Pour ces questions, le validateur final impose **au moins une citation**
correspondant à une unité d'un document officiel effectivement ouvert et
lu par le moteur live (`Citation.evidence_id`), et non une simple série
statistique `S...` ou une notice de recherche. Si le modèle ne fournit
que des citations statistiques, la réponse est convertie en
`status=insufficient`, sans conserver son affirmation non étayée.

Les questions financières indépendantes restent autorisées à utiliser
les séries statistiques déterministes. Ce contrôle est une **condition
nécessaire, pas suffisante** : il ne prouve pas à lui seul que chaque
affirmation de la réponse est supportée par le bon extrait, la bonne
version ou le bon statut juridique. Il faudra un benchmark
`claim → preuve` et une validation par assertion pour aller plus loin.
Tests : `tests/test_civic_grounding_gate.py`.


## Dépendances vérifiées restant bloquantes (état de novembre 2026)

La phase 3 n'est **pas terminée** : les versions complètes et normatives,
les transcriptions de débats, les rapports Sénat autonomes, les décisions
constitutionnelles intégrales et la consultation Légifrance restent incomplets.
Le client PISTE ne peut faire l'objet d'un test bout-en-bout authentifié sans
identifiants habilités. Aucune case normative ne doit être cochée sur la base
de notices, d'intitulés heuristiques ou d'un diff HTML.

La phase 4 n'est **pas terminée** : les deux fonctionnalités expérimentales
ci-dessus ne suffisent ni à aligner les articles, ni à attribuer des
modifications à des amendements, ni à comparer le texte proposé avec le
droit applicable. Il faut une structure d'articles validée par comparaison
sur corpus officiel et un contrôle exact des versions/dates.

La phase 5 reste **entièrement à intégrer** : relier une disposition applicable
aux décrets d'application, aux autorisations et exécutions budgétaires puis
aux indicateurs de résultat demande des identifiants et sources distincts,
avec tests de non-confusion et provenance documentée.

La CI actuelle vérifie Ruff, la syntaxe et les tests JavaScript,
les tests Python déterministes ainsi que les tests d'intégration
sur les archives publiques de l'Assemblée. Elle ne remplace pas
des tests directs de l'API PISTE authentifiée ni un audit de fidélité
`assertion → passage → version → date`.


### Socle `PublicActionDossier` : couverture sans liens supposés

Le module `acfpf.public_action` fournit un modèle explicite des jalons
du projet, de l'examen parlementaire, du contrôle constitutionnel et
de la promulgation jusqu'au texte applicable, aux décrets, au financement,
à l'exécution, aux indicateurs et aux évaluations. La nouvelle API
`GET /api/legislation/<dossier_id>/public-action` et la fiche dossier
montrent **quelles catégories possèdent des métadonnées officielles
identifiables** et lesquelles restent non vérifiées.

Seuls les événements dont `source_id` correspond à une référence
Assemblée ou Sénat officielle du dossier contribuent à cette couverture.
La date initiale fusionnée du dossier n'est pas attribuée à l'une des chambres
sans événement explicite de dépôt : elle peut provenir de plusieurs sources.
Les événements Sénat codés `PROMULGATION` ou
`CONSTITUTIONAL_COUNCIL` sont conservés comme jalons, mais jamais
comme texte normatif validé. Pour toutes les étapes,
`normative_text_verified=false` ; les relations entre loi et
budget/évaluation restent explicitement à `false`.
Cette API ne reconstitue aucun lien de causalité ni aucun financement
par rapprochement approximatif.

Tests : `tests/test_public_action.py`. Il s'agit du **socle de données
de phase 5**, non de l'intégration des textes réglementaires, du
financement, de l'exécution ou des évaluations ; ces tâches restent ouvertes.


### Audit de transport des débats Syceron (XVIIe législature)

La page officielle
https://data.assemblee-nationale.fr/travaux-parlementaires/debats
référence l'archive XML `syseron.xml.zip`. Son URI publiée avec le
segment `/17/VP/` renvoie actuellement HTTP 404 ; la variante
`/17/vp/` a répondu HTTP 200, mais le transfert complet de l'archive
annoncée à environ 61 Mo a été interrompu en CI avant vérification du ZIP.

La CI n'exécute donc qu'un **test léger de transport** sur l'adresse
en minuscules, avec inspection de la signature ZIP et des en-têtes.
L'audit réel du schéma XML est conservé derrière
`ACFPF_LIVE_DEBATES_FULL=1`, volontairement exclu de la CI standard
jusqu'à l'établissement d'une stratégie de téléchargement intègre
et reproductible. Aucun identifiant d'intervention, de séance ou de
dossier n'a pu être validé à partir de cet essai : les comptes rendus
intégraux restent non intégrés, sans rattachement inventé.


### Acquisition résiliente de l'archive Syceron

`acfpf.data.assemblee_debates.download_debate_archive` utilise les
plages d'octets HTTP 206 effectivement annoncées par le serveur
officiel (ZIP de 61 335 085 octets lors du contrôle de novembre 2026).
Chaque bloc est demandé par `Range`, et les bornes, le total ainsi que
le nombre d'octets sont contrôlés avant assemblage. Les blocs
incomplets sont retentés et un ZIP entier n'est adopté en cache
qu'après vérification des membres, de la taille décompressée maximale
et des CRC. L'ancien cache intègre peut être conservé en cas d'échec
réseau, avec `from_cache=true`.

Les tests déterministes de transport sont dans
`tests/test_assemblee_debates.py`. Un premier audit live complet a
**réussi** : archive de 61 335 085 octets, 656 comptes rendus XML et
contrôle CRC intégral. Le fichier `compteRendu` possède des métadonnées
`uid`, `seanceRef`, `sessionRef` et `dateSeance`.
L'audit approfondi reste opt-in via
`ACFPF_LIVE_DEBATES_FULL=1`, car cette acquisition réseau coûteuse
ne doit pas ralentir toutes les PR. La présence de `seanceRef` ne suffit
pas à elle seule à relier une séance à un dossier ni à attribuer des
propos à un texte ; cette jointure doit être vérifiée séparément.
