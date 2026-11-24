"""Planches par émotion : intensité 0 / 50 / 100 % sur 3 morphologies, vue de face et de trois quarts (rendu Workbench).

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/render_emotion_boards.py -- DOSSIER_DE_SORTIE [--size 240] [--only joie,peur]

L'intensité multiplie TOUTES les valeurs de la pose (commandes, `_jaw`) ; sortie `<emotion>_<morphologie>_<vue>_<niveau>.png`. Assemblage : `tools/assemble_emotion_boards.py` (Pillow)."""
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
from extension.animation import face, skeleton  # noqa: E402
from extension.proportions import FACE_PRESETS  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:]
OUT = Path(ARGS[0])
SIZE = int(ARGS[ARGS.index("--size") + 1]) if "--size" in ARGS else 240
ONLY = ARGS[ARGS.index("--only") + 1].split(",") if "--only" in ARGS else [k for k in FACE_PRESETS if k not in ("neutre", "clignement")]
OUT.mkdir(parents=True, exist_ok=True)
MORPHOLOGIES = {"neutre": {}, "femme_jeune": {"sex": 1.0, "age": 1.0}, "homme_age": {"sex": 0.0, "age": 3.0}}
LEVELS = (0.0, 0.5, 1.0)
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
    camera_data.ortho_scale = 0.24
    camera = bpy.data.objects.new("cam", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    for view, azimuth in (("face", 0.0), ("trois_quarts", 38.0)):
        a = math.radians(azimuth)
        camera.location = Vector(centre.tolist()) + Vector((0.6 * math.sin(a), -0.6 * math.cos(a), 0.0))
        camera.rotation_euler = (math.radians(90), 0.0, a)
        for emotion in ONLY:
            pose = FACE_PRESETS[emotion]
            for level in LEVELS:
                scaled = {k: ([x * level for x in v] if isinstance(v, list) else {kk: vv * level for kk, vv in v.items()} if isinstance(v, dict) else v * level) for k, v in pose.items()}
                face.apply_pose(body, scaled)
                bpy.context.view_layer.update()
                scene.render.filepath = str(OUT / f"{emotion}_{label}_{view}_{int(level * 100):03d}.png")
                bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(camera, do_unlink=True)
    print("PLANCHES", label)
