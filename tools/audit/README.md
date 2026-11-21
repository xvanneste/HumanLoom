# tools/audit — scripts jetables de l'audit (2026-11-21)

Ces scripts ont produit les mesures citées dans `SUIVI_REPRISE.md`, `ETAT_DES_LIEUX.md` et `docs/audit/`. Ils sont conservés pour **reproduire** un résultat, pas comme code de production.

- `shim.py` : adaptateur qui fait pointer `bl_ext.user_default.human_modeling` vers le dossier `extension/` d'un clone, puis exécute un script d'essai (`blender --background --factory-startup --python shim.py -- --shim-root <clone> --shim-test <script> -- <arguments du script>`).
- `proto*.py` : prototypes d'API pour la conception native (voir `SUIVI_REPRISE.md`, tests P1 à P7).
- `gnproto*.py` : faisabilité d'une déformation du corps par Geometry Nodes.
- `ft*.py`, `deep.py`, `ops.py`, `vis.py`, `mac.py`, `anim*.py`, `drv.py`, `names.py` : mesures fonctionnelles, rendus, animation, analyse des drivers.
- `gui*.py`, `live.py`, `proto2_ui.py` : scripts lancés dans une instance Blender avec interface (captures d'écran de panneaux).
- `cproto.py`, `cfacade*.py` : option C (déformation par nœuds ; façade de nœuds + drivers). `migrate*.py` : migration d’anciens fichiers. `api_*.py`, `fbx2.py`, `trim2.py`, `scalpmove.py` : assets, overrides, exports, ordre des modificateurs. `proto2b_ui.py`, `proto2c_theme.py` : menus, F9, pie, outil, thème clair.
- `run7.sh`, `run8.sh` : lots de scripts historiques de `tools/` avec leurs arguments.

Les chemins absolus (dossier temporaire de session) sont à adapter. Ne jamais les lancer sur la session Blender de l'utilisateur : utiliser un clone et une instance séparée.
