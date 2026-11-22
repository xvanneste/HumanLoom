# ANALYSE_RIG_VISAGE — comment construire le rig du visage de HumanLoom (Blender seulement)

Date : 2026-11-22. Périmètre : **un addon Blender** ; aucune contrainte d'export Unreal sur le rig (D-30). Sources lues en lecture seule : `rain_v3.4.blend` (CloudRig, CC-BY 4.0 Blender Studio ; scripts non exécutés) et les armatures de la bibliothèque d'animations (squelette UEFN 88 os, MetaHuman Face Archetype 843 os faciaux, 2 actions faciales). Tout ce qui est chiffré ci-dessous est mesuré ; ce qui est une proposition est dit tel quel. Rien n'est codé.

## 1. Comment le visage de Rain fonctionne (mesuré)

Trois couches empilées :

1. **Contrôles (peu d'os, l'utilisateur les manipule)** : 21 os de contrôle « actionneurs » (`ACT-*`, `MSTR-*`, `TGT-*`) : coins des lèvres (L/R), roulement des lèvres haute/basse, moue (`Sneer`), joues intérieure/extérieure, bague des yeux haute/basse, paupières haute/basse, sourcils, mâchoire, tête haute/basse, cible du regard. Chacun a un **`LIMIT_LOCATION` serré** (ex. coin de la lèvre : −1,5 à +3 cm en X ; paupière haute : −4 à +2 cm en Y ; joue extérieure : 0 à 4 cm) : le mouvement de la commande est borné.
2. **Poses déclenchées par contrainte ACTION** : 457 contraintes ACTION lisent la position/rotation d'un contrôle (canal, min, max) et **évaluent une action de pose** (19 actions : `Rain_Lips_Wide`, `Rain_Lips_UpDown`, `Rain_Lips_Corner_Up+Wide`, `Rain_Eyebrows`, `Rain_Eyelid_Upper/Lower`, `Rain_Eyering_*`, `Rain_Cheeks_Inner/Outer`, `Rain_Sneer`, `Rain_Lips_Roll_*`, `Rain_Head_Lower`…) sur **les os de déformation** (mode `AFTER`, trames 0–40 pour 427 contraintes, 0–20 pour 30). Une action de pose contient de 36 à 238 courbes (location/rotation/échelle d'os de déformation). C'est une **« bibliothèque de formes en os »** : chaque pose est le déplacement (local) de dizaines d'os de déformation, mélangé linéairement par la valeur du contrôle. L'ensemble est l'équivalent « os » des clés de forme.
3. **Déformation** : 511 os de visage au total dont **279 os de déformation** (272 `DEF-*`) ; **253 os à 10 segments bendy** (+10 à 8 segments) pour des lèvres, paupières et sillons lisses avec peu d'os ; 160 os `BB-*` (poignées de bendy bones), 9 `GRP-*` (groupes), 4 `SK-*` (clés de forme pilotées par la position d'un os, ex. `Cheek_Puff`). Le maillage de tête (6 395 sommets) a **279 groupes de sommets, en moyenne 8,5 influences par sommet (max 34)** : le skinning est très dense. S'y ajoutent **25 clés de forme** sur la tête (`mouth_open`, `Smile.L/R`, `LipsWide`, `CheekPuff`, `EyelidsClose`…) pilotées par des pilotes à expressions simples (ex. `Z*20`, `userY*50`) lisant les os de contrôle, un **lattice** (`Lattice_Head_Main`) et un modificateur Corrective Smooth.
4. **Comportements** : paupières et orbites « collantes » (`sticky_eyelids`, `sticky_eyesockets` : influences de 0,1 à 0,3 par rangée de paupière, via pilotes), `teeth_follow_mouth`, `eye_target_parents`, `head_hinge`/`neck_hinge` (propriétés sur un os `Properties_Face`).

**Ce que ça implique** : le visage de Rain n'est pas « 21 os qui déforment la peau », c'est 21 commandes → 19 poses → ~280 os de déformation → 6 395 sommets très densément pondérés. La qualité vient surtout de la finesse de ces poses et de ces poids, tous modelés à la main pour **cette** tête.

## 2. Ce que montrent les autres rigs disponibles

- **Squelette UEFN/UE5 Mannequin** : **aucun os de visage** (88 à 150 os, `head` en bout de chaîne). Il fixe seulement l'attache : un visage s'attache sous `head`.
- **MetaHuman Face Archetype** (bibliothèque) : 843 os `FACIAL_*` sous `FACIAL_C_FacialRoot` (parent `head`), organisés par série (`12IPV_LipUpper` 48, `12IPV_LipLower` 48, `NasolabialB` 30, `Forehead*`, `Nostril`, `Chin`, `Eyesack`, `Jawline`, dents, langue, cheveux). Pilotage par courbes d'expression (`CTRL_expressions_*`, proches d'ARKit) évaluées par un solveur RBF ; **2 actions seulement** (correctifs du cou). Utile comme **carte des zones à couvrir** et comme repère de nommage, pas comme données.
- Aucun de ces rigs n'est un rig « générique » transférable tel quel : ils sont liés à leur maillage et à leurs poids.

## 3. Ce que HumanLoom impose (contraintes propres)

- Le corps est un **maillage natif piloté par des nœuds de géométrie** (10 582 sommets, **topologie fixe**), la forme du visage **change** avec le sexe, l'âge et 20+ contrôles faciaux (amplitudes du lot 4). Les os doivent suivre la morphologie (à recaler quand elle change) ; des poids écrits une fois restent valides (topologie fixe).
- **Pas de bouche intérieure** : ni dents, ni langue, ni gencives (I-42, plan « dents/langue » encore à faire). Les os et poses de mâchoire/dents/langue de Rain n'ont donc rien à déformer tant que ces maillages n'existent pas ; les yeux, eux, existent (2 objets, 65 clés et pilotes déjà branchés).
- Les clés de forme sur le maillage d'**entrée** (`HL Human Base`) sont évaluées **avant** les nœuds : on peut donc ajouter des clés de forme faciales qui se **somment** au corps morphé sans casser le groupe de nœuds (à vérifier par prototype avant de promettre).

## 4. Trois approches possibles (possibilités et limites)

| | A. Portage du système de Rain (os + poses ACTION) | B. Clés de forme faciales (ARKit 52) sur le maillage d'entrée | C. Hybride (recommandé à valider) |
|---|---|---|---|
| Principe | recaler ~280 os de déformation sur la tête de HumanLoom, reporter les poids, réutiliser les 21 contrôles et les 19 poses | 52 clés (ou jeu réduit) sculptées/dérivées, pilotées par propriétés (ARKit) | contrôles et expressions en clés ; os seulement pour yeux, paupières et mâchoire (articulations réelles) |
| Avantages | qualité de mouvement de Rain (bendy, lèvres roulées) ; poses prêtes ; contrôles ergonomiques | simple, robuste, compatible ARKit/Live Link, pas de skinning dense, suit la topologie fixe | simplicité des clés + vraies rotations des yeux/mâchoire ; moins d'os |
| Limites mesurées/prévisibles | recalage non rigide de 280 os vers une autre tête (proportions et topologie différentes) ; poids très denses (8,5 influences, max 34) peu transférables sans artefacts ; poses calibrées pour la tête de Rain ; mâchoire/dents inutilisables sans dents ; coût de rig ×10 | clés **additives** : plus de 2 clés actives = artefacts possibles ; il faut les créer (sculpt ou génération depuis les 25 clés de Rain, forme à transférer) ; ne suit pas parfaitement la morphologie extrême | deux systèmes à maintenir |
| Compatibilité bibliothèque d'animations | os `head` + point d'attache | n'utilise pas de squelette de visage | les os restent sous `head` |
| Risque principal | **qualité du transfert des poids** (à mesurer) | qualité des clés (travail de sculpture ou de transfert) | complexité |

Dans tous les cas : la **bibliothèque des 19 poses** de Rain (et ses 25 clés) est la matière première à réutiliser (CC-BY, attribution). Reprendre le mécanisme (« contrôle → pose par contrainte ACTION ») est la partie la plus portable : il ne dépend pas du maillage, seulement des os que les poses animent.

## 5. Ce qu'il faut mesurer avant de choisir (propositions de tests, à faire par le dev)

1. **Correspondance de têtes** : définir sur la tête de Rain et celle de HumanLoom un jeu commun de repères (yeux, coins de bouche, centre des lèvres, nez, menton, oreilles, sourcils) ; mesurer l'écart de proportions (rapports faciaux) entre les deux ; si l'écart dépasse un seuil, le portage direct est exclu.
2. **Recalage des os** : déformation non rigide (RBF/thin-plate) des positions d'os de Rain vers HumanLoom ; vérifier que les os restent dans le volume du visage (distance à la surface) et que les orientations locales sont conservées (sinon les poses se déforment).
3. **Transfert des poids** : projection des poids de Rain sur le maillage de HumanLoom, lissage, normalisation ; mesurer les artefacts en appliquant les 19 poses (étirement d'arêtes, volume, faces retournées), comme pour les amplitudes du lot 4.
4. **Prototype hybride** : une clé de forme faciale sur `HL Human Base` + le groupe de nœuds, pour confirmer l'addition (et l'impact sur le temps d'évaluation, critère 33 ms).
5. **Yeux** : brancher le regard sur les yeux existants (os de visée + pilotes) ; vérifier les paupières avec les clés de paupière existantes (`eyelid_aperture`).
6. **Intégrité du corps** : l'ajout du rig ne change pas la forme du corps ni la référence figée (D-19).

## 6. Ordre recommandé (Blender seulement)

1. Rig du **corps** compatible UEFN (A2) — prérequis de tout.
2. **Prototypes de mesure du visage** (section 5) avant de choisir entre A, B ou C ; rapport chiffré à l'utilisateur.
3. **Dents, langue, gencives** (lot 10 du plan) avant tout rig de mâchoire/bouche.
4. Rig du visage selon l'approche retenue, bouton « Apply Facial Rig », statuts (Not installed/Installed/Needs configuration/Error), validation, retrait propre.
5. Galerie de poses faciales (les 19 poses de Rain adaptées, plus nos expressions), mapping ARKit 52.

## 7. Limites générales à annoncer à l'utilisateur

- Aucune garantie que le visage de Rain s'adapte à toutes les morphologies de HumanLoom ; la mesure du point 5.1 tranche.
- Le rig facial ne fera pas de miracle sur un visage dont la topologie n'a pas de boucles autour des yeux et de la bouche adaptées au skinning ; à vérifier sur le maillage de base de HumanLoom (boucles des lèvres et des paupières).
- Aucune animation faciale n'est fournie par la bibliothèque (seulement 2 actions de correctifs du cou) : les expressions viennent des 19 poses de Rain, de nos propres poses, ou des animations que l'utilisateur importe lui-même.
- Licence : CC-BY 4.0 pour tout ce qui vient de Rain (attribution, mention des modifications, sous-ensemble de données seulement). Pas un avis juridique.
