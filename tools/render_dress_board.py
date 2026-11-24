"""Planche des robes simulées (lot V4) : robe mi-longue sur 3 morphologies (repos, marche à mi-pas, bras levés) puis robe courte, robe longue et jupe en marche sur le corps par défaut. Rendu Workbench, simulation native
(Cloth Dynamics) calculée en direct image par image depuis la première image.

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/render_dress_board.py -- DOSSIER_DE_SORTIE [--size 260]

Sortie : `<ligne>_<colonne>.png`. Assemblage : `tools/assemble_dress_board.py` (Pillow)."""
import math
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension import cloth_sim, garments, human  # noqa: E402
from extension.animation import skeleton  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:]
OUT = Path(ARGS[0])
SIZE = int(ARGS[ARGS.index("--size") + 1]) if "--size" in ARGS else 260
OUT.mkdir(parents=True, exist_ok=True)
FRAMES = 40
MORPHOLOGIES = {"defaut": {}, "femme_jeune": {"sex": 1.0, "age": 1.0}, "gabarit": {"legs": 1.0, "torso": -1.0}}
addon.register()


def raise_sign(rig, side):
    pb = rig.pose.bones["arm_upper." + side]
    best = {}
    for sign in (1.0, -1.0):
        pb.rotation_euler = (0.0, 0.0, sign * math.radians(60))
        bpy.context.view_layer.update()
        best[sign] = float((rig.matrix_world @ rig.pose.bones["hand." + side].head).z)
    pb.rotation_euler = (0.0, 0.0, 0.0)
    bpy.context.view_layer.update()
    return 1.0 if best[1.0] > best[-1.0] else -1.0


def animate(rig, kind):
    sl, sr = raise_sign(rig, "L"), raise_sign(rig, "R")
    rig.animation_data_create()
    rig.animation_data.action = None
    keys = {"marche": [(1, {}), (10, {"leg_upper.L": (math.radians(35), 0, 0), "leg_upper.R": (math.radians(-35), 0, 0), "leg_lower.R": (math.radians(-40), 0, 0)}), (FRAMES, {})],
            "bras_leve": [(1, {}), (20, {"arm_upper.L": (0, 0, sl * math.radians(80)), "arm_upper.R": (0, 0, sr * math.radians(80))}), (FRAMES, {})]}[kind]
    for frame, pose in keys:
        for pb in rig.pose.bones:
            pb.rotation_euler = pose.get(pb.name, (0.0, 0.0, 0.0))
            pb.keyframe_insert("rotation_euler", frame=frame)


def render(path, body, frame, simulate):
    scene = bpy.context.scene
    if simulate:
        scene.frame_set(1)
        bpy.context.view_layer.update()
        for f in range(2, frame + 1):  # la simulation avance image par image
            scene.frame_set(f)
            bpy.context.view_layer.update()
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def setup_scene():
    scene = bpy.context.scene
    scene.frame_start, scene.frame_end = 1, FRAMES
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x, scene.render.resolution_y = SIZE, int(SIZE * 1.4)
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_cavity = True
    scene.world = bpy.data.worlds.new("w") if scene.world is None else scene.world
    scene.world.color = (1, 1, 1)
    camera_data = bpy.data.cameras.new("cam")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = 2.0
    camera = bpy.data.objects.new("cam", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    a = math.radians(30)
    camera.location = Vector((6.0 * math.sin(a), -6.0 * math.cos(a), 0.9))
    camera.rotation_euler = (math.radians(90), 0.0, a)


def fresh(values):
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for collection in list(bpy.data.collections):
        bpy.data.collections.remove(collection)
    bpy.ops.humanloom.create()
    body = bpy.context.object
    for name, value in values.items():
        human.set_value(body, name, value)
    rig = skeleton.install(body)
    body.modifiers["Human Modeling · Surface"].show_viewport = False
    setup_scene()
    return body, rig


for label, values in MORPHOLOGIES.items():
    for column, (kind, frame) in {"repos": (None, 1), "marche": ("marche", 10), "bras_leve": ("bras_leve", 20)}.items():
        body, rig = fresh(values)
        dress = garments.add_garment(body, "robe_mi_longue")
        cloth_sim.enable(dress)
        if kind:
            animate(rig, kind)
        render(OUT / f"{label}_{column}.png", body, frame, simulate=kind is not None)
    print("PLANCHE", label)
for key in ("robe_courte", "robe_longue", "jupe"):
    body, rig = fresh({})
    garments.add_garment(body, "t_shirt") if key == "jupe" else None
    dress = garments.add_garment(body, key)
    cloth_sim.enable(dress)
    animate(rig, "marche")
    render(OUT / f"autres_{key}.png", body, 10, simulate=True)
print("PLANCHE autres")
