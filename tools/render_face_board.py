"""Planche des expressions du visage (lot visage) : expressions prédéfinies sur 3 morphologies, vue de face (rendu Workbench).

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/render_face_board.py -- DOSSIER_DE_SORTIE

Sortie : `visage_<morphologie>_<expression>.png`. Les expressions sont des combinaisons de commandes écrites par nous (non calibrées) ; les amplitudes unitaires sont celles de `mesh["hl_face_layers"]`."""
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

OUT = Path(sys.argv[sys.argv.index("--") + 1])
OUT.mkdir(parents=True, exist_ok=True)
MORPHOLOGIES = {"neutre": {}, "femme_jeune": {"sex": 1.0, "age": 1.0}, "homme_age": {"sex": 0.0, "age": 3.0}}
addon.register()
for label, values in MORPHOLOGIES.items():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.ops.humanloom.create()
    body = bpy.context.object
    for name, value in values.items():
        human.set_value(body, name, value)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = scene.render.resolution_y = 560
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_cavity = True
    scene.world = bpy.data.worlds.new("w") if scene.world is None else scene.world
    scene.world.color = (1, 1, 1)
    skeleton.install(body)  # squelette : la clé « _jaw » des expressions ouvre la mâchoire (le correctif de bouche suit)
    cage = skeleton.cage_points(body)
    top = cage[:, 2].max()
    centre = np.array([0.0, -0.12, float(top - 0.105)])
    camera_data = bpy.data.cameras.new("cam")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = 0.27
    camera = bpy.data.objects.new("cam", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.location = Vector(centre.tolist()) + Vector((0, -0.6, 0))
    camera.rotation_euler = (np.radians(90), 0, 0)
    for key, commands in FACE_PRESETS.items():
        for name in FACE_COMMANDS:
            if name != "mouth_open":
                human.set_value(body, name, float(commands.get(name, 0.0)))
        skeleton.open_jaw(body, float(commands.get("_jaw", 0.0)))
        bpy.context.view_layer.update()
        scene.render.filepath = str(OUT / f"visage_{label}_{key}.png")
        bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(camera, do_unlink=True)
    print("PLANCHE", label)
