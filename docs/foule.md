# Foule HumanLoom (moteur natif, lots C1 et C2)

Moteur de foule intégré à l'extension : `extension/crowd.py` (moteur) et `extension/crowd_ui.py` (panneau « Foule » de l'onglet Humain). Tests : `tools/validate_crowd.py` (C1 à C12) ; mesures : `tools/measure_crowd.py`.

## Principes
- **Ensembles d'éléments variables** (`default_spec`) : plages de sexe, d'âge et de 24 contrôles de morphologie ; expressions pondérées ; comportements pondérés (marche, course, attente, discussion, saut, traversée) ; vitesses ; zones (trottoirs, passages piétons, aire libre) ; variantes extensibles (`variants` : tenues, coiffures…, appliquées par des fonctions enregistrées avec `register_variant_applier`, pour les lots vêtements).
- **Tirage à graine** : chaque personnage est tiré par `default_rng([graine, régénération, indice, essai])` ; même graine = même foule.
- **Garde-fous** : bornes des prises du groupe de nœuds, adiposité + muscles <= 1,4, distance minimale (0,12) entre personnages dans l'espace de diversité : un tirage trop proche d'un autre est retiré (jusqu'à 50 fois), donc pas de clones. Mesuré sur 150 personnages : distance minimale 0,72 (médiane 1,29).
- **Foule figée** : spec, tirages et résultats sont enregistrés dans la scène (`scene["humanloom_crowd"]`, JSON) et sur les objets (`hl_crowd_id`). Rien n'est recalculé à la réouverture ni au changement d'un réglage. Seuls `generate(replace=True)`, `regenerate_member` (un personnage, les autres inchangés) et `regenerate_all` la modifient ; « Générer » est refusé si une foule existe.
- **Comportements** : marche/course (trajet à vitesse propre, allers-retours), attente, discussion (paires face à face à 1 m), saut sur place, traversée d'un passage (retard de départ selon le cycle du feu). Évitement : répulsion + contournement latéral (rayon 1,1 m) ; distance minimale 0,50 m dans un flux de 6 contre 6 sur 3 m de large (0,02 m sans évitement).
- **Animations** : `spec["clips"][comportement]` = noms d'actions de la bibliothèque de l'utilisateur (déjà re-ciblées). À défaut, clips SYNTHÉTIQUES (balancement des jambes et des bras, respiration, gestes, saut) servent de bouchon et de test : aucune donnée tierce. Chaque clip est une bande NLA « Foule » avec décalage de phase tiré au hasard et échelle de vitesse selon la vitesse de marche.
- **Trajet** : clés de position et de cap toutes les 5 images (interpolation linéaire) sur le corps.
- **Mémoire** : le maillage de base (293 couches de morphologie) et le groupe de nœuds sont partagés entre tous les personnages ; fichier .blend de 21 Mo pour 10 personnages au lieu de 182 Mo.

## Niveaux de détail (C2)
0 complet ; 1 subdivision coupée et dents masquées ; 2 cage figée (nœuds géométriques retirés, groupes de poids conservés ; mêmes triangles que le niveau 1 mais évaluation environ 3 fois plus rapide) ; 3 cage décimée (30 %). `auto_lod` choisit selon la distance à la caméra (12 / 30 / 60 m). Le passage aux niveaux 2 et 3 est irréversible pour les contrôles du corps : régénérer le personnage pour revenir.

## Performances mesurées (machine de développement, 64 Go, 120 images, évaluation du graphe en arrière-plan, caméra à 30 m)

| Personnages | Génération (s) | par personnage (s) | Mémoire après génération (Mo) | .blend compressé (Mo) | Triangles évalués sans / avec LOD (millions) | Évaluation par image sans / avec LOD (ms) |
|---|---|---|---|---|---|---|
| 10 | 13 | 1,29 | 1 623 | 21 | 0,8 / 0,2 | 80 / 26 |
| 25 | 39 | 1,56 | 2 500 | 25 | 2,1 / 0,5 | 148 / 45 |
| 50 | 109 | 2,19 | 4 599 | 32 | 4,2 / 1,1 | 294 / 92 |
| 100 | 323 | 3,23 | 8 248 | 45 | 8,5 / 2,1 | 581 / 164 |
| 150 | 650 | 4,34 | 12 696 | 59 | 12,7 / 3,2 | 886 / 224 |

Lecture : la génération coûte 1,3 s par personnage pour 10, mais 4,3 s pour 150 (le coût par personnage augmente avec l'effectif : chaque nouvel objet relance la mise à jour du graphe de dépendances) ; la mémoire est d'environ 85 Mo par personnage au niveau de détail 0 ; les niveaux de détail réduisent le temps d'évaluation par image d'un facteur 3 à 4 (886 ms -> 224 ms pour 150) mais pas la mémoire (elle augmente : les cages figées s'ajoutent avant que les anciennes données soient libérées ; appliquer les niveaux de détail à la génération est une piste non faite). Ces temps sont ceux d'une évaluation du graphe sans rendu ; le rendu (Cycles, Eevee) n'est pas mesuré ici.

## Lot B (28 nov. 2026) : élimination hors caméra, partage des données, vêtements, cadence

### Élimination hors caméra (`crowd.cull`, boutons « Masquer hors caméra » / « Tout afficher »)
Image par image, un personnage dont la sphère englobante (1,1 m + 2 m de marge pour les ombres et reflets proches) est ENTIÈREMENT hors du champ de la caméra (marge de cadre 5 %) ou derrière elle est masqué : clés CONSTANTES de `hide_viewport` et `hide_render` sur le corps et ses enfants (armature, dents, langue, yeux, vêtements). La caméra peut être animée ; le résultat est figé (à refaire si la caméra ou les trajets changent ; régénérer un personnage supprime ses clés). `crowd.uncull` retire tout. Tests : `tools/validate_crowd_cull.py` (K1 à K7).
- **Mesuré, honnêtement : le gain n'est PAS dans la vue 3D.** Une clé de visibilité animée laisse l'objet dans le graphe d'évaluation de la vue (14 personnages, 6 masqués : 100,7 -> 99,3 ms par image) alors qu'un masquage STATIQUE fait baisser le coût (7 sur 14 : 97 -> 69 ms, le reste est un coût fixe de la scène). Les objets masqués sortent bien des instances du graphe (K5) donc des rendus.
- **Rendu Cycles, 100 personnages, niveaux de détail actifs** (8 niveau 0, 56 niveau 1, 36 niveau 2 ; GPU OptiX RTX 3080, 1080p, 32 échantillons, caméra à 22 m, 50 mm, une seule mesure par cas) : 19 personnages sur 100 hors champ à l'image 30. Temps de rendu 5,1 s -> 5,1 s (aucun gain mesurable : le coût est dominé par la scène visible et un coût fixe), VRAM 4272 -> 4277 Mo (aucun gain), mémoire du processus après rendu 8504 -> 4733 Mo (-44 %) et pic 8991 -> 8278 Mo (-8 %). Conclusion : utile pour la mémoire vive d'une grande scène, pas pour le temps de rendu à cette densité et cette focale ; un cadre plus serré (plus de personnages hors champ) augmenterait la part masquée.

### Partage des données
Déjà partagés entre tous les personnages (mesuré en comparant 5 et 10 personnages) : le maillage de base « HL Human Base » (10 582 sommets, 293 couches de morphologie, `users` = effectif), le groupe de nœuds « HL Human », les 5 matériaux, les 3 images. Non partagés, par personnage : 1 armature + sa donnée (+1 armature), 5 petits maillages (dents hautes et basses, langue, 2 yeux), 2 actions (trajet, clip), 3 datablocks de clés de forme. Ces objets sont petits ; **les ~85 Mo par personnage viennent de la géométrie ÉVALUÉE** (subdivision, mélange des couches, deux modificateurs Armature) : seuls les niveaux de détail et le masquage la réduisent, pas un partage supplémentaire de données. Partager les yeux et les dents entre personnages n'a pas été tenté (ils sont construits pour la morphologie de chacun ; gain attendu faible : quelques Mo par personnage).
- **Correctifs de flexion dans la foule : non faisables sans perdre le partage.** Les correctifs sont des clés de forme pilotées par des propriétés de l'armature de CHAQUE personnage ; les clés vivent sur le maillage de base, partagé : un pilote par personnage exige un maillage par personnage. **Mis à jour (28 nov. 2026, CONCEPTION_RIG_CORRECTIFS.md §17)** : `correctives.install_independent(corps, armature)` rend le maillage de base propre à UN personnage puis installe ses correctifs ; mesuré (`tools/measure_crowd_correctives.py`) : 36,6 Mo de mémoire et +18,5 Mo de fichier par personnage, le coude d'un personnage ne déplace que ses sommets ; réservé aux personnages proches (une douzaine ≈ 450 Mo), pas à toute la foule (150 personnages ≈ 5,5 Go). Les clés de dégagement de flexion des PIÈCES (veste, jean, robe…, `garment_clearance.build`) n'ont pas ce problème : chaque pièce a son maillage ; mesuré sur 2 personnages : pénétration du coude de la veste à 110° de 13 mm à −7 mm. Désactivés par défaut depuis le rendu validé « sans correctifs ». Option du panneau Foule non ajoutée.

### Vêtements dans la foule (variante « outfit »)
`spec["variants"] = {"outfit": [["t_shirt", "jean"], ["t_shirt", "jean", "chaussures"], ["robe_courte"]]}` : chaque personnage reçoit une tenue tirée dans la liste (applicateur `garments.crowd_outfit`, enregistré par l'extension ; clé inconnue refusée). Régénération d'un personnage et effacement de la foule gèrent les pièces (test C14). **Coût mesuré, 25 personnages** (`tools/measure_crowd.py --n 25 --outfit 0|1`) : génération 40,5 s -> 64,2 s (+0,95 s par personnage), mémoire +55 Mo (+2,2 Mo par personnage), .blend +2,3 Mo, évaluation par image 165 -> 168 ms sans niveau de détail (+2 %) et 56,5 -> 70,7 ms avec (+25 % : les vêtements ne sont pas décimés par les niveaux de détail). Le coût est donc acceptable ; non mesuré à 100 personnages (extrapolation linéaire : ~95 s de génération en plus, ~220 Mo).

### Cadence de la scène
La simulation tourne à la cadence de la scène (`scene.render.fps / fps_base`, enregistrée dans `spec["fps"]`) : les clés de trajet sont à UNE image de scène par pas de simulation, donc une simulation à 24 i/s lue à 30 i/s aurait fait marcher les personnages 25 % trop vite. `spec["fps_scene"] = False` conserve le `fps` du spec (test C13). Le rééchantillonnage des animations retargetées est traité séparément (`retarget_ui.convert`, test R13).

## Lot E (28 nov. 2026) : simulation de tissu des robes DANS la foule
`tools/measure_crowd_cloth.py` (foule dont chaque personnage porte une robe, clips de marche synthétiques, simulation native XPBD activée sur chaque robe, 48 images, cette machine). **Mesuré** :
| Personnages (robes simulées) | Évaluation par image sans / avec tissu en direct (ms) | Coût par robe et par image | Cuisson par robe (48 images) | Cache cuit par robe (48 images) | Évaluation avec cache cuit (ms) |
|---|---|---|---|---|---|
| 1 | 63 / 117 | 54 ms | 5,7 s | 6,5 Mo | 61 |
| 4 (24 images) | 57 / 181 | 31 ms | 3,4 s | 3,0 Mo | 89 |
| 12 | 99 / 439 | 28 ms | 10,3 s | 5,5 Mo | 161 (+5 ms par robe) |
- **Stabilité** : aucune valeur non finie sur 1, 4 et 12 robes ; pas maximal par image des sommets de robe, mesuré relativement à l'origine du personnage : 0,46 à 0,54 m contre 0,27 à 0,32 m SANS simulation (la rotation d'ensemble du personnage compte déjà), 2 robes sur 12 au-delà de 0,3 m : pas d'explosion (la simulation reste bornée) mais ce critère ne sépare pas bien un mouvement de course d'un à-coup de tissu ; la validation visuelle de robes en foule n'a pas été faite.
- **Limites chiffrées** : en direct, ≈ 28 à 54 ms par robe et par image : 12 robes = 440 ms par image (2 images/s), irréaliste pour une lecture ; avec le cache cuit le surcoût tombe à ≈ 5 ms par robe. Extrapolation LINÉAIRE à 100 robes sur 240 images (NON mesurée) : ≈ 2,8 s par image en direct ; cuisson ≈ 100 x 240 x 0,12 à 0,21 s = 50 à 85 minutes ; cache cuit ≈ 27 Mo par robe, soit ≈ 2,7 Go dans le .blend. **Recommandation** : simuler seulement les personnages proches de la caméra (une douzaine au plus), cuire le cache, laisser les autres en robe suivant l'armature.
- **Défaut corrigé** (mesuré avant correction : effacement impossible avec message obscur « La foule contient des objets liés à une autre scène… », 4 collections de collision « HL Colliders » laissées) : effacer ou régénérer une foule dont une robe a la simulation ACTIVE est refusé AVANT toute modification, avec un message clair (désactiver le tissu d'abord) ; après désactivation, l'effacement ne laisse aucun objet ni collection (test C15).

## Limites connues
- Vêtements : voir « Vêtements dans la foule » (variante « outfit ») ; pas de coiffures dans la foule (point d'extension prêt).
- Les clips synthétiques ne sont pas des animations de qualité : pour la production, renseigner `clips` avec des actions re-ciblées.
- Les trajectoires ne tiennent pas compte de décors (pas de collision avec des obstacles, seulement entre personnages).
- Évitement simple (pas de planification globale) : les flux très denses (plus de 2 personnes par mètre de largeur) descendent à 0,33 m de distance minimale.
- L'extension n'est pas testée au-delà de 150 personnages ; la mémoire à ce niveau (12,7 Go) suppose une machine de 32 Go ou plus.
