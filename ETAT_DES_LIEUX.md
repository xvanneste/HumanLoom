# ÉTAT DES LIEUX EXHAUSTIF — HumanLoom 0.15.2 (schéma 9)

Date : 2026-11-21. Base : `codex/groom` @ `443d278`, Blender 5.2.0 LTS. Tests faits sur un clone isolé, dans mes propres instances de Blender, jamais dans la session de l'utilisateur. Aucune modification du plugin. Données brutes : `docs/audit/*.json` ; images : `docs/audit/*.png`.

**Légende :** ✅ validé (exécuté avec succès) · 🟡 partiel / avec réserve · ❌ défaut reproduit · ⬜ non testé · ➖ absent.

**Limites générales :** mesures géométriques faites sur la cage (modificateurs désactivés) sauf mention ; les croisements de triangles sont mesurés avec les modificateurs par défaut actifs. Le corps par défaut est masculin (Morphologie = 1, 168,9 cm). Rendus Workbench, sans matériaux (le plugin n'en fournit pas pour le corps). Mon accès pour piloter l'interface à la souris a été refusé : **undo/redo, glisser un slider à la souris, clics réels : ⬜ non testés**. L'interface a été vue par captures dans une instance de test (démarrage d'usine).

---

## 1. Résumé par domaine

| Domaine | État |
|---|---|
| Création du corps (`Créer un humain`) | ✅ 0,64 s, 10 582 sommets, schéma 9, 2 yeux, 459 drivers valides |
| Paquet / installation | ✅ `extension validate`, `extension build` (23,9 Mo), installation isolée, activation, création d'un humain et groom depuis le paquet installé |
| Enregistrer/désenregistrer ×3 | ✅ aucune classe résiduelle |
| Sauvegarde / réouverture `.blend` | ✅ schéma 9, 0 driver invalide |
| 48 sliders corps/corpulence/muscles/visage | 🟡 tous répondent ; effet souvent faible (§3) |
| Sexe, âge, silhouettes, variation | 🟡 fonctionnent ; différence d'âge 30/75 ans faible ; silhouettes faibles en profil (§4) |
| Corpulence | ❌ trois échelles incohérentes (§3.2) |
| Visage | 🟡 géométrie propre, mais amplitudes ≤ 7 mm (§3.3) ; yeux sans matériau |
| Matériaux, textures, dents, langue | ➖ corps et yeux sans matériau ; pas de dents (§5) |
| Mesures, repères, ajustement | 🟡 flux manuel complet qui fonctionne ; 3 mesures sur 7 non concluantes avec mes repères (§6) |
| Groom | ✅ 11 zones, suivi du corps ≤ 0,22 mm ; ❌ bug de bornes (§7) ; XPBD 🟡 |
| Rig, vêtements, poses, export dédié | ➖ |
| Undo/redo | ⬜ |

---

## 2. Inventaire de l'interface (tout ce qui est visible)

**Onglet « Humain » > « HumanLoom · Modélisation »** (panneau parent). Sous-panneaux : Silhouettes, Corps, Âge · formes de référence, Corpulence et tissus (+ « Volumes des anciennes versions »), Musculature, Visage, Préréglages, Mesures et référence, Repères et dimensions locales, Contrôle du maillage, **HumanLoom · Cheveux et pilosité**.

### 2.1 Opérateurs (32) : disponibilité par contexte

Polls mesurés : scène vide / corps actif / œil actif / mode Édition.

| Opérateur | Rôle | Vide | Corps | Œil | Édition | Résultat des tests |
|---|---|:-:|:-:|:-:|:-:|---|
| `human_modeling.create` | Créer un humain | ✅ | ✅ | ✅ | non | ✅ 3 créations indépendantes (mesh/clés distincts) |
| `set_height` | Régler la taille | non | ✅ | ✅ | non | ✅ 0,5 à 3,0 m exacts, sur la surface lissée ; ❌ sans bornes ; non-uniforme non corrigé |
| `smooth` | Aperçu lissé | non | ✅ | ✅ | non | 🟡 FINISHED mais le Subsurf existe déjà (redondant) |
| `reset_proportions` | Réinitialiser | non | ✅ | ✅ | non | ✅ retour à 0 sans résidu |
| `add_proportions` | Mise à jour des réglages (anciens fichiers) | non | non | non | non | ⬜ poll faux sur un corps courant (attendu) ; migration non testable (pas de fichier ancien) |
| `body_profile` | Silhouettes (8) | non | ✅ | ✅ | non | ✅ 8/8 s'appliquent |
| `age_reference` | 5/15/30/75 ans | non | ✅ | ✅ | non | ✅ |
| `calibrate_age_height` | Stature source F/M | non | ✅ | ✅ | non | ✅ 8 cas sexe × âge (§4) |
| `randomize` | Variation (visage/corps/tout) | non | ✅ | ✅ | non | ✅ 6 cas + 30 graines : 0 croisement |
| `save_preset` / `load_preset` | Préréglage JSON | non | ✅ | ✅ | non | ✅ aller-retour 0,0 mm ; mélange à 50 % non linéaire |
| `reference_height` | Appliquer la stature de référence | non | ✅ | ✅ | non | ✅ 30–39 M P50 → 176,4 cm |
| `measurement_report` | Exporter contrôle dimensionnel | non | ✅ | ✅ | non | ✅ 42 combinaisons groupe×sexe×percentile sans erreur |
| `mark_pelvis`, `mark_anatomy` | Placer un repère | non | non | non | ✅ | ✅ 10 repères posés (en Édition, 1 sommet sélectionné) |
| `fit_measurement` | Ajuster la dimension (7 mesures) | non | ✅ | ✅ | non | 🟡 4/7 réussis, 3 non concluants (§6) |
| `save_landmarks` / `load_landmarks` | Repères JSON | non | ✅ | ✅ | non | ✅ |
| `mirror_landmarks` | Compléter par symétrie | non | ✅ | ✅ | non | ✅ ; renvoie CANCELLED quand rien à faire |
| `check_geometry` / `export_geometry_report` | Contrôle du maillage | non | ✅ | ✅ | non | ✅ (§3.4) |
| `repair_surface` | Corriger les paupières internes | non | ✅ | ✅ | non | ✅ FINISHED (effet non mesuré) |
| `humanloom.groom_build/select/apply/quality/remove/paint/export/import/preset` | Groom | non | ✅ | ✅ | non | ✅ sauf bornes (§7) |
| `humanloom.groom_density` | Clairsemé/Normal/Dense | non | non* | non* | non | ✅ une fois une zone « Cheveux » présente |

\* exige une zone Cheveux existante.

### 2.2 Réglages hors sliders de contrôle
Morphologie (0–1), Transition d'âge (0–3), Subdivision (1), Taille (dialogue), propriétés `hm_landmark`, `hm_reference_group/sex/percentile` (7×2×3 = 42 combinaisons ✅).

---

## 3. Les 48 sliders de morphologie (mesures)

Déplacement maximal d'un sommet, mesuré sur la cage, corps masculin adulte, ±1. « Zone » = centre de gravité des sommets déplacés de plus de moitié du maximum (hauteur relative à la taille ; avant (−)/arrière (+) en mm). « Croisements » : paires de triangles qui se coupent après lissage (0 partout). « Yeux » : déplacement de l'œil à +1. Dernière colonne : amplitude à +1 selon sexe et âge.

| Contrôle (id) | Libellé UI | ±1 : déplacement max (mm) | Zone (hauteur rel. / avant−arrière) | Croisements ±1 (lissé) | Yeux | Max à +1 : féminin / 5 ans / 15 ans / 75 ans (mm) |
|---|---|---|---|---|---|---|
| `corpulence` | Corpulence | 19.39 / 29.84 | 0.558 / -28 mm | 0/0 | 0 mm | 29.11 / 21.16 / 29.84 / 29.55 |
| `shoulders` | Carrure | 14 / 14 | 0.559 / -62 mm | 0/0 | 0 mm | 14 / 9.93 / 14 / 13.87 |
| `waist` | Tour de taille | 17.97 / 17.97 | 0.604 / -34 mm | 0/0 | 0 mm | 17.22 / 12.75 / 17.98 / 17.8 |
| `hips` | Largeur du bassin | 17.83 / 17.83 | 0.48 / -27 mm | 0/0 | 0 mm | 17.84 / 12.65 / 17.83 / 17.66 |
| `torso_depth` | Profondeur du buste | 12.94 / 12.94 | 0.705 / -50 mm | 0/0 | 0 mm | 13.52 / 9.18 / 12.95 / 12.82 |
| `neck` | Largeur du cou | 14.42 / 14.42 | 0.828 / 9 mm | 0/0 | 0 mm | 16.46 / 10.23 / 14.42 / 14.28 |
| `legs` | Longueur des jambes | 48.67 / 48.67 | 0.764 / -69 mm | 0/0 | 48.67 mm | 47.21 / 43.16 / 48.67 / 48.51 |
| `torso` | Longueur du buste | 28 / 28 | 0.889 / -72 mm | 0/0 | 28 mm | 28 / 24.83 / 28 / 27.91 |
| `whole_body` | Corpulence globale | 19 / 34.13 | 0.612 / -9 mm | 0/0 | 0 mm | 29.9 / 40.47 / 74.61 / 86.94 |
| `body_mass` | Volume hérité · 0.12 | 32.67 / 93.35 | 0.565 / -68 mm | 0/0 | 0 mm | 93.11 / 52.92 / 65.34 / 92.46 |
| `adiposity` | Couverture régionale | 18.15 / 45.36 | 0.578 / -53 mm | 0/0 | 0 mm | 41.64 / 32.18 / 45.37 / 44.93 |
| `fat_abdomen` | Abdomen | 17.41 / 43.52 | 0.604 / -133 mm | 0/0 | 0 mm | 39.37 / 30.87 / 43.52 / 43.11 |
| `fat_flanks` | Flancs | 10.07 / 25.17 | 0.596 / 6 mm | 0/0 | 0 mm | 25.86 / 17.85 / 25.17 / 24.93 |
| `fat_hips` | Bassin et fessiers | 11.03 / 27.58 | 0.47 / 56 mm | 0/0 | 0 mm | 25.44 / 19.56 / 27.58 / 27.31 |
| `fat_thighs` | Cuisses | 5.72 / 14.29 | 0.355 / 26 mm | 0/0 | 0 mm | 15.21 / 10.14 / 14.29 / 14.15 |
| `fat_arms` | Bras | 5.82 / 14.56 | 0.663 / 15 mm | 0/0 | 0 mm | 15.25 / 10.33 / 14.56 / 14.42 |
| `fat_face` | Visage | 3.37 / 8.43 | 0.904 / -121 mm | 0/0 | 0 mm | 8.45 / 7.31 / 8.43 / 8.4 |
| `muscles` | Musculature globale | 20.22 / 27.48 | 0.595 / 17 mm | 0/0 | 0 mm | 28.51 / 4.06 / 13.6 / 14.55 |
| `muscles_shoulders` | Épaules | 6.01 / 17.18 | 0.793 / 0 mm | 0/0 | 0 mm | 15.79 / 3.09 / 10.92 / 10.82 |
| `muscles_chest` | Pectoraux | 6.82 / 19.48 | 0.772 / -118 mm | 0/0 | 0 mm | 18.72 / 1.82 / 6.41 / 6.35 |
| `muscles_back` | Dos | 7.25 / 20.7 | 0.749 / 98 mm | 0/0 | 0 mm | 18.12 / 2.06 / 7.27 / 7.2 |
| `muscles_arms` | Bras | 7.37 / 21.06 | 0.713 / 19 mm | 0/0 | 0 mm | 12.15 / 2.77 / 9.77 / 9.68 |
| `muscles_abdomen` | Abdomen | 1.17 / 3.34 | 0.69 / -136 mm | 0/0 | 0 mm | 2.19 / 0.39 / 1.37 / 1.36 |
| `muscles_glutes` | Fessiers | 5.85 / 16.72 | 0.503 / 113 mm | 0/0 | 0 mm | 15.99 / 3.09 / 10.88 / 10.78 |
| `muscles_thighs` | Cuisses | 8.32 / 23.77 | 0.415 / -19 mm | 0/0 | 0 mm | 22.24 / 2.41 / 8.49 / 8.41 |
| `muscles_calves` | Mollets | 6.53 / 18.67 | 0.194 / 102 mm | 0/0 | 0 mm | 16.21 / 2.01 / 7.1 / 7.03 |
| `muscle_definition` | Définition musculaire | 0.48 / 0.48 | 0.664 / -136 mm | 0/0 | 0 mm | 0.5 / 0.14 / 0.48 / 0.48 |
| `head_width` | Largeur de la tête | 6.39 / 6.39 | 0.929 / -60 mm | 0/0 | 2.31 mm | 6.15 / 5.67 / 6.39 / 6.37 |
| `head_height` | Hauteur de la tête | 8.86 / 8.86 | 0.917 / -102 mm | 0/0 | 0 mm | 8.55 / 7.85 / 8.86 / 8.83 |
| `jaw` | Largeur de la mâchoire | 6.73 / 6.73 | 0.888 / -119 mm | 0/0 | 0 mm | 6.56 / 5.47 / 6.73 / 6.69 |
| `chin` | Avancée du menton | 4 / 4 | 0.871 / -133 mm | 0/0 | 0 mm | 4 / 3.1 / 4 / 3.97 |
| `cheeks` | Pommettes | 2.97 / 2.97 | 0.917 / -119 mm | 0/0 | 0 mm | 2.98 / 2.6 / 2.97 / 2.95 |
| `nose_length` | Avancée du nez | 4.99 / 4.99 | 0.914 / -155 mm | 0/0 | 0 mm | 4.98 / 4.39 / 4.99 / 4.98 |
| `nose_width` | Largeur du nez | 1.78 / 1.78 | 0.913 / -148 mm | 0/0 | 0 mm | 1.82 / 1.56 / 1.78 / 1.77 |
| `mouth` | Largeur de la bouche | 2.26 / 2.26 | 0.893 / -134 mm | 0/0 | 0 mm | 2.26 / 1.89 / 2.26 / 2.25 |
| `lips` | Relief des lèvres | 1.5 / 1.5 | 0.894 / -141 mm | 0/0 | 0 mm | 1.5 / 1.25 / 1.5 / 1.49 |
| `eye_spacing` | Écartement des yeux | 3 / 3 | 0.934 / -120 mm | 0/0 | 3 mm | 3 / 2.66 / 3 / 2.99 |
| `eye_height` | Position verticale des yeux | 2.5 / 2.5 | 0.936 / -120 mm | 0/0 | 2.5 mm | 2.5 / 2.22 / 2.5 / 2.49 |
| `forehead` | Hauteur du front | 5 / 5 | 0.984 / -78 mm | 0/0 | 0 mm | 5 / 4.43 / 5 / 4.98 |
| `ears_size` | Taille des oreilles | 4.64 / 4.64 | 0.924 / -34 mm | 0/0 | 0 mm | 4.75 / 4.11 / 4.64 / 4.62 |
| `ears_angle` | Orientation des oreilles | 4.56 / 4.56 | 0.925 / -36 mm | 0/0 | 0 mm | 4.54 / 4.04 / 4.56 / 4.54 |
| `eyelid_aperture` | Ouverture des paupières | 0.63 / 0.63 | 0.934 / -133 mm | 0/0 | 0 mm | 0.64 / 0.56 / 0.63 / 0.63 |
| `nose_bridge` | Relief de l’arête nasale | 3 / 3 | 0.928 / -147 mm | 0/0 | 0 mm | 2.99 / 2.66 / 3 / 2.99 |
| `lip_thickness` | Épaisseur des lèvres | 1.06 / 1.06 | 0.894 / -144 mm | 0/0 | 0 mm | 1.04 / 0.89 / 1.06 / 1.05 |
| `mouth_corner` | Hauteur des commissures | 1.99 / 1.99 | 0.893 / -136 mm | 0/0 | 0 mm | 1.99 / 1.63 / 1.99 / 1.98 |
| `jaw_angle` | Angle de la mâchoire | 3.35 / 3.35 | 0.879 / -113 mm | 0/0 | 0 mm | 3.26 / 2.62 / 3.35 / 3.32 |
| `facial_asymmetry` | Asymétrie du visage | 1.76 / 1.76 | 0.915 / -129 mm | 0/0 | 0.99 mm | 1.76 / 1.53 / 1.76 / 1.75 |
| `skin_relief` | Relief de peau âgée | 0 / 0 | 0.545 / -54 mm | 0/0 | 0 mm | 0 / 0 / 0 / 0 |

### 3.1 Constats sur les sliders
1. **Tous répondent**, valeurs finies, retour à 0 sans résidu, aucun croisement (±1, modificateurs actifs).
2. **Amplitude faible** : pour le visage, le maximum est de 0,6 à 8,9 mm sur une tête de 182 × 214 mm ; dix contrôles < 3 mm. Les rendus (`docs/audit/`, grilles de visage) montrent des différences à peine visibles à ±1.
3. **Étiquette vs zone** : la zone déplacée correspond au libellé (jaw, nose, mouth, ears, glutes, calves, thighs : ✅). **Diaphonies** : « Carrure » (`shoulders`) à ±1 modifie aussi la taille (±13,8 mm) et le bassin (±18 mm) ; « Pectoraux »/« Bras » modifient la largeur du buste ; « Longueur des jambes », « Longueur du buste », « Hauteur de la tête », « Hauteur du front » changent la stature (±48,7, ±28, ±8,9, ±5 mm).
4. **Contrôle masqué** : `corpulence` n'est pas affiché dans l'interface quand `whole_body` existe, mais il reste actif et la variation aléatoire (corps) le modifie.
5. **`skin_relief`** : sans effet avant 30 ans ; 0,38 mm à 2,5 ; 0,76 mm à 75 ans (pilotage par `max(0, stade−2)·0,002·(1+amount)`).
6. **Yeux** : suivent `eye_spacing` (+6 mm entre les yeux), `eye_height` (2,5 mm), `head_width` (+4,6 mm), `facial_asymmetry` (1 mm), la stature ; immobiles pour les autres.
7. **Dépendance à l'âge** : l'amplitude de la plupart des contrôles est réduite à 5 ans (~0,7×), mais **`whole_body` vaut 34 mm à 30 ans, 40 mm à 5 ans, 75 mm à 15 ans, 87 mm à 75 ans** ; `body_mass` 93/53/65/92 mm ; les muscles sont réduits à 5 ans (4 mm contre 27) et de moitié à 15 et 75 ans.
8. **Sexe** : `muscles_arms` 21 mm (M) contre 12 mm (F) ; le reste est comparable.

### 3.2 Corpulence : trois échelles différentes (rendus `rendu-corpulence-*.png`)
Largeur/profondeur de coupe à la taille et au bassin, ±1, mm (masculin) :

| Contrôle | Taille −1 | Taille +1 | Bassin −1 | Bassin +1 |
|---|---|---|---|---|
| `whole_body` (UI « Corpulence globale ») | −34 / −30 | +61 / +35 | −16 / −10 | +64 / +39 |
| `adiposity` (UI « Couverture régionale ») | −22 / −8 | +56 / +19 | −11 / −6 | +33 / +15 |
| `body_mass` (« Volume 0.12 », hérité) | −45 / −42 | **+129 / +119** | −31 / −38 | +89 / +115 |
| `corpulence` (masqué) | −25 / −26 | +39 / +40 | −33 / −31 | +50 / +48 |

Rendu : `whole_body` +1 donne un ventre modéré, `adiposity` +1 aussi, **`body_mass` +1 donne un ventre très proéminent et, chez le corps féminin, un bassin si large que les cuisses se confondent en vue de face**. Le contrôle principal affiché est donc le plus faible, le plus fort est un « volume hérité ». Les amplitudes dépendent de l'âge de façon incohérente (§3.1 point 7). Cohérent avec le README (extrêmes insuffisants, projection abdominale).

### 3.3 Visage (rendus gros plan `rendu-visage-*.png`)
Géométrie propre et symétrique (asymétrie de base 0,15 mm), oreilles, narines, paupières présentes ; bouche fermée sans intérieur ; **les deux sexes ont des visages proches** ; yeux = sphères sans matériau (ni iris, ni sclère, ni pupille).

### 3.4 Qualité du maillage
Fermé (1 composante, 0 arête limite, 0 non-manifold, 0 face nulle). Croisements de triangles : **maillage de base seul : 68 (pieds 61, tête 7)** ; **avec Subsurf + relief : 0**, y compris pour chacun des 96 réglages ±1, les 30 graines aléatoires (force 1, tout) et tous les contrôles à −1 ; **tous les contrôles à +1 simultanément : 168 croisements (mains/bras)**.

---

## 4. Sexe, âge, silhouettes, variation

- **Morphologie (0 → 1)** : taille 1,639 → 1,690 m, largeur 0,842 → 0,881 m, valeurs finies ✅.
- **Âge** (féminin, cage) : 5 ans 1,094 m ; 15 ans 1,617 ; 30 ans 1,639 ; 75 ans 1,630. Interpolation continue (stade 0,5 = 1,356 m). Visuellement, 30 et 75 ans sont très proches (`rendu-ages-sexes.png`) ; l'enfant a des proportions d'adulte réduites. Les textes de l'interface le disent : « amplitude artistique », non chronologique.
- **Calibration de stature** (`calibrate_age_height`) : F 109,4 / 161,7 / 162,8 / 157,9 cm ; M 110 / 169 / 176,4 / 172,7 cm pour 5/15/30/75 ans ✅.
- **Silhouettes** : profondeur de buste de 0,281 (très mince) à 0,346 m (forte corpulence) ; largeur identique ; projection abdominale faible en profil ❌ léger (`rendu-silhouettes-profil-M.png`).
- **Variation** : visage, corps, tout ; graine reproductible ✅ ; la variation « corps » modifie aussi le contrôle masqué `corpulence`.

## 5. Matériaux, textures, anatomie fine
Corps : **0 matériau**, 1 UV (`UVMap`), 1 groupe de sommets (`HM · Relief visage`). Yeux : 546 sommets chacun, UV, **0 matériau**. Pas de dents, langue ni intérieur de bouche. Matériaux uniquement pour les cheveux (Principled Hair BSDF). Pas de rig.

## 6. Mesures, repères, ajustement

Flux : repères posés à la main sur un sommet en mode Édition (10 repères ✅). Mesures : largeur/profondeur/stature, distances de visage, sections. `fit_measurement` (avec **mes** repères, placés au jugé) :

| Mesure | Résultat |
|---|---|
| Taille (périmètre abdominal) | ✅ 87,7 → 92,1 cm demandé et obtenu ; plage permise 79,8–95,7 cm |
| Bassin (périmètre) | ✅ 99,5 → 104,4 cm ; plage 93,8–105,2 cm |
| Distance intercanthale | ✅ 52,5 → 55,2 mm ; plage 46,5–58,5 mm |
| Sol → repère / stature | ✅ 51,5 → 52,5 % ; plage 50,0–52,8 % |
| Thorax (périmètre) | ⬜ cible hors plage 157–168 cm (mon repère donne probablement une coupe qui englobe les bras) |
| Largeur du nez | ⬜ « La mesure ne varie pas régulièrement avec ce réglage et ces repères » (mes repères) |
| Largeur de la bouche | 🟡 plage permise 74,0–76,2 mm seulement (±1,5 %) : un ajustement de 5 % est refusé |

Les ajustements hors plage sont refusés avec un message précis ✅. Les 42 combinaisons de référence NHANES (7 groupes × 2 sexes × 3 percentiles) répondent sans erreur ✅. Aucun repère n'est placé automatiquement.

## 7. Groom (détail)

- **Construction** : 11 zones, 0,55 à 1,9 s chacune, 4 modificateurs (densité, suivi 5.2, profil, matériau) ✅. « Pilosité adulte » (9 zones) 2,0 s ✅. Guides : 850 (cheveux), 240 (sourcils), 500 (barbe), 240 (moustache), 420, 280, 350, 550, 800, 160, 220.
- **Suivi du corps** : racines à ≤ 0,22 mm de la surface après morphologie extrême et mise à l'échelle ✅.
- **Qualité du viewport** : Léger 9 786, Équilibré 29 324, Complet 97 774 mèches évaluées ✅ ; viewport 0 % → 0 mèche ; densité 0 → 0 mèche ; densité 8 M/m² → 130 355 mèches.
- **Densités** : Clairsemé 700 000, Normal 1 800 000, Dense 2 500 000 /m² ✅ (l'infobulle annonce 250 cheveux/cm² = 2 500 000 ✅).
- **❌ Bug reproduit** : « Variation » = 0,8 (maximum du curseur) et « Rayon à la racine » à ses deux extrémités (5e-6 et 1,5e-4) provoquent « Valeur invalide » à l'application, car la valeur en simple précision dépasse la borne stricte de `validate()`. D'autres bornes passent par chance (rugosité 0,05, longueur 0,001/0,45).
- **Styles** (Vers l'arrière, Avec raie, Dressé), graine 0 et max, 20 et 3000 guides, longueur 1 mm et 45 cm : ✅ construisent.
- **Peindre la densité** : entre en Weight Paint ✅. **Export/import JSON** : 11 couches ; import refusé s'il existe déjà une zone ✅ ; JSON invalide refusé ✅ ; import après suppression ✅.
- **XPBD** : 12 images pour 128 guides ≈ 10,6 s (arrière-plan) ; allongement < 0,1 % sur banc droit ; collisions/longues coiffures : ⬜ non validés (README).
- Message « Zones manquantes ajoutées » même sans ajout.

## 7 bis. Interface réelle pilotée à la souris (instance de test, Blender 5.2, extension du clone)

| Action testée | Résultat |
|---|---|
| Onglet « Humain », panneau « HumanLoom · Modélisation » | ✅ s'affiche ; sous-panneaux « Corpulence et tissus » et « Musculature » repliés par défaut, « Repères… » et « Contrôle du maillage » aussi |
| Ajouter > Mesh > « Créer un humain » | ✅ entrée présente (icône générique) |
| « Créer un humain » (bouton) | ✅ le corps apparaît au curseur 3D, **à l'intérieur du cube par défaut** (invisible tant qu'on ne le masque pas) |
| Glisser le slider « Carrure » | ✅ 0,070 ; **Ctrl+Z → 0,000 ; Ctrl+Maj+Z → 0,070** |
| Silhouette « Musclé » | ✅ Musculature globale = 1,000 ; **undo/redo ✅** |
| « Régler la taille » (dialogue Taille / OK / Annuler) | ✅ glisser la valeur → 1,6 m ; échelle 0,941 ; la mesure du panneau affiche 158,9 cm ; **undo/redo ✅** |
| Âge « 5 ans » | ✅ forme d'enfant ; « Transition » passe à 0,000 |
| « Créer une variation » (dialogue) | ✅ s'ouvre : Graine 0, Amplitude 0,45, Zone Visage ; annulation ✅ |
| Groom « Court » | ✅ « Zones manquantes ajoutées. » ; objet « HumanLoom · Cheveux » ; **undo/redo ✅** ; ❌ rangé dans « Collection », pas dans celle du corps (I-28) |
| Panneau groom (largeur par défaut) | 🟡 libellés tronqués (« Variation de… », « Rayon à la ra… », « Densité au r… », « Viewport (… », « Reconstruire les guides (remplace la sc… ») ; « Densité au rendu » affichée 1800000.00 |
| Vue Cadrer la sélection | ✅ |

Non testé à la souris : saisie clavier dans un champ (mon outil de pilotage n'a pas réussi à taper dans les champs : limite de l'outil), glisser prolongé d'un slider (fluidité), boutons de mesures, repères, préréglages (sélecteur de fichiers), import/export, mode Édition, Weight Paint, undo multiple.

## 7 ter. Interface réelle : deuxième passe (clics réels)

| Action | Résultat |
|---|---|
| Slider « Morphologie » glissé | ✅ 0,829, la forme du corps change à l'écran |
| Champ « Subdivision » | 🟡 un glisser ouvre l'édition de texte ; la flèche droite fonctionne (1 → 2) ; **la saisie au clavier n'a pas fonctionné avec mon outil de pilotage** (limite de l'outil) |
| Âge 5 / 15 / 75 ans, « Stature source M » | ✅ 75 ans : Transition 3,000, 15 ans : 1,000 ; la stature source change l'échelle |
| Mesures : Groupe (7 entrées), Sexe, Percentile ; « Appliquer la stature de référence » | ✅ 172,7 cm pour 70–79 M P50, écart +0,0 |
| « Exporter le contrôle dimensionnel » | ✅ sélecteur de fichiers (dossier par défaut : Documents de l'utilisateur, nom `Untitled.json`) ; annulé |
| « Contrôler le maillage » | ✅ affiche sommets, composantes, bords, non-manifold, faces nulles ; « Intersections non calculées » à Subdivision 2 |
| Groom « Pilosité adulte » | ✅ visible sur cuir chevelu, sourcils, barbe, torse, bras, jambes (viewport 30 %) ; le premier clic n'a pas été pris en compte (artefact probable de focus) |
| Densités Dense / Léger / Complet | ✅ « 250 cheveux/cm² », viewport 1,00 puis 0,10 |
| Dynamique XPBD, « Appliquer… » | 🟡 appliqué (« gravité XPBD »), mais ❌ interface figée ≈ 20 s puis ≈ 5–10 s par image à la lecture (I-31) ; retour à l'image 1 ✅ |
| « Sélectionner les guides », mode Sculpt Curves, brosse peigne | ✅ passage en sculpture, coup de brosse, annulation ; les boutons du panneau sont grisés hors mode Objet ✅ |
| Liste des zones (11) et ajout « Pubis » | ✅ |
| Mode Édition (Tab) | ✅ s'active (panneau groom grisé) ; sélection d'un sommet et pose d'un repère à la souris : ⬜ non menée à bout (touches clavier peu fiables avec mon outil) |

## 7 quater. Scripts historiques (voir `TEST_REPORT.md`)
27 réussis, 8 en échec par assertion (dont 4 tests périmés, 1 travail en cours, 3 écarts de forme vs 0.13 : I-30). Au total, avec les scripts exécutés plus tôt, la quasi-totalité des scripts de `tools/` a maintenant été exécutée au moins une fois.

## 8. Interface : voir `UI_REVIEW.md`
Captures : `ui-sidebar-*.png`, `ui-groom-panel.png`, `ui-rien-selectionne.png`. Panneaux sans erreur Python à l'affichage dans les états testés (corps seul, corps + groom, œil actif, rien de sélectionné, mode Édition : 0 trace d'erreur dans la console).

## 9. Non testé (explicite)
Saisie au clavier dans les champs et pose d'un repère à la souris (limite de mon outil de pilotage) ; undo en chaîne de plusieurs actions ; qualité de la sculpture de cheveux et collisions complexes (le travail `collision29` échoue encore) ; export vers d'autres formats ; performances de l'interface hors charge (mes mesures de XPBD ont été faites pendant un lot de tests) ; thème clair/panneau étroit ; Blender 5.3 (le manifeste borne à 5.3.0) ; comportement après suppression d'un enfant (yeux, repères) ; migration depuis des fichiers plus anciens que 0.13 ; le script `validate_controls` au-delà de la section de migration (fichier d'ancien schéma absent). Les migrations 0.13 → 0.14 (`regional_upgrade18`) et la compatibilité neutre (`regional_compat18`) sont validées.
