"""Galerie des poses du visage : vignettes (rendu Workbench de face, corps neutre) + index `face_gallery.json` pour l'interface.

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/build_face_gallery.py -- <DOSSIER_SORTIE> [--size 160]

Écrit `<DOSSIER_SORTIE>/<slug>.png` et `<DOSSIER_SORTIE>/face_gallery.json` (id, libellé, catégorie, vignette, source). À copier dans `extension/data/face_thumbs/` (vignettes) et `extension/data/` (index)."""
from pathlib import Path
import json
import re
import sys

import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension import human  # noqa: E402
from extension.animation import face, skeleton  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:]
OUT = Path(ARGS[0])
SIZE = int(ARGS[ARGS.index("--size") + 1]) if "--size" in ARGS else 160
OUT.mkdir(parents=True, exist_ok=True)


def slug(pose_id):
    table = str.maketrans("éèêàçùô", "eeeacuo")
    return re.sub(r"[^a-z0-9]+", "_", pose_id.lower().translate(table)).strip("_")


addon.register()
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
bpy.ops.humanloom.create()
body = bpy.context.object
scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.render.resolution_x = scene.render.resolution_y = SIZE
scene.display.shading.light = "STUDIO"
scene.display.shading.color_type = "MATERIAL"
scene.display.shading.show_cavity = True
scene.world = bpy.data.worlds.new("w") if scene.world is None else scene.world
scene.world.color = (1, 1, 1)
skeleton.install(body)
cage = skeleton.cage_points(body)
centre = np.array([0.0, -0.12, float(cage[:, 2].max() - 0.105)])
camera_data = bpy.data.cameras.new("cam")
camera_data.type = "ORTHO"
camera_data.ortho_scale = 0.27
camera = bpy.data.objects.new("cam", camera_data)
scene.collection.objects.link(camera)
scene.camera = camera
camera.location = Vector(centre.tolist()) + Vector((0, -0.6, 0))
camera.rotation_euler = (np.radians(90), 0, 0)
index = []
for pose_id, entry in face.builtin_poses().items():
    face.apply_pose(body, entry["pose"])
    bpy.context.view_layer.update()
    name = slug(pose_id) + ".png"
    scene.render.filepath = str(OUT / name)
    bpy.ops.render.render(write_still=True)
    index.append({"id": pose_id, "label": entry["label"], "categorie": entry["categorie"], "vignette": name, "source": entry["source"]})
(OUT / "face_gallery.json").write_text(json.dumps(index, indent=1, ensure_ascii=False), encoding="utf-8")
print("GALERIE_OK", len(index), "vignettes")
