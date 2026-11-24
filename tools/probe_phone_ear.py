"""Sonde : téléphone (forme + écran), pose « à l'oreille », parapluie tenu (poignet tourné). Imprime les mesures.

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/probe_phone_ear.py"""
from pathlib import Path
import sys

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension import accessories as A  # noqa: E402
from extension.animation import skeleton  # noqa: E402

addon.register()
bpy.ops.humanloom.create()
body = bpy.context.object
rig = skeleton.install(body)
body.modifiers["Human Modeling · Surface"].show_viewport = False
print("KEYS", list(A.ACCESSORIES))

phone = A.add_accessory(body, "telephone")
print("phone mats", [m.name for m in phone.data.materials], "verts", len(phone.data.vertices), "slots idx", sorted({p.material_index for p in phone.data.polygons}))
report = A.pose_phone_ear(body, "R")
print("EAR", report)
bpy.context.view_layer.update()
origin, x, y, z = A._hand_frame(rig, "R")
print("hand origin", origin)
target, head = A.ear_target(body, "R")
print("target", target, "head", head)
A.remove_accessory(phone)
A.reset_hand(body, "R")

for key in ("parapluie_ferme", "parapluie_ouvert"):
    obj = A.add_accessory(body, key)
    bpy.context.view_layer.update()
    pts = np.array([(obj.matrix_world @ v.co)[:] for v in obj.data.vertices])
    ext = pts.max(0) - pts.min(0)
    print(key, "extent", ext.round(3), "roll", A.grip_roll(body, "R") if False else [round(float(np.degrees(a)), 1) for a in rig.pose.bones["hand.R"].rotation_euler], "elbow", [round(float(np.degrees(a)), 1) for a in rig.pose.bones["arm_lower.R"].rotation_euler], "shaft_dot", None)
    A.remove_accessory(obj)

