# CONCEPTION A3 — retargeting analytique, root motion, aperçu, NLA (rapport de conception, critères chiffrés)

Date : 2026-11-22. Statut : conception **avant** le code. Entrées : `STRATEGIE_ANIMATION.md` §2 (D-32), `CONCEPTION_A2_RIG.md`, mapping A2b. Mesures : lectures seules de la bibliothèque locale de l'utilisateur (une armature / une action par chargement, aucun nom consigné). Aucun nom de squelette tiers dans ce document.

## 1. Mesures qui fondent les choix
- **Repères de repos très différents** (88 os appariés par le mapping A2b, deux variantes de l'armature de référence) : l'angle entre le repère d'un os source et celui de l'os cible a pour **médiane 126°** (p90 169°) ; la direction « Y de l'os » diffère de **90° en médiane** : copier des rotations locales telles quelles est exclu, la **correction de repos par os est indispensable**.
- **Poses de repos différentes** (direction de chaîne os-parent → os-enfant, source contre HumanLoom) : avant-bras → main 30–32°, clavicule → haut du bras 30–31°, haut du bras → coude 16–18°, cou → tête 18°, pied → orteil 18°, colonne 7–8°, jambe 1–5°. **Un transfert « delta » (rotation relative au repos) conserve donc un écart de 16 à 32° sur les bras** : une main attendue le long du corps serait à ≈ 15 cm de sa place.
- **Proportions** : rapport de longueurs cible/source de 0,86 à 0,98 selon le segment ; rapport de hauteur de bassin 0,87 à 0,90 (translations source en cm).
- **Actions réelles** (60 tirées au hasard) : 57 sur 60 sont marquées root motion, **aucun os ne porte le déplacement global** (pieds et mains IK en espace monde ; le bassin se déplace de 29 cm en moyenne, max 113 cm) ; os auxiliaires animés = 7,8 % des os animés (IK, accessoires) ; 5 220 courbes d'échelle (87 par action en moyenne).
- Coût : 80 os × ≤ 300 images = ≈ 24 000 matrices 4×4 par action : négligeable en numpy.

## 2. Algorithme (calcul pur, sans bpy dans le cœur)
Entrées : action source chargée seule (courbes de translation, rotation, échelle par os), squelette source (repos), mapping (A2b), squelette cible (repos), options.
1. **Échantillonnage** : une valeur par image entière de la plage de l'action (cadence de l'action, `ualm_fps`), canaux manquants = identité ; rotations euler ou quaternion normalisées.
2. **Cinématique directe source** vectorisée sur les images : `M_s(b, f) = M_s(parent, f) · Repos_local_s(b) · Base_s(b, f)`, en espace de l'armature, pour chaque os source (échelle des os ignorée pour la chaîne, voir §6).
3. **Orientation transférée** (par os apparié) : `P_t = Δ_s · G_b · R_t_repos` avec `Δ_s = P_s · R_s_repos⁻¹` (rotation monde depuis le repos source) et `G_b` la rotation d'arc minimal qui amène la direction de chaîne du repos cible sur celle du repos source (`G_b = I` en mode « delta »). **Deux modes** à comparer par mesure (§4 Q2) : **absolu** (`G_b` appliqué : le personnage reprend les directions monde de la source, y compris à la pose de repos) et **delta** (formule de la stratégie : `P_s · R_s⁻¹ · R_t` ; conserve les écarts de repos, 16 à 32° sur les bras). Le défaut sera celui qui minimise l'erreur de position des articulations.
4. **Os cibles sans source** (torsions, os de colonne en trop, métacarpes, orteil absent) : règle déterministe consignée dans le rapport : torsion = rotation nulle ; colonne : interpolation sphérique entre os appariés voisins selon la fraction le long de la chaîne ; doigts sans métacarpe : métacarpe = identité.
5. **Repassage en local par la chaîne cible** : `Base_t(b, f) = Repos_local_t(b)⁻¹ · (M_t(parent, f)⁻¹ · [P_t | position])`. La position d'un os cible vient de la cinématique directe sur ses propres longueurs ; seule la translation du bassin (puis de `root`) est transférée.
6. **Translations** : décalage du bassin source par rapport à son repos, **mis à l'échelle par le rapport des hauteurs de bassin** (cible / source, mesuré 0,87–0,90) et converti dans le repère local du bassin cible ; les autres os n'ont pas de canal de translation (longueur d'os cible conservée).
7. **Continuité** : signe des quaternions rendu continu, normalisation ; **nouvelle action** pour NOS os (rotation sur tous, translation sur `pelvis` et `root`), nommée « <action>@HumanLoom », une clé par image (cuite) ; aucune contrainte, aucun bake de Blender.
8. **Cache** par (empreinte de l'action, signature du mapping, options) dans le dossier utilisateur (`retarget/*.npz` : images × os × quaternion, translations) : relecture sans recalcul ; invalidation si le mapping ou les options changent.
9. **Additives** (37 sur 2 046 dans la bibliothèque de l'utilisateur) : **non prises en charge en A3**, signalées et ignorées (rapport).

## 3. Root motion (gestionnaire déterministe)
Entrée : déplacement horizontal (x, y) du bassin au cours de l'action (translation transférée, repère du personnage). Trois modes :
- **Sur place** : le déplacement horizontal est retiré (bassin recentré sur sa position initiale), `root` fixe ;
- **Conserver** : le déplacement reste sur le bassin, `root` fixe (comportement de la source) ;
- **Extraire vers `root`** : le déplacement horizontal passe sur `root` (translation + rotation autour de la verticale suivant la direction du déplacement si demandé) et le bassin garde son décalage local.
Invariant mesurable : la position monde du bassin est identique en « conserver » et « extraire » (écart < 1e-4 m) ; « sur place » a un déplacement horizontal nul ; la composante verticale n'est jamais extraite. Les 3 % d'actions non marquées root motion sont traitées de même (le drapeau n'est qu'une indication).

## 4. Critères d'acceptation chiffrés (à tenir avant de déclarer A3 fait)
| # | Critère | Seuil proposé | Base de mesure |
|---|---|---|---|
| Q1 | Exactitude mathématique (circuit fermé synthétique : rig dont les repères sont tournés aléatoirement de 0 à 40° ; l'animation source est construite pour avoir la même pose monde que l'animation cible connue) | erreur d'orientation ≤ 0,1° (médiane) et ≤ 0,5° (max) ; position ≤ 1 mm | squelettes synthétiques (4 conventions), 3 animations aléatoires |
| Q2 | Fidélité sur actions réelles (30 actions de la bibliothèque de l'utilisateur, test IGNORÉ si absente) : erreur de position monde des mains, pieds, coudes et genoux entre la source mise à l'échelle (hauteur de bassin) et le résultat, en % de la stature | médiane ≤ 3 %, p95 ≤ 6 % ; comparaison des deux modes (absolu / delta) et d'une référence naïve sans correction de repos (attendue > 30 %) | cinématique directe des deux squelettes |
| Q3 | Glissement des pieds : intervalles où le pied source est posé (hauteur < 3 % de la stature et vitesse < 3 % de la stature par seconde), dérive horizontale du pied cible sur l'intervalle | ≤ max(1,5 × dérive source, 2 cm) ; distribution rapportée | mêmes 30 actions |
| Q4 | Continuité des boucles (actions dont la première et la dernière image coïncident à 2 % de la stature près) | écart première/dernière pose cible ≤ écart source + 0,5 % de la stature | mêmes actions |
| Q5 | Vitesse | ≤ 0,25 s par action à froid (80 os, ≤ 300 images), ≤ 50 ms depuis le cache | chronométrage de 30 actions |
| Q6 | Aperçu non destructif | après aperçu puis retrait : même action active, même `animation_data`, mêmes transformations de pose, même image courante ; 0 bloc orphelin | test avant/après |
| Q7 | Root motion | invariants du §3 ; sur 10 actions réelles marquées root motion, déplacement extrait ≥ 90 % du déplacement horizontal du bassin | mesure |
| Q8 | Rapport | chaque conversion produit : os cibles sans source (règle appliquée), os sources ignorés, actions additives refusées, durée, mode | contrôle de structure |

## 5. Interface
Panneau « Animations » (bibliothèque A1c) : sélection d'une animation → **Aperçu** (action convertie assignée temporairement au rig, état initial restauré au retrait) ; **Ajouter au NLA** (nouvelle piste) ; **Remplacer** (action active) ; options : mode de pose (absolu / delta), root motion (sur place / conserver / extraire), échelle des translations (auto par hauteur de bassin / manuelle), vitesse. Le mapping utilisé est celui du profil choisi (A2b) ; sans profil, auto-mapping avec rapport affiché.

## 6. Limites annoncées
- Pas de correction IK des pieds en A3 (glissement mesuré et rapporté ; verrouillage des pieds = lot ultérieur si Q3 échoue).
- Échelle des os ignorée (les 5 220 courbes d'échelle mesurées sont jugées inutiles pour des squelettes de déformation : à confirmer sur les 30 actions).
- Mains et doigts : transfert de rotation par os ; pas d'adaptation à des proportions de main différentes.
- Les actions additives, les os IK/accessoires et les courbes non liées à des os ne sont pas converties.
- Qualité visuelle : planches d'images à chaque jalon ; aucune garantie esthétique avant validation à l'œil.

## 7. Plan de tests
`tools/validate_animation_retarget.py` (synthétique : Q1, Q6, Q7, Q8, cache) ; `tools/validate_animation_retarget_library.py` (IGNORÉ sans bibliothèque : Q2, Q3, Q4, Q5) ; planche : 4 images clés d'une animation sur 3 morphologies.

## 8. Mesure du 3e mode (F0-g) — absolu + IK des membres
Mode `absolu_ik` : mode absolu, puis IK analytique à 2 os sur bras et jambes (la main ou le pied vise la position source relative au bassin, mise à l'échelle par le rapport des hauteurs de bassin, limitée à la portée de NOS segments ; le coude/genou garde la direction de pôle de la source). Mesuré sur les **mêmes 30 actions** de la bibliothèque locale (erreur de position mains/pieds/coudes/genoux relative au bassin, % de la stature) :

| mode | médiane | p95 |
|---|---|---|
| copie naïve (référence) | 22,76 | 59,24 |
| delta | 4,56 | 9,97 |
| absolu | 3,88 | 7,67 |
| **absolu + IK** | **2,57** | **7,54** |

Verdict : **meilleur mode retenu par défaut** (`Options.pose_mode`, interface). La médiane passe sous le seuil (≤ 3 %) ; le **95e centile (7,54 %) reste au-dessus du seuil (≤ 6 %) : Q2 reste KO, seuil non assoupli**. Le p95 est donc dominé par des cas que l'IK ne corrige pas (hypothèse non testée : portée limitée des segments plus courts, ou coudes/genoux dont le pôle source est mal défini). Q3 (glissement des pieds : 0 dépassement sur 60, dérive max 0,5 cm), Q4 (boucles : écart supplémentaire 0 %), Q5 (durée : médiane 0,078 s, max 0,12 s) passent avec ce mode. Non mesuré : aspect visuel de la déformation du maillage.
