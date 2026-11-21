# ARCHITECTURE — Actuelle et cible

## Actuelle (observée)

```
extension/
  __init__.py      ~1 100 l. : opérateurs, panneaux (Humain > …), register()/unregister()
  proportions.py   contrôles (BODY/FAT/MUSCLE/FACE_CONTROLS), CURRENT_SCHEMA=9, drivers sur shape keys
  anatomy / landmark_sets / measurements / geometry_quality / surface_fix / skin_relief
  age_shapes / body_profiles / character_presets / muscle_upgrade
  groom.py         626 l. : 11 zones Hair Curves natives, PropertyGroup, opérateurs, panneau
  groom_fibers.py
  data/realistic.blend (24 Mo), data/*.json (références WHO, NHANES, physique)
tools/             ~157 scripts : build_ / validate_ / check_ / diagnose_ / render_ / assemble_
```

Points observés :
- Corps = maillage de base + shape keys « Morphologie » pilotés par drivers à expressions simples ; deux modificateurs (Surface, Relief de peau) ; schéma versionné (`human_modeling_schema`).
- Aucun handler global (`app.handlers` absent) : bon pour la stabilité au rechargement.
- Le groom est déjà séparé du reste dans ses modules (`groom.py` s'enregistre lui-même) et n'importe pas `tools/`.
- Défauts : `__init__.py` monolithique ; tests couplés à l'installation (ISSUES I-01) ; pas de séparation services/UI.

> **Mise à jour 2026-11-21 :** la conception cible détaillée (propriétés natives sur l'objet, intégration Blender, cycle de vie, phasage) est dans `DESIGN_NATIF.md`. Le schéma ci-dessous reste valable pour le découpage du code ; contrôleur/moteurs abstraits sont reportés.

## Cible proposée (progressive, pas de réécriture)

```
extension/
  __init__.py            register()/unregister() minimal, imports différés
  core/                  proportions, schéma, migrations, presets/sérialisation (sans UI)
  body/ face/ age/       morphing, contrôles, corpulence, visage, âge
  measure/               anatomy, landmark_sets, measurements, geometry_quality
  groom/                 groom.py, groom_fibers.py, physique
  materials/             (à créer : peau, yeux)
  rig/                   (à créer, hors périmètre actuel)
  ui/                    panneaux et opérateurs, un fichier par domaine
tests/                   lanceur unique (blender --background), fixtures générées, un test par module
tools/                   outils de dev uniquement ; prototypes anciens dans tools/archive/
```

Règles : `core` n'importe pas `bpy.types` d'UI ; `ui` dépend de tout le reste ; données de personnage sérialisées avec version de schéma et migration testée ; enregistrement de classes via une liste unique par domaine.

Séquence : d'abord le lanceur de test (I-01), puis extraction de `ui/` hors de `__init__.py` module par module en gardant les tests verts. À valider avec l'utilisateur avant tout déplacement de fichiers.
