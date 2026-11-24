"""Planche téléphone / parapluie (lot restes) : téléphone dans la main au repos, téléphone « à l'oreille » (face, 3/4, profil), parapluie fermé et ouvert tenus (corps entier + gros plan de la main). Rendu Workbench.

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/render_phone_umbrella_board.py -- DOSSIER_DE_SORTIE [--size 360]

Sortie : PNG numérotés ; assemblage : `tools/assemble_phone_umbrella_board.py` (Pillow)."""
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension import accessories as A  # noqa: E402
from extension.animation import skeleton  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:]
OUT = Path(ARGS[0])
SIZE = int(ARGS[ARGS.index("--size") + 1]) if "--size" in ARGS else 360
OUT.mkdir(parents=True, exist_ok=True)
addon.register()
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
bpy.ops.humanloom.create()
body = bpy.context.object
rig = skeleton.install(body)
body.modifiers["Human Modeling · Surface"].show_viewport = False

scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.render.resolution_x = scene.render.resolution_y = SIZE
scene.display.shading.light = "STUDIO"
scene.display.shading.color_type = "MATERIAL"
scene.display.shading.show_cavity = True
scene.world = scene.world or bpy.data.worlds.new("w")
scene.world.color = (1, 1, 1)
cam_data = bpy.data.cameras.new("cam")
cam_data.type = "ORTHO"
camera = bpy.data.objects.new("cam", cam_data)
scene.collection.objects.link(camera)
scene.camera = camera


def shoot(name, target, scale, azimuth):
    a = math.radians(azimuth)
    cam_data.ortho_scale = scale
    camera.location = Vector(target) + Vector((6.0 * math.sin(a), -6.0 * math.cos(a), 0.0))
    camera.rotation_euler = (math.radians(90), 0.0, a)
    bpy.context.view_layer.update()
    scene.render.filepath = str(OUT / f"{name}.png")
    bpy.ops.render.render(write_still=True)


def hand_point():
    return tuple(rig.matrix_world @ rig.pose.bones["hand.R"].head)


# 1. téléphone dans la main (repos) : gros plan
phone = A.add_accessory(body, "telephone")
bpy.context.view_layer.update()
shoot("1_tel_main", hand_point(), 0.45, 40)
# 2. téléphone à l'oreille : face, 3/4, profil (côté droit du personnage = −x : on regarde depuis ce côté pour le profil)
report = A.pose_phone_ear(body, "R")
print("OREILLE", report)
head = (0.0, 0.0, float(skeleton.cage_points(body)[:, 2].max()) - 0.15)
shoot("2_oreille_face", head, 0.9, 0)
shoot("3_oreille_3q", head, 0.9, -40)
shoot("4_oreille_profil", head, 0.9, -90)
A.remove_accessory(phone)
A.reset_hand(body, "R")
# 3. parapluies tenus
for k, key in enumerate(("parapluie_ferme", "parapluie_ouvert")):
    umbrella = A.add_accessory(body, key)
    bpy.context.view_layer.update()
    shoot(f"{5 + 2 * k}_{key}_corps", (0.0, 0.0, 0.95), 2.2, 30)
    shoot(f"{6 + 2 * k}_{key}_main", hand_point(), 0.5, 30)
    A.remove_accessory(umbrella)
print("PLANCHE ok")
