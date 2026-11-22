# LOT5_INVENTAIRE — retrait de l'ancien moteur : **migrer d'abord, ne supprimer que le nécessaire**

Date : 2026-11-22 (révision 2). Rien n'est supprimé par ce document. Consignes de l'utilisateur : « qu'on décommissionne l'ancien code et qu'on parte sur notre code » (22/11), puis « on ne supprime que ce qui est nécessaire ou on le migre si besoin » (22/11, remplace la liste de suppression de la révision 1). Les fichiers anciens n'ont aucune valeur de production (D-21).

## Règle appliquée à chaque élément

1. **Nécessaire** = ce qui bloque le moteur natif (deux moteurs actifs en même temps, marqueurs en conflit, poids du paquet, ou code qui casserait au premier appel sur un corps natif) → retiré.
2. **À migrer** = ce qui sert encore au corps natif mais lit l'ancien moteur → porté sur la façade `humanloom`, puis l'ancien accès est retiré.
3. **À garder** = code inoffensif (jamais appelé sur un corps natif, `poll` faux) → **conservé tel quel**, éventuellement déplacé dans `tools/archive/` plus tard ; **pas supprimé par principe**.

## Condition de départ (ordre imposé)

1. Lot 2 terminé et commité (interface, portage de `measurements`, `anatomy`, `landmark_sets`, `geometry_quality`, `character_presets`, `groom`, duplication complète).
2. **Yeux autonomes** : aujourd'hui chargés depuis `realistic.blend`. Les migrer vers un fichier de données propre (`human_eyes.blend`) avant de toucher à l'asset.
3. Suite complète à 0 régression avant, puis après chaque étape du lot 5.

## Tableau de décision

| Élément | Où | Décision | Justification |
|---|---|---|---|
| `realistic.blend` (23,9 Mo, 462 clés) | `extension/data/` | **Migrer** : déplacer vers `tools/data/` (hors paquet) ; les yeux vont dans `human_eyes.blend` | Nécessaire pour alléger le paquet (~24 Mo) ; **non supprimé** car `build_human_nodes.py` lit ses clés pour régénérer `human_nodes.blend` et `make_neutral_reference.py` en dépend |
| Opérateur `human_modeling.create` (création de l'ancien corps) | `__init__.py` | **Retirer** (nécessaire) après passage de Ajouter > Humain sur `humanloom.create` | Deux moteurs actifs = deux humains possibles, schémas différents |
| Alias `human_modeling.*` d'opérateurs | `__init__.py` | **Garder** tant qu'un test ou un script les appelle ; sinon rediriger vers le nouveau | Pas nécessaire de supprimer |
| Moteur à clés : génération des clés et pilotes (`bind_control`, `property_name`) | `proportions.py` | **Retirer** les parties qui créent des clés/pilotes (nécessaires) ; **garder** les déclarations de contrôles (`*_CONTROLS`) que l'interface lit | Les déclarations servent de source tant que l'interface ne lit pas le groupe |
| `CURRENT_SCHEMA = 9` et lectures de `human_modeling_schema` | `__init__.py`, `groom.py`, `measurements.py` | **Migrer** vers `humanloom.schema_version` | Sinon un corps natif est refusé par `groom` |
| Marqueur `human_modeling_body` | partout | **Migrer** vers `humanloom.is_human` ; **ne pas** renommer l'identifiant d'extension | D-22 |
| `age_shapes.py`, `body_profiles.py`, `skin_relief.py`, `character_presets.py` | modules | **Migrer** (déjà en cours dans le lot 2) | Servent au corps natif |
| `HUMANMODELING_OT_upgrade` + contrôle de schéma < 9 | `__init__.py` | **Garder** (poll faux sur un corps natif) | Inoffensif ; pas nécessaire de retirer |
| `muscle_upgrade.py` | module | **Garder** | Inoffensif, aucun appel sur un corps natif |
| Panneau « Volumes des anciennes versions » et `human_modeling_show_legacy` | `__init__.py` | **Retirer** seulement si le lot 3 supprime `corpulence`/`body_mass` ; sinon garder | Dépend d'une décision de contrôles |
| `surface_fix.py` et `HUMANMODELING_OT_repair_surface` (paupières internes) | module, `__init__.py` | **Garder** jusqu'à preuve que le corps natif n'en a pas besoin | **Point à vérifier** : `validate_geometry_quality` sur corps natif |
| Lecture des anciens formats de préréglages | `character_presets.py` | **Garder** si la lecture ne gêne pas l'écriture du format v2 ; sinon retirer | D-22 : abandon, mais pas de suppression forcée |

## Tests et outils

| Élément | Décision |
|---|---|
| `validate_controls`, `validate_presets`, `validate_surface_fix` | **Garder** classés OBSOLÈTE (déjà le cas) |
| `validate_delivery12_reopen`, `validate_delivery13_reopen`, `validate_regional_upgrade18`, `validate_regional_compat18` et parties « mise à jour » | **Classer OBSOLÈTE** dans le lanceur (comme les précédents), **sans supprimer les fichiers** |
| Tests qui lisent `hm_*` pour des fonctions conservées | **Migrer** sur la façade (lot 2, en cours) |
| `make_legacy_fixtures.py`, `update_open_*`, `update_live_*`, `reload_installed_extension.py`, `repair_*_eyelids.py` | **Garder** ; déplacer vers `tools/archive/` seulement quand ils gênent le lanceur |
| `validate_human_nodes`, `validate_human_native`, `neutral_reference*` | **Conserver impérativement** : seul garde-fou de forme |

## Risques

1. **Régénération du groupe de nœuds** : impossible si `realistic.blend` disparaît du dépôt ; c'est pourquoi il est déplacé et non supprimé.
2. **Correction des paupières** : à confirmer sur corps natif avant tout retrait de `surface_fix`.
3. **Référence figée** : ne jamais la régénérer après le déplacement de l'asset (D-19).
4. **Mesure** : taille du paquet avant/après et test d'installation (`extension build` + activation isolée).

## Critères d'acceptation

- Aucun humain de l'ancien moteur ne peut plus être créé ; Ajouter > Humain crée un humain natif.
- `groom`, mesures, repères, géométrie, préréglages fonctionnent sur un corps natif.
- Paquet plus léger (taille mesurée) ; `extension build` réussit.
- Suite complète à 0 régression ; liste des tests classés OBSOLÈTE.
- Ce qui est resté (code gardé « inoffensif ») est listé dans `SUIVI_REPRISE.md`.
