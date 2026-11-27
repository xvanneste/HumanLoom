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

## 6. Résultats de l'étape 1 (prototype d'épaule, `tools/` uniquement, 2026-11-24)

**Références effectivement lues (D-35)** : Sloan, Rose & Cohen, « Shape by Example » (I3D 2001), PDF lu (résumé, introduction, travaux liés, §3 : interpolation = approximation LINÉAIRE aux moindres carrés + bases RADIALES qui corrigent les résidus et passent exactement par les exemples ; base radiale = B-spline cubique dont le rayon vaut deux fois la distance à l'exemple le plus proche ; systèmes « cardinaux » résolus par exemple (et non par degré de liberté) en une fraction de seconde ; extrapolation possible hors de l'enveloppe convexe ; l'article indique que Lewis et al. posent un système linéaire PAR DEGRÉ DE LIBERTÉ, donc moins efficace). Les parties « articulated figures » et expérimentations n'ont pas été lues en détail. Lewis, Cordner & Fong (SIGGRAPH 2000) : seule la notice officielle (résumé) a été lue ; le texte intégral n'a pas pu être obtenu (PDF institutionnel non accessible) → **toujours « non vérifié (non lu) » pour le détail de la méthode**. Kry/James/Pai 2002 et Kavan 2007 : non lus.

**Représentation (mesure `tools/proto_corrective_cost.py`, évaluation de la cage, ms/image, bruit ≈ ±3 ms)** : base 27–33 ; option A (clés de forme sur le maillage de base + drivers à 4 variables de quaternion local) : K=12 → 31–33 ; K=60 → 35–38 (+20 à +30 %) ; option B (nœuds de géométrie) : K=12 → 30–33 ; K=60 → 34–47 avec drivers. Le corps n'a AUCUNE clé de forme de base ; la morphologie vient des nœuds « HL Human ». **Les clés de forme de base traversent la morphologie** (écart mesuré 3,5 mm pour 12 clés aléatoires de 0,5 mm). **Les attributs de sommet ajoutés au maillage de base n'ont produit AUCUN effet via un modificateur de nœuds (écart 0,0 m), placé avant ou après HL Human** (test non concluant : montage à revoir, pas de preuve que ce soit impossible). → **Décision provisoire : option A** (clés de forme + drivers), exportable, coût dans le budget jusqu'à K≈60 ; B écartée tant qu'elle n'est pas démontrée.

**Génération des cibles (épaule)** :
- Poids de peau seuls (`proto_shoulder_weights.py`, optimisation par gradient exact des longueurs d'arête, plis et aires de section, poids positifs de somme 1, 20 os candidats, 3 632 sommets) : l'étirement d'arête est ramené sous ×3 sur toutes les poses d'entraînement et de test (de 10–22 poses hors critère à 0–2) avec des poids presque inchangés (écart moyen 0,002), SANS coût d'exécution, et les vêtements en héritent ; mais plis et aires de section ne s'améliorent pas (la peau linéaire ne peut pas : limite connue). → à intégrer comme première étape (poids optimisés), à valider sur les 5 morphologies et sur les 30 actions.
- ARAP avec contraintes de longueur d'arête (`--arap`) : REJETÉ (zone de raccord déchirée, visible sur la planche, plis et étirement dans la zone large ; les critères sur la seule zone proche masquaient les dégâts → la zone de mesure doit inclure la zone de raccord, R≈0,27 : désormais mesurée).
- Mélange peau linéaire / quaternions duals : REJETÉ (bosse, aire de section jusqu'à 1,48).
- **Cibles par optimisation directe des positions posées** (`proto_shoulder_targets.py` : énergie = arêtes + plis + aire de section + rappel vers la peau linéaire croissant vers le bord + lissage du déplacement, gradient exact, Adam, 400 itérations, ≈ 3 s par pose) : sur 3 morphologies, plis 0 à 4 (peau linéaire : 5 à 137) en zone proche ET large, arêtes ×1,3 à ×2,9 (peau linéaire ×2,7 à ×7), surface 0,87–0,99 ; aire de section 0,57–1,17 (cas sagittal à 180° et épaule sans clavicule à 180° encore trop bas : 0,57–0,80). La planche (`planche_proto_epaule_v2.png`) montre un creux d'aisselle lisse à 90–135° sans crête, MAIS : (a) des défauts sur le cou/visage (la zone libre R=0,30 inclut le cou et la mâchoire : à exclure par masque d'os), (b) des aspérités sur le dessus de l'épaule à 180°.
- **Critère « faces retournées ≤ 2 »** : mesuré par la rotation rigide de l'os dominant, il donne 30–83 « retournées » sur les cibles lissées (plis réels = 0–4), parce que les triangles de la transition tournent progressivement de 0 à 180° et dépassent 90° de la rotation de leur os dominant. Je propose de MESURER AUSSI le critère « plis » (deux triangles voisins à plus de 90°), sans relâcher l'autre sans décision de l'analyste.

**Prochaines étapes** : masque d'exclusion tête/cou ; terme anti-aspérité ; rythme scapulo-huméral automatique (clavicule suit l'élévation) ou animation de la clavicule exigée ; encodage en espace de repos (évaluation-et-correction) et interpolation RBF (B-spline cubique, rayon = 2 × distance au plus proche exemple, selon Sloan) sur la base des cibles échantillonnées ; validation hors entraînement et combinaisons ; mesure du coût réel avec drivers.

### 6 bis. Compléments d'étape 1 (même jour, après « COMMIT FAIT 238433f »)
- **L4_M2 (mapping --library)** : préexistant, identique sur l'état 6cbfa80 exporté proprement (médiane 5,48 % de la stature, p95 8,98 %, max 9,93 %) : pas une régression.
- **Couplage épaule / cou / visage** : sous élévation avec rythme scapulo-huméral, la peau linéaire plie déjà le COU et la ligne de la mâchoire (zone large : 92–137 plis à 180°), car la clavicule et le trapèze entraînent des poids du cou. L'optimiseur de cibles « répare » ce pli en froissant le cou et la joue (artefacts visibles sur la planche) ; si on protège le visage (atténuation par distance en arêtes), les plis du cou reviennent (36–56 en zone large). Conclusion : ce défaut n'est PAS un défaut d'épaule mais de poids du cou / trapèze ; il doit être traité par l'optimisation des poids (qui n'agit pas sur la forme), pas par un correctif de forme.
- **Réglages qui stabilisent l'optimiseur** : décroissance du pas (Adam sans décroissance laisse des oscillations de l'ordre du pas sur tous les sommets, source de bruit visible), seuil de pli RELATIF au repos (les arêtes vives du visage ne doivent pas être pénalisées), rappel vers la peau linéaire croissant vers le bord de zone, lissage du déplacement.
- **État des cibles (défaut, rythme frontal 135–180°, sans protection du visage)** : plis 0, arêtes ×2,0–2,3, surface 0,90–0,94, aire de section 0,93–1,04 ; épaule seule à 180° et sagittal à 180° : aire de section 0,57–0,73 (hors critère). Les cibles ne sont pas encore encodées en espace de repos.
- **Suite recommandée** : (1) optimiser d'abord les POIDS de toute la ceinture scapulaire + cou/trapèze (étirement et plis, zone large), en intégrant la clavicule suivant l'élévation ; (2) seulement ensuite générer les correctifs de forme sur le résidu ; (3) encodage en repos + RBF (Sloan) + validation hors entraînement.

### 6 ter. Poids optimisés de la ceinture scapulaire : essai d'intégration (mesuré, NON retenu)
Outil : `tools/build_shoulder_weights.py` (entraînement sur 3 morphologies × 34 poses d'épaule gauche, énergie = arêtes + plis relatifs + aire de section + rappel + lissage ; visage (poids head/jaw) et zone distale exclus, symétrie par miroir), superposition `human_rig_weights_shoulder.npz` appliquée par `skeleton.apply_weight_overlay` (sans fichier : aucun effet). Preuve de non-régression (`tools/check_shoulder_overlay.py`) : écart sur le visage 0,0 mm, sur le cou ≤ 9 mm, sur le reste jusqu'à 91 mm (épaule/bras aux poses extrêmes).
Inventaire (`inventory_rig_defects.py`, critère « plis » NOUVEAUX = pli apparu par rapport au repos, bloquant ; « retournées » en information ; 5 morphologies, 540 cas) : sans superposition 167 cas hors critère ; avec superposition 160 (réglage prudent) / 160 (réglage libre) : étirement 57→44–46, plis 137→127–131, aire de section 77→81 (légèrement pire), aire de surface 32→38–39. Seules 477–529 sommets sont libres (visage et zone distale exclus) et les poids ne bougent que de 0,006 en moyenne.
**Conclusion : les poids seuls ne peuvent pas atteindre les critères d'épaule (limite de la peau linéaire, comme prévu) ; le gain (−4 % de cas hors critère) ne justifie pas d'embarquer la superposition.** Fichier retiré de `extension/data/` (copie dans `validation/rig-correctifs-00/`, gitignoré) ; la fonction `apply_weight_overlay` reste, inactive. Les correctifs de forme restent nécessaires ; le couplage cou/mâchoire sous clavicule suivant l'élévation reste à traiter séparément.

### 6 quater. Poids optimisés en zone large (cou/trapèze inclus) : même conclusion, NÉGATIVE
Réglage libre (`--lw 0,05 --lf 1 --la 3`, 833 sommets libres : ceinture scapulaire + cou/trapèze, le visage — 2 700 sommets de la tête dans R=0,30 — et la zone distale exclus) puis inventaire avec deux familles « rythme scapulo-huméral, zone large (R=0,27) » : l'étirement baisse (×4,5–7 → ×2,5–3,9) mais les plis et l'aire de section EMPIRENT (rythme frontal 135° : plis 25→53, 42→69, 31→51 ; aire de section 1,17→1,43) ; total 124 → 141 cas hors critère sur 3 morphologies. L'optimisation des poids seule dégrade donc les plis du cou/trapèze : **non retenue** (fichier retiré de `extension/data/`, copies dans `validation/rig-correctifs-00/`). Un correctif de forme est le seul levier restant ; le couplage cou/mâchoire sous clavicule suit l'élévation (plis 73–99 à 180°) doit y être traité (cible de forme sur le cou aussi, ou rythme plus faible de la clavicule).

## 7. Palier 1 : résultats intermédiaires (pose space sur cibles optimisées ; NON intégré)
Outils : `tools/rig_solver.py` (cibles par gradient exact), `tools/build_shoulder_correctives.py` (cibles → encodage en repos par la matrice de peau → poids RBF), `tools/rig_metrics.py` (critères ; « plis » = plis NOUVEAUX par rapport au repos, bloquant ; « retournées » informatif). Corrections de méthode faites en route : (a) la mesure de plis comptait les plis de géométrie du REPOS (visage) : désormais relatifs au repos ; (b) la base RBF de Sloan avec terme linéaire EXTRAPOLE et aggrave les poses hors entraînement : remplacée par des poids de Shepard (bases radiales gaussiennes normalisées, partition de l'unité, bornés) avec un exemple de repos à correctif nul ; (c) l'aire de section exige un poids fort (λa=150) pour passer de 0,75 à 0,86 sur le sagittal 90°.
Mesure (corps par défaut, côté gauche ; droite équivalente ; zone proche R=0,14 + zone large R=0,27, critères §1 avec plis nouveaux) :
- Poses d'ENTRAÎNEMENT (19 : 30/60/90/120/135° dans 3 plans, extensions, rotations bras levé) : hors critère 14 → 12 ; plis nouveaux cumulés en zone large 273 → 89 (L), 287 → 118 (R) ; visage inchangé (0,000 mm).
- Poses HORS entraînement (19 : 45/75/105° + 10 aléatoires) : hors critère 12 → 11 (L), 11 → 13 (R) ; plis nouveaux cumulés 219 → 222 (L), 202 → 242 (R) : **AUCUN GAIN, parfois pire**.
**Constat** : les cibles par pose sont très spécifiques (minimiseurs non uniques, détail à haute fréquence) ; leur interpolation entre exemples espacés de 15–30° ne reproduit pas un état sans plis. Les correctifs ne se généralisent pas à ce pas d'échantillonnage ; il faudrait soit un échantillonnage beaucoup plus dense (≥ 60–100 poses par côté, coût de génération et de stockage à mesurer), soit des cibles lissées dans l'espace des poses (régularisation entre exemples voisins : démarrage à chaud de chaque pose depuis la solution de la pose voisine), soit un correctif basse fréquence seulement (aire de section et creux d'aisselle, sans le détail des plis). Rien n'est intégré dans `extension/` à ce stade (aucun jalon livrable : le palier 1 n'est PAS atteint).

## 8. Ratio de clavicule (paramètre mesuré) et usage RÉEL de l'épaule dans la bibliothèque (24 nov. 2026)
**Ratio** (`tools/measure_clavicle_ratio.py` : le bras porte (1−r)·a, la clavicule r·a ; peau linéaire ; 3 morphologies ; plis nouveaux en zone large R=0,27, aire de section en zone proche) :
| plan / angle | r = 0 | 1/6 | 1/4 | 1/3 | 1/2 |
|---|---|---|---|---|---|
| sagittal 90° (plis large : défaut / femme / homme) | 43 / 46 / 49 | 33 / 36 / 31 | 27 / 32 / 22 | 20 / 12 / 15 | 26 / 25 / 28 |
| sagittal 135° | 46 / 49 / 49 | 46 / 46 / 46 | 42 / 38 / 42 | 58 / 58 / 53 | 72 / 80 / 82 |
| frontal 90° | 2 / 14 / 8 | 0 / 10 / 6 | 0 / 8 / 4 | 0 / 6 / 2 | 20 / 23 / 22 |
| frontal 135° | 18 / 59 / 32 | 11 / 37 / 15 | 9 / 33 / 15 | 25 / 42 / 31 | 59 / 71 / 67 |
| frontal 180° | 57 / 70 / 57 | 51 / 61 / 54 | 60 / 94 / 64 | 73 / 99 / 86 | 104 / 122 / 105 |
Aire de section (sagittal 90°, défaut) : 0,75 (r=0) → 0,85 (1/6) → 0,91 (1/4) → 0,96 (1/3). Meilleur compromis pour ≤ 135° : **r ≈ 1/4** (plis minimaux à 135°, aire ≥ 0,85) ; à 90° 1/3 est meilleur ; à 180° 1/6 ; r = 1/2 est mauvais partout au-delà de 90°. Ce ratio serait un réglage de rig (valeur variable avec l'angle possible) ; aucune amplitude physiologique publiée n'a été lue.
**Usage réel** (`tools/measure_library_shoulder.py`, 30 actions de la bibliothèque retargetées en « absolu + IK jambes », images échantillonnées 1 sur 3, bras gauche et droit, bras élevé ≥ 60°) : 77 images de bras élevé sur toutes les actions ; par plage d'élévation : 60–90° : 59 images ; 90–120° : 14 ; 120–150° : 1 ; 150–180° : 3. La CLAVICULE est DÉJÀ animée par la bibliothèque : rotation médiane 35° (60–90°), 36° (90–120°), 45° (> 120°), soit un ratio réel ≈ 0,4–0,5 de l'élévation (au-dessus du compromis 1/4). Aucune de ces images ne passe les critères (plis en zone large médiane 20–32, max 58 ; étirement large jusqu'à 5,2) ; l'image la plus plissée (élévation 153°) est une chute/roulade avec plis sur le torse et la hanche (non spécifique à l'épaule). Conséquences : (1) un couplage automatique de clavicule dans le rig compterait la clavicule deux fois : **non retenu** (décision (b) de l'analyste) ; (2) 96 % des images réelles d'épaule levée sont ≤ 120° : le palier 1 (≤ 135°) couvre l'usage ; (3) la clavicule retargetée est plus forte que le meilleur ratio mesuré ; une option « limiter la clavicule retargetée » (à mesurer sur les 30 actions : Q2 et plis) est une piste moins coûteuse que des correctifs de forme.

## 9. Palier 3 (creux du coude et du genou) : RÉALISÉ et intégré (24 nov. 2026)
Les articulations à charnière sont monotones et à un seul paramètre : l'interpolation 1D en angle (chapeaux linéaires entre clés tous les 15°) généralise, contrairement à l'épaule (§7).
- **Génération** (`extension/animation/correctives.generate`, copie du solveur dans `correctives_solver.py`, données livrées par `tools/build_hinge_correctives.py`) : cibles par optimisation (arêtes, plis relatifs, aire de section λa=150, lissage) à 15°, 30°… 150° (genou 135°), PUIS encodage EXACT en espace de repos par la jacobienne réelle du pipeline (différences finies : clés de forme sur le maillage de base → morphologie → peau linéaire/quaternions duals ; l'approximation par la matrice de peau échouait aux grands angles : erreur jusqu'à 2 m sur quelques sommets du coude, 28–85 mm après amortissement ; erreur d'encodage 0,00 mm avec la jacobienne réelle).
- **Exécution** : clés de forme « HLC <articulation>_<côté> <angle> » sur le maillage de base, valeur = chapeau de l'angle lu par pilote d'expression simple sur la rotation LOCALE de l'os (variable de pilote en mode quaternion : sans ce réglage ROT_W vaut 0, mesuré ; indépendant du mode de rotation de l'os) ; angle = ±2·atan2(x·w/(|w|+ε), |w|) (insensible au signe du quaternion).
- **Mesures** (`tools/validate_correctives.py`, angles HORS entraînement 22/52/97/128/142° coude et 22/52/97/120/130° genou, 4 articulations × 5 morphologies = 100 poses ; critères de zone proche, plis NOUVEAUX) : correctifs livrés (corps par défaut) appliqués à toutes les morphologies : plis cumulés 1 080 → 463 (−57 %), sur le corps par défaut 225 → 32 (−86 %), hors critère 60 → 49 ; **recalculés sur la morphologie (homme âgé)** : 214 → 39 (−82 %), recalcul en 115 s ; visage inchangé 0,000 mm ; coût d'évaluation 34,1 → 35,0 ms (ratio 1,03) ; foule sans correctifs ; vêtements (sous-maillages) : mêmes clés, mêmes pilotes, déplacements identiques à 6·10⁻⁸ m, conservés par `update_garment`, retirés avec le rig.
- **Limites** : le critère strict « plis ≤ 2 » n'est pas atteint partout (résidu de quelques plis aux angles intermédiaires) ; correctifs génériques moins efficaces hors du corps par défaut (−57 % en moyenne, un cas pire : homme âgé coude gauche 58 → 76 avant recalcul) → utiliser « Recalculer » ; robes et pièces importées sans correctifs ; hanche, poignet et cou non traités ; épaule non traitée.

### 9 bis. Mesure sur les poses RÉELLES de la bibliothèque et correction d'un défaut de région (25–27 nov. 2026)
`tools/measure_library_hinges.py` (30 actions retargetées, 1 image sur 3, mesures ≥ 60° de flexion, corps par défaut, plis nouveaux en zone proche, correctifs actifs vs clés muettes). Première mesure (correctifs livrés initiaux) : coude plis 11 759 → 4 746 (−60 %), **genou 5 905 → 6 602 (+12 %, PIRE)**. Diagnostic : le pire cas réel (genou 88°, plis 11 → 39) n'était pas reproduit par des poses synthétiques ; dichotomie sur les os de la pose réelle : seule la JAMBE OPPOSÉE fléchie suffisait (plis 15 | 35). Cause : la région de génération d'une articulation (rayon 0,22–0,26 m) englobait les sommets du MEMBRE OPPOSÉ (et du tronc pour le coude), qui recevaient des déplacements pour une flexion qu'ils ne subissent pas. Correction (`correctives.generate`) : seuls les sommets dont l'os dominant est du MÊME CÔTÉ (suffixe .L / .R) sont libres. Données régénérées (genou jusqu'à 150°, car la bibliothèque va jusqu'à ~151°). Résultat réel après correction : coude 11 874 → 4 294 (−64 %), **genou 7 253 → 2 139 (−71 %)**, étirement genou max 3,75 → 1,71, hors critère genou 625 → 251 ; hanche 0–30° / 30–60° / > 60° : plis genou −65 % / −73 % / −74 % (la hanche n'est pas un facteur : la géométrie locale du genou ne dépend que de la rotation relative). Validation synthétique inchangée (C3 : plis cumulés −57 % toutes morphologies, −84 % sur le corps par défaut ; C7 recalcul −82 %).
Répartition des angles réels (toutes images, 30 actions) : poignet |angle| ≥ 60° sur 80 % des images (médiane −70°, aucun correctif, 100 % hors critère : à examiner comme biais de repos de la main au retargeting), coude 35 %, genou 26 %, hanche 5 %, cou 2 %.

### 9 ter. Poignet : biais de repos du retargeting, CORRIGÉ à la source (27 nov. 2026)
Mesure : sur les 30 actions, le poignet dépassait 60° de flexion sur 80 % des images (médiane −70°). `tools/probe_wrist_bias.py` (lecture seule) retargete la pose de REPOS de la source : le poignet de la cible fait −78° (rotation totale 80°) alors qu'un mannequin au repos doit rester au repos. Cause : en mode absolu la direction de la main est alignée sur celle de son « enfant principal », choisi comme le premier enfant apparié, l'`index.00`, dont la tête est quasi au poignet (vecteur court et latéral, sensible à quelques degrés) ; l'axe de la main se retrouvait à 66° de l'avant-bras (repos : 14°) pendant que les doigts se contre-tournaient pour que les articulations des doigts s'alignent, ce qui déformait le poignet. Correction (`retarget.retarget`) : enfant principal de la main = `middle.01` (articulation du majeur) quand il est apparié ; signature de cache « algorithme 2 » (anciens caches non rejoués). Résultat : axe avant-bras/main 9° (repos 14°), rotation locale de la main au repos de la source 20°, sur les 30 actions poignet médiane −9° (p5 −21°, p95 +11°), part ≥ 60° : 80 % → 0 %. Retargeting : validate_animation_retarget PASS, validate_animation_retarget_library (Q2 coudes/genoux, mains/pieds, Q3 glissement 0/60, Q4, Q5) PASS, validate_animation_derived_library PASS. Les correctifs de poignet deviennent inutiles tant que l'angle réel reste dans ±25°.

## 10. Épaule : décision utilisateur et rythme scapulo-huméral (27 nov. 2026)
**Décision de l'utilisateur** (planches du §9 bis) : le coude et le genou sont corrects SANS correctifs ; seule l'épaule est « pas naturelle du tout » à forte élévation. Les correctifs HLC coude/genou sont donc **coupés par défaut** (`correctives.ENABLED_PROP`, bouton « Correctifs de flexion » du panneau Squelette ; clés installées muettes, recalcul conservé ; `tools/validate_correctives.py` C9).

**Planche de l'état actuel** (`tools/render_shoulder_board.py` + `assemble_shoulder_board.py`) : à ≥ 135° la peau du flanc et de l'aisselle est tirée en nappe plate, le moignon/deltoïde ne suit pas (aucune montée de clavicule), le pectoral est tiré et plié en flexion.

**Approche A, rythme scapulo-huméral, mesurée (agent Opus, prototypes `tools/proto_epaule_A_*.py`, non livrés)** : la clavicule est calculée d'après l'élévation humérothoracique θ ; élévation 0/0/0/6,7/13,3/20/20° et rotation axiale postérieure 0/0/3/9/18/27/30° aux nœuds 0/30/60/90/120/150/180° ; pas de rétraction (elle aggrave plis et aire de section : mesuré) ; orientation monde du bras conservée (contre-rotation exacte, 0,000°). Résultats (corps par défaut) : angle gléno-huméral 180° → 145° ; frontal 135° plis 7 → 0 ; 180° 48 → 38 (proche 28 → 12) ; aire de section 0,76 → 0,90 ; grille 0–180° : plis −14 % (zone large), −33 % (proche) ; dérive de la main 1,6 cm à 90°, 4,1 cm à 135°, 4,9 cm à 150–180°. **Limites** : le sagittal ne bouge presque pas (aire 0,56–0,64, critère 0,85), car le flanc et le grand dorsal (pondérés sur spine.03/.04) ne suivent pas la clavicule ; le nombre de poses hors critère ne baisse pas (28 → 30). Les os d'aide « Copy Rotation » 1/4–1/2–3/4 (approche B) n'apportent que 5–19 % de plis et, en éventail complet, gonflent l'aisselle en « ballon » (aire 1,25–1,6, étirement ×5–8) ; Damped Track est singulier à 180°.

**Intégré (option, défaut OFF)** : `retarget.Options.clavicle_mode = "rythme"` (case « Rythme scapulo-huméral » du panneau de retargeting) ; la rotation de clavicule de la source et `clavicle_scale` sont alors ignorées (pas de double comptage) ; l'orientation monde de tous les autres os est conservée (`tools/validate_animation_retarget.py` Q1c ; `validate_animation_retarget_library.py` Q9 sur les actions réelles : dérive de main ≤ 8 cm, clavicule ≤ 45°). Défaut conservé tant que l'utilisateur n'a pas validé les planches. La pose MANUELLE (pilotes sur la clavicule) n'est pas intégrée : elle changerait le sens des clés de `arm_upper` (migration nécessaire).

**Suite** : un os d'omoplate/thorax déformant (poids dos-flanc-pectoral, poids cou/mâchoire retirés de la clavicule) est à l'étude (agent Opus) : c'est la seule piste identifiée pour le sagittal.
