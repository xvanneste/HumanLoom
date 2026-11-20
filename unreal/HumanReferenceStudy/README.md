# Étude MetaHuman pour la modélisation Blender

Projet isolé créé le 19 novembre 2026 avec Unreal **5.8.4**, build 58902052. Il contient les copies importées des deux personnages du paquet fourni par l'utilisateur. Notre base Blender reste conservée ; les références servent à l'étude des volumes, en particulier des muscles.

## Résultat vérifié

- Le serveur MCP natif répond sur `http://127.0.0.1:8000/mcp`. `tools/list`, `list_toolsets`, `describe_toolset`, `ListSkills`, la sauvegarde et une recherche réelle des deux personnages ont été appelés avec succès.
- Les plugins `ModelContextProtocol` et `AllToolsets` sont activés, ainsi que MetaHuman Creator, le SDK, Python et Geometry Scripting. La connexion HTTP du plugin Codex existant utilise le même endpoint ; aucune seconde connexion Codex concurrente n'a été ajoutée. Le catalogue Unreal n'était pas exposé dans cette session cliente : les appels vérifiés ont utilisé le protocole MCP HTTP local directement, via `tools/unreal_mcp_local17.py`.
- Les personnages sont `/Game/ReferenceImports/MHC_Base_Female` et `/Game/ReferenceImports/MHC_Base_Male`.
- Les corps complets générés sont dans `/Game/ReferenceGeometry/`. L'export de géométrie utilise le modèle source LOD0 par Geometry Script, puis écrit des OBJ pour l'analyse locale. Il ne demande ni service d'auto-rig ni téléchargement de textures.
- Chaque OBJ possède **49 104 sommets et 95 330 triangles**. Les deux imports Blender 5.2 conservent ces effectifs après sauvegarde et réouverture. Les huit vues orthographiques montrent les corps entiers.

Les rapports, OBJ et scènes Blender sont dans `../../validation/unreal-17/`. Les fichiers de référence et sorties générées ne font pas partie du paquet du générateur. Ils ne sont pas redistribués dans l'extension.

## Relancer le serveur

Depuis la racine BlenderDev :

```powershell
./tools/start_unreal_study17.ps1
```

Ce lanceur démarre l'éditeur en arrière-plan, avec `-NullRHI`, un cache local au projet et le MCP actif. Il garde l'instance ouverte, contrairement aux commandes `-ExecutePythonScript`, qui ferment l'éditeur une fois le script terminé. Le projet peut aussi être ouvert dans Unreal pour une inspection interactive.

## Scripts et contrôles

- `Content/Python/import_reference_characters.py` : import initial du paquet `.mhpkg` dans ce projet uniquement.
- `Content/Python/export_reference_cpu.py` : génération des géométries si nécessaire, puis extraction de leur LOD0 avec `GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh`.
- `tools/inspect_metahuman_exports17.py`, à la racine BlenderDev : import des OBJ dans Blender 5.2, vues sans texture et scènes d'inspection.
- `tools/verify_metahuman_exports17.py` : réouverture des deux scènes et comparaison des effectifs avec le rapport Unreal.
- `validation/unreal-17/check-imported-assets.json` : réponse réelle du serveur MCP après le dernier redémarrage, contenant les deux personnages.

L'OBJ contient la géométrie en mètres. Il ne transporte pas les UV, matériaux, morphs ou poids du personnage. Les ressources Unreal du projet conservent les données importées. Les axes locaux du maillage diffèrent de ceux d'un acteur Unreal : les scènes Blender appliquent une rotation d'affichage de 90° autour de Z, vérifiée visuellement, pour présenter la face vers −Y. Aucun sommet n'est sculpté lors de cette orientation.

La géométrie comporte plusieurs composantes et des bords de sections. Elle n'est pas déclarée comme un corps monolithique étanche : les futures mesures de contours doivent identifier la peau externe et les raccords, sans confondre les surfaces internes, les yeux ou les séparations de sections avec une silhouette biologique.

## Diagnostic conservé

Le premier démarrage a échoué parce que le cache Unreal global n'était pas accessible en écriture depuis l'environnement d'exécution. Le lanceur donne désormais un `LocalDataCachePath` dans le projet.

L'exporteur FBX de maillage squelettique a provoqué une assertion `MeshObject` dans `SkinnedMeshComponent.cpp` sous NullRHI, y compris avec le baking de matériaux désactivé. Les journaux sont conservés dans `Saved/Logs`. L'extraction CPU directe a abouti pour les deux personnages. `export_reference_geometry.py` est un essai FBX réservé à un éditeur avec rendu ; un garde empêche de le rejouer sous NullRHI.

Ces formes sont des références artistiques, pas des échantillons anthropométriques. Leur import et export réussis ne valident pas automatiquement leurs proportions comme norme pour tous les adultes ou pour d'autres âges.
