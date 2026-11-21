# TEST_REPORT — Tests exécutés pendant l'audit

Date : 2026-11-21. Blender 5.2.0 LTS (hash fbe6228777e7), Windows 11. Commit audité : `443d278` (branche `codex/groom`), cloné dans un dossier temporaire pour ne toucher ni au dépôt ni à `validation/`.

Légende : **Validé** = exécuté avec succès · **Partiel** · **Échec** = reproduit · **Non testé**.

## Méthode et limite majeure

La plupart des scripts `tools/validate_*.py` importent `bl_ext.user_default.human_modeling`, c'est-à-dire l'extension **installée** dans le Blender de l'utilisateur, pas le code du dépôt (voir ISSUES I-01). Je n'ai pas installé l'extension. J'ai écrit un adaptateur temporaire (hors dépôt) qui alias `bl_ext.user_default.human_modeling` vers `extension/` du clone, puis exécute le script. Les résultats ci-dessous portent donc sur le code du dépôt. Les scripts `*groom*` importent `extension` directement et n'ont pas eu besoin de l'adaptateur.

Commande type : `blender --background --factory-startup --offline-mode --threads 4 --python-exit-code 1 --python <script>` (+ `-- <dossier de sortie>` pour ceux qui l'exigent).

## Résultats

| Script | Statut | Preuve / observation |
|---|---|---|
| `validate_groom25.py` | **Validé** (111 s) | `GROOM25_PASS 11 66` : 11 zones, 66 cas d'attache |
| `validate_groom_workflow25.py` | **Validé** (13 s) | `GROOM25_WORKFLOW_PASS` ; XPBD sur banc droit : allongement max ≈ 0,08 % |
| `validate_groom_quality26.py` | **Validé** (32 s) | `QUALITY26_PASS`, version 0.15.1 ; viewport 0/10/50/100 % vs 6544 courbes au rendu |
| `validate_geometry_quality.py` | **Validé** | `PASS: known crossing, ... atomic JSON export` |
| `validate_measurements.py` | **Validé** | `PASS: published medians, rotation and nonuniform scale, ... reopen` |
| `validate_landmark_sets.py` | **Validé** | `PASS: landmark IO, topology guard, ... reopen` |
| `validate_anatomy.py` | **Validé** (39 s) | `PASS: analytic sections, ... 21 fits, ... reopen` |
| `validate_model.py` | **Échec** | `assert abs(body.dimensions.z - 1.75) < 1e-5` (ligne 31). Reproduit : après `set_height(1.75)`, `dimensions.z` = **1,7508** (écart 0,83 mm), avec ou sans modificateurs. |
| `validate_controls.py` | **Échec** | `assert max(abs(actual - expected)) < 1e-6` (ligne 49, mélange de sexe). Écart non chiffré ; cause non diagnostiquée. |
| `validate_presets.py` | **Partiel** | Les étapes d'enregistrement/application passent ; échoue à la ligne 128 : fixture `legacy-03.blend` absente (produite par une exécution antérieure). Non imputable au produit. |
| `validate_groom_reopen25.py` | **Non testé** | Exige `validation/groom-25/HumanLoom-groom-revue.blend`, absent d'un clone neuf. |
| `validate_groom_collision29.py` | **Non testé** | Fichier non suivi (travail en cours), absent du clone ; exige aussi le `.blend` ci-dessus. |
| `validate_modeling_workflow.py`, `validate_skin_relief.py`, `validate_surface_fix.py` | **Non testé** | Exigent un `.blend` d'ancien actif en argument (`old_asset`) que je n'ai pas. |
| ~40 autres `validate_*`, `check_*`, `probe_*` | **Non testé** | Hors périmètre de cette première passe. |

Sonde directe : `human_modeling.create` produit un corps de 10 582 sommets (test existant), taille par défaut 1,690 m, deux enfants (yeux), deux modificateurs (`Human Modeling · Surface`, `Human Modeling · Relief de peau`), schéma 9.

## Après correction des tests (arbre de travail, non committé)

| Script | Statut | Observation |
|---|---|---|
| `validate_model.py` (hauteur mesurée sur la surface lissée) | **Validé** | `PASS: five morphologies, height, independent meshes and eyes, subdivision, save/reopen` |
| `validate_controls.py` (attendu = formule générale des shape keys) | **Partiel** | Passe jusqu'à la ligne ~112 ; la section de migration exige un `adult-original.blend` d'ancien schéma absent. Migration d'anciens fichiers : **non testée** |

## Passe sur les 35 autres scripts `validate_*` / `check_*` (clone isolé, adaptateur, `-- <dossier>`)

**Résultat : 2 réussis, 33 non exécutables en l'état. Aucun n'a produit d'échec attribuable au produit.**

| Statut | Scripts | Observation |
|---|---|---|
| **Validé** | `validate_nature21` (`NATURE21_MATH_PASS 21`), `validate_physics_rest21` (`NATURE21_XPBD_REST_PASS`, allongement relatif −0,05 %) | Calculs de fibre et XPBD au repos. |
| **Non testé — arguments spécifiques** | `validate_age_dimensions`, `age_eye_fit`, `age_geometry`, `age_transitions`, `body_mass_neutral`, `modeling_batch`, `modeling_workflow`, `muscle_workflow`, `musculature`, `skin_relief`, `surface_fix`, `regional_muscles18` | Exigent 2 à 3 chemins (`asset`, `old_asset`, `output`) ou un mode ; `ValueError: not enough values to unpack`, `IndexError`. Les `old_asset` sont des versions antérieures de `realistic.blend` introuvables dans le dépôt. |
| **Non testé — convention de sortie différente** | `validate_extended_body`, `global_physique`, `mass_render_surface`, `mass_transitions`, `relief_render_surface` | `PermissionError` : ils traitent l'argument comme un fichier, pas un dossier. |
| **Non testé — fichiers de `validation/` absents** | `age…`, `atlas14_measurements`, `atlas14_reopen`, `surface_atlas15`, `surface_atlas15_ages`, `delivery12_reopen`, `delivery13_reopen`, `check_delivery18`, `regional_compat18`, `regional_upgrade18`, `hair20`, `dense_hair20`, `physics_profile22`, `check_nature21` | `Cannot read file …\validation\…` : dépendent de résultats d'itérations antérieures. |
| **Non testé — conflit de mon adaptateur** | `validate_groom28`, `check_groom_continuity25`, `check_review_scenes23` | `already registered as a subclass 'HUMANMODELING_OT_create'` : ces scripts enregistrent déjà l'extension eux-mêmes ; mon adaptateur l'avait enregistrée avant. À relancer sans lui. |

Le dossier `validation/` local pèse 13 Go ; je ne l'ai pas copié dans le clone. Les scripts qui en dépendent ne sont donc pas reproductibles sur un clone neuf ni par un autre développeur.

## Tests fonctionnels et visuels propres (scripts jetables, clone isolé, sans toucher à la session Blender de l'utilisateur)

Données : `docs/audit/mesures-controles.json` (48 contrôles ±1, sexe, âge, silhouettes, aléatoire, tout à +1, temps) et `mesures-fonctions.json` (relief, préréglages, géométrie, taille, calibration d'âge, groom). Rendus Workbench : `rendu-ages-sexes.png`, `rendu-silhouettes-profil-M.png`. Captures d'interface : `ui-sidebar-*.png` (voir UI_REVIEW.md).

Note de méthode : un premier passage donnait 0 mm partout parce que mon script ne faisait pas `Key.update_tag()` après chaque changement de propriété ; corrigé. Mesures faites sur la cage (modificateurs désactivés) sauf mention. Le corps créé par défaut est masculin (Morphologie = 1, 1,689 m) ; mes balayages d'âge, silhouettes et aléatoire ont été faits avec Morphologie = 0 (féminin), donc les écarts « vs neutre » de ces balayages incluent l'écart de sexe (≈ 96 mm) et ne servent pas de mesure d'amplitude.

Résultats : voir FEATURE_STATUS (lignes correspondantes) et ISSUES I-13 à I-18. Non testé : qualité visuelle fine du visage, yeux/dents, matériaux, sculpture des cheveux, collisions, mode Édition, anciens fichiers.

## Passe des scripts historiques avec leurs vrais fichiers d'essai (2026-11-21)

Méthode : copie (lecture seule sur l'original) de 15 dossiers de `validation/` (7,3 Go) dans le clone isolé ; arguments (`asset` = `extension/data/realistic.blend`, `old_asset` = `validation/proportions-14/extension-13/data/realistic.blend`) ; adaptateur d'alias pour les scripts qui importent `bl_ext.user_default.human_modeling`. Une première erreur de ma part (substitution `@O` dans `@OUT`) a faussé 3 sorties ; relancés ensuite.

**Réussis (27)** — `validate_age_eye_fit`, `age_geometry`, `age_dimensions` (mesure, sans assertion), `atlas14_measurements` (`ATLAS_EVALUATED_TARGETS_PASS`), `atlas14_reopen`, `delivery13_reopen`, `check_delivery18`, `extended_body` (96 cas, 0 échec), `mass_render_surface`, `mass_transitions`, `relief_render_surface`, `modeling_batch` (109 cas, 0 échec), `modeling_workflow`, `skin_relief` (30), `regional_compat18` (57), `regional_muscles18` (48 cas, 0 échec), `regional_upgrade18` (18, migration 0.13 → 0.14), `surface_atlas15`, `surface_atlas15_ages`, `hair20` (36), `dense_hair20` (12), `check_nature21` (5), `physics_profile22` (5), `check_review_scenes23` (scènes de revue : 48 contrôles, schéma 9, 0 driver invalide), `groom_reopen25`, `groom28` (densités 70/180/250 cm²), `check_groom_continuity25`.

**Échecs par assertion (8) — à interpréter, pas tous des défauts du produit :**

| Script | Assertion | Lecture |
|---|---|---|
| `validate_age_transitions` | `unchanged_from_previous` faux (sexe 0, stade 1,5) | Le neutre aux âges intermédiaires diffère de la version 0.13 (voir `body_mass_neutral`) |
| `validate_body_mass_neutral` | écart 0,0177 m à (sexe 0, stade 1,5) contre le seuil 1e-7 m | **Changement de forme de 17,7 mm** au neutre entre 0.13 et aujourd'hui pour un stade intermédiaire féminin ; voulu ou non : à trancher |
| `validate_musculature` | `max |courant − ancien| < 1e-6` faux | Identité au neutre avec l'ancien asset non respectée (même famille) |
| `validate_muscle_workflow` | `hm_corpulence == fat et hm_muscles == muscle` faux | Test périmé probable : les silhouettes pilotent désormais `whole_body`, `corpulence` est masqué |
| `validate_delivery12_reopen` | 47 contrôles attendus | Test périmé : 49 contrôles (ajouts depuis 0.12) |
| `validate_global_physique` | tous les écarts régionaux > 0,5 mm | Le cou ne bouge que de 0,049 mm quand la corpulence globale change |
| `validate_surface_fix` | l'ancien asset devrait avoir 82 croisements | Fixture ancienne non équivalente (inconclusif) |
| `validate_groom_collision29` (non suivi, travail en cours) | allongement < 5 % | 7,3 % à l'image 4, 1 guide pénètre de 1,9 mm : la correction en cours n'est pas encore au niveau visé |

Fichiers manquants restants : aucun script n'est resté bloqué par un fichier absent après la copie, sauf ceux ci-dessus.

## Passe exhaustive (voir `ETAT_DES_LIEUX.md`)

Scripts jetables hors dépôt : caractérisation de 48 contrôles ±1 (+ sexe et âges), zones déplacées, yeux, croisements ; 32 opérateurs dont polls dans 4 contextes ; repères, ajustements, référence ; transformations et duplication ; groom exhaustif (11 zones, paramètres, qualité, densité, export/import, XPBD) ; contraintes (tous les contrôles à ±1, 30 graines) ; rendus Workbench de 6 familles de visage et 9 de corps en vue de face et de profil ; gros plans (visage, yeux, bouche, oreille, mains, pieds) ; captures d'interface dans 5 états ; paquet : `extension validate`, `extension build` (23,9 Mo), installation dans un dossier de configuration isolé (`BLENDER_USER_RESOURCES`), activation, création d'un humain et d'un groom depuis le paquet installé ✅.

Refusé : accès pour piloter la souris dans Blender (undo et interactions réelles non testés).

Correction de ma part : mon premier relevé de croisements (68, puis 162) avait été fait modificateurs désactivés ; avec les modificateurs par défaut, 0 sur le corps neutre et sur chaque contrôle. Cette précision est reportée dans ISSUES I-14.

## Sondes complémentaires (scripts jetables hors dépôt, même adaptateur)

| Sonde | Statut | Résultat observé |
|---|---|---|
| `unregister()` puis `register()` ×3 | **Validé** | 13 classes présentes après chaque `register`, 0 après `unregister`, pas d'exception ; propriétés `Object.hm_*` et `hl_groom*` présentes |
| Drivers des shape keys | **Validé** | 459 drivers, 0 invalide, avant et après enregistrement/réouverture du `.blend` |
| Enregistrer puis rouvrir un corps | **Validé** | schéma 9 conservé, 0 driver invalide |
| `set_height` : convergence | **Validé** | 3 appels successifs → échelle stable 1,0360 ; sans modificateurs : 1,600000023 pour 1,60 demandé |
| Écart `set_height` / `dimensions` | **Cause établie** | Subsurf niveau 1 : surface évaluée 1,75 vs `dimensions` 1,750835 ; Displace sans effet (force 0,0) |
| Écart mélange de sexe | **Cause établie** | clés actives hors formule du test (voir ISSUES I-02) |
| Undo (`ed.undo`) | **Non testé** | `ed.undo` impossible en mode background (contexte incorrect). Les opérateurs modifiants déclarent `UNDO` : 47 `bl_idname`, 5 `bl_options` sans `UNDO` sont des panneaux (`DEFAULT_CLOSED`). Le comportement réel d'undo n'est pas vérifié. |

## Non vérifié

- Installation réelle de l'archive (`extension build`) et activation dans l'interface ; affichage des panneaux.
- Rechargement de l'extension (unregister/register) à chaud ; undo/redo.
- Performances des sliders (aucune mesure effectuée).
- Rendu, UV/matériaux visuels, symétrie visuelle ; les prototypes restent « en revue » selon le README.
- Branches : `codex/modelisation` = `main` (rien à tester de spécifique).

## Passe finale (2026-11-21)

Option C de bout en bout (poids compilés dans les nœuds, façade de nœuds), interface native (menus, F9, pie, raccourcis, annulation en chaîne, repères à la souris, thème clair), assets/lien/override, exports glTF/FBX, migration de 6 anciens fichiers, masque de densité, XPBD à vide, ordre des modificateurs : voir `SUIVI_REPRISE.md` §4 bis (G à J) et `docs/audit/proto-*.json`. Résultat global : tout est validé sauf (1) la déformation complète par nœuds jugée trop lente, (2) le gizmo non concluant, (3) Blender 5.0/5.1/5.3 non lancés par consigne, (4) la persistance des overrides non testée.
