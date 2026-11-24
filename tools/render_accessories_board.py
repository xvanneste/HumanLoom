"""Planche des accessoires (lot V3) : six vues (rendu Workbench) — sacs à main et de courses, parapluie fermé et sac à dos, parapluie ouvert, lunettes et casquette, gros plans de la main (téléphone, poignée).

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/render_accessories_board.py -- DOSSIER_DE_SORTIE [--size 300]

Sortie : `scene_<n>.png`. Assemblage : `tools/assemble_accessories_board.py` (Pillow)."""
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension import accessories as A, garments  # noqa: E402
from extension.animation import skeleton  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:]
OUT = Path(ARGS[0])
SIZE = int(ARGS[ARGS.index("--size") + 1]) if "--size" in ARGS else 300
OUT.mkdir(parents=True, exist_ok=True)
SCENES = [
    ("1_sacs", ["sac_a_main", "sac_de_courses"], "corps"),
    ("2_parapluie_ferme_et_sac_a_dos", ["parapluie_ferme", "sac_a_dos"], "corps"),
    ("3_parapluie_ouvert", ["parapluie_ouvert"], "corps"),
    ("4_lunettes_et_casquette", ["lunettes"], "tete"),
    ("5_telephone", ["telephone"], "main"),
    ("6_poignee", ["sac_a_main"], "main"),
]
addon.register()
for name, pieces, view in SCENES:
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.ops.humanloom.create()
    body = bpy.context.object
    rig = skeleton.install(body)
    body.modifiers["Human Modeling · Surface"].show_viewport = False
    for key in ("t_shirt", "jean", "chaussures") + (("casquette",) if view == "tete" else ()):
        garments.add_garment(body, key)
    for key in pieces:
        A.add_accessory(body, key)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = scene.render.resolution_y = SIZE
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_cavity = True
    scene.world = bpy.data.worlds.new("w") if scene.world is None else scene.world
    scene.world.color = (1, 1, 1)
    camera_data = bpy.data.cameras.new("cam")
    camera_data.type = "ORTHO"
    camera = bpy.data.objects.new("cam", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    bpy.context.view_layer.update()
    if view == "corps":
        camera_data.ortho_scale, target, azimuth = 2.3, Vector((0.0, 0.0, 0.9)), 25.0
    elif view == "tete":
        camera_data.ortho_scale, target, azimuth = 0.4, Vector((0.0, -0.12, 1.55)), 35.0
    else:
        hand = rig.matrix_world @ rig.pose.bones["hand.R"].head
        camera_data.ortho_scale, target, azimuth = 0.55, Vector((hand.x, hand.y, hand.z - 0.05)), 40.0
    a = math.radians(azimuth)
    camera.location = target + Vector((6.0 * math.sin(a), -6.0 * math.cos(a), 0.0))
    camera.rotation_euler = (math.radians(90), 0.0, a)
    scene.render.filepath = str(OUT / f"scene_{name}.png")
    bpy.ops.render.render(write_still=True)
    print("SCENE", name)
