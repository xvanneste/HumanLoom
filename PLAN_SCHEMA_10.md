# PLAN_SCHEMA_10 — schéma 10 « départ de zéro » (proposition à valider, rien n'est codé)

Date : 2026-11-21. Branche `codex/natif`. **Révision 2** : l'utilisateur a décidé que les anciens fichiers peuvent être jetés (aucun fichier en production) : **D-21**. La migration de fichiers existants, le paramètre `shape_revision` et le bouton « adopter la forme actuelle » (D-20) **disparaissent** du plan ; la version précédente de ce document les contenait. Les faits viennent de mesures citées ; les **propositions** et les **points à vérifier** sont marqués comme tels.

## 1. Objectif et règles qui s'imposent

Passer du schéma 9 (462 clés de forme, drivers sur `hm_*`) à un schéma 10 propre : paramètres sur l'objet (façade D, UUID), identité du corps et du visage portée par le groupe de nœuds « HL Human » (D-05, D-07, D-14), amplitudes ×6 (D-18), contrôles redondants regroupés (I-46), **sans code de migration**.

| Règle | Source |
|---|---|
| Plus aucun fichier à préserver : pas de migration, pas de rétrocompatibilité de scène | **D-21** |
| La forme de référence est celle de l'asset actuel avec Atlas14 (`tools/data/neutral_reference.json`) | D-19 |
| Arbitrage vitesse accepté : nœuds ≈ +16 à +20 ms avec Subsurf niveau 1 | D-09 |
| Facteur ×6, plafonné par contrôle là où des faces se retournent | D-18 |
| Blender 5.2 uniquement | D-13 |

**Ce que D-21 simplifie** : plus de test d'équivalence « forme d'un ancien fichier », plus de fixtures d'anciennes versions, fusions de contrôles et amplitudes valables **pour tout le monde** (le « facteur 1 pour les fichiers migrés » et la limite « une fusion ne conserve pas la forme » ne comptent plus). **Ce qu'il ne change pas** : l'asset actuel reste la référence de forme (D-19), et l'équivalence entre moteur de nœuds et clés de forme reste à prouver sur des états courants.

## 2. À arbitrer (nouvelles questions ouvertes par D-21)

1. **Identifiants** : l'id d'extension `human_modeling` et les propriétés `hm_*` / `human_modeling_*` ont été gardés « pour ne pas casser les installations et scènes existantes » (`CLAUDE.md`, D-02). Sans fichier à préserver, **peut-on les renommer** (par exemple `humanloom` et `humanloom.<chemin>`) ? Recommandation : oui pour les propriétés de personnage (la façade D les remplace de toute façon), **id d'extension : à décider** (vérifié : aucun tag ni release GitHub, version 0.15.2 dans le manifeste ; mais le dépôt est public, un tiers a pu l'installer ; risque faible, non mesurable).
2. **Préréglages JSON** des anciennes versions : les abandonne-t-on aussi ? (`character_presets` lit des formats antérieurs.)
3. **Groom** (zones de cheveux, JSON d'export) : même règle, ou le format `humanloom.groom` schéma 1 reste-t-il compatible ? Il n'est pas concerné par la migration du corps ; à confirmer.

## 3. Lots proposés (chacun livrable et testable seul)

### Lot 1 — Générateur du groupe « HL Human » (étape 3 de `SUIVI_REPRISE.md` §9)
`tools/build_human_nodes.py` (point de départ : `tools/audit/cproto3_1e4.py`) → `extension/data/human_nodes.blend`, déterministe. Une couche de base locale par contrôle, couche Atlas14 incluse.
**Critères** : équivalence < 0,02 mm sur ≥ 25 états contre la référence figée et le moteur actuel (prototype mesuré : 0,047 mm sur ~150 déformations, ~8 ms ; **à refaire avec Subsurf**) ; suppression des couches ; fichier rouvert sans l'extension ; temps d'un curseur ≤ 33 ms sur la cage (`DESIGN_NATIF.md` §10).

### Lot 2 — Tranche verticale native (étape 5)
Ajouter > Humain (F9), objet `MESH` identifié par `humanloom.is_human` et un UUID, façade D, panneau Propriétés > Objet et barre latérale, duplication, annulation, animation, yeux et cheveux liés par pointeurs. Critères : `DESIGN_NATIF.md` §10 (onze cases).

### Lot 3 — Contrôles regroupés (I-46)
- Une seule échelle de corpulence : on garde `whole_body` (forme de référence) ; `corpulence`, `body_mass` et le panneau « Volumes des anciennes versions » disparaissent du schéma 10 (plus de fichier qui en dépende).
- Fusions candidates : `lips`/`lip_thickness`, `jaw`/`jaw_angle` (cosinus 0,61 et 0,77) : à décider avec l'artiste.
- **Test** : la forme obtenue par les nouveaux contrôles reste dans la tolérance de la référence aux états courants.

### Lot 4 — Amplitudes ×6 (D-18, I-45)
- ×6 pour `eyelid_aperture`, `lip_thickness`, `lips`, `mouth`, `mouth_corner`, `eye_height`, `cheeks`, `jaw`, `forehead`, `nose_bridge`, `jaw_angle`, `chin`, `head_width`, `muscle_definition` ; plafond ×2–×3 pour `ears_size`, `ears_angle`, `eye_spacing`, `facial_asymmetry`, `nose_length`, `nose_width`, `head_height` ; `fat_face` et `muscles_abdomen` à reformuler (expressions bornées à ±1).
- Facteur **dépendant de l'âge** (plafonds plus bas pour les enfants ; matrice de `AMPLITUDES_CONTROLES.md` §9, 2 sexes × 4 âges).
- **Non fait** : les cibles sculptées des contrôles plafonnés ; la vérification sur la **surface lissée** (les mesures actuelles portent sur la cage, neutre adulte).
- Critère : aucun retournement de face aux facteurs retenus, par sexe et par âge.

### Lot 5 — Retrait du code et des tests de migration
Inventaire à faire avant de supprimer (rien n'est supprimé sans accord) :
- **Code** (`extension/`) : opérateur de mise à jour `HUMANMODELING_OT_upgrade` et son contrôle de schéma (`__init__.py`), `muscle_upgrade.py`, `surface_fix.py`, panneau des volumes hérités, lecture des anciens préréglages (`character_presets`). **Point à vérifier** : certaines de ces pièces servent peut-être aussi aux nouveaux corps (correction des paupières internes).
- **Tests** à classer « obsolète » : `validate_controls` et `validate_presets` (acceptation de migration, en échec attendu aujourd'hui), `validate_delivery12_reopen`, `validate_delivery13_reopen`, `validate_regional_upgrade18`, `validate_regional_compat18`, `validate_surface_fix` (déjà obsolète) ; partie « mise à jour 0.8 » de `validate_muscle_workflow` ; à examiner : `validate_atlas14_reopen`, `validate_modeling_workflow`.
- `tools/make_legacy_fixtures.py` devient inutile.

## 4. Ordre

1 → 2 → 3 et 4 (indépendants entre eux, après le lot 1) → 5 en dernier, après accord sur l'inventaire. Les étapes 7 et suivantes (repères, nouveaux contrôles, UV, dents, rig, anatomie) restent après le schéma 10.

## 5. Tests d'acceptation

| Test | Lot |
|---|---|
| Équivalence nœuds / référence figée < 0,02 mm sur ≥ 25 états ; temps ≤ 33 ms (cage) | 1 |
| Fichier rouvert sans l'extension : forme et animation conservées | 1, 2 |
| Critères `DESIGN_NATIF.md` §10 | 2 |
| Aucun retournement de face aux facteurs retenus, par sexe et âge | 4 |
| 0 régression sur les tests conservés du lanceur (44 OK aujourd'hui, moins les obsolètes retirés) | tous |

## 6. Risques

- **Bascule de moteur** : plus de filet de sécurité par fichiers anciens ; la référence figée est le seul garde-fou de forme (1 sommet sur 25, plus pieds, mains, paupières et yeux) : une déformation locale ailleurs peut passer inaperçue.
- **Suppression trop large** : retirer du code « de migration » qui sert aussi aux nouveaux corps (paupières) ; d'où l'inventaire du lot 5 avant toute suppression.
- **XPBD des cheveux** : non revalidé après le changement d'ordre de pile ; sans lien direct avec le schéma 10.
- **Dépôt public** : aucun tag ni release (vérifié), mais un tiers a pu installer l'extension depuis le dépôt ; renommer l'id d'extension casserait cette installation (voir §2, question 1).

## 7. Décisions attendues de l'utilisateur

1. Renommer les propriétés de personnage ? (recommandation : oui) et l'id d'extension ? (à décider ; risque faible, aucune release).
2. Abandonner aussi les anciens préréglages JSON ? Le format groom reste-t-il compatible ?
3. Valider l'ordre des lots et l'inventaire de retrait (lot 5) avant d'y toucher.

## 8. Décisions prises (D-22, 2026-11-21)

Propriétés de personnage renommées ; id d'extension `human_modeling` conservé ; anciens préréglages JSON abandonnés, format groom inchangé ; ordre des lots validé ; lot 5 seulement après inventaire montré et accord. **Lot 1 lancé.**
