# CONCEPTION_RIG_CORRECTIFS — formes correctives pilotées par l'angle (pose space)

Date : 2026-11-24. Statut : CONCEPTION + mesures de référence (aucun code dans `extension/` avant « COMMIT FAIT » de l'analyste). Demande de l'utilisateur : « quelque chose de parfait » ; épaule levée jusqu'à 180°, torsion, tous les défauts articulaires restants, sur les 3 morphologies et des morphologies extrêmes, sans limite d'amplitude à 135°.

Règle de sources (D-35) : ce document ne cite que ce qui a été LU ou MESURÉ dans cette session. Les références de la littérature ci-dessous sont connues de mémoire et marquées **non vérifié (non lu)**.

## 0. Point de départ (état mesuré)

Rig actuel (état stable, non commité au moment de l'écriture) : deux modificateurs Armature à masques complémentaires (linéaire : tronc, épaules, bras, cou, tête ; quaternions duals + Preserve Volume : avant-bras, mains, cuisses, jambes, pieds), torsion de l'avant-bras pilotée par la main. Coude/genou/hanche/torsion d'avant-bras nettement améliorés ; l'épaule est inchangée (liaison linéaire). Essais sur l'épaule déjà REJETÉS par mesure (voir `SUIVI_REPRISE.md`, section « Articulations ») : quaternions duals sur le bras (bosse +20 à +47 %), nettoyage de la fuite du tronc (arêtes ×10), lissage des poids, os « demi-rotation », contraintes de torsion par copie d'Euler (ambiguïté).
Conséquence : les poids et la hiérarchie d'os seuls ne suffisent pas à 180° ; il faut des formes correctives.

## 1. Inventaire mesuré des défauts restants (`tools/inventory_rig_defects.py`)

Lecture seule de l'extension. Sorties : `validation/rig-correctifs-00/inventaire_base.json` (gitignoré). 5 morphologies (défaut, femme jeune, homme âgé, « gabarit » jambes +1 / torse −1, « inverse » jambes −1 / torse +1), 25 familles de poses, sens ± essayés pour les charnières.

**Critères chiffrés (cibles de réception)** :
| Critère | Seuil | Mesure |
|---|---|---|
| Aire de section | 0,85 ≤ aire ≤ 1,10 (pas d'effondrement, pas de bosse > +10 %) | tranche perpendiculaire à l'os enfant, ACP des sommets, rapport posé/repos |
| Aire de surface de région | 0,85 ≤ rapport ≤ 1,10 | somme des aires des triangles de la région (généralise aux régions sans tranche : tronc, cou, clavicule) |
| Pincement (poses de roulis) | rayon moyen posé/repos par tranche, minimum ≥ 0,9 | |
| Faces retournées | ≤ 2 par région | normale posée à > 90° de la normale de repos tournée par la rotation RIGIDE de l'os dominant (un triangle qui suit son os n'est pas retourné) |
| Arêtes étirées | rapport maximal < ×3 (R6 : ×3,5 pour les flexions à 90°, existant) | arêtes de la région |
Limite connue du critère « faces retournées » : un pli concave (creux du coude fléchi) fait plier des triangles ; le seuil ≤ 2 est volontairement strict et pourra être relâché PAR DÉCISION DOCUMENTÉE (jamais en silence) si la planche montre des plis naturels.
Les amplitudes testées sont des choix de test (aucune amplitude physiologique publiée n'a été lue).

**Résultat de référence** (angles × morphologies hors critère / total) : 142 / 540.
| Famille | Hors critère | Famille | Hors critère |
|---|---|---|---|
| épaule sagittal 0–180° | 15/25 | coude flexion | 15/25 |
| épaule frontal 0–180° | 18/25 | poignet flexion | 5/25 (retournées à 60°) |
| épaule intermédiaire | 14/25 | hanche flexion | 10/20 |
| épaule extension | 1/15 | hanche abduction | 4/15 (arête ×3) |
| épaule rotation (neutre) | 11/30 (aire, pincement à 90°) | hanche flexion+abduction | 5/15 |
| épaule rotation bras levé 90° | **15/15** | genou flexion | 10/20 |
| clavicule X / Z | 4/20, 3/20 (aire de section) | cou flexion 70° | 5/25 |
| avant-bras torsion | 0/25 | cou rotation ±60° | 7/25 |
| poignet déviation, hanche extension/rotation, cheville, cou inclinaison, tronc (flexion, torsion, inclinaison) | 0 | |
Lecture : les défauts se concentrent sur (1) l'ÉPAULE dans tous les plans et surtout bras levé + rotation (15/15) ; (2) les creux articulaires en flexion forte (coude ≥ 90°, genou ≥ 90°, hanche ≥ 90°) : faces retournées / arêtes étirées / aire de surface, même après le correctif d'avant ; (3) le cou à ±60–70°. Le tronc, la cheville, le poignet latéral, la torsion de l'avant-bras et la rotation de la hanche passent.
Dans l'inventaire, le critère « coude 90° : retournées » signale des plis du creux du coude ; voir la réserve ci-dessus.

## 2. Méthode proposée

### 2.1 Principe : déformation par espace de poses (PSD)
Pour chaque articulation, un petit ensemble de **correctifs** : un champ de déplacements δₖ par sommet (région limitée), déclenché par un poids wₖ(pose) calculé d'après l'orientation locale de l'os. Les wₖ sont interpolés dans l'espace des poses par fonctions à base radiale (RBF) sur des poses échantillonnées : référence Lewis, Cordner & Fong, « Pose Space Deformation: A Unified Approach to Shape Interpolation and Skeleton-Driven Deformation », SIGGRAPH 2000 — **non vérifié (non lu)** ; variantes citées de mémoire, **non vérifiées** : Sloan, Rose & Cohen 2001 (« Shape by Example ») ; Kry, James & Pai 2002 (EigenSkin) ; Kavan et al. 2007 (quaternions duals).
Caractéristique clé : on n'invente pas de sculpture ; les δₖ sont CALCULÉS (§2.2).

### 2.2 Génération par calcul (pas de sculpture manuelle)
Pour chaque pose échantillon p et chaque région :
1. Évaluer le corps avec le rig actuel (état S_p).
2. Résoudre pour un champ de déplacement d des sommets de la région (en espace posé) minimisant
   E(d) = Σ_tranches (aire_section(S_p + d) − 1)² + λ_v (Δvolume_local(S_p + d))² + λ_s ‖Laplacien(d)‖² + λ_r ‖d‖² + λ_e Σ_arêtes pénalité(rapport d'arête hors [0,7 ; 1,5]) + λ_f pénalité(faces retournées)
   par Gauss-Newton / L-BFGS sur les vertex de la région, bords de région fixés (d = 0) avec un fondu doux. Les cibles (aire 1, volume local conservé) sont les critères mesurés §1 : ce qu'on optimise est ce qu'on vérifie.
3. Ramener d dans l'espace de REPOS (là où vit une forme corrective) par **évaluation-et-correction** : δ_rest ← δ_rest + (d_visé − d_obtenu), 2 à 3 passes d'évaluation du rig réel. Cela évite d'inverser à la main la matrice de peau, y compris dans la zone en quaternions duals (non linéaire).
4. Stocker δ en repère LOCAL (axes de l'os + normale du sommet), pas en coordonnées du monde.

### 2.3 Échantillonnage des poses
Épaule : swing-twist = élévation 0–180° par pas de 30° × azimut (sagittal, plan de l'omoplate, frontal, extension) × rotation axiale −60…+90° (≈ 60 poses). Coude 5, genou 4, hanche ≈ 30 (flexion × abduction × rotation), cou et tronc ≈ 15 chacun, clavicule ≈ 8. Les caractéristiques de pose sont les composantes du quaternion LOCAL de l'os (w, x, y, z) : aucune décomposition d'Euler (c'est l'ambiguïté qui a fait échouer les contraintes de torsion, mesuré).

### 2.4 Combinaisons sans explosion
- Poids normalisés (type Shepard) et bornés [0, 1,2], support borné par la distance dans l'espace des poses ;
- correctifs organisés par os : le correctif d'un os enfant est exprimé dans le repère du parent (hiérarchique) ;
- validation obligatoire sur poses COMBINÉES (épaule + coude + poignet ; hanche + genou + cheville ; cou + tronc) avec les mêmes critères §1 plus un plafond sur ‖δ‖ total par sommet ;
- symétrie L/R : correctifs générés sur le côté L et reflétés par une table de correspondance de sommets (calculée une fois sur la cage de repos ; erreur de miroir à mesurer, seuil proposé 1 mm).

### 2.5 Morphologies
Les δ sont exprimés en repère local et mis à l'échelle de la région (longueur du segment, épaisseur locale). Validation sur les 5 morphologies de l'inventaire ; si l'erreur (critères §1) dépasse les seuils sur une morphologie, deux replis : (a) opérateur « Recalculer les correctifs » (régénère par §2.2 sur le corps actuel : coût à mesurer, objectif ≤ quelques minutes) ; (b) échantillonner plusieurs corps de base et interpoler. Choix final après le prototype de l'étape 1.

### 2.6 Représentation dans Blender 5.2 (à prototyper, trois options)
A. **Clés de forme** sur le maillage de base + drivers sur les composantes de quaternion local des os. Avantage : exportable (FBX/glTF) ; inconvénient : le maillage de base passe ensuite par le groupe de nœuds « HL Human » (morphologie) : il faut vérifier que le décalage en repère de base survit à la morphologie (non vérifié).
B. **Modificateur de nœuds de géométrie « HL Correctif »** inséré entre « HL Human » et les armatures, lisant des attributs de sommet (un vecteur par correctif, en repère local de l'os) et des entrées pilotées par drivers ; il construit le déplacement de repos juste avant la peau. Avantage : s'adapte à la morphologie (les attributs sont lus après la morphologie) ; peu de clés de forme. À vérifier : lecture des orientations d'os dans les nœuds en 5.2 (**non vérifié**) — sinon les poids viennent des drivers.
C. Calcul des poids RBF par drivers à expressions simples (variables « canal de transformation » en quaternion local, fonctions exp/sqrt) : seulement si le nombre de drivers reste raisonnable.
Option recommandée à l'état actuel de nos connaissances : **B + C**, repli A pour l'export. Décision à l'étape 1 sur mesure (coût et exactitude).

### 2.7 Vêtements, accessoires, foule, bibliothèque d'animations
- **Vêtements** : ce sont des sous-maillages de la topologie du corps (indices `sommets_du_corps`), décalés le long des normales, avec poids hérités. Les correctifs se propagent par le MÊME indice : attributs copiés à la création/mise à jour de la pièce (`add_garment`, `update_garment`) et même modificateur « HL Correctif » sur la pièce, mêmes drivers. Alternative écartée par défaut : Shrinkwrap/Surface Deform sur le corps posé (≈ 15 ms par pièce et par image, mesuré en V1).
- **Accessoires** : objets rigides parentés aux os ; non concernés.
- **Les 30 actions de la bibliothèque** : les correctifs sont pilotés par les quaternions locaux des os (pas par des noms d'actions) ; les actions retargetées en profitent sans modification. Test : pour les 30 actions, critères §1 sur toutes les images avant/après, plafond de ‖δ‖, et les tests de retargeting existants (Q2–Q5) restent verts.
- **Foule** : correctifs coupés aux niveaux de détail 2–3 (la cage y est déjà figée) et au niveau 1 pour les personnages lointains ; coût mesuré à 100 personnages.
- **Export/baked** : les formes ARKit (visage) ne sont pas concernées. Export vers un moteur de jeu : option A (clés de forme) ou cuisson des correctifs sur les images d'une animation ; à décider à l'étape 5.

### 2.8 Coût (budget ≤ +30 % de l'évaluation par image)
Référence mesurée : 20–22 ms/image (corps par défaut, rig actuel). Estimation à valider : un modificateur de nœuds avec ≈ 12 correctifs actifs sur ≈ 10,6 k sommets et quelques dizaines de drivers : ordre de la milliseconde — **non mesuré**. L'étape 1 mesure le coût de chaque option avant tout engagement ; si > +30 %, dégrader : correctifs par région active, calcul des poids à fréquence réduite, désactivation au viewport.

## 3. Mesures de référence prêtes (avant correctifs)
`tools/inventory_rig_defects.py` (ci-dessus) + `tools/diagnose_joints.py` + `tools/render_joint_board.py` (planche ombrée). Les mêmes scripts servent d'après : tests d'acceptation = critères §1 sur 5 morphologies, poses simples puis combinées, 30 actions.

## 4. Plan d'implémentation (étapes, chacune avec test d'acceptation)
0. (en cours) Conception, inventaire, critères. Aucune modification de `extension/`.
1. **Prototype minimal** (épaule, 1 morphologie, hors extension, dans `tools/`) : générer δ par §2.2 pour 12 poses d'épaule, les appliquer par B, mesurer exactitude (critères §1), coût, combinaison avec coude. Décision A/B/C et §2.5.
2. Épaule complète (60 poses) + clavicule + torsion du bras ; symétrie ; 5 morphologies ; planche avant/après ombrée.
3. Creux articulaires (coude, genou, hanche, poignet, cou) ; poses combinées.
4. Intégration dans `extension/` (module `rig_correctives.py`, installation/retrait/mise à jour avec le rig, migration des corps déjà riggés : ils restent en l'état jusqu'à réinstallation), propagation aux vêtements, LOD de la foule, interface (bouton « Recalculer »).
5. Export/baked, documentation (guide), tests `validate_rig_correctives.py` (critères §1 sur 5 morphologies), suite complète, `validate_install`, `--library` (30 actions).
Critère de sortie : plus aucun (angle, morphologie) hors critère §1 sur l'inventaire de référence, ou chaque écart restant justifié et décidé par l'utilisateur.

## 5. Risques et inconnues (à lever à l'étape 1)
- Lecture des os dans les nœuds de géométrie en 5.2 : non vérifiée (voir §2.6 B).
- Interaction avec la zone en quaternions duals (évaluation-et-correction §2.2.3 la traite sans inversion explicite).
- Morphologies extrêmes : l'échelle locale des δ peut ne pas suffire (repli §2.5).
- Coût et nombre de drivers.
- Les critères « faces retournées » et « arêtes < ×3 » sont stricts ; relâchement possible seulement par décision documentée.
- Compatibilité des corps déjà riggés (ancien rig) : pas de migration automatique des correctifs.
