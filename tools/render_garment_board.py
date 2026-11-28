"""Planche AVANT / APRÈS du dégagement de flexion des vêtements (rendu ombré Workbench) : veste au coude 0/90/110/135/150°, jean au genou 0/90/110/135°, profil et trois-quarts, gros plan de l'articulation.
États : `sans` (aucune clé de dégagement, pas de passe Shrinkwrap), `cles` (clés de dégagement de la pièce), `passe` (passe Shrinkwrap « Dégagement » seule).

  blender --background --factory-startup --offline-mode --python-exit-code 0 --python tools/render_garment_board.py -- DOSSIER_DE_SORTIE [--size 260]

Sorties : <état>_<articulation>_<angle>_<vue>.png. Assemblage : tools/assemble_garment_board.py (Pillow)."""
import math
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Quaternion, Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension import garment_clearance as gc, garments  # noqa: E402
from extension.animation import correctives, skeleton  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:]
OUT = Path(ARGS[0])
SIZE = int(ARGS[ARGS.index("--size") + 1]) if "--size" in ARGS else 260
OUT.mkdir(parents=True, exist_ok=True)
addon.register()
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
bpy.ops.humanloom.create()
body = bpy.context.object
rig = skeleton.install(body, correctives=False)
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
skin.diffuse_color = (0.95, 0.45, 0.35, 1.0)
body.data.materials.clear()
body.data.materials.append(skin)
data = dict(np.load(correctives.DATA, allow_pickle=False))
signs = {"coude": float(data["coude_L_sign"]), "genou": float(data["genou_L_sign"])}
jacket = garments.add_garment(body, "veste", color=(0.18, 0.22, 0.45))
jean = garments.add_garment(body, "jean", color=(0.15, 0.30, 0.60))
for piece in (jacket, jean):
    piece.data.materials[0].diffuse_color = (*piece.data.materials[0].diffuse_color[:3], 1.0)
gc.build(jacket, body)
gc.build(jean, body)


def reset():
    for b in rig.pose.bones:
        b.rotation_mode = "QUATERNION"
        b.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
        b.location = (0.0, 0.0, 0.0)


def state(name):
    for piece in (jacket, jean):
        for key in gc.keys_of(piece.data):
            key.mute = name != "cles"
        garments.set_clearance(piece, name == "passe")


def shoot(path, centre, scale, direction):
    d = Vector(direction).normalized()
    cam_data.ortho_scale = scale
    camera.location = Vector(centre) + d * 4.0
    camera.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    bpy.context.view_layer.update()
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


VIEWS = {"profil": (1.0, 0.0, 0.0), "trois_quarts": (0.7, -0.7, 0.15)}
JOINTS = {"coude": ("arm_lower.L", [0, 90, 110, 135, 150]), "genou": ("leg_lower.L", [0, 90, 110, 135])}
for st in ("sans", "cles", "passe"):
    state(st)
    for joint, (bone, angles) in JOINTS.items():
        for angle in angles:
            reset()
            rig.pose.bones[bone].rotation_quaternion = Quaternion((1.0, 0.0, 0.0), math.radians(signs[joint] * angle))
            bpy.context.view_layer.update()
            centre = np.array((rig.matrix_world @ rig.pose.bones[bone].head)[:])
            for view, direction in VIEWS.items():
                shoot(OUT / f"{st}_{joint}_{angle}_{view}.png", centre, 0.55, direction)
print("PLANCHE ok")
