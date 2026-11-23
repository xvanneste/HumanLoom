# CONCEPTION — plis du cou (retour utilisateur : « le cou a des plis bizarres »)

Date : 2026-11-23. D-35 : aucune amplitude physiologique du cou n'a été LUE (rotation, flexion, inclinaison « non vérifié ») ; les mesures ci-dessous sont celles de NOTRE modèle.

## 1. Diagnostic (`tools/diagnose_neck.py`, 3 morphologies, poids en couleurs : rouge neck.01, vert neck.02, bleu head, cyan jaw, jaune clavicules/colonne)
- Avant : rotation axiale TOTALE (1/3 sur `neck.01`, 2/3 sur `neck.02`) : 30° = 0 triangle retourné ; **60° = 5 à 11 retournés** (étirement d'arête 2,4) ; **80° = 32 à 44** (2,8). Flexion 30/45°, extension 30°, inclinaison 30° : 0 retourné (étirement 1,3-1,9).
- Les poids stockés SONT ceux de la liaison automatique de Blender (même méthode) : la « référence Blender » donne exactement les mêmes nombres (7/5 retournés à 60°, 2,43) : on ne peut pas être « meilleur que la référence » sans changer les poids.
- Où : les triangles retournés (`neck_flips.py`) sont sur les FLANCS du cou (x = ±57 à 83 mm, z = 1 395-1 440 mm) où se mélangent head, neck.02, neck.01 et clavicules ; la peau du cou était surtout pondérée sur les clavicules et la colonne (jaune sur les planches), avec une transition vers la tête étroite (≈ 70 mm).
- Lien avec la mâchoire : élargir le fondu des poids de `jaw` vers le menton et l'oreille (profil plus lisse) faisait retourner 190 triangles à la torsion du cou 45° (R6) : la transition head/neck ne supportait pas un 3e os dans la zone.

## 2. Essais (mesurés, neutre ; homme âgé et femme jeune donnent les mêmes ordres)
| essai | 60° | 80° | torsion R6 45° | note |
|---|---|---|---|---|
| poids d'origine | 7 / 5 | 33 / 44 | 4 / 3 | étirement 2,43 |
| lissage en bande, 80 itérations | 3 / 3 | 41 / 51 | 2 / 0 | bande 70 mm sous la base du cou à 10 mm au-dessus du menton |
| rampe par la hauteur seule (poids z-only) | 20 / 14 | 62 / 70 | 6 / 9 | PIRE (aussi en flexion) : abandonné |
| quaternions duals (« Preserve Volume ») | 8 / 7 | 35 / 32 | 0 / 1 | aucun gain : abandonné |
| **lissage 600 itérations, demi-largeur 100 mm (RETENU)** | **2 / 0** (homme âgé 6 / 3) | **35 / 43** | **0 / 0** | étirement 2,42 ; avec fondu de mâchoire LARGE |
- Retenu : `tools/build_neck_weights.py` (diffusion des poids sur le graphe du maillage dans une bande autour du cou ; condition aux limites fixe hors bande ; 4 influences) appliqué à `human_rig_weights.npz` (`--below 70 --above 10 --iterations 600 --half-width 100`), PUIS fondu de mâchoire large (`tools/build_human_jaw.py`, défaut `HL_JAW_WIDE=1`). La torsion du cou 45° de R6 passe de 3-4 retournés à 0, sans assouplir de seuil.
- **Non atteint** : « 0 retourné à 60° » (reste 0 à 2 pour la moyenne, 2 à 6 pour l'homme âgé) et le critère 80° (≈ 35 retournés : un cou à 2 os en liaison linéaire ne tient pas 80° de torsion). Pistes non essayées : 3e os de cou (torsion répartie sur 3 segments), correctifs de forme d'angle dépendants (sterno-cléido-mastoïdien), liaison au muscle.

## 3. À refaire après une régénération des poids
`tools/build_human_rig.py` régénère `human_rig_weights.npz` depuis la chaleur de Blender : il faut ensuite rejouer `build_neck_weights.py` (paramètres ci-dessus) puis `build_human_jaw.py`.
