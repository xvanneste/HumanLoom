"""Rendu de PROFIL des expressions (lot visage) : une image par expression (+ neutre), pour comparer le contour du menton avant / après un changement des couches.
  blender ... --python tools/render_face_profile.py -- DOSSIER [--morph neutre|homme_age|femme_jeune]"""
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension import human  # noqa: E402
from extension.animation import skeleton  # noqa: E402
from extension.proportions import FACE_COMMANDS, FACE_PRESETS  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:]
OUT = Path(ARGS[0])
OUT.mkdir(parents=True, exist_ok=True)
MORPH = ARGS[ARGS.index("--morph") + 1] if "--morph" in ARGS else "neutre"
VALUES = {"neutre": {}, "homme_age": {"sex": 0.0, "age": 3.0}, "femme_jeune": {"sex": 1.0, "age": 1.0}}[MORPH]
addon.register()
bpy.ops.humanloom.create()
body = bpy.context.object
for name, value in VALUES.items():
    human.set_value(body, name, value)
scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.render.resolution_x = scene.render.resolution_y = 520
scene.display.shading.light = "STUDIO"
scene.display.shading.color_type = "MATERIAL"
scene.world = bpy.data.worlds.new("w") if scene.world is None else scene.world
scene.world.color = (1, 1, 1)
cage = skeleton.cage_points(body)
top = cage[:, 2].max()
centre = np.array([0.0, float(cage[cage[:, 2] > top - 0.2][:, 1].mean()), float(top - 0.14)])
camera_data = bpy.data.cameras.new("cam")
camera_data.type = "ORTHO"
camera_data.ortho_scale = 0.30
camera = bpy.data.objects.new("cam", camera_data)
scene.collection.objects.link(camera)
scene.camera = camera
camera.location = Vector(centre.tolist()) + Vector((0.7, 0, 0))
camera.rotation_euler = (np.radians(90), 0, np.radians(90))
for key, commands in FACE_PRESETS.items():
    for name in FACE_COMMANDS:
        if name != "mouth_open":
            human.set_value(body, name, float(commands.get(name, 0.0)))
    bpy.context.view_layer.update()
    scene.render.filepath = str(OUT / f"profil_{MORPH}_{key}.png")
    bpy.ops.render.render(write_still=True)
