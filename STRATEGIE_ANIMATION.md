# STRATEGIE_ANIMATION — la meilleure voie pour atteindre l'objectif (synthèse de l'analyste, à valider)

Date : 2026-11-22. Objectif de l'utilisateur : dans **HumanLoom (addon Blender)**, créer un personnage, lui donner un rig corps et visage, parcourir une galerie d'animations (bibliothèque **locale** de l'utilisateur, non redistribuée), les prévisualiser et les appliquer avec auto-mapping modifiable, combiner animations corps et visage. Contraintes actuelles : D-22 à D-31 de `SUIVI_REPRISE.md` (pas de redistribution des animations, nos propres os, mapping, visage inspiré de Rain v3.4 CC-BY, Blender seulement).

Cette synthèse retient, pour chaque problème, **la solution la plus robuste d'après les mesures** (`ANALYSE_ANIMATION.md`, `ANALYSE_RIG_VISAGE.md`, `CONCEPTION_A2_RIG.md`), les alternatives écartées et ce qui reste à prouver. Les choix marqués « à valider par mesure » ne sont pas des certitudes.

## 1. Architecture d'ensemble : trois couches indépendantes

| Couche | Rôle | Dépend de |
|---|---|---|
| **Données de la bibliothèque** (lecture seule, locale) | index, métadonnées, une action à la fois | rien du rig |
| **Retargeting** (calcul pur, sans bpy dans le cœur) | convertit une action source en action pour NOS os | mapping + squelette |
| **Rig HumanLoom** | corps (squelette propre) et visage (expressions) | corps natif à topologie fixe |

Intérêt : chaque couche se teste seule, hors interface, sur des données synthétiques (la bibliothèque n'étant pas dans le dépôt, ses tests sont « IGNORÉ » si elle est absente).

## 2. Corps : squelette de déformation propre + retargeting analytique

**Choix** : un squelette de **déformation** simple (≈ 90 os, nos noms `.L/.R`, repères locaux par règle) ; les animations s'appliquent **directement dessus**. Les contrôles d'animateur (IK, FK/IK) viendront plus tard par-dessus (Rigify ou maison), sans changer la couche d'animation.

**Retargeting par calcul, pas par contraintes** (choix principal) :
- Alternative écartée : contraintes « Copier rotation/transformation » depuis une armature source gardée dans la scène, puis `bake`. Inconvénients : une armature source par famille à charger (la bibliothèque fait 1,6 Go, plantages mesurés au chargement groupé), bake lent (secondes par animation), état de scène à nettoyer, peu testable.
- **Solution retenue** : pour chaque animation, charger l'action seule (une à la fois), lire ses courbes, puis calculer **en espace de l'armature** (cinématique directe vectorisée avec numpy) l'orientation posée de chaque os source, la transférer à l'os cible par la correction de repos `R_pose_cible = R_pose_source · R_repos_source⁻¹ · R_repos_cible`, repasser en local par la chaîne cible, et écrire une **nouvelle action** pour nos os. Le calcul est déterministe, rapide (88 os × quelques centaines d'images), sans armature source, mis en cache par (action, profil de mapping).
- **Translations** : échelle par le rapport des hauteurs de bassin (et non seulement cm→m) ; os IK de la source (`ik_*`) ignorés puisque la cinématique directe porte déjà le mouvement (à vérifier par mesure).
- **Root motion** (aucun os racine dans la bibliothèque, mesuré) : **notre squelette a son propre os `root`**. Un « gestionnaire de root motion » en extrait le déplacement horizontal du bassin (option : sur place / conserver / extraire vers `root`), de façon déterministe.
- **Qualité mesurable** : erreur de position des articulations en espace monde entre la source mise à l'échelle et le résultat (en % de la stature), glissement des pieds, continuité des boucles. Critères chiffrés à fixer au démarrage de A3.
- Aperçu non destructif : l'action convertie est assignée temporairement, l'état initial restauré ; « Ajouter au NLA » / « Remplacer » ensuite.

## 3. Mapping : ontologie propre + auto-mapping en trois niveaux

1. **Noms** : normalisation (espaces de noms, `_l`/`Left`/`.L`, casse, séparateurs) + dictionnaire de synonymes anatomiques **générique**.
2. **Structure** : appariement des chaînes (colonne, membres, doigts) par profondeur et nombre d'enfants, pour les rigs aux noms inconnus.
3. **Géométrie** : positions de repos normalisées par la stature, en dernier recours.
Chaque os reçoit un **score de confiance** ; l'interface montre les appariements douteux ; l'utilisateur corrige à la main ; le profil se sauvegarde dans son dossier. Les os sans équivalent sont listés, jamais ignorés en silence. **Aucun profil de rig tiers n'est livré** (ils contiendraient des noms de tiers) : ils sont produits à l'exécution.

## 4. Galerie : un panneau maison, plus l'Asset Browser pour les favoris

- **Choix** : panneau latéral « Animation Gallery » (grille de vignettes paginée + recherche instantanée, déjà indexée en moins de 2 ms), car la bibliothèque de 2 046 actions ne doit pas être dupliquée (1,6 Go) et l'index/ la pagination restent fluides. L'image de référence (Mixamo) est approchée par : grille de vignettes à gauche, aperçu dans la vue 3D, paramètres (vitesse, trim, échelle) en dessous ; un vrai écran à deux volets n'est pas réalisable dans un panneau.
- **Complément natif** : « Publier les favoris dans l'Asset Browser » (actions converties en assets avec catalogues et vignettes, dans une petite bibliothèque d'assets de l'utilisateur) : glisser-déposer natif, sans dupliquer toute la bibliothèque.
- **Vignettes** : générées hors du processus principal (rendu simple d'une pose représentative sur un mannequin neutre), cache disque, génération en tâche de fond par lots. À mesurer : temps par vignette sur 100 actions.

## 5. Visage : changer de méthode (proposition, à valider par mesure)

**Constat** : le visage de Rain est un système de **~280 os de déformation et 457 contraintes**, très ajusté à sa tête (6 395 sommets, ×1,5 plus large que la nôtre). Le porter tel quel exige un recalage de 476 os, un transfert de poids très denses et le remise à l'échelle des 19 poses : coûteux et risqué (prototypes : 8 repères insuffisants, 21 mm d'erreur en validation croisée).

**Solution proposée : extraire de Rain le *résultat* des poses, pas son *rig*.**
1. **Hors ligne, dans `tools/`** : appliquer chacune des 19 poses (et ses 25 clés de forme) à pleine valeur sur la tête de Rain, avec son propre rig, et enregistrer les **déplacements de sommets** (un « blendshape » par pose).
2. **Transfert de déformation** vers la tête de HumanLoom (« deformation transfer », Sumner & Popović 2004, méthode classique pour reporter des expressions entre maillages de topologies différentes) : correspondance dense Rain ↔ HumanLoom par recalage non rigide guidé par ~22 repères, puis transport des déplacements (mise à l'échelle par l'étirement local).
3. **Au runtime** : ces déplacements deviennent des **couches d'expression dans le groupe de nœuds `HL Human`** (comme nos 46 contrôles de morphologie, preuve T5 : addition exacte, coût mesuré nul), exposées sur la façade `humanloom` : animables par images clés, pilotables, sans os de peau, sans poids à transférer.
4. **ARKit 52** : chaque coefficient est une combinaison de couches (honnêtement : les 19 poses + 25 clés couvrent une partie seulement ; la langue et certains coefficients n'ont pas de source) ; **rapport de couverture chiffré**, jamais de coefficient inventé.
5. **« Apply Facial Rig »** : active la couche d'expressions et crée des **os de contrôle** (une vingtaine, enfants de `head`, déplacement borné comme les contrôles de Rain) dont la position pilote les expressions par pilotes : le visage se manipule dans la vue 3D, sans peau à skinner. Yeux : objets existants et leurs pilotes ; mâchoire : couche d'ouverture (os de mâchoire quand dents et langue existeront).
6. **Corps + visage ensemble** : le corps est animé par l'armature, le visage par des propriétés de l'objet ; leurs animations (NLA) sont séparées et se combinent sans conflit.

**Pourquoi c'est meilleur** : pas de skinning dense à transférer, coût d'évaluation maîtrisé, compatible avec la morphologie (les expressions s'additionnent à la forme), compatible ARKit, et **réalisable sans sculpteur** puisque la matière première est le travail de Rain. **Risques** : qualité du recalage (dépend des 22 repères, à placer soigneusement), déplacements non adaptés aux proportions (à mesurer), mouvements de bouche fermée (pas d'intérieur de bouche), attribution CC-BY des déplacements dérivés de Rain. **Porte de décision** : le prototype jetable (1 jour) — 22 repères, transfert de 3 poses (`Smile`, `mouth_open`, `CheekPuff`) — décide entre cette voie (B/C) et le portage complet (A) sur des chiffres : écart de surface, faces retournées, étirement.

## 6. Ordre des lots (révisé)

| Lot | Contenu | État |
|---|---|---|
| A1, A1b, A1d | index, import, export Unreal de l'auteur (outil), import enrichi | fait (A1d à commiter) |
| A1c | panneau de bibliothèque minimal + préférences | à commiter |
| **A2** | squelette de déformation propre, placement, repères, poids, statuts, retrait | **en cours** |
| **A2b** | moteur de mapping (auto + manuel + profils + rapport) | suit A2 |
| **A3** | retargeting analytique, aperçu non destructif, Add to NLA/Replace, root motion | |
| A4 | vignettes, galerie polie, favoris → Asset Browser | |
| **Fa–Fd** | prototype visage (22 repères, 3 poses) → décision ; extraction des poses de Rain ; transfert ; couches d'expression + os de contrôle + « Apply Facial Rig » | après A2b |
| Fe | galerie de poses faciales, ARKit 52, mixeur facial | |
| A5 | profils de rigs additionnels (Rigify, Mixamo, MetaHuman corps…) | selon besoin |
| **V0–V4, C1, C2, T** | galerie de vêtements, accessoires, foule aléatoire, niveaux de détail, test final « Paris Golden Hour » (D-33) | après A3 ; voir `TEST_FINAL_FOULE_PARIS.md` |
| (dents, langue, gencives) | prérequis de la mâchoire et de la bouche ouverte | à planifier avant Fd |

## 7. Ce qui ne sera pas promis

- Compatibilité « universelle » : un rapport d'incompatibilités est affiché pour chaque rig.
- Qualité visuelle du visage tant qu'aucune planche n'a été validée à l'œil par l'utilisateur.
- Export Unreal (hors périmètre, D-30).
- Les animations elles-mêmes (non redistribuées, `.gitignore`).

## 8. Validation par l'utilisateur à chaque jalon

Chaque lot se termine par des **images de contrôle** (planches : rig sur 3 morphologies, animation en 4 images clés, visage sur 6 expressions) pour que la décision esthétique soit la sienne ; les mesures ne remplacent pas l'œil.
