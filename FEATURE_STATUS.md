# FEATURE_STATUS — État réel des fonctionnalités

Base : `codex/groom` @ `443d278`. Seul ce qui a été exécuté est marqué « Validé » (preuves dans TEST_REPORT.md). Un code qui existe n'est pas pour autant opérationnel.

| Domaine | Statut | Preuve ou limite |
|---|---|---|
| Création du corps (`human_modeling.create`) | **Validé** (sonde) | 10 582 sommets, 1 UV, 2 yeux enfants, schéma 9 |
| Réglage de taille (`set_height`) | **Validé fonctionnellement ; test périmé** | Surface évaluée = 1,75 m exactement ; le test lit `dimensions` (1,7508, cage sans Subsurf). Voir ISSUES I-02 |
| Contrôles morphologiques / mélange de sexe (shape keys + drivers) | **Test en échec, produit non mis en cause** | La formule du test ignore 3 clés actives par défaut (écart 1,8–3,6 cm) ; drivers tous valides. Non confirmé que ces valeurs par défaut sont voulues |
| Mesures anthropométriques et références (WHO/NHANES) | **Validé** | `validate_measurements.py` |
| Repères anatomiques, sections, ajustements | **Validé** | `validate_anatomy.py`, `validate_landmark_sets.py` |
| Contrôle de qualité géométrique (croisements, NaN) | **Validé** | `validate_geometry_quality.py` |
| Préréglages de personnage (capture/application/JSON) | **Partiel** | Étapes principales passent ; migration legacy non testée (fixture manquante) |
| Visage, âge apparent, corpulence, muscles régionaux | **Non testé** dans cette passe | Scripts existent ; README : dosage insuffisant des extrêmes de corpulence |
| Relief de peau, correctifs de surface | **Non testé** | Nécessitent un ancien actif |
| UV, matériaux de peau | **Partiel / non testé** | 1 couche UV vérifiée ; pas de contrôle de matériaux de peau trouvé |
| Groom : 11 zones, attache par UV, reconstruction, JSON | **Validé** | `GROOM25_PASS 11 66` |
| Groom : viewport/rendu indépendants | **Validé** | `QUALITY26_PASS` |
| Groom : XPBD | **Partiel** | Banc droit sans collision : < 0,1 %. Cheveux courts avec collisions : > 5 % d'allongement sur certains réglages selon `docs/groom.md`. Collisions : non testé (collision29) |
| Groom : réouverture du `.blend` | **Non testé** | `validate_groom_reopen25.py` exige un fichier absent |
| Rigging / armature | **Absent** | README : « le rig n'est pas livré » |
| Vêtements, accessoires, dents | **Absent** (rien trouvé dans `extension/`) | — |
| Les 48 sliders (corps, corpulence, muscles, visage) | **Partiellement validé** | Tous répondent, valeurs finies, retour à 0 sans résidu. Mais 10 déplacent < 3 mm à ±1 (ISSUES I-13) ; `skin_relief` inactif avant 30 ans |
| Curseur Morphologie (sexe) | **Validé** | 5 positions, hauteur 1,639 → 1,690 m, valeurs finies |
| Âge (5/15/30/75 ans) | **Partiellement validé** | Hauteurs monotones et finies ; visuellement 30 ans et 75 ans très proches (`docs/audit/rendu-ages-sexes.png`) ; stature calibrée par `calibrate_age_height` pour les 8 cas sexe × âge |
| Silhouettes (8 profils) | **Partiellement validé** | Tous s'appliquent ; effet surtout sur la profondeur du buste (0,281 → 0,346 m) ; projection abdominale faible en profil (`rendu-silhouettes-profil-M.png`), en cohérence avec le README |
| Variation aléatoire (FACE/BODY/ALL) | **Validé** | 6 cas, valeurs finies (qualité visuelle non jugée) |
| Préréglages JSON : enregistrer/charger | **Validé** | aller-retour exact (0,0 mm) ; mélange à 50 % non linéaire (I-18) |
| Contrôle du maillage (`check_geometry`) | **Validé** | 68 croisements sur la cage seule, 0 avec les modificateurs par défaut ; 168 si tous les contrôles sont à +1 (I-14, corrigé) |
| Groom : préréglages dans l'extension | **Validé** | Court : 850 + 240 guides en 1,2 s ; « Pilosité adulte » 9 zones en 2,0 s |
| Groom : suivi du corps après morphologie et mise à l'échelle | **Validé** | écart racine–surface ≤ 0,22 mm après corpulence/tête/jambes à +1 et taille 1,5 m |
| Taille (`set_height`) | **Validé** | 0,5 à 3,0 m atteints exactement, sans garde-fou (I-15) |
| Rechargement (unregister/register ×3) | **Validé** | TEST_REPORT, sondes |
| Drivers et enregistrement/réouverture d'un corps | **Validé** | 459 drivers valides ; schéma 9 conservé |
| Undo/redo | **Non testé** | impossible en mode background ; opérateurs déclarent `UNDO` |
| Installation de l'archive, rendu de l'interface | **Non testé** | — |
