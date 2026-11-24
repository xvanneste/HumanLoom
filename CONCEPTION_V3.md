# CONCEPTION V3 — accessoires, points d'attache et poses de préhension (réalisation)

Code : `extension/accessories.py` (moteur), `extension/accessories_ui.py` (panneau « Accessoires »). Tests : `tools/validate_accessories.py` (A1–A9). Planche : `tools/render_accessories_board.py` + `tools/assemble_accessories_board.py`. Aucun asset tiers : toutes les formes sont construites par le code (boîtes, cylindres, cônes, calottes, tores).

## Réalisation
- **7 accessoires** : sac à main, sac de courses, sac à dos, téléphone, parapluie fermé, parapluie ouvert, lunettes. Dimensions proportionnelles à la stature du corps.
- **Points d'attache** (`SOCKETS`) : paume gauche/droite, dessus des épaules, milieu du dos, côté de la taille, dessus de la tête, devant des yeux. Chaque repère (origine, x travers, y longueur ou haut, z normale sortante) est calculé sur le corps ACTUEL (cage) ; l'accessoire est un objet enfant de l'os (parent « os »), il suit donc toutes les animations.
- **Repère de la paume** : normale sortante de la paume déterminée par l'ANATOMIE (pouce du côté radial, signe selon la main), pas par un essai de rotation ; mesurée : les paumes regardent vers le milieu du corps en pose neutre.
- **Poses de préhension** (`GRASPS`) : « poignée » et « plat » (angles de flexion de chaque phalange : valeurs de modélisation, non issues d'une publication). Le sens de fermeture de chaque doigt est MESURÉ (le bout se déplace du côté de la normale de la paume). `apply_grasp(corps, côté, pose, fermeture 0–1)` et `release_grasp` ; ajouter un objet tenu ferme la main, retirer le dernier objet tenu la rouvre.
- **Poignée calée sur les doigts** : le centre de la poignée est le centre des articulations des quatre doigts refermés, son rayon 60 % de leur distance moyenne : les bouts des doigts sont au contact de la poignée (mesuré).
- Le fût du parapluie et les sacs pendent à la verticale (axe de la poignée ramené à l'horizontale).

## Mesures (`validate_accessories`)
| Critère | Résultat |
|---|---|
| A2 sac à dos : pénétration au repos | 0 sommet à l'intérieur ; distance minimale au dos 8,3 mm |
| A2 lunettes | centrées sur l'axe des yeux (0,0 mm d'écart), distance minimale au visage 2,8 mm, 0 sommet à l'intérieur |
| A3 l'accessoire suit l'os | main déplacée de 51 cm par une rotation du bras : le téléphone reste à moins de 2 cm de la paume |
| A4 préhension | bouts des doigts / paume : 0,62 de la distance de la main ouverte ; progression monotone (0,5 puis 1) ; retour exact à la main ouverte ; bouts à 3–6 cm du centre de la poignée |
| A5 parapluie | largeur 9 cm fermé, 98 cm ouvert |
| A6 échelle | sac de courses 45 cm (adulte) contre 30 cm (enfant) |

## Limites connues
- Pas de pose de bras « téléphone à l'oreille » (il faudrait de l'IK ou une animation dérivée) : le téléphone est tenu dans la paume, bras le long du corps.
- Formes schématiques (pas d'ouverture de fermeture éclair, de poches, de baleines de parapluie) ; matériaux sans texture.
- La préhension « poignée » ferme les quatre doigts de façon symétrique ; le pouce est fermé avec le même sens que l'index (approximation, non mesuré séparément).
- Pas de contact physique garanti entre l'objet et les doigts autre que la mesure de proximité des bouts de doigts ; pas d'ajustement fin phalange par phalange.
- Les accessoires du visage (lunettes) ne tiennent pas compte de la forme du nez au-delà de la distance minimale mesurée.
