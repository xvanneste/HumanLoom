"""Planche des articulations hanche / cou / poignet à 0 %, 50 % et 100 % des amplitudes de docs/anatomie_articulations.md §12 (rendu ombré Workbench, profil et trois-quarts) : hanche flexion 0/60/120 et abduction 0/20/40, cou rotation 0/35/70 et flexion 0/25/45, poignet flexion 0/40/80 et extension 0/35/70.

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/render_hnw_board.py -- DOSSIER_DE_SORTIE --morph defaut|femme_jeune|homme_age [--size 240]
Lecture seule sur l'extension ; assemblage : tools/assemble_hnw_board.py (Pillow)."""
import math
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

ARGS = sys.argv[sys.argv.index("--") + 1:]
OUT = Path(ARGS[0])
STATE = "apres"
MORPH = ARGS[ARGS.index("--morph") + 1]
SIZE = int(ARGS[ARGS.index("--size") + 1]) if "--size" in ARGS else 240
MORPHS = {"defaut": {}, "femme_jeune": {"sex": 1.0, "age": 1.0}, "homme_age": {"sex": 0.0, "age": 3.0}}
OUT.mkdir(parents=True, exist_ok=True)
addon.register()
if STATE == "avant":
    skeleton.attach_twist = lambda armature: None
    skeleton.redistribute_distal = lambda names, idx, w, points, table: (idx, w)
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
bpy.ops.humanloom.create()
body = bpy.context.object
for name, value in MORPHS[MORPH].items():
    human.set_value(body, name, value)
rig = skeleton.install(body)
body.modifiers["Human Modeling · Surface"].show_viewport = False
if STATE == "avant":  # tout en liaison linéaire
    everything = list(range(len(body.data.vertices)))
    body.vertex_groups[skeleton.GROUP_DQS].add(everything, 0.0, "REPLACE")
    body.vertex_groups[skeleton.GROUP_LBS].add(everything, 1.0, "REPLACE")
for bone in rig.pose.bones:
    bone.rotation_mode = "XYZ"

scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.render.resolution_x = scene.render.resolution_y = SIZE
scene.display.shading.light = "STUDIO"
scene.display.shading.color_type = "SINGLE"
scene.display.shading.single_color = (0.78, 0.66, 0.58)
scene.display.shading.show_cavity = False
scene.world = scene.world or bpy.data.worlds.new("w")
scene.world.color = (1, 1, 1)
camera_data = bpy.data.cameras.new("cam")
camera_data.type = "ORTHO"
camera_data.ortho_scale = 0.62
camera = bpy.data.objects.new("cam", camera_data)
scene.collection.objects.link(camera)
scene.camera = camera
S = "L"


def head(name):
    return np.array((rig.matrix_world @ rig.pose.bones[name].head)[:])


def tail(name):
    return np.array((rig.matrix_world @ rig.pose.bones[name].tail)[:])


def set_pose(values):
    for bone in rig.pose.bones:
        bone.rotation_euler = (0.0, 0.0, 0.0)
    for name, (axis, degrees) in values.items():
        e = [0.0, 0.0, 0.0]
        e[axis] = math.radians(degrees)
        rig.pose.bones[name].rotation_euler = e
    bpy.context.view_layer.update()


def pick(name, axis, metric):
    scores = {}
    for sign in (1.0, -1.0):
        set_pose({name: (axis, 40 * sign)})
        scores[sign] = metric()
    set_pose({})
    return 1.0 if scores[1.0] <= scores[-1.0] else -1.0


sign_hip = pick(f"leg_upper.{S}", 0, lambda: float(head(f"leg_lower.{S}")[1]))
sign_abd = pick(f"leg_upper.{S}", 2, lambda: -abs(float(head(f"leg_lower.{S}")[0])))
sign_nf = pick("head", 0, lambda: float(tail("head")[1]))
sign_wrist = pick(f"hand.{S}", 0, lambda: float(tail(f"hand.{S}")[1]))
neck3 = lambda axis, a: {"neck.01": (axis, a / 3), "neck.02": (axis, a / 3), "head": (axis, a / 3)}
JOINTS = {
    "hanche_flexion": (f"leg_upper.{S}", [0, 60, 120], lambda a: {f"leg_upper.{S}": (0, sign_hip * a)}),
    "hanche_abduction": (f"leg_upper.{S}", [0, 20, 40], lambda a: {f"leg_upper.{S}": (2, sign_abd * a)}),
    "cou_rotation": ("neck.02", [0, 35, 70], lambda a: {"neck.01": (1, a / 3), "neck.02": (1, 2 * a / 3)}),
    "cou_flexion": ("neck.02", [0, 25, 45], lambda a: neck3(0, sign_nf * a)),
    "poignet_flexion": (f"hand.{S}", [0, 40, 80], lambda a: {f"hand.{S}": (0, sign_wrist * a)}),
    "poignet_extension": (f"hand.{S}", [0, 35, 70], lambda a: {f"hand.{S}": (0, -sign_wrist * a)}),
}
VIEWS = {"profil": (1.0, 0.0), "trois_quarts": (0.7, -0.7)}
for joint, (pivot_bone, angles, pose) in JOINTS.items():
    for angle in angles:
        set_pose(pose(angle))
        centre = head(pivot_bone)
        for view, (dx, dy) in VIEWS.items():
            d = Vector((dx, dy, 0.0)).normalized()
            camera.location = Vector(centre) + d * 3.0
            camera.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
            scene.render.filepath = str(OUT / f"{MORPH}_{joint}_{angle}_{view}.png")
            bpy.ops.render.render(write_still=True)
print("PLANCHE", MORPH, "ok")
