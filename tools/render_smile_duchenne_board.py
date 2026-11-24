"""Planche du sourire de Duchenne : intensité 0 / 25 / 50 / 75 / 100 % sur 3 morphologies, vue de face, vue de trois quarts et gros plan des yeux (rendu Workbench).

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/render_smile_duchenne_board.py -- DOSSIER_DE_SORTIE [--size 260]

Sortie : `<morphologie>_<vue>_<niveau>.png`. Une seule commande (`smile_duchenne`) pilote tout ; les autres commandes restent à 0. Assemblage : voir `tools/assemble_smile_duchenne_board.py` (Pillow)."""
from pathlib import Path
import math
import sys

import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension import human  # noqa: E402
from extension.animation import skeleton  # noqa: E402
from extension.proportions import FACE_COMMANDS  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:]
OUT = Path(ARGS[0])
SIZE = int(ARGS[ARGS.index("--size") + 1]) if "--size" in ARGS else 260
OUT.mkdir(parents=True, exist_ok=True)
MORPHOLOGIES = {"neutre": {}, "femme_jeune": {"sex": 1.0, "age": 1.0}, "homme_age": {"sex": 0.0, "age": 3.0}}
LEVELS = (0.0, 0.25, 0.5, 0.75, 1.0)
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
    scene.render.resolution_x = scene.render.resolution_y = SIZE
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_cavity = True
    scene.world = bpy.data.worlds.new("w") if scene.world is None else scene.world
    scene.world.color = (1, 1, 1)
    skeleton.install(body)
    bpy.context.view_layer.update()
    cage = skeleton.cage_points(body)
    centre = np.array([0.0, -0.12, float(cage[:, 2].max() - 0.105)])
    camera_data = bpy.data.cameras.new("cam")
    camera_data.type = "ORTHO"
    camera = bpy.data.objects.new("cam", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    from extension.animation import face as face_module  # noqa: E402
    eye_centre = (cage[face_module.SMILE_LID_UP] + cage[face_module.SMILE_LID_DOWN]) / 2.0  # peau des paupières du côté +x (sommets communs à toutes les morphologies)
    views = {
        "face": (0.27, centre, 0.0),
        "trois_quarts": (0.27, centre, 38.0),
        "yeux": (0.070, np.array([eye_centre[0] + 0.004, eye_centre[1], eye_centre[2] + 0.004]), 0.0),
    }
    for view, (ortho, target, azimuth) in views.items():
        camera_data.ortho_scale = ortho
        a = math.radians(azimuth)
        camera.location = Vector(target.tolist()) + Vector((0.6 * math.sin(a), -0.6 * math.cos(a), 0.0))
        camera.rotation_euler = (math.radians(90), 0.0, a)
        for level in LEVELS:
            for name in FACE_COMMANDS:
                if human.has_control(body, name):
                    human.set_value(body, name, 0.0)
            human.set_value(body, "smile_duchenne", level)
            bpy.context.view_layer.update()
            scene.render.filepath = str(OUT / f"{label}_{view}_{int(level * 100):03d}.png")
            bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(camera, do_unlink=True)
    print("PLANCHE", label)
