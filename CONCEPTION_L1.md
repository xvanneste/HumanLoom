# Conception L1 — visage complet

Branche `codex/natif`. D-34 : tout est écrit par nous ; D-35 : rien n'est présenté comme calibré sans source lue.

## Contenu
| Élément | Où | Test | Statut des valeurs |
|---|---|---|---|
| Regard (os `eye.L/.R`, rotation, convergence, suivi, limites 45°/35°) | `animation/skeleton.py` | `validate_gaze` G1–G7 | limites provisoires, non vérifiées |
| Paupières suivant le regard (drivers sur `blink_*`, `eye_wide`) | `skeleton.attach_lid_follow` | G8 | 30 % de fermeture/ouverture à regard maximal : provisoire |
| Échelle d'amplitude selon l'âge | `tools/build_face_scale.py`, groupe `HL Human` | `validate_face_pilot` F7 | profondeur de tête de **notre** modèle : 0,895 / 0,955 / 1 / 1 aux âges 0 / 1 / 2 / 3 |
| Langue articulée (7 formes) | `animation/dental.py` `TONGUE_SHAPES` | `validate_dental` D10 | amplitudes provisoires |
| Lèvre inférieure abaissée (AU16) | `tools/build_face_lower_lip.py`, `b_f19` | F1–F7, P7 | 7 mm provisoire, réduit si faces retournées |
| Dents du bas visibles (sourire large, rire) | présets `sourire_large`, `rire` | `validate_face_poses` P7 ; `tools/measure_lower_teeth.py` | mesure relative (part de sommets visibles de face) |
| Visèmes (15) | `animation/face.py` `VISEMES` | P3 | liste de mémoire (MPEG-4), table non lue : « non vérifié » |
| ARKit 52 | `face.ARKIT`, `arkit_report`, `arkit_to_pose` | P4 | noms de mémoire, correspondances nôtres ; 7 directs, 9 os, 1 langue, 23 approchés, 12 non couverts |
| Formes cuites (commandes + ARKit couverts) | `face.bake_shapes` | P5 | cage seule (topologie du corps, poids copiés) |
| Galerie, favoris, mélangeur, clip NLA | `animation/face_ui.py`, `face.build_clip` | P1, P2, P6, P8 | — |

## Choix
- Une pose = commandes 0–1 + `_jaw` (degrés) + `_tongue` + `_gaze`. Les poses de l'utilisateur et les favoris vivent dans la scène (JSON), pas dans les préférences.
- L'animation faciale est répartie par porteur (corps : commandes ; armature : mâchoire et yeux ; clé de forme : langue), chacun dans une piste NLA « Visage » : l'action du corps n'est jamais touchée.
- Les commandes pilotées (mâchoire → `mouth_open`, suivi des paupières) ne sont ni keyframées ni cuites.

## Limites connues
- Parois de la bouche encore presque droites ; amplitudes faciales non vérifiées ; fermeture du clignement ≈ 73 % ; pas de formes pour `jawForward/Left/Right`, `mouthRoll*`, `mouthDimple*`, `mouthLeft/Right`, `mouthClose`, `mouthLowerDown*`.
- Le mélangeur est linéaire ; le clip A → B n'a que deux clés.

## Sourire de Duchenne (reprise du 24 nov.)
Retour de l'utilisateur : le sourire doit être un mouvement coordonné de tout le visage, piloté par un seul curseur. Réalisé par `tools/build_face_smile.py` (sur la cage par défaut, après `lower_lip_depress`) :
- nouvelles couches : `smile_pull` (traction latérale des commissures, diagonale 44° vers l'oreille avec `smile_L/R`), `cheek_raise` (remontée et bombement de la pommette, avec compensation de volume sur une couronne de 35 à 60 mm), `nasolabial_deepen`, `crows_feet` (trois plis radiaux, 1,4 mm) ;
- commande maîtresse `smile_duchenne` (sans couche) : valeur m → courbe commune m²(3 − 2m) → ajoutée (bornée à 1) à `smile_pull`, `smile_L`, `smile_R`, `cheek_raise`, `nasolabial_deepen`, `crows_feet` (poids 1) et `eye_squint` (0,6) ; les commandes restent utilisables seules (asymétrie) ;
- présets `joie`, `sourire_large`, `rire` fondés sur la commande maîtresse ;
- mesures (`face.smile_metrics`, test F8 de `validate_face_pilot`) sur 3 morphologies : angle de la commissure 44,4°, réduction de l'ouverture palpébrale de −0,9 / −3,0 / −5,1 / −6,0 mm à 25 / 50 / 75 / 100 %, volume des joues (flux net / brut) 6 à 16 %, 0 face retournée, progression = smoothstep à ±0,02 près ;
- amplitudes et poids : provisoires, « non vérifié » (FACS : numérotation des AU seulement). Les mesures de volume sont celles de la cage, pas d'un volume de tissu mou.
- Correctif découvert en route : les formes de la langue étaient créées à la valeur 1 (la langue sortait du menton) ; elles sont maintenant à 0 à l'installation (test D10).
