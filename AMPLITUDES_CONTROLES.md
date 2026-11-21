# AMPLITUDES_CONTROLES — contrôles « timides » et proposition d'augmentation

Date : 2026-11-21. Branche `codex/natif`. **Proposition, rien n'est modifié.** Mesures : `docs/audit/mesures-controles.json` (déplacement maximal en mm des sommets à ±1, état neutre, cage seule). Les ordres de grandeur anatomiques cités sont de la **connaissance générale non sourcée ici** (⚠) : ils servent à fixer des cibles, pas à valider.

## 1. Mesure : amplitude maximale à ±1 (triée)

| Groupe | Contrôles (max à ±1 en mm) | Verdict |
|---|---|---|
| **A — quasi invisible (< 1,6 mm)** | `skin_relief` 0 (inactif avant 30 ans) · `muscle_definition` 0,48 · `eyelid_aperture` 0,63 · `lip_thickness` 1,06 · `lips` 1,50 | timides ; à **réécrire ou multiplier fortement** |
| **B — faible (1,7 à 3,4 mm)** | `facial_asymmetry` 1,76 · `nose_width` 1,78 · `mouth_corner` 1,99 · `mouth` 2,26 · `eye_height` 2,50 · `cheeks` 2,97 · `eye_spacing` 3,00 · `nose_bridge` 3,00 · `jaw_angle` 3,35 · `muscles_abdomen` (+1) 3,34 | timides pour un visage (traits de 10 à 50 mm : ±3 mm = ±6 à 30 %) |
| **C — modéré (4 à 9 mm)** | `chin` 4,0 · `ears_angle` 4,6 · `ears_size` 4,6 · `nose_length` 5,0 · `forehead` 5,0 · `head_width` 6,4 · `jaw` 6,7 · `fat_face` (+1) 8,4 · `head_height` 8,9 | correct pour un réalisme sobre, court pour des personnages marqués |
| **D — suffisant (≥ 12 mm)** | carrure 14 · cou 14 · bassin 18 · taille 18 · muscles 17–27 · graisses 14–45 · corpulence 30–34 · jambes 49 · buste 28 · `body_mass` 93 | à ne pas augmenter ; `body_mass` est même excessif (hérité) |

**Remarques** :
- **Pôles dissymétriques** : `muscles_abdomen` (−1 : 1,2 mm contre +1 : 3,3 mm), `fat_face` (3,4 / 8,4), les graisses et muscles (−1 environ 40 % de +1). C'est voulu (on retire moins de tissu qu'on n'en ajoute), mais le côté négatif est très faible.
- Les contrôles du visage touchent **peu de sommets** (5 à 17 %) : l'effet est local donc encore moins visible.

## 2. Cibles proposées (point de départ à valider visuellement)

Principe : à ±1, un contrôle doit amener un trait **proche d'un extrême plausible**, soit environ **±20 à ±30 % de la taille du trait** (⚠ choix de départ, pas une valeur de la littérature). Cibles chiffrées indicatives :

| Contrôle | Actuel | Cible ±1 | Facteur |
|---|---|---|---|
| `eyelid_aperture` | 0,6 mm | 3 mm | ×5 |
| `lip_thickness` | 1,1 mm | 5 mm | ×5 |
| `lips` | 1,5 mm | 5 mm | ×3 |
| `muscle_definition` | 0,5 mm | 3 mm | ×6 (à repenser : surtout un effet de relief/normale) |
| `nose_width` | 1,8 mm | 6 mm | ×3 |
| `mouth_corner` | 2,0 mm | 5 mm | ×2,5 |
| `mouth` | 2,3 mm | 8 mm | ×3,5 |
| `facial_asymmetry` | 1,8 mm | 4 mm | ×2,3 |
| `eye_height` / `eye_spacing` | 2,5 / 3,0 mm | 6 mm | ×2 à ×2,4 |
| `cheeks`, `nose_bridge`, `jaw_angle` | 3,0 à 3,4 mm | 7 mm | ×2 à ×2,3 |
| `chin`, `ears_*`, `nose_length`, `forehead` | 4 à 5 mm | 8 à 10 mm | ×1,7 à ×2 |
| `head_width`, `jaw` | 6,4 / 6,7 mm | 10 mm | ×1,5 |
| `muscles_abdomen` (−1) | 1,2 mm | 4 mm | ×3 (pôle négatif) |
| `skin_relief` | 0 | à déterminer | actif dès l'adulte (matériau et carte, pas seulement géométrie) |

Les facteurs du groupe D restent à 1.

## 3. Comment augmenter sans dégrader

1. **Dans l'architecture native** (groupe « HL Human »), l'amplitude est un simple **facteur multiplicatif sur le poids** de la couche de déformation : réglage immédiat, sans refaire de sculpt. C'est **la bonne occasion** de le faire (migration schéma 10, sans changer la forme au neutre pour les anciens fichiers : les contrôles déjà réglés garderaient leur valeur via un facteur de conversion).
2. **Plage souple et plage dure** : curseur ±1 pour le réglage courant, **plage dure ±2** accessible en tapant la valeur (exagération pour les personnages **stylisés**, D-12). Blender gère nativement cette distinction (`soft_min/soft_max` contre `min/max`) ⚠ à confirmer pour la façade (D) sur les propriétés de l'objet.
3. **Les corrections non linéaires** (clés « correction » associées à chaque contrôle) ont été calibrées pour ±1 : au-delà, la forme peut se **déformer** (retournements de faces, intersections des lèvres/paupières, oreilles). Il faut donc **tester la qualité géométrique** (module `geometry_quality` du dépôt) à ×1, ×2, ×3 pour chaque contrôle augmenté.
4. **Contrôles à très faible effet par nature** (`muscle_definition`, `skin_relief`, `lips` en relief) : augmenter la géométrie ne suffit pas, c'est surtout du **relief de peau** (normales, microrelief, rides) — à relier au matériau de peau (`RECHERCHE_PEAU.md`).
5. **Âge** : vérifier que les amplitudes accrues restent cohérentes avec les 308 clés d'âge (un front ×2 peut entrer en conflit avec la correction d'âge).

## 4. Tests proposés (rien n'est fait)

- **T-A1** : pour chaque contrôle du groupe A–C, déplacement et qualité géométrique à ×1, ×2, ×3 (faces retournées, aire minimale, distance lèvres/paupières), à 3 âges et 2 sexes.
- **T-A2** : rendu comparatif (visage de face et ¾) pour valider les cibles à l'œil ; **c'est la validation qui compte**, les mm ne remplacent pas le regard.
- **T-A3** : migration : un fichier ancien avec `hm_nose_width` = 0,5 garde la même forme après changement de facteur.

## 5. Décision demandée à l'utilisateur

Tu confirmes le principe (augmenter les groupes A à C, laisser D) et la plage dure ±2 ? Je lancerais alors T-A1 et T-A2 pour fixer les facteurs avec images avant toute modification.

## 6. Résultats des tests T-A1 et T-A2 (2026-11-21, Blender 5.2 isolé, corps neutre par défaut)

Scripts : `tools/audit/amplitude_test.py`, `tools/audit/amplitude_render.py` ; données `docs/audit/mesures-amplitudes.json` ; planches `docs/audit/planche-amplitudes-face.png` et `planche-amplitudes-tiers.png`.

**T-A1 (géométrie, cage seule, 23 contrôles des groupes A à C, ±1, ±2, ±3)** :
- **Linéarité** : 21 contrôles sur 23 évoluent **exactement** en proportion du facteur (×2 → 2,00 ; ×3 → 3,00) : multiplier l'amplitude est donc un simple facteur sur le poids.
- **Qualité** : jusqu'à ×3, **aucune face dégénérée, aucune arête étirée de plus de ×2,5**, aucun sommet non fini. **Une seule anomalie** : `eye_spacing` à −3 (yeux rapprochés) retourne **6 faces** ; elle reste à surveiller (limite d'écartement proche de ×2).
- **Deux exceptions** : `fat_face` et `muscles_abdomen` **ne passent pas à l'échelle** (leurs expressions de pilotage bornent la valeur à ±1, `min(max(…,-1),1)`) ; il faudra les reformuler.
- **Limite de la méthode actuelle** : les clés de forme ont un curseur borné (±1) ; j'ai **élargi temporairement leur plage** pour simuler le facteur. Dans l'architecture par nœuds, le facteur est un multiplicateur de poids : aucune borne à lever.
- **Limites du test** : un seul état (corps neutre, sexe et âge par défaut), cage seule (sans Subsurf), détection d'intersections non faite (ni lèvres, ni paupières).

**T-A2 (rendus Workbench, visage de face et de ¾, neutre / ×1 / ×3 pour 6 contrôles)** : lecture à l'œil de la planche de face.
- **×1 (actuel)** : différence **à peine perceptible** sur les six contrôles : le défaut « timide » est confirmé visuellement.
- **×3** : changement **visible et naturel** pour `nose_width`, `lips`, `mouth` et `eye_height` ; `lip_thickness` visible mais discret ; `eyelid_aperture` encore **très subtil** (1,9 mm à ×3) : cible ×5 ou plus.
- **Aucun artefact visible** à ×3 sur ces six contrôles (rendu de face).
- **Limites** : rendu Workbench sans peau ni éclairage de production, un seul corps, vue de ¾ non examinée en détail.

**Conclusion provisoire** : les cibles du §2 (×2 à ×5 pour les groupes A et B, ×1,5 à ×2 pour le groupe C) sont **cohérentes avec les mesures** ; elles restent à **valider par l'utilisateur à l'œil** sur les planches avant de figer les facteurs.

## 7. Seconde passe (l'utilisateur voit à peine les différences) — ×6 et ×10, rendus agrandis

Retour de l'utilisateur : les amplitudes restent faibles, les différences sont difficiles à voir. **Constat confirmé** : à ×3 et en rendu de 420 px (1 pixel ≈ 0,8 mm), un déplacement de 2 à 6 mm représente 3 à 8 pixels. Nouvelle passe : rendus de **700 px sur un champ de 20 cm** (≈ 0,3 mm par pixel), facteurs ×1, ×3, ×6, ×10, et **carte de différence amplifiée** (×6 contre neutre). Planches : `docs/audit/planche-amplitudes-face-a.png`, `-face-b.png`, `-tiers-a.png`, `-tiers-b.png`.

**Lecture** : à **×6**, les changements deviennent **nets** (`nose_width` : nez nettement plus large ; `lip_thickness` : lèvres épaissies ; `eyelid_aperture` : forme de l'œil modifiée). **Les facteurs proposés au §2 (×2 à ×5) étaient trop prudents** : il faut viser **×5 à ×8** pour les groupes A et B.

**Limite géométrique (T-A1, refait jusqu'à ×10)** : jusqu'à ×3 tout est propre (sauf `eye_spacing` négatif). Au-delà, des **faces se retournent** pour plusieurs contrôles : à ×6 `ears_size` (28 faces), `facial_asymmetry` (8), `eye_spacing` (21 en négatif), `ears_angle` (5) ; à ×10 presque tous (`head_height` 175, `jaw` 146, `forehead` 132…). Le facteur sûr dépend donc du contrôle :

| Contrôle | max à ±1 (mm) | facteur maximal sûr testé | linéarité ×3 |
|---|---|---|---|
| `muscle_definition` | 0.48 | ×10 | 3.02 |
| `eyelid_aperture` | 0.63 | ×10 | 3.0 |
| `lip_thickness` | 1.06 | ×6 | 3.0 |
| `lips` | 1.5 | ×10 | 3.0 |
| `facial_asymmetry` | 1.76 | ×3 | 3.0 |
| `nose_width` | 1.78 | ×3 | 3.0 |
| `mouth_corner` | 1.99 | ×6 | 3.01 |
| `mouth` | 2.26 | ×6 | 3.0 |
| `eye_height` | 2.5 | ×6 | 3.0 |
| `cheeks` | 2.97 | ×6 | 3.0 |
| `eye_spacing` | 3.0 | ×2 | 3.0 |
| `nose_bridge` | 3.0 | ×10 | 3.0 |
| `muscles_abdomen` | 3.34 | ×10 | 1.0 |
| `jaw_angle` | 3.35 | ×10 | 3.0 |
| `chin` | 4.0 | ×10 | 3.0 |
| `ears_angle` | 4.56 | ×3 | 3.0 |
| `ears_size` | 4.64 | ×3 | 3.0 |
| `nose_length` | 4.99 | ×3 | 3.0 |
| `forehead` | 5.0 | ×6 | 3.0 |
| `head_width` | 6.39 | ×10 | 3.0 |
| `jaw` | 6.73 | ×6 | 3.0 |
| `fat_face` | 8.43 | ×10 | 1.0 |
| `head_height` | 8.86 | ×3 | 3.0 |

*(Critère « sûr » : aucun retournement et au plus 2 faces d'aire < 10 % ou 12 arêtes étirées à ×2,5 ; test sur un seul état (neutre, cage seule), à refaire par âge et sexe.)*

**Conséquences** :
1. **Facteur d'amplitude par contrôle** (pas un facteur unique) : ×5 à ×6 pour les contrôles marqués sûrs à ×6, plafonné à ×3 pour ceux qui retournent des faces plus tôt (`ears_*`, `eye_spacing`, `facial_asymmetry`, `nose_length`).
2. **Pour dépasser ces plafonds** (exagération stylisée), il faut **de nouvelles cibles sculptées** qui ne retournent pas les faces, ou une déformation de région plus douce (masque + gonflement) — pas un simple facteur sur la cible actuelle.
3. **Les corrections non linéaires** actuelles ne suffisent plus au-delà de ×3 ; elles devront être recalibrées lors de la migration schéma 10.
4. **Réglage visuel** : prévoir un mode « exagérer » (plage dure ×2 à ×3 du réglage normal) à part du réglage courant.
5. **Méthode de validation** : toute comparaison de formes se fait désormais avec des **rendus agrandis et une carte de différence**, pas à l'œil sur des vignettes (ajouté au registre).

## 8. Décision de l'utilisateur (2026-11-21) : ×6

Après lecture des planches, l'utilisateur retient **×6** comme amplitude visible (×3 trop discret). **D-18** dans `SUIVI_REPRISE.md`.
- **Appliquer ×6** aux contrôles dont le facteur sûr testé est ≥ ×6 (`eyelid_aperture`, `lip_thickness`, `lips`, `mouth`, `mouth_corner`, `eye_height`, `cheeks`, `jaw`, `forehead`, `nose_bridge`, `jaw_angle`, `chin`, `head_width`, `muscle_definition`).
- **Plafonner à ×2–×3** : `ears_size`, `ears_angle`, `eye_spacing`, `facial_asymmetry`, `nose_length`, `nose_width`, `head_height`, tant que de nouvelles cibles ne sont pas sculptées.
- **Reformuler** `fat_face` et `muscles_abdomen` (expressions bornées à ±1).
- **Quand** : à la migration schéma 10, après T-A3 (un ancien fichier garde sa forme) ; aucune modification de l'extension avant.

## 9. Amplitude par sexe et par âge (T-A1 bis, 2026-11-21 : 2 sexes × 4 âges × 21 contrôles × ±1, ±3, ±6 = 1 008 mesures)

Scripts : `tools/audit/amplitude_matrix.py` ; données `docs/audit/mesures-amplitudes-matrice.json` et `mesures-amplitudes-synthese.json`. Même critère que le §7 (aucun retournement ; au plus 2 faces d'aire < 10 % ; au plus 12 arêtes étirées). « ×1 » signifie que des problèmes apparaissent déjà à ×3 (le facteur sûr est compris entre ×1 et ×3, non affiné) ; « ×3 » signifie des problèmes à ×6.

| Contrôle | tous les âges (enfant à senior) | adulte + senior | adulte seul |
|---|---|---|---|
| `cheeks` | ×3 | ×3 | ×3 |
| `chin` | ×6 | ×6 | ×6 |
| `ears_angle` | ×3 | ×3 | ×3 |
| `ears_size` | ×3 | ×3 | ×3 |
| `eye_height` | ×3 | ×6 | ×6 |
| `eye_spacing` | ×1 | ×1 | ×1 |
| `eyelid_aperture` | ×6 | ×6 | ×6 |
| `facial_asymmetry` | ×1 | ×1 | ×3 |
| `forehead` | ×6 | ×6 | ×6 |
| `head_height` | ×1 | ×1 | ×1 |
| `head_width` | ×1 | ×1 | ×1 |
| `jaw` | ×3 | ×6 | ×6 |
| `jaw_angle` | ×6 | ×6 | ×6 |
| `lip_thickness` | ×3 | ×3 | ×6 |
| `lips` | ×6 | ×6 | ×6 |
| `mouth` | ×3 | ×6 | ×6 |
| `mouth_corner` | ×3 | ×3 | ×6 |
| `muscle_definition` | ×6 | ×6 | ×6 |
| `nose_bridge` | ×1 | ×3 | ×3 |
| `nose_length` | ×3 | ×3 | ×3 |
| `nose_width` | ×3 | ×3 | ×3 |

**Lecture** :
- **Les facteurs sûrs dépendent de l'âge** : plusieurs contrôles qui tiennent à ×6 chez l'adulte posent problème chez l'enfant/adolescent (visage plus petit, mêmes déplacements en mm). **Il faut donc un facteur d'amplitude qui dépend de l'âge** (par exemple proportionnel à la taille de la tête), ou limiter ×6 aux stades adulte et senior.
- **×6 sûr chez l'adulte** (D-18 applicable) : `chin`, `eyelid_aperture`, `eye_height`, `forehead`, `jaw`, `jaw_angle`, `lip_thickness`, `lips`, `mouth`, `mouth_corner`, `muscle_definition`.
- **×3 chez l'adulte** : `cheeks`, `ears_angle`, `ears_size`, `nose_length`, `nose_width`, `nose_bridge`, `facial_asymmetry`.
- **Déjà au plafond (< ×3)** : `eye_spacing`, `head_height`, `head_width` : ne pas augmenter (ou sculpter de nouvelles cibles).
- **Limites** : cage seule (sans Subsurf), détection de retournements de faces seulement (pas d'intersections), états sexe 0/1 et âges entiers (pas les transitions intermédiaires), un seul réglage à la fois (pas les combinaisons).

**D-18 mis à jour** : ×6 retenu par l'utilisateur ; **applicable tel quel à 11 contrôles chez l'adulte**, plafonné à ×3 pour 7 contrôles, laissé tel quel pour 3 ; **à moduler par l'âge**.
