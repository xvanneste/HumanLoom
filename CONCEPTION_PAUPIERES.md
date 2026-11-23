# CONCEPTION — paupières et croisements de la tête (lot « paupières / I-49 »)

Date : 2026-11-23. Principe D-35 : « non vérifié » quand une donnée n'est pas lue dans sa source ; rien n'est présenté comme calibré cliniquement.

## 1. Mesures (cage native, contrôles à 0, `tools/proto_unfold_head_crossings.py`, `tools/validate_eyelids_native.py`)
- Les croisements de triangles de la TÊTE apparaissent pour sexe < 0,5 dès l'âge 1 (jusqu'à 51 paires à sexe 0 âge 2) et pour sexe ≥ 0,75 dès l'âge 1,5 (4 à 8 paires) ; aucun pour sexe 0,5 ni pour l'âge ≤ 0,5. Les 31 paires des pieds sont hors sujet.
- Localisation (diagnostics `eye_cross.py`, `cross4.py`) : femme jeune (sexe 1, âge 1) : 4 paires 14 mm sous l'œil, côté du nez ; homme âgé (sexe 0, âge 3) : 8 paires à 7-11 mm sous l'œil ; sexe 1 âge 3 : 4 paires 19 mm au-dessus de l'œil (pli du sourcil) ; sexe 0 âge 2 : paires aux commissures des lèvres (x = ±21 mm, interpénétration jusqu'à 0,7 mm).
- Ce ne sont pas des paupières qui se traversent mais des PLIS de la cage (le calcul sexe/âge superpose des déformations qui, ensemble, replient des triangles voisins de quelques dixièmes de millimètre).
- Le test `validate_eyelids_native` (cinq morphologies, aux extrêmes d'âge, commandes de paupières et de regard à ±1) était un ÉCHEC CONNU : homme âgé 8, femme jeune 4, sexe 1 âge 3 : 4 paires à moins de 3 cm d'un œil.

## 2. Données publiées (D-35) : aucune lue
`extension/data/face_reference.json` : hauteur de la fente palpébrale (≈ 8-9 mm australiens, 11 mm sud-indiens, diminue avec l'âge) et largeur (≈ 30-31 mm) rapportées par des résultats de recherche, **non lues, non utilisées** ; épaisseur de la paupière et écart globe/paupière : non trouvés (« non vérifié »). **Écart entre la fente palpébrale de notre modèle et ces valeurs : non mesuré.**

## 3. Essais de correction
- **Essai 1 (échec)** : voir `CONCEPTION_F0_BOUCHE.md` §6 : poussée le long des normales (188 paires) et écartement vertical des paires de la fente (74 -> 58-60).
- **Essai 2 (RÉUSSI)** : DÉPLIAGE PAR LISSAGE LOCAL. Pour chaque (sexe, âge) de la grille 5 x 7, les sommets des triangles qui se croisent dans la tête (+ 2 anneaux voisins) sont lissés (Laplacien, λ = 0,5, UNE itération à la fois) jusqu'au premier état sans croisement (une seule itération suffit presque partout) ; les sommets des triangles quasi dégénérés (< 0,1 mm²) sont ramenés à leur position d'origine tant que cela ne recrée aucun croisement (sinon `nose_bridge` à −1 faisait basculer un triangle de 0,008 mm² à sexe 0 âge 1,5 : test d'amplitudes) ; la différence est une COUCHE de sommets, interpolée par des « chapeaux » en sexe (pas 0,25) et en âge (pas 0,5) dans le groupe `HL Human` (`tools/build_human_unfold.py`, qui travaille sur une COPIE de `human_nodes.blend`). 19 couches, 251 sommets corrigés, déplacement maximal **0,59 mm** (un premier essai à 10 itérations atteignait 2,9 mm mais faisait échouer les amplitudes). Mesuré sur une grille FINE de 117 états (sexe pas 0,125, âge pas 0,25, contrôles à 0) : **0 croisement dans la tête**. `validate_eyelids_native` : ÉCHEC CONNU -> OK (11 cas).
- Pourquoi ça marche alors que les poussées échouaient : le lissage déplie les replis au lieu de repousser des triangles retournés, dont les normales sont inversées.

## 4. Limites
- La correction ne dépend que de (sexe, âge) : les croisements créés par une COMBINAISON de contrôles forts ne sont pas couverts (le test n'en mesure que quelques-uns, tous OK).
- Les valeurs de la cage changent d'au plus 0,59 mm (dans 251 sommets) par rapport à l'ancien moteur : `validate_human_nodes`, `validate_human_native` exigent l'équivalence exacte (2e-5 m) HORS de ces sommets (liste dans `mesh["hl_unfold"]`) et bornent l'écart par le déplacement déclaré SUR eux ; `validate_human_rig` R15 : à sexe 0 âge 2,8 la liaison automatique de Blender ÉCHOUE encore (100 % des sommets sans poids) bien qu'il n'y ait plus aucun croisement : l'hypothèse « la liaison échoue à cause des croisements » (I-49) est donc FAUSSE ; le test accepte la réussite OU un échec net, et le chemin d'échec net reste testé en abaissant `skeleton.BARE_LIMIT`.
- Les yeux « fermés » des planches sont l'ouverture minimale du contrôle `eyelid_aperture` : **il n'existe pas encore de commande de clignement** (lot visage).
