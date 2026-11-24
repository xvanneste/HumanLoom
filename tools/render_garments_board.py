"""Planche des vêtements procéduraux (lot V1) : 3 tenues sur 5 morphologies, au repos (de face) et dans une pose (bras droit levé à 90° et genou gauche fléchi, dégagement activé) ; rendu Workbench.

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/render_garments_board.py -- DOSSIER_DE_SORTIE [--size 260]

Sortie : `<tenue>_<morphologie>_<repos|pose>.png`. Assemblage : `tools/assemble_garments_board.py` (Pillow)."""
import math
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Euler, Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension import garments, human  # noqa: E402
from extension.animation import skeleton  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:]
OUT = Path(ARGS[0])
SIZE = int(ARGS[ARGS.index("--size") + 1]) if "--size" in ARGS else 260
OUT.mkdir(parents=True, exist_ok=True)
MORPHOLOGIES = {"defaut": {}, "homme_age": {"sex": 0.0, "age": 3.0}, "femme_jeune": {"sex": 1.0, "age": 1.0}, "enfant": {"age": 0.0}, "gabarit": {"legs": 1.0, "torso": -1.0}}
OUTFITS = {
    "tenue_A": ["t_shirt", "jean", "chaussures", "casquette"],
    "tenue_B": ["chemise", "pantalon", "veste", "chaussures", "echarpe"],
    "tenue_C": ["pull", "short", "bottes", "bonnet", "gants"],
}
addon.register()
for label, values in MORPHOLOGIES.items():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.ops.humanloom.create()
    body = bpy.context.object
    for name, value in values.items():
        human.set_value(body, name, value)
    rig = skeleton.install(body)
    body.modifiers["Human Modeling · Surface"].show_viewport = False
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x, scene.render.resolution_y = SIZE, int(SIZE * 1.5)
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_cavity = True
    scene.world = bpy.data.worlds.new("w") if scene.world is None else scene.world
    scene.world.color = (1, 1, 1)
    camera_data = bpy.data.cameras.new("cam")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = 2.25
    camera = bpy.data.objects.new("cam", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.location = Vector((0.0, -6.0, 0.85))
    camera.rotation_euler = (math.radians(90), 0.0, 0.0)
    for outfit, pieces in OUTFITS.items():
        for g in list(garments.garments_of(body)):
            garments.remove_garment(g)
        for key in pieces:
            garments.add_garment(body, key)
        for state in ("repos", "pose"):
            for pb in rig.pose.bones:
                pb.rotation_mode = "XYZ"
                pb.rotation_euler = (0.0, 0.0, 0.0)
            clearance = state == "pose"
            for g in garments.garments_of(body):
                garments.set_clearance(g, clearance)
            if state == "pose":
                rig.pose.bones["arm_upper.R"].rotation_euler = Euler((0.0, math.radians(-90.0), 0.0))
                rig.pose.bones["leg_lower.L"].rotation_euler = Euler((math.radians(70.0), 0.0, 0.0))
            bpy.context.view_layer.update()
            scene.render.filepath = str(OUT / f"{outfit}_{label}_{state}.png")
            bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(camera, do_unlink=True)
    print("PLANCHE", label)
