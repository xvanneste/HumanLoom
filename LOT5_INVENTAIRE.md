# LOT5_INVENTAIRE — retrait de l'ancien moteur (clés de forme + pilotes) et du code de migration

Date : 2026-11-22. Rédigé pendant que la session de dev porte le lot 2 : **rien n'est supprimé par ce document**. Décision de l'utilisateur (message du 2026-11-22) : « qu'on décommissionne l'ancien code et qu'on parte sur notre code ». Les fichiers anciens n'ont aucune valeur de production (D-21).

## Condition de départ (ordre imposé)

1. Lot 2 terminé et commité : interface, portage de `measurements`, `anatomy`, `landmark_sets`, `geometry_quality`, `character_presets`, `groom`, duplication complète.
2. **Les yeux n'appartiennent plus à `realistic.blend`** : ils sont aujourd'hui chargés depuis cet asset (23,9 Mo, 462 clés). Il faut d'abord un asset de yeux autonome (ex. `human_eyes.blend`, deux objets, pilotes déjà relus sur les entrées du modificateur) **avant** de retirer `realistic.blend`. Le relief de peau et son groupe de sommets doivent aussi avoir quitté l'asset.
3. Suite complète à 0 régression avant la suppression, puis après.

## À retirer (code de l'extension)

| Élément | Où | Lié à | Remarque / vérification |
|---|---|---|---|
| Opérateur de mise à jour `HUMANMODELING_OT_upgrade` et contrôle de schéma < 9 | `__init__.py` | migration d'anciens fichiers (D-21) | |
| Panneau « Volumes des anciennes versions » + `human_modeling_show_legacy` | `__init__.py` | `corpulence`, `body_mass` retirés (lot 3) | |
| `muscle_upgrade.py` | module | migration muscles 0.8 → 0.14 | seul usage hors outils : `__init__.py` |
| `surface_fix.py` (clé « Surface · Paupières internes », révision 1) | module | réparation d'un ancien asset | **point à vérifier** : la correction des paupières internes sert-elle aussi au corps natif ? `validate_surface_fix` déjà OBSOLÈTE (I-34) ; contrôle par `validate_geometry_quality` sur corps natif avant de supprimer |
| `HUMANMODELING_OT_repair_surface` | `__init__.py` | idem | |
| `proportions.py` : `bind_control`, `property_name`, génération des clés de forme et des pilotes | module | moteur à clés | garder les **déclarations** de contrôles (`BODY_CONTROLS`, `FAT_CONTROLS`, `MUSCLE_CONTROLS`, `FACE_CONTROLS`) tant que l'interface les lit ; sinon les lire dans le groupe |
| `CURRENT_SCHEMA = 9` et lectures de `human_modeling_schema` | `__init__.py`, `groom.py`, `measurements.py` | schéma 9 | remplacé par `humanloom.schema_version` |
| Lecture des anciens formats de préréglages | `character_presets.py` | D-22 | nouveau format, version 2 |
| Opérateur `human_modeling.create` et alias `human_modeling.*` | `__init__.py` | conservés pendant le lot 2 (PLAN_LOT2 §9.3) | retrait ici |
| Marqueur `human_modeling_body`, propriétés `hm_*` du bloc de clés | partout | D-22 (propriétés renommées) | **ne pas** renommer l'identifiant d'extension `human_modeling` |
| `realistic.blend` (23,9 Mo, 462 clés) | `extension/data/` | moteur à clés | retrait seulement après l'asset de yeux autonome ; **allège le paquet de ~24 Mo** |
| `age_shapes.py`, `body_profiles.py`, `skin_relief.py` | modules | déjà portés vers `human.py` (la session de dev les modifie) | à conserver s'ils lisent déjà la façade ; sinon porter |

## À retirer (outils et tests)

| Élément | Raison |
|---|---|
| `validate_controls`, `validate_presets` (déjà OBSOLÈTE, D-21), `validate_surface_fix` (OBSOLÈTE, I-34) | migration / ancien asset |
| `validate_delivery12_reopen`, `validate_delivery13_reopen`, `validate_regional_upgrade18`, `validate_regional_compat18` | acceptation de migration d'anciens fichiers |
| Partie « mise à jour 0.8 » de `validate_muscle_workflow` ; à examiner : `validate_atlas14_reopen`, `validate_modeling_workflow` | idem |
| `tools/make_legacy_fixtures.py`, fixtures `adult-original.blend`, `legacy-03.blend` | plus de fichier ancien à préserver |
| Scripts `update_open_*`, `update_live_*`, `reload_installed_extension.py`, `repair_*_eyelids.py`, `build_*` d'anciennes livraisons | historique ; **déplacer vers `tools/archive/`** plutôt que supprimer tant que l'historique git ne suffit pas |
| `validate_human_nodes` | **conserver** : il garde la forme native contre la référence figée |

## À conserver (important)

- `tools/data/neutral_reference.json`, `tools/neutral_reference.py`, `tools/make_neutral_reference.py` : **seul garde-fou de forme**. Attention : `make_neutral_reference.py` régénère depuis `realistic.blend` ; il faudra le faire pointer vers un humain natif **et** garder l'ancien fichier de référence comme référence de la forme actuelle (D-19) ; ne pas régénérer la référence après la suppression de l'asset.
- `human_nodes.blend`, `build_human_nodes.py` : le générateur lit encore les clés de `realistic.blend` pour compiler les couches. **Conséquence : supprimer `realistic.blend` du dépôt empêche de régénérer `human_nodes.blend`.** À trancher : soit garder `realistic.blend` dans `tools/data/` (hors paquet de l'extension), soit considérer `human_nodes.blend` comme source.
- Format de zones de cheveux `humanloom.groom` (D-22) et `groom.py`.

## Risques

1. **Régénération impossible** si `realistic.blend` est supprimé du dépôt : à décider avant (voir ci-dessus). Recommandation : le déplacer hors de `extension/` vers `tools/data/` (non empaqueté), pas le supprimer.
2. **Correction des paupières** : à vérifier sur corps natif avant retrait de `surface_fix`.
3. **Pas de retour en arrière par fichiers** : l'historique git est le seul filet.
4. **Mesure à refaire** : taille du paquet avant/après ; test d'installation par `extension build` + activation isolée.

## Critères d'acceptation du lot 5

- Plus aucune référence à `hm_*`, `human_modeling_body`, `human_modeling_schema`, `bind_control` dans `extension/` (grep à 0, sauf l'identifiant d'extension et la lecture documentée de l'ancien nom si conservée).
- `extension build` réussit ; paquet plus léger (taille mesurée).
- Suite complète à 0 régression ; tests obsolètes retirés et listés.
- Humain natif : toutes les cases de `DESIGN_NATIF.md` §10 qui sont automatisables passent.
