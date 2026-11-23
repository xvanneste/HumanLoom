# CONCEPTION V0 — vêtements : accrochage à la surface, masques, poids hérités, pénétration (rapport de conception)

Date : 2026-11-23. Statut : conception avant le code (lots V1 à V4). Entrées : `TEST_FINAL_FOULE_PARIS.md` §C et §D, `CONCEPTION_A2_RIG.md` (squelette, poids). Un prototype jetable de mesure a été exécuté (`tools/proto_garment_measure.py`, aucune donnée tierce). **Pas de validation à l'œil à ce stade** : aucune planche de vêtement n'a été produite.

## 1. Mesure faite : vêtement « surface décalée » sous pose
Principe testé : une région du corps (sommets dont l'os dominant appartient à un ensemble) est décalée le long de la normale du corps de `d` mètres ; le vêtement reçoit **les poids de peau du corps** (mélange linéaire, mêmes 4 influences). Deux régions : « haut » (colonne, clavicules, bras : 1 835 sommets) et « bas » (bassin, jambes : 1 460 sommets). 5 morphologies (défaut, homme âgé, femme jeune, enfant, gabarit modifié), 6 poses (coude 90°, épaule levée 90°, épaule fléchie 90°, genou 90°, hanche 60°, torsion du buste 45°), décalages de 5, 10 et 20 mm, mesure de la profondeur de pénétration dans le corps posé (signe par la normale de la face la plus proche).
- **Au repos, sur toute morphologie** : le vêtement est à `d` de la peau **par construction** (distance mesurée = décalage à 0,01 mm près) : **aucun ajustement à recalculer quand la morphologie change**, puisque la topologie est fixe et que le vêtement est défini par rapport à la surface évaluée.
- **Sous pose** : part des sommets du vêtement qui pénètrent le corps de plus de 1 mm : **0,07 à 2,5 %** (haut : 0,27 à 2,5 % ; bas : 0,07 à 0,5 % à 5–10 mm) ; la pire pose est presque toujours **l'épaule (fléchie ou levée) pour le haut, le genou ou la hanche pour le bas** ; profondeur maximale ≈ le décalage lui-même (5 mm pour 5 mm, 10 pour 10, 20 pour 20 pour le haut) : quelques sommets du creux de l'aisselle/pli reviennent sur la peau. Plus le décalage est grand, plus la fraction en pénétration augmente légèrement (haut : 1,1 → 2,0 % de 5 à 20 mm sur le corps par défaut).
- **Conclusion mesurée** : l'approche est viable pour des pièces proches du corps ; les pénétrations restantes sont **localisées aux plis** et se corrigent par une passe de dégagement (§4) ; elle ne convient pas telle quelle aux pièces amples (robe, manteau long), qui demandent la simulation de tissu (V4) ou des poids propres.

## 2. Accrochage à la surface (choix)
- **Choix** : le vêtement procédural est un **sous-maillage de la topologie du corps** (faces dont tous les sommets sont dans un masque), décalé le long de la normale du corps évalué ; il est produit par un groupe de nœuds (comme `HL Human`) qui lit le corps : épaisseur, ourlet (coupe par une courbe de niveau sur la surface), aisance par région (poitrine, taille, hanches), couches (décalage cumulatif). Aucun recalage quand la morphologie change.
- **Alternative écartée pour les pièces d'origine** : Surface Deform/Shrinkwrap de Blender (liaison à calculer, dérive sur morphologies extrêmes, plus lent) ; **retenue pour les pièces importées** (V2) : liaison par correspondance de surface (triangle d'ancrage + coordonnées barycentriques + décalage normal, comme le groom) calculée une fois et à la demande.
- **Ordre des modificateurs** : `HL Human` → corps ; le vêtement est un objet enfant qui lit le corps évalué **avant** l'armature (ses sommets se déforment avec le rig par les poids hérités), puis passe de dégagement.

## 3. Masques du corps
- **Régions de base** (sommets du corps) dérivées des poids du squelette (os dominant) : colonne et clavicules, bras, avant-bras, mains, bassin, cuisses, jambes, pieds, cou, tête ; **limites nettes** (ourlets) définies par des courbes de niveau (hauteur, distance géodésique) pour que le bord d'une manche ne suive pas la frontière des poids.
- **Masquage de la peau** sous le vêtement : attribut de sommet « couvert » + modificateur de masque sur le corps (le corps reste évalué, seul son rendu est masqué) ; à mesurer : économie de rendu sur 150 personnages (lot T).
- **Couches** : sous-vêtement, haut, veste, manteau ; ordre, décalage cumulatif (5, 10, 20 mm d'après la mesure ci-dessus), aucune intersection au repos par construction.

## 4. Poids hérités et correctifs
- Poids du vêtement = **poids du corps** au même sommet d'ancrage (mesuré ci-dessus), 4 influences maximum. Les vêtements suivent donc les animations retargetées (A3) sans calcul propre.
- **Passe de dégagement** (proposée, à mesurer en V1) : après la déformation, pousser les sommets du vêtement qui pénètrent le corps posé vers l'extérieur le long de la normale du corps jusqu'à `d` (tracé de rayons ou plus proche point sur la surface posée) ; critère : fraction en pénétration ≤ 0,5 % et profondeur ≤ 2 mm sur les 6 poses de test ; coût mesuré en ms par pièce (objectif ≤ 5 ms par personnage lointain, LOD).
- **Simulation de tissu (V4)** : optionnelle, par pièce, avec cache ; désactivée par défaut dans la foule.

## 5. Critères d'acceptation chiffrés
| # | Critère | Seuil proposé |
|---|---|---|
| V-1 | Distance vêtement–peau au repos sur 5 morphologies | décalage demandé ± 0,1 mm |
| V-2 | Pénétration sous les 6 poses (corps posé), après la passe de dégagement | ≤ 0,5 % des sommets, profondeur ≤ 2 mm |
| V-3 | Étirement d'arête du vêtement et faces retournées sous pose | ≤ référence du corps (CONCEPTION_A2 : mêmes seuils par classe de pose) |
| V-4 | Pièces d'origine : 15 pièces (haut, bas, robes, vestes, chaussures, couvre-chefs, accessoires) | construites sans asset tiers ; vérifiées sur les 5 morphologies |
| V-5 | Temps de mise à jour d'une pièce quand la morphologie change | < 100 ms ; évaluation d'un personnage habillé ≤ 33 ms (critère existant) |
| V-6 | Import d'un vêtement de l'utilisateur : ajustement automatique | rapport de pénétration chiffré ; échec signalé, jamais masqué |
| V-7 | Tenue enregistrable | liste de pièces + couleurs + ordre des couches rechargée à l'identique (empreinte) |
| V-8 | Licence | aucune pièce tierce dans le dépôt ; les vêtements importés restent dans le dossier de l'utilisateur |

## 6. Jeu de morphologies de test (5) et planche
Défaut, homme âgé, femme jeune, enfant, gabarit modifié (jambes +1, torse −1) : celles du prototype. Planche de contrôle à produire en V1 : chaque pièce sur les 5 morphologies au repos et dans 2 poses (épaule fléchie 90°, genou 90°), fil de fer + surface, pour validation à l'œil par l'utilisateur.

## 7. Limites annoncées
- Pièces amples, plis dynamiques, glissement des tissus : non couverts sans simulation (V4, à mesurer).
- Les 0,07 à 2,5 % de sommets en pénétration sont **avant** la passe de dégagement (non encore écrite).
- Rien n'a été validé visuellement ; le prototype mesure des distances, pas l'apparence.
- Les accessoires (sacs, téléphone, parapluie) et les poses de main (V3) ne sont pas traités ici.
