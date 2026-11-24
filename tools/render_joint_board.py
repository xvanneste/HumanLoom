"""Planche AVANT / APRÈS des articulations (rendu ombré Workbench, gros plans de profil et de trois-quarts) : coude 0/45/90/120/150°, épaule levée 0/45/90/135/180°, genou 0/45/90/135°.

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/render_joint_board.py -- DOSSIER_DE_SORTIE --state avant|apres --morph defaut|femme_jeune|homme_age [--size 240]

`avant` reproduit l'état précédent du rig (liaison linéaire seule, pas de torsion pilotée, poids d'origine) ; `apres` = rig actuel. Les sens de rotation sont mesurés comme dans `diagnose_joints.py`.
Assemblage : `tools/assemble_joint_board.py` (Pillow)."""
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
STATE = ARGS[ARGS.index("--state") + 1]
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


sign_elbow = pick(f"arm_lower.{S}", 0, lambda: float(np.linalg.norm(tail(f"arm_lower.{S}") - head(f"arm_upper.{S}"))))
sign_shoulder = pick(f"arm_upper.{S}", 2, lambda: -float(tail(f"arm_upper.{S}")[2]))
sign_knee = pick(f"leg_lower.{S}", 0, lambda: float(np.linalg.norm(tail(f"leg_lower.{S}") - head(f"leg_upper.{S}"))))
JOINTS = {
    "coude": (f"arm_lower.{S}", [0, 45, 90, 120, 150], lambda a: {f"arm_lower.{S}": (0, sign_elbow * a)}),
    "epaule": (f"arm_upper.{S}", [0, 45, 90, 135, 180], lambda a: {f"arm_upper.{S}": (2, sign_shoulder * a)}),
    "genou": (f"leg_lower.{S}", [0, 45, 90, 135], lambda a: {f"leg_lower.{S}": (0, sign_knee * a)}),
}
VIEWS = {"profil": (1.0, 0.0), "trois_quarts": (0.7, -0.7)}  # direction de la caméra (x, y) vers le corps : depuis +x ; depuis +x−y
for joint, (pivot_bone, angles, pose) in JOINTS.items():
    for angle in angles:
        set_pose(pose(angle))
        centre = head(pivot_bone)
        if joint == "epaule":
            centre = centre + np.array([0.0, 0.0, -0.05])
        for view, (dx, dy) in VIEWS.items():
            d = Vector((dx, dy, 0.0)).normalized()
            camera.location = Vector(centre) + d * 3.0
            camera.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
            scene.render.filepath = str(OUT / f"{STATE}_{MORPH}_{joint}_{angle}_{view}.png")
            bpy.ops.render.render(write_still=True)
print("PLANCHE", STATE, MORPH, "ok")
