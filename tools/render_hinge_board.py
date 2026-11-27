"""Planche AVANT / APRÈS des correctifs de flexion (rendu ombré Workbench) : coude 0/45/90/120/150°, genou 0/45/90/135°, profil et trois-quarts, gros plans de l'articulation ; poses humaines (téléphone à l'oreille, accroupi) ;
gros plan AVEC vêtements (t-shirt, jean). États : `avant` = clés de correctifs muettes ; `apres` = correctifs livrés ; `recalcule` = correctifs recalculés pour la morphologie (femme jeune, homme âgé).

  blender --background --factory-startup --offline-mode --python-exit-code 0 --python tools/render_hinge_board.py -- DOSSIER_DE_SORTIE --morph defaut|femme_jeune|homme_age [--recalcul 1] [--size 220] [--extras 1]

Sorties : <état>_<morph>_<articulation>_<angle>_<vue>.png ; poses humaines et vêtements avec --extras 1. Assemblage : tools/assemble_hinge_board.py (Pillow)."""
import math
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Quaternion, Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension import accessories, garments, human  # noqa: E402
from extension.animation import correctives, skeleton  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:]
OUT = Path(ARGS[0])
MORPH = ARGS[ARGS.index("--morph") + 1]
SIZE = int(ARGS[ARGS.index("--size") + 1]) if "--size" in ARGS else 220
RECALC = "--recalcul" in ARGS and ARGS[ARGS.index("--recalcul") + 1] == "1"
EXTRAS = "--extras" in ARGS and ARGS[ARGS.index("--extras") + 1] == "1"
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
data = dict(np.load(correctives.DATA, allow_pickle=False))
signs = {label: float(data[f"{label}_sign"]) for label in correctives.labels(data)}


def reset():
    for b in rig.pose.bones:
        b.rotation_mode = "QUATERNION"
        b.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
        b.location = (0.0, 0.0, 0.0)


def mute(state):
    for obj in [body] + [c for c in body.children if c.type == "MESH"]:
        for key in correctives.keys_of(obj.data):
            key.mute = state
    bpy.context.view_layer.update()


def flex(label, angle):
    joint, side = label.split("_")
    reset()
    rig.pose.bones[f"{correctives.BONES[joint]}.{side}"].rotation_quaternion = Quaternion((1.0, 0.0, 0.0), math.radians(signs[label] * angle))
    bpy.context.view_layer.update()


def shoot(path, centre, scale, direction):
    d = Vector(direction).normalized()
    cam_data.ortho_scale = scale
    camera.location = Vector(centre) + d * 4.0
    camera.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    bpy.context.view_layer.update()
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def joint_centre(label):
    joint, side = label.split("_")
    return np.array((rig.matrix_world @ rig.pose.bones[f"{correctives.BONES[joint]}.{side}"].head)[:])


VIEWS = {"profil": (1.0, 0.0, 0.0), "trois_quarts": (0.7, -0.7, 0.15)}
ANGLES = {"coude_L": [0, 45, 90, 120, 150], "genou_L": [0, 45, 90, 135]}


def render_joints(state):
    for label, angles in ANGLES.items():
        for angle in angles:
            flex(label, angle)
            centre = joint_centre(label)
            for view, direction in VIEWS.items():
                shoot(OUT / f"{state}_{MORPH}_{label}_{angle}_{view}.png", centre, 0.5, direction)


def render_extras(state):
    """Poses humaines : téléphone à l'oreille (face, profil) ; accroupi (profil, trois-quarts) ; vêtements (t-shirt, jean) sur le coude plié et le genou plié."""
    reset()
    phone = accessories.add_accessory(body, "telephone")
    accessories.pose_phone_ear(body, "R")
    bpy.context.view_layer.update()
    head = np.array([0.0, 0.0, float(skeleton.cage_points(body)[:, 2].max()) - 0.15])
    for view, direction in (("face", (0.0, -1.0, 0.0)), ("profil", (-1.0, 0.0, 0.0))):
        shoot(OUT / f"{state}_{MORPH}_telephone_{view}.png", head, 0.8, direction)
    accessories.remove_accessory(phone)
    reset()
    for side in ("L", "R"):
        rig.pose.bones[f"leg_upper.{side}"].rotation_quaternion = Quaternion((1.0, 0.0, 0.0), math.radians(signs["genou_L"] * -1.0 * 110))
        rig.pose.bones[f"leg_lower.{side}"].rotation_quaternion = Quaternion((1.0, 0.0, 0.0), math.radians(signs["genou_L"] * 140))
    rig.pose.bones["pelvis"].location = (0.0, 0.0, -0.40)
    bpy.context.view_layer.update()
    centre = np.array([0.0, 0.0, 0.55])
    for view, direction in (("profil", (1.0, 0.0, 0.0)), ("trois_quarts", (0.7, -0.7, 0.15))):
        shoot(OUT / f"{state}_{MORPH}_accroupi_{view}.png", centre, 1.5, direction)
    # vêtements : mêmes poses en gros plan
    shirt = garments.add_garment(body, "t_shirt", color=(0.2, 0.4, 0.8))
    jean = garments.add_garment(body, "jean", color=(0.15, 0.2, 0.45))
    for piece in (shirt, jean):
        piece.hide_render = False
    reset()
    flex("coude_L", 110)
    shoot(OUT / f"{state}_{MORPH}_vetements_coude.png", joint_centre("coude_L"), 0.6, VIEWS["trois_quarts"])
    flex("genou_L", 110)
    shoot(OUT / f"{state}_{MORPH}_vetements_genou.png", joint_centre("genou_L"), 0.7, VIEWS["trois_quarts"])
    for piece in (shirt, jean):
        garments.remove_garment(piece)


states = [("avant", True), ("apres", False)]
for state, muted in states:
    mute(muted)
    render_joints(state)
    if EXTRAS:
        render_extras(state)
if RECALC:
    steps = correctives.rebuild_steps(body, rig)
    while True:
        try:
            next(steps)
        except StopIteration:
            break
    mute(False)
    render_joints("recalcule")
    if EXTRAS:
        render_extras("recalcule")
print("PLANCHE", MORPH, "ok")
