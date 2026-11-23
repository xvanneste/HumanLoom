"""Planche du SOURIRE (preset Joie) : face, trois-quarts et profil, 3 morphologies, squelette installé (dents visibles). blender ... --python tools/render_smile_board.py -- DOSSIER [--preset joie]"""
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
OUT = Path(ARGS[0]); OUT.mkdir(parents=True, exist_ok=True)
PRESET = ARGS[ARGS.index("--preset") + 1] if "--preset" in ARGS else "joie"
MORPH = {"neutre": {}, "femme_jeune": {"sex": 1.0, "age": 1.0}, "homme_age": {"sex": 0.0, "age": 3.0}}
addon.register()
for label, values in MORPH.items():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.ops.humanloom.create(); body = bpy.context.object
    for n, v in values.items():
        human.set_value(body, n, v)
    skeleton.install(body)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"; scene.render.resolution_x = scene.render.resolution_y = 520
    scene.display.shading.light = "STUDIO"; scene.display.shading.color_type = "MATERIAL"; scene.display.shading.show_cavity = True
    scene.world = bpy.data.worlds.new("w") if scene.world is None else scene.world; scene.world.color = (1, 1, 1)
    cage = skeleton.cage_points(body); top = cage[:, 2].max()
    centre = np.array([0.0, -0.12, float(top - 0.150)])
    cam_data = bpy.data.cameras.new("c"); cam_data.type = "ORTHO"; cam_data.ortho_scale = 0.17
    cam = bpy.data.objects.new("c", cam_data); scene.collection.objects.link(cam); scene.camera = cam
    for name in FACE_COMMANDS:
        if name != "mouth_open":
            human.set_value(body, name, float(FACE_PRESETS[PRESET].get(name, 0.0)))
    bpy.context.view_layer.update()
    for view, direction in (("face", (0, -1, 0)), ("trois_quarts", (0.6, -0.8, 0.1)), ("profil", (1, 0, 0))):
        d = Vector(direction).normalized()
        cam.location = Vector(centre.tolist()) + d * 0.6
        cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = str(OUT / f"{PRESET}_{label}_{view}.png")
        bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam, do_unlink=True)
