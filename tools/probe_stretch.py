"""Sonde : arêtes les plus étirées pour une pose d'épaule (position, poids des deux sommets, membre des masques)."""
import math
from pathlib import Path
import sys

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension import human  # noqa: E402
from extension.animation import skeleton  # noqa: E402

addon.register()
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
bpy.ops.humanloom.create()
body = bpy.context.object
rig = skeleton.install(body)
for b in rig.pose.bones:
    b.rotation_mode = "XYZ"
mesh = body.data
edges = np.array([e.vertices[:] for e in mesh.edges])
names = {g.index: g.name for g in body.vertex_groups}


def cage():
    for m in body.modifiers:
        m.show_viewport = m.name in (human.MODIFIER_NAME, skeleton.MODIFIER_NAME, skeleton.DQS_MODIFIER)
    human.touch(body)
    bpy.context.view_layer.update()
    ev = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    m = ev.to_mesh()
    p = np.array([v.co[:] for v in m.vertices])
    ev.to_mesh_clear()
    return p


rest = cage()
rig.pose.bones["arm_upper.L"].rotation_euler = (0, 0, math.radians(90))
bpy.context.view_layer.update()
pts = cage()
L0 = np.linalg.norm(rest[edges[:, 0]] - rest[edges[:, 1]], axis=1)
L1 = np.linalg.norm(pts[edges[:, 0]] - pts[edges[:, 1]], axis=1)
order = np.argsort(-(L1 / np.maximum(L0, 1e-9)))[:6]
for i in order:
    a, b = edges[i]
    print("etirement", round(float(L1[i] / L0[i]), 2), "pos repos", rest[a].round(3))
    for v in (a, b):
        print("   ", v, {names[g.group]: round(g.weight, 2) for g in mesh.vertices[v].groups})
