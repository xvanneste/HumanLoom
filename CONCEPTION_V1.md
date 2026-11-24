# CONCEPTION V1 — vêtements procéduraux d'origine (réalisation)

Suite de `CONCEPTION_V0.md`. Code : `extension/garments.py` (moteur), `extension/garments_ui.py` (panneau « Vêtements »). Tests : `tools/validate_garments.py` (G1–G10). Planche : `tools/render_garments_board.py` + `tools/assemble_garments_board.py`. Aucun asset tiers : toutes les pièces sont produites par le code à partir de la surface du corps.

## Réalisation
- **15 pièces** : T-shirt, chemise, pull, veste, manteau court, pantalon, jean, short, chaussures, bottes, chaussettes, bonnet, casquette (calotte), écharpe, gants. Chaque pièce est un SOUS-MAILLAGE de la topologie du corps (faces dont tous les sommets sont dans un masque), décalé le long de la normale du corps (de 3 à 22 mm selon la couche), avec un modificateur Solidify (épaisseur) et un modificateur Armature sur le même squelette.
- **Masque** : os dominant des poids stockés (colonne, bras, jambes, pieds…) + coupes le long des membres (manches, jambes : paramètre 0-1 de l'articulation proximale à la distale) + fenêtre de hauteur en fraction de la stature (l'ourlet est une ligne horizontale). Toutes les valeurs sont des choix de modélisation (non issus d'une publication).
- **Poids hérités** : copie des poids du corps (mêmes os, 4 influences), écrits par la couche de déformation (≈ 100 ms par pièce).
- **Couches** : dessous < haut < veste < manteau, décalages 5 / 8 / 14 / 22 mm (écart >= 3 mm, sans intersection au repos par construction).
- **Mise à jour** quand la morphologie change : recalcul des positions (topologie fixe), 40 à 50 ms pour un T-shirt.
- **Dégagement sous pose** (Shrinkwrap, surface proche, extérieur, offset = 0,6 × décalage) : optionnel (coûte ≈ 15 ms par pièce et par image : reconstruction de l'arbre du corps), COUPÉ par défaut.
- **Masque de la peau couverte** : groupe de sommets du corps + modificateur Masque (inversé) placé après le groupe de nœuds.
- **Tenues** : liste ordonnée par couche de {pièce, couleur, décalage}, enregistrée dans la scène (JSON) et rechargée à l'identique (empreinte de chaque pièce : clé, couleur, décalage, sommets, faces).
- **Matériaux** : Principled BSDF (couleur, rugosité) par pièce ; pas de texture.

## Mesures (`validate_garments`)
| Critère (V0) | Résultat |
|---|---|
| V-1 distance à la peau au repos, 5 morphologies | chaque sommet à son décalage ± 0,0001 mm de SA peau ; hauts/bas/vestes/couvre-chefs : au plus 2,5 % des sommets plus près d'une autre surface que 40 % du décalage (aisselle, entrejambe) ; pieds/mains/cou rapportés (jusqu'à 29 % pour l'écharpe, 9 % chaussures : doigts, orteils, menton) |
| V-2 pénétration sous 6 poses, après dégagement | part des sommets : 0,45 % au pire (<= 0,5 %) ✔ ; **profondeur maximale 8,1 mm : NON atteint (critère 2 mm)** : sous l'épaule fléchie ou levée le corps s'auto-intersecte à l'aisselle ; avant dégagement : 3,96 % et 14 mm |
| V-4 15 pièces sur 5 morphologies | ✔ (aucune exception, sommets finis, >= 100 sommets) |
| V-5 mise à jour d'une pièce | 40–53 ms (< 100 ms) ✔ ; évaluation d'un personnage habillé (3 pièces) : 12,8 ms sans dégagement ✔ (<= 33 ms), 59,8 ms avec dégagement ✘ |
| V-7 tenue enregistrable | rechargée à l'identique ✔ |
| V-8 licence | aucun nom ni fichier de vêtement tiers ✔ |

## V2 — galerie et import (réalisé)
- **Galerie** (panneau « Vêtements ») : grille par catégorie (Hauts, Vestes, Bas, Chaussures, Couvre-chefs, Accessoires) avec vignettes (`extension/data/garment_thumbs/`, index `garment_gallery.json`, générés par `tools/build_garment_gallery.py` hors du processus principal), boutons Ajouter / Retirer, étoile = favori (enregistré dans la scène), sélecteur de couleur, filtre « favoris seulement », tenues enregistrables (V-7), ordre des couches par construction (décalages croissants).
- **Import d'un vêtement de l'utilisateur** (`.obj`, `.fbx`, `.blend`, depuis SON dossier ; rien n'est copié dans le dépôt) : `garments.import_garment(body, fichier, mode)`. Mode « pose » : poids de peau transférés du corps (Data Transfer, face la plus proche interpolée) + Armature. Mode « morphologie » : Surface Deform lié au corps (suit la morphologie et la pose, sans Armature). Ajustement automatique au repos : mesure (distance moyenne à la peau, part des sommets à l'intérieur, profondeur maximale), puis les sommets intérieurs sont repoussés à 2 mm au-dessus de la peau ; **rapport chiffré** affiché. **Échec signalé, jamais masqué** : pièce trop éloignée (distance moyenne > 10 cm), plus de 20 % de sommets à l'intérieur, format inconnu, fichier absent, mode inconnu : l'erreur est levée et rien n'est laissé dans la scène.
- Tests (`tools/validate_garments_import.py` I1–I5, PASS) sur une pièce « de l'utilisateur » fabriquée par le test : poids transférés (82 groupes, somme moyenne 1,0), la pièce suit une pose (écart moyen à la pièce procédurale 0,2 mm), mode morphologie suit un changement de corpulence, pièce serrée repoussée (9 % de sommets intérieurs → 0), échecs signalés (trop petite : 83 % à l'intérieur ; éloignée : 86 cm).
- Limites : un vêtement importé n'est pas ajusté à nouveau automatiquement quand la morphologie change en mode « pose » (utiliser le mode « morphologie ») ; pas de tri automatique des couches pour les pièces importées ; fbx dépend de l'importateur fourni avec Blender ; les matériaux du fichier sont conservés tels quels.

## Limites connues
- Formes schématiques collées au corps : pas de pièces amples (robe, manteau long, jupe) sans simulation de tissu (V4) ; le veste et le manteau épousent le bassin (aspect « combinaison »).
- Pas de plis ni de tissu dynamique ; hem franc (ligne horizontale), pas d'ourlet ni de col/poche.
- Galerie à vignettes, import de vêtements de l'utilisateur, accessoires et poses de main : lots V2 et V3 (non faits).
- Le dégagement n'élimine pas les sommets déjà à l'intérieur du corps à l'aisselle (voir V-2).
