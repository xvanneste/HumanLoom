"""Sonde : répartition moyenne des poids le long de chaque membre (os dominants par tranche), pour le diagnostic des articulations.

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/probe_limb_weights.py"""
from pathlib import Path
import sys

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension.animation import skeleton  # noqa: E402

addon.register()
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
bpy.ops.humanloom.create()
body = bpy.context.object
rig = skeleton.install(body)
pts = skeleton.cage_points(body)
names = {g.index: g.name for g in body.vertex_groups}
W = {}
for v in body.data.vertices:
    W[v.index] = {names[g.group]: g.weight for g in v.groups}
print("n groups", len(names), "constraints", sum(len(b.constraints) for b in rig.pose.bones))
for limb, a, b in (("avant-bras", "arm_lower.L", None), ("bras", "arm_upper.L", None), ("cuisse", "leg_upper.L", None), ("jambe", "leg_lower.L", None)):
    bone = rig.data.bones[a]
    h, t = np.array(bone.head_local), np.array(bone.tail_local)
    ax = t - h
    L = float(np.linalg.norm(ax))
    u = ax / L
    s = (pts - h) @ u / L
    rad = np.linalg.norm((pts - h) - np.outer((pts - h) @ u, u), axis=1)
    sel = np.where((s > -0.25) & (s < 1.25) & (rad < 0.11))[0]
    print(limb, "longueur", round(L, 3))
    for lo in np.arange(-0.2, 1.2, 0.1):
        idx = [i for i in sel if lo <= s[i] < lo + 0.1]
        if not idx:
            continue
        acc = {}
        for i in idx:
            for k, w in W[i].items():
                acc[k] = acc.get(k, 0) + w / len(idx)
        top = sorted(acc.items(), key=lambda kv: -kv[1])[:4]
        print("  t=%.1f" % lo, ", ".join(f"{k.replace('.L','')}:{w:.2f}" for k, w in top))
