"""Vignettes de la galerie de vêtements (lot V2) : une vignette par pièce procédurale (corps par défaut, vue de face, rendu Workbench) + index `garment_gallery.json`.

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/build_garment_gallery.py -- <DOSSIER_SORTIE> [--size 120]

À copier dans `extension/data/garment_thumbs/` (vignettes) et `extension/data/` (index)."""
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension import garments  # noqa: E402
from extension.animation import skeleton  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:]
OUT = Path(ARGS[0])
SIZE = int(ARGS[ARGS.index("--size") + 1]) if "--size" in ARGS else 120
OUT.mkdir(parents=True, exist_ok=True)
addon.register()
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
bpy.ops.humanloom.create()
body = bpy.context.object
skeleton.install(body)
body.modifiers["Human Modeling · Surface"].show_viewport = False
scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.render.resolution_x, scene.render.resolution_y = SIZE, int(SIZE * 1.5)
scene.display.shading.light = "STUDIO"
scene.display.shading.color_type = "MATERIAL"
scene.display.shading.show_cavity = True
scene.world = bpy.data.worlds.new("w") if scene.world is None else scene.world
scene.world.color = (1, 1, 1)
camera_data = bpy.data.cameras.new("cam")
camera_data.type = "ORTHO"
camera = bpy.data.objects.new("cam", camera_data)
scene.collection.objects.link(camera)
scene.camera = camera
camera.rotation_euler = (math.radians(90), 0.0, 0.0)
# cadrage par catégorie : corps entier pour les hauts/bas, plus serré pour les pieds, les mains et la tête
FRAMES = {"Hauts": (1.35, 1.12), "Vestes": (1.45, 1.1), "Bas": (1.3, 0.62), "Chaussures": (0.75, 0.2), "Couvre-chefs": (0.55, 1.6), "Accessoires": (0.8, 1.45)}
index = []
for key, definition in garments.GARMENTS.items():
    for g in list(garments.garments_of(body)):
        garments.remove_garment(g)
    garments.add_garment(body, key)
    scale, height = FRAMES.get(definition["categorie"], (2.0, 0.9))
    if key == "gants":
        scale, height = 1.1, 0.8
    camera_data.ortho_scale = scale
    camera.location = Vector((0.0, -6.0, height))
    scene.render.filepath = str(OUT / f"{key}.png")
    bpy.ops.render.render(write_still=True)
    index.append({"id": key, "label": definition["label"], "categorie": definition["categorie"], "couche": definition["couche"], "vignette": f"{key}.png"})
(OUT / "garment_gallery.json").write_text(json.dumps(index, indent=1, ensure_ascii=False), encoding="utf-8")
print("GALERIE_VETEMENTS_OK", len(index))
