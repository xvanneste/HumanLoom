# REGROUPEMENT_CONTROLES — contrôles redondants (proposition, rien n'est modifié)

Date : 2026-11-21. Mesure : `tools/audit/control_similarity.py` → `docs/audit/mesures-controles-similarite.json`. Pour chacun des 48 contrôles, on mesure le champ de déplacement des sommets à +1 (cage seule, état neutre adulte), puis la **similarité cosinus** entre deux contrôles (1 = même déformation, 0 = indépendantes) et le **recouvrement** des sommets déplacés. Limite : état neutre seulement (pas selon l'âge ni le sexe) ; une forte similarité n'implique pas que deux contrôles aient le même *sens* pour l'artiste.

## 1. Fortes redondances mesurées

| Groupe | Mesures | Constat | Proposition |
|---|---|---|---|
| **Corpulence** : `corpulence`, `whole_body`, `body_mass` (« Volume hérité · 0.12 »), `adiposity` | corpulence↔whole_body cos 0,82 ; corpulence↔body_mass 0,81 ; whole_body↔body_mass 0,73 ; body_mass↔adiposity 0,66 | quatre échelles de corpulence qui déforment presque dans la même direction (amplitudes différentes : `body_mass` +1 ≈ 93 mm contre 34 mm pour `whole_body`, I-16) | **Étape 1 (interface seulement)** : masquer `body_mass` et `corpulence` dans le panneau (les propriétés restent, les anciens fichiers fonctionnent) ; garder **« Corpulence globale »** (`whole_body`) et **« Couverture régionale »** (`adiposity`) puis les 6 zones de graisse. **Plus tard (schéma 10)** : une seule corpulence, sans changer la forme au neutre (D-10). |
| **Taille/flancs** : `waist` ↔ `fat_flanks` | cos 0,82 ; recouvrement 97 % | la même zone, par la structure (tour de taille) ou par la graisse (flancs) | **Garder les deux** pour l'instant (sens différents : ossature vs tissus) ; à fusionner seulement si la corpulence unifiée (schéma 10) les couvre. |
| **Mâchoire** : `jaw` ↔ `jaw_angle` | cos 0,77 ; `jaw` ↔ `mouth` 0,78 | trois contrôles qui agissent sur le bas du visage | **Candidat à regroupement** : sous-section « Mâchoire et menton » ; fusion de `jaw_angle` dans `jaw` à étudier (schéma 10). |
| **Nez** : `nose_length` ↔ `nose_bridge` | cos 0,75 | proches | regrouper visuellement (« Nez ») ; fusion non proposée. |
| **Lèvres** : `lips` ↔ `lip_thickness` | cos 0,61 ; recouvrement 80 % ; **amplitudes faibles** (1,5 et 1,06 mm à ±1) | deux curseurs faibles pour la même zone | **Candidat à fusion** (« Lèvres ») : à confirmer avec l'artiste ; fusion = schéma 10. |
| **Abdomen** : `adiposity` ↔ `fat_abdomen` 0,71 ; `muscles_abdomen` ↔ `muscle_definition` 0,70 | | un contrôle global et un régional : voulu | **Garder** (global + régional). |
| **Longueurs** : `legs` ↔ `torso` | cos 0,84 (recouvrement 64 %) | tous deux allongent le corps verticalement, mais sur des segments différents | **Garder** les deux ; renommer clairement (« Longueur des jambes » / « Longueur du buste »). |

## 2. Contrôles à très faible effet (< 2 mm à ±1) — pas des doublons, un problème d'amplitude

`muscle_definition` 0,48 mm · `eyelid_aperture` 0,63 mm · `lip_thickness` 1,06 mm · `lips` 1,5 mm · `facial_asymmetry` 1,76 mm · `nose_width` 1,78 mm · `mouth_corner` 1,99 mm · `skin_relief` 0,0 mm (**inactif avant 30 ans**, I-13). Ce sont des contrôles utiles mais **sous-dimensionnés** : plutôt qu'un regroupement, régler leur amplitude (chantier « amplitudes du visage ») et **griser** `skin_relief` quand il est sans effet.

## 3. Ce que je ferais à l'étape 1 (changement d'interface uniquement, sans toucher aux formes)

1. Masquer `body_mass` (« Volume hérité · 0.12 ») et le panneau « Volumes des anciennes versions » par défaut ; les ranger sous un réglage « Afficher les contrôles hérités ».
2. Ne montrer que « Corpulence globale » + « Couverture régionale » + zones de graisse.
3. Regrouper le visage en sous-sections repliables (yeux, nez, bouche et lèvres, mâchoire et menton, oreilles, peau).
4. Griser `skin_relief` quand l'âge le rend inactif.

Aucune propriété `hm_*` n'est supprimée ni renommée (D-02) ; aucun fichier existant ne change de forme.

## 4. Ce qui est reporté (migration schéma 10, avec test d'équivalence)

Fusion `corpulence`/`whole_body`/`body_mass` ; fusion éventuelle `lips`/`lip_thickness` et `jaw`/`jaw_angle` ; amplitudes des contrôles faibles.
