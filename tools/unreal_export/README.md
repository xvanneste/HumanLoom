# Export des animations depuis Unreal Engine (côté Unreal)

Scripts de l'outil personnel « UnrealBlenderBridge » de l'auteur (repris tels quels, non modifiés). Ils s'exécutent **dans l'éditeur Unreal** (plugin *Python Editor Script Plugin* activé), pas dans Blender :

```
py "<dépôt>/tools/unreal_export/unreal/ue_probe.py"                 # vérifie l'API Unreal (chaque ligne doit dire OK)
py "<dépôt>/tools/unreal_export/unreal/run_export.py"               # export incrémental de toutes les AnimSequence
py "<dépôt>/tools/unreal_export/unreal/run_export.py" --analyze-only
py "<dépôt>/tools/unreal_export/unreal/run_export.py" --out D:/Export --root /Game/Characters --filter Locomotion
```

Faire *File > Save All* avant (la détection des changements lit les `.uasset` enregistrés). Sortie par défaut : `<Projet>/Saved/BlenderExport/` avec `manifest.json`, `inventory.json`, `export_report.json` et `animations/<squelette>/<dossier>/<Nom>.fbx`. `unreal_animation_library_manager/ualm_core.py` est le module partagé que `ue_inventory.py` importe (ne pas le déplacer).

Ensuite, côté HumanLoom : la galerie importe ces FBX (voir `docs/animations-import.md`).

**Droits** : ces scripts sont du code de l'auteur ; **les animations exportées ne le sont pas** (contenu Epic ou autre) : elles ne sont jamais ajoutées au dépôt (`.gitignore`) ni au paquet. Chaque utilisateur exporte ses propres fichiers dont il détient les droits d'usage.
