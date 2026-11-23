# Commandes pilotes du visage (lot visage, étape 3) — réalisation

Date : 2026-11-23. Principe : peau = couches du groupe `HL Human` (décision validée), amplitudes issues de sources LUES quand elles existent (`extension/data/face_reference.json`), « provisoire / non vérifié » sinon.

## Contenu (12 commandes, `proportions.FACE_COMMANDS`)
`mouth_open` (piloté par la mâchoire, lot bouche), `brow_up`, `brow_down`, `brow_inner_up`, `smile_L`, `smile_R`, `cheek_puff`, `lip_pucker`, `nose_wrinkle`, `mouth_down`, `blink_L`, `blink_R`. Construction : `tools/build_face_pilot.py` (patch d'une COPIE de `human_nodes.blend` : une entrée flottante 0 à 1 et une couche de sommets `b_f<n>` par commande, ajoutées au décalage avant `Set Position`) ; `human_sockets.json` mis à jour ; panneau « Expressions (commandes pilotes) » (sous-panneau Visage) et opérateur `humanloom.face_preset` (Neutre, Joie, Surprise, Tristesse, Colère, Dégoût, Clignement : combinaisons ÉCRITES PAR NOUS, non calibrées).

## Amplitudes
| commande | amplitude | source |
|---|---|---|
| brow_up | **13,4 mm** | LUE : Baude et al. 2015 (Tableau 1, marqueur 2D, 10 adultes) : 13,2 mm D / 13,6 mm G |
| smile_L / smile_R | **8,05 mm** | LUE : idem, sourire du zygomatique 8,8 D / 7,3 G |
| cheek_puff | **5,2 mm** | LUE : idem, joues gonflées 5,6 D / 4,8 G |
| brow_down, brow_inner_up, lip_pucker, nose_wrinkle, mouth_down | 6 / 6 / 8 / 2,5 / 5 mm | PROVISOIRE (non vérifié, aucune donnée lue) |
| blink_L / blink_R | fermeture à ≈ 73 % (9,4 mm de déplacement de la peau de paupière) | géométrique ; la valeur de Baude pour le marqueur de paupière (4,2 / 4,0 mm) n'est PAS reprise (définition différente) ; fermeture complète non atteinte : au-delà, des faces se retournent |
Réserves sur la source : excursions de marqueurs 2D (pas de déplacements 3D de la cage), un seul groupe d'âge (39 ± 12 ans), fiabilité jugée faible par les auteurs pour le bas du visage. L'amplitude de la cage = déplacement maximal d'un sommet, atteint à 100 % (test F1) ; ce n'est pas une validation.

## Méthode de champ de déplacement
Chaque commande est un champ de déplacement défini par une règle géométrique (gaussiennes autour des coins de la bouche, des yeux, du nez, du front), puis DIFFUSÉ sur le graphe du maillage (12 itérations, 4 pour les paupières) : les sommets voisins bougent de façon cohérente. Sans cette diffusion, les amplitudes se limitaient à 2-3 mm (faces retournées) ; avec elle les amplitudes lues passent à 100 %.

## Tests (`tools/validate_face_pilot.py`, F1-F5) et planche (`tools/render_face_board.py`)
F1 amplitude déclarée et superposition (les commandes s'ajoutent exactement) ; F2 au plus 3 faces de plus de 1 mm² retournées sur 3 morphologies (observé : 0, sauf clignement homme âgé 2-3) ; F3 amplitudes lues atteintes, provisoires déclarées ; F4 opérateur et panneau ; F5 commandes à 0 : cage inchangée. Équivalence au groupe d'origine : `validate_human_nodes` (hors sommets listés).

## Limites
- Amplitudes en mm ABSOLUS d'un adulte (pas de mise à l'échelle par la taille de la tête : un enfant reçoit les mêmes déplacements).
- Les règles géométriques sont calculées sur le corps par défaut ; les autres morphologies reçoivent les mêmes déplacements par sommet.
- Clignement incomplet (≈ 73 %), pas de commande de regard (os des yeux à faire), pas de visèmes, pas de langue articulée.
- Aucune des 4 amplitudes lues ne vient d'un déplacement 3D de la peau.
