# Mesures de faisabilité — option C (déformation par Geometry Nodes)

Date : 2026-11-21. Blender 5.2.0 LTS, clone `codex/groom` @ `443d278`, scripts jetables (non versionnés), arrière-plan, CPU. Corps par défaut : 10 582 sommets.

## Structure des shape keys
- 461 clés hors `Basis`, 457 avec un delta non nul ; toutes relatives à `Basis`.
- Préfixes : `Age` 308, `HM` 135, `Surface` 11, `Morphologie` 1, `Enfant` 2, `Adolescent` 2, `Senior` 2.
- Clés « correction » : 218 (correction au sexe de chaque contrôle).
- Les 308 clés `Age · {Enfant, Adolescent, Senior} · HM · …` déclinent chaque contrôle par stade d'âge.
- Matrice des deltas : 58,5 Mo (457 × 31 746 float32).

## Rang (SVD de la matrice des deltas)
| Seuil relatif au plus grand singulier | Rang effectif |
|---|---|
| 1e-3 | 69 |
| 1e-4 | 128 |
| 1e-5 | 150 |

## Mélange par Geometry Nodes (Nommé attribut → Échelle → Ajouter → Définir la position / Offset)
| R | médiane (ms) | p90 (ms) | attributs (Mo) | nœuds | erreur max vs numpy |
|---|---|---|---|---|---|
| 50 | 3,0 | 3,2 | 6,3 | 152 | 0,0 mm |
| 150 | 7,8 | 8,4 | 19,0 | 452 | 0,0 mm |
| 300 | 19,8 | 23,9 | 38,1 | 902 | 0,0 mm |
| 457 | 37,5 | 51,8 | 58,0 | 1 373 | 0,0 mm |

Mesure : 30 évaluations avec poids aléatoires, mise à jour de l'objet, lecture du maillage évalué (`to_mesh`). Référence actuelle : 11 ms (cage, shape keys + 459 drivers).

## Limites
Somme linéaire seulement ; non-linéarités des drivers, interpolation d'âge/sexe, yeux, coût dans l'interface réelle, taille du `.blend` et erreur de reconstruction d'une base réduite non mesurés. Un premier essai donnait une erreur apparente de 250 mm : elle venait d'une base de comparaison différente (sommets du maillage vs clé de référence) dans mon script, corrigée ensuite (erreur 0,0 mm).

## Compléments (prototype P7, même date)
- Le modèle « forme = base + Σ valeur_clé × delta » est exact : erreur max 0,0009 mm sur 40 états aléatoires (déplacement jusqu'à 547 mm).
- Erreur de reconstruction par une base réduite (SVD) : R = 50 → 11,4 mm ; 70 → 3,2 ; 100 → 1,9 ; 128 → 0,42 ; **150 → 0,047** ; 200 → 0,0009 (maximum sur 40 états ; médiane du maximum : 3,9 / 2,0 / 0,93 / 0,15 / 0,02 / 0,0007 mm).
- Taille de fichier (non compressé) : corps avec 461 shape keys 79,3 Mo ; + 150 attributs 98,5 Mo (+19,2) ; compressé 41,9 Mo. Remplacer les clés par la base donnerait ≈ 40 Mo (estimation).
- Structure des poids actuels : 119 expressions de driver distinctes (produits de fonctions « chapeau » d'âge, du sexe et d'écrêtages), toutes exprimables avec des nœuds Math.
- Non testé : cheveux et yeux suivant un corps déformé par un modificateur de nœuds ; poids calculés en nœuds ; temps dans l'interface réelle.
