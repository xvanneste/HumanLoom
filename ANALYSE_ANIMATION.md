# ANALYSE_ANIMATION — galerie d'animations, retargeting et rig facial (analyse préalable, rien n'est codé)

Date : 2026-11-22. Demande de l'utilisateur : galerie d'animations style Mixamo, retargeting, rig facial inspiré de Rain v3.4, export Unreal, dans HumanLoom. Rôle : j'analyse, la session de dev implémente lot par lot sous mon contrôle. **Toutes les mesures ci-dessous viennent de lectures seules** (Blender 5.2 headless, copies dans le dossier temporaire ; aucun fichier source modifié, aucun fichier de l'utilisateur ouvert dans sa session Blender).

## 1. La bibliothèque `Unreal_Animations_Library.blend` (mesuré)

- 1,6 Go, écrite par Blender 5.2.44, 1 scène, **2 046 actions**, 22 armatures, 23 maillages, 100 matériaux, 24 collections. Un outil de l'utilisateur (« UALM », texte `UALM_State`) l'a produite à partir d'un export Unreal (`inventory.json`, `manifest.json`, `export_report.json` : 1 901 exportées + 145 inchangées, 0 échec).
- **Chaque action porte déjà ses métadonnées** (propriétés personnalisées `ualm_*`) : `ualm_id` (chemin Unreal), `ualm_name`, `ualm_category` (dossier Unreal, ex. `Characters/UEFN_Mannequin/Animations/Idle`), `ualm_family`, `ualm_skeleton`, `ualm_flags` (`root_motion`, `additive`, `retargeted`), `ualm_fps`, `ualm_fp`/`ualm_digest` (empreintes). L'index et les catégories peuvent donc être construits **sans ouvrir le .blend** (lire `inventory.json`, 2 Mo) ou en listant les noms d'actions (17 s via `libraries.load(link=True)`).
- **Répartition par squelette** : UEFN Mannequin **1 879 (92 %)**, 88 os ; MetaHuman corps 89 (341 os) ; RIGIPO UE5 38 (88 os) ; UE5 Mannequins (Manny/Quinn) 28 (150 os) ; Echo 9 (134 os) ; **MetaHuman visage 2** (874 os) ; capuche 1.
- Fréquence : 30 i/s pour 2 014 actions, 24 pour 25, 60 pour 7. Durée médiane 3,8 s (0,03 à 25 s), max 750 images. **Root motion : 1 795 actions (88 %)**. Additives : 37 (36 `ROTATION_OFFSET_MESH_SPACE`, 1 `LOCAL_SPACE_BASE`). Retargetées : 107. Types non pris en charge côté export : blendspaces (15) etc.
- **Structure d'une action** (Blender 5.2 : actions à emplacements/couches, **pas de `action.fcurves`**) : 1 emplacement `Armature` (type OBJECT), canaux denses `location` + `rotation_quaternion` + `scale` pour **chaque os** (ex. 90 os × 10 = 900 courbes). Elles sont **sans cycle** (`use_cyclic` faux) : la boucle vient de `ualm_flags`/du nom, à déterminer. Unités : les os de la bibliothèque sont en **centimètres** (têtes à z≈160) ; HumanLoom est en mètres.
- **Pas de catalogue facial utilisable** : seulement 2 actions « visage » (correctifs RBF du cou sur 874 os MetaHuman), **aucune bibliothèque d'expressions**. La « Facial Animation Gallery » de la demande n'a donc pas de source dans cette bibliothèque : les expressions seraient à créer.
- **Avertissements de familles dans `UALM_State`** : un même nom de squelette existe en plusieurs « familles » aux poses de repos différentes (ex. UE5 Mannequin v2 : 156 positions d'os, 108 directions, 107 rolls différents ; MetaHuman : jusqu'à 341 positions). Conséquence directe : **appliquer une action sur un autre rig par nom d'os ne suffit pas**, la pose de repos doit être comparée (rôle du retargeting).
- Piège d'environnement : charger **plusieurs** types de blocs d'un coup (22 armatures + 10 actions, ou avec objets) a fait planter Blender 5.2 (`EXCEPTION_ACCESS_VIOLATION`) ; charger les blocs séparément ou **une action à la fois** fonctionne (vérifié sur 5 actions et 22 armatures). À respecter dans le code (une action par chargement, dans un processus séparé pour l'analyse).

## 2. Rain v3.4 (`C:\Users\xvann\Downloads\Rain v3.4.zip`, 68,7 Mo, extrait dans un dossier temporaire)

- Fichier `rain_v3.4.blend` (écrit en 5.2.45), **licence CC-BY 4.0, Blender Studio** (texte `ReadMe.txt` dans le fichier). Attribution obligatoire si une donnée est reprise ; une simple lecture ne l'exige pas.
- **Ce n'est pas un rig standard ni Rigify** : généré par **CloudRig** (`is_generated_cloudrig`, texte `cloudrig.py` embarqué qui ne s'exécute qu'avec l'exécution automatique de scripts). `RIG-rain` : **2 166 os**, 70 collections d'os, 392 os de déformation, **519 pilotes**, **2 247 propriétés personnalisées d'os**, contraintes : ACTION 457, COPY_ROTATION 525, DAMPED_TRACK 511, COPY_LOCATION 352, STRETCH_TO 335, ARMATURE 416, TRANSFORM 78, etc. Affichage en os bendy. Taille : 1,616 m.
- **Visage** : 1 585 os de nom facial (Lip, Cheek, JawLine, LaughLine, Teeth, Tongue…), collections « Face Main / Secondary / Tweak / Mechanism / Deform / BBone Grid / Lattices », mécanisme de paupières collantes (« Sticky Eyelid »), os de contrôle + os BB/TAN/AIM (bendy bones). Géométrie du visage séparée : `GEO-rain-head` 6 395 sommets, **25 clés de forme** et 20 pilotes, modificateurs ARMATURE + LATTICE + CORRECTIVE_SMOOTH ; corps `GEO-rain-body` 10 256 sommets, 72 clés, 69 pilotes ; yeux, cils, dents, langue, gencives = objets séparés (`GEO-rain-gums_*`, `tongue`…). 19 actions (poses).
- **Conséquence** : le rig facial de Rain est un rig de production lié à **sa** topologie (6 395 sommets de tête). Il ne se « transfère » pas à un autre visage en un clic : il faudrait reporter 1 585 os, 457 contraintes ACTION et 519 pilotes avec des poids calculés sur le maillage de HumanLoom. À reprendre comme **modèle de conception** (contrôles principaux/secondaires/tweak, paupières collantes, bendy bones, poses par actions) et **non comme données**, sauf décision explicite (CC-BY à valider selon D-25).

## 3. HumanLoom aujourd'hui (rappel)

- **Aucun squelette** : corps = maillage natif piloté par le groupe de nœuds `HL Human` (10 582 sommets, topologie **fixe** → des poids de peau écrits une fois restent valides quelle que soit la morphologie). Rig prévu à l'étape 11 du plan (Rigify), non commencé. Pas de clés de forme sur le corps (ajoutées seulement sur les yeux). Les repères automatiques existent (étape 7 partielle).
- Donc **le chemin critique est : un squelette sur le corps natif**. Sans lui, ni preview, ni application, ni retargeting ne sont possibles.

## 4. L'image de référence

C'est l'interface web **Mixamo** : barre de titre sombre, à gauche une grille de 6 colonnes de vignettes (pose représentative, nom dessous) avec champ de recherche et filtre, à droite une vue 3D du personnage en animation, un bouton principal orange (« Download »), puis des paramètres sous forme de curseurs (intensité, espacement des bras, trim, FPS…). Thème sombre, accent orange. Dans Blender : la grille de vignettes est réalisable avec `bpy.utils.previews` + `template_icon_view` ou une `UIList`/grille de `template_preview` dans la barre latérale ; une vraie disposition deux volets à la Mixamo n'est pas réalisable dans un panneau de la vue 3D (le volet 3D est la vue 3D elle-même). La couleur d'accent suit le thème de l'utilisateur (non modifiable proprement par un addon).

## 5. Écarts critiques avec le prompt (esprit critique)

1. **Ordre** : la demande place la galerie avant le rig. Dans les faits la galerie (index, miniatures) ne dépend pas du rig, mais **l'application** dépend du squelette : il faut un rig corps d'abord.
2. **Meilleure architecture pour 92 % des animations** : donner au corps HumanLoom un squelette **compatible UEFN/UE5 Mannequin** (mêmes noms d'os, même hiérarchie, 88 os) dimensionné d'après les repères. 1 879 animations s'appliquent alors **par nom**, sans moteur de retargeting ; le retargeting complet ne sert qu'aux autres rigs (Rigify, Mixamo, MetaHuman). Cela sert aussi l'export Unreal. À valider par prototype (orientations/rolls d'os UE à reproduire ; l'avertissement « bone rolls differ » le montre).
3. **Retargeting « universel »** : à ne pas promettre. Sources de risque mesurées : familles de squelettes à repos différents, unités cm/m, root motion (88 %), os twist. Un retargeting par nom + correction de pose de repos + échelle racine est réaliste ; un mapping automatique pour des rigs arbitraires donne des résultats inégaux (à afficher comme tel).
4. **Rig facial Rain** : non transférable tel quel (voir §2). Un rig facial HumanLoom doit être conçu pour **notre** maillage (poids sur topologie fixe, donc faisable), en s'inspirant de la structure de Rain. **Décision d'architecture à prendre** : visage par os (comme Rain/MetaHuman) ou par clés de forme (ARKit 52) ; le corps étant un maillage de nœuds sans clés, les clés devraient être calculées sur un maillage figé. Pas de source d'expressions dans la bibliothèque : ces poses seraient à créer.
5. **Licence (point à traiter avant tout)** : ces animations proviennent de contenu Unreal (Game Animation Sample, mannequins Epic, MetaHuman). Les licences de contenu d'Epic limitent en général l'usage à des projets Unreal ; **je ne peux pas conclure ici** (à vérifier sur la licence exacte). Règle proposée : **rien de la bibliothèque (animations, miniatures, index, noms) n'entre dans le dépôt public ni dans le paquet** ; l'extension lit la bibliothèque **locale** de l'utilisateur, les miniatures/index sont dans un cache utilisateur hors dépôt.
6. **Périmètre** : le prompt couvre ~10 lots (galerie, preview, retargeting, visage, mixeur NLA, export Unreal, mixage facial…). C'est le plan F4/F5/F7 + étape 11 du plan existant. Un lot à la fois, avec critères mesurés, comme pour le schéma 10.
7. **Test Unreal** : non faisable ici (environnement Unreal non utilisé par moi) ; un export FBX valide ne prouve pas la compatibilité (la demande le dit aussi).

## 6. Plan de lots proposé (à valider par l'utilisateur)

| Lot | Contenu | Critères d'acceptation (à chiffrer au démarrage) |
|---|---|---|
| **A0** Analyse | ce document | fait |
| **A1** Index de la bibliothèque | module `extension/animation/` : lecture de `inventory.json` ou des noms d'actions + `ualm_*`, cache persistant (dossier utilisateur), recherche, catégories d'après `ualm_category`, favoris, chemin configurable dans les préférences ; **aucune ouverture du .blend de 1,6 Go au démarrage** | index de 2 046 entrées en < 1 s depuis le cache ; recherche < 50 ms ; catégories listées avec le nombre d'actions « sans catégorie » explicite |
| **A2** Rig corps compatible UEFN | génération du squelette 88 os sur le corps natif d'après les repères, poids de peau sur la topologie fixe, statuts Installed/Not installed, retrait propre, rig qui suit la morphologie (à re-générer ou à recaler) | rig créé sur 5 morphologies ; déformation sans artefact mesuré (volume, étirements) ; réouverture sans l'extension ; pas de double installation |
| **A3** Aperçu et application | charger **une** action (processus séparé ou `libraries.load` unique), appliquer sur le rig HumanLoom par nom avec échelle cm→m, aperçu non destructif (restauration), Add to NLA / Replace | animation de 20 actions réelles jouée ; état initial restauré à 0 résidu ; root motion préservé |
| **A4** Miniatures | génération hors processus principal (une pose représentative par action), cache disque | 100 miniatures générées ; UI fluide avec 2 046 entrées |
| **A5** Retargeting autres rigs | Rigify, Mixamo, UE5 Manny/Quinn (150 os), MetaHuman corps ; mapping auto + manuel, profils JSON, diagnostic des os non mappés | rapport d'incompatibilités ; mouvement essentiel conservé sur 3 rigs |
| **A6** Visage | décision visage par os ou clés (après revue), puis rig facial HumanLoom sur bouton « Apply Facial Rig » (statuts, validate, remove) | déformations mesurées ; pas d'installation double |
| **A7** Expressions, NLA, export | galerie d'expressions (à créer), mixeur, export FBX/UE5 | export vérifié par import dans Blender ; test Unreal si environnement disponible |

Ordre recommandé : **A1 (peut démarrer maintenant, sans toucher au rig) → A2 → A3 → A4 → A5 → A6 → A7**.

## 7. Décisions attendues de l'utilisateur

1. Valider l'ordre A1→A7 et le choix « squelette compatible UEFN d'abord ».
2. Licence : confirmer que la bibliothèque reste **locale et hors dépôt** (recommandé).
3. Rain : reprise de **conception** seulement (par défaut), ou reprise de données CC-BY (attribution dans `CREDITS.md`) ?
4. Visage : os (type Rain/MetaHuman) ou clés de forme ARKit 52, ou les deux plus tard ?
