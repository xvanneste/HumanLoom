"""Planche de l'épaule (rendu ombré Workbench) : état ACTUEL du rig (correctifs d'épaule absents), élévation 0/45/90/135/180°, plans frontal (abduction) et sagittal (flexion), vues face / profil / trois-quarts et gros plan
aisselle-deltoïde. `--rythme 1` ajoute la variante où la clavicule prend 1/3 de l'élévation (rythme scapulo-huméral simplifié, bras compensé).

  blender --background --factory-startup --offline-mode --python-exit-code 0 --python tools/render_shoulder_board.py -- DOSSIER [--size 220] [--rythme 1] [--morph defaut|femme_jeune|homme_age]
Sorties : <variante>_<plan>_<angle>_<vue>.png ; assemblage : tools/assemble_shoulder_board.py (Pillow)."""
import math
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Quaternion, Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension import human  # noqa: E402
from extension.animation import skeleton  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:]
OUT = Path(ARGS[0])
SIZE = int(ARGS[ARGS.index("--size") + 1]) if "--size" in ARGS else 220
RYTHME = "--rythme" in ARGS and ARGS[ARGS.index("--rythme") + 1] == "1"
MORPH = ARGS[ARGS.index("--morph") + 1] if "--morph" in ARGS else "defaut"
MORPHS = {"defaut": {}, "femme_jeune": {"sex": 1.0, "age": 1.0}, "homme_age": {"sex": 0.0, "age": 3.0}}
OUT.mkdir(parents=True, exist_ok=True)
addon.register()
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
bpy.ops.humanloom.create()
body = bpy.context.object
for name, value in MORPHS[MORPH].items():
    human.set_value(body, name, value)
rig = skeleton.install(body)
body.modifiers["Human Modeling · Surface"].show_viewport = False
scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.render.resolution_x = scene.render.resolution_y = SIZE
scene.display.shading.light = "STUDIO"
scene.display.shading.color_type = "MATERIAL"
scene.display.shading.show_cavity = False
scene.world = scene.world or bpy.data.worlds.new("w")
scene.world.color = (1, 1, 1)
cam_data = bpy.data.cameras.new("cam")
cam_data.type = "ORTHO"
camera = bpy.data.objects.new("cam", cam_data)
scene.collection.objects.link(camera)
scene.camera = camera
skin = bpy.data.materials.new("peau")
skin.diffuse_color = (0.78, 0.62, 0.52, 1.0)
body.data.materials.clear()
body.data.materials.append(skin)
SIDE = "L"


def reset():
    for b in rig.pose.bones:
        b.rotation_mode = "QUATERNION"
        b.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
        b.location = (0.0, 0.0, 0.0)
    bpy.context.view_layer.update()


def world_tail(name):
    return np.array((rig.matrix_world @ rig.pose.bones[name].tail)[:])


def local_axis_sign(bone, axis, metric):
    """Signe de rotation locale (axe 0=X, 2=Z) qui fait croître `metric()` : le même repère que tools/inventory_rig_defects.py."""
    scores = {}
    for sign in (1.0, -1.0):
        reset()
        vec = [0.0, 0.0, 0.0]
        vec[axis] = 1.0
        rig.pose.bones[bone].rotation_quaternion = Quaternion(vec, math.radians(40 * sign))
        bpy.context.view_layer.update()
        scores[sign] = metric()
    reset()
    return 1.0 if scores[1.0] >= scores[-1.0] else -1.0


arm = f"arm_upper.{SIDE}"
clav = f"clavicle.{SIDE}"
sagittal_sign = local_axis_sign(arm, 0, lambda: -float(world_tail(arm)[1]))  # le coude va vers l'avant (−y)
frontal_sign = local_axis_sign(arm, 2, lambda: float(world_tail(arm)[2]))  # le coude monte
clav_sign = {}
for axis in (0, 2):
    clav_sign[axis] = local_axis_sign(clav, axis, lambda: float(world_tail(arm)[2]))


def pose(plane, angle, rythme):
    reset()
    axis = 2 if plane == "frontal" else 0
    sign = frontal_sign if plane == "frontal" else sagittal_sign
    vec = [0.0, 0.0, 0.0]
    vec[axis] = 1.0
    share = angle / 3.0 if rythme else 0.0
    rig.pose.bones[arm].rotation_quaternion = Quaternion(vec, math.radians(sign * (angle - share)))
    if rythme:
        rig.pose.bones[clav].rotation_quaternion = Quaternion(vec if plane == "frontal" else vec, math.radians(clav_sign[axis] * share))
    bpy.context.view_layer.update()


def shoot(path, centre, scale, direction):
    d = Vector(direction).normalized()
    cam_data.ortho_scale = scale
    camera.location = Vector(centre) + d * 4.0
    camera.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    bpy.context.view_layer.update()
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def shoulder_centre():
    reset()
    return np.array((rig.matrix_world @ rig.pose.bones[arm].head)[:])


centre0 = shoulder_centre()
VIEWS = {"face": ((0.0, -1.0, 0.0), 0.75), "profil": ((1.0, 0.0, 0.0), 0.75), "trois_quarts": ((0.7, -0.7, 0.15), 0.75), "aisselle": ((0.0, -1.0, -0.35), 0.38)}
ANGLES = [0, 45, 90, 135, 180]
for variant in (("actuel", False),) + ((("rythme", True),) if RYTHME else ()):
    for plane in ("frontal", "sagittal"):
        for angle in ANGLES:
            pose(plane, angle, variant[1])
            for view, (direction, scale) in VIEWS.items():
                shoot(OUT / f"{variant[0]}_{MORPH}_{plane}_{angle}_{view}.png", centre0, scale, direction)
print("PLANCHE EPAULE", MORPH, "ok ; signes", sagittal_sign, frontal_sign, clav_sign)
