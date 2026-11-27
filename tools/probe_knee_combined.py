"""Sonde : genou en poses COMBINÉES (flexion du genou × flexion de la hanche × torsion du tibia), plis nouveaux avec / sans correctifs de flexion (côté gauche, corps par défaut).

  blender --background --factory-startup --offline-mode --python-exit-code 0 --python tools/probe_knee_combined.py"""
import math
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Quaternion

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import extension as addon  # noqa: E402
from extension.animation import correctives, skeleton  # noqa: E402
import rig_metrics as M  # noqa: E402

addon.register()
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
bpy.ops.humanloom.create()
body = bpy.context.object
rig = skeleton.install(body)
body.modifiers["Human Modeling · Surface"].show_viewport = False
data = np.load(correctives.DATA, allow_pickle=False)
sign = float(data["genou_L_sign"])
mesh = body.data
mesh.calc_loop_triangles()
tris = np.array([t.vertices[:] for t in mesh.loop_triangles])
edges = np.array([e.vertices[:] for e in mesh.edges])
groups = {g.index: g.name for g in body.vertex_groups}
dominant = []
for v in mesh.vertices:
    c = [g for g in v.groups if groups[g.group] not in (skeleton.GROUP_LBS, skeleton.GROUP_DQS)]
    dominant.append(groups[max(c, key=lambda g: g.weight).group] if c else "")
tri_bone = np.array(dominant)[tris[:, 0]]
lookup = {b.name: i for i, b in enumerate(rig.pose.bones)}
rest_local = {b.name: np.array(b.matrix_local.to_3x3()) for b in rig.data.bones}


def reset():
    for b in rig.pose.bones:
        b.rotation_mode = "QUATERNION"
        b.rotation_quaternion = (1, 0, 0, 0)


def mute(state):
    for k in correctives.keys_of(body.data):
        k.mute = state
    bpy.context.view_layer.update()


reset()
mute(False)
bpy.context.view_layer.update()
rest = correctives._evaluate(body)
bone = rig.data.bones["leg_lower.L"]
pivot, tail = np.array(bone.head_local), np.array(bone.tail_local)
axis = (tail - pivot) / np.linalg.norm(tail - pivot)
region = M.Region(rest, tris, edges, pivot, 0.14, pivot, axis, 0.0)
hip_sign = 1.0
scores = {}
for s in (1.0, -1.0):
    rig.pose.bones["leg_upper.L"].rotation_quaternion = Quaternion((1, 0, 0), math.radians(40 * s))
    bpy.context.view_layer.update()
    scores[s] = float(np.array((rig.matrix_world @ rig.pose.bones["leg_lower.L"].head)[:])[1])  # le genou va vers l'avant (−y)
hip_sign = 1.0 if scores[1.0] <= scores[-1.0] else -1.0
print("combinaison : genou° / hanche° / torsion tibia° -> plis sans | avec ; étirement sans | avec")
for twist in (-20, -10, 0, 10, 20):  # rotation locale résiduelle autour de Z (hors axe de flexion)
    for hip in (0,):
        for knee in (60, 90, 120):
            out = {}
            for state, muted in (("sans", True), ("avec", False)):
                reset()
                rig.pose.bones["leg_upper.L"].rotation_quaternion = Quaternion((1, 0, 0), math.radians(hip_sign * hip))
                rig.pose.bones["leg_lower.L"].rotation_quaternion = Quaternion((1, 0, 0), math.radians(sign * knee)) @ Quaternion((0, 0, 1), math.radians(twist))
                mute(muted)
                points = correctives._evaluate(body)
                rot3 = np.array([np.array(b.matrix.to_3x3()) @ np.linalg.inv(rest_local[b.name]) for b in rig.pose.bones])
                tri_rot = np.array([rot3[lookup[n]] if n in lookup else np.eye(3) for n in tri_bone])
                out[state] = region.measure(points, tri_rot)
            print(f"  genou {knee:3d} hanche {hip:2d} Z {twist:3d} -> plis {out['sans']['plis']:3d} | {out['avec']['plis']:3d} ; étir {out['sans']['etirement_max']:.2f} | {out['avec']['etirement_max']:.2f}", flush=True)

print("quaternions réels (pire cas de la bibliothèque) appliqués seuls à leg_lower.L :")
for q in ((0.715, -0.693, -0.018, -0.086), (0.701, -0.706, -0.026, -0.096), (0.283, -0.95, -0.023, -0.132), (0.715, -0.693, 0.0, 0.0), (0.715, -0.693, 0.0, -0.086), (0.715, -0.693, -0.018, 0.0)):
    out = {}
    for state, muted in (("sans", True), ("avec", False)):
        reset()
        rig.pose.bones["leg_lower.L"].rotation_quaternion = Quaternion(q).normalized()
        mute(muted)
        points = correctives._evaluate(body)
        rot3 = np.array([np.array(b.matrix.to_3x3()) @ np.linalg.inv(rest_local[b.name]) for b in rig.pose.bones])
        tri_rot = np.array([rot3[lookup[n]] if n in lookup else np.eye(3) for n in tri_bone])
        out[state] = region.measure(points, tri_rot)
    angle_prop = float(rig["hlc_angle_genou_L"])
    print(f"  q {q} -> plis {out['sans']['plis']} | {out['avec']['plis']} ; étir {out['sans']['etirement_max']:.2f} | {out['avec']['etirement_max']:.2f} ; angle lu par le pilote {angle_prop:.1f}°", flush=True)

print("pire cas réel complet (cuisse + genou) :")
for qu, ql in (((0.827, 0.393, -0.194, 0.351), (0.715, -0.693, -0.018, -0.086)), ((0.943, 0.176, 0.049, 0.279), (0.701, -0.706, -0.026, -0.096)), ((0.982, 0.055, 0.166, 0.071), (0.283, -0.95, -0.023, -0.132))):
    out = {}
    for state, muted in (("sans", True), ("avec", False)):
        reset()
        rig.pose.bones["leg_upper.L"].rotation_quaternion = Quaternion(qu).normalized()
        rig.pose.bones["leg_lower.L"].rotation_quaternion = Quaternion(ql).normalized()
        mute(muted)
        points = correctives._evaluate(body)
        rot3 = np.array([np.array(b.matrix.to_3x3()) @ np.linalg.inv(rest_local[b.name]) for b in rig.pose.bones])
        tri_rot = np.array([rot3[lookup[n]] if n in lookup else np.eye(3) for n in tri_bone])
        out[state] = region.measure(points, tri_rot)
    print(f"  cuisse {qu} genou {ql} -> plis {out['sans']['plis']} | {out['avec']['plis']} ; étir {out['sans']['etirement_max']:.2f} | {out['avec']['etirement_max']:.2f}", flush=True)

import os
pose_file = os.environ.get("HL_POSE_FILE")
if pose_file:
    d = np.load(pose_file, allow_pickle=False)
    print("pose réelle complète (tous les os) :")
    VARIANTS = {"complète": None, "genou+cuisse seulement": {"leg_upper.L", "leg_lower.L"}, "+ pied gauche": {"leg_upper.L", "leg_lower.L", "foot.L", "toe.L"}, "+ bassin et racine": {"leg_upper.L", "leg_lower.L", "pelvis", "root"},
                "+ jambe droite": {"leg_upper.L", "leg_lower.L", "leg_upper.R", "leg_lower.R", "foot.R", "toe.R"}, "+ colonne": {"leg_upper.L", "leg_lower.L"} | {n for n in d["names"] if str(n).startswith("spine")},
                "+ bras": {"leg_upper.L", "leg_lower.L"} | {n for n in d["names"] if any(k in str(n) for k in ("arm", "hand", "clavicle", "thumb", "index", "middle", "ring", "pinky"))}}
    for variant, only in VARIANTS.items():
        out = {}
        for state, muted in (("sans", True), ("avec", False)):
            reset()
            for i, n in enumerate(d["names"]):
                pb = rig.pose.bones[str(n)]
                if only is not None and str(n) not in only:
                    continue
                pb.rotation_quaternion = tuple(d["quat"][i])
                pb.location = tuple(d["loc"][i])
            mute(muted)
            points = correctives._evaluate(body)
            rot3 = np.array([np.array(b.matrix.to_3x3()) @ np.linalg.inv(rest_local[b.name]) for b in rig.pose.bones])
            tri_rot = np.array([rot3[lookup[n]] if n in lookup else np.eye(3) for n in tri_bone])
            out[state] = region.measure(points, tri_rot)
            out[state + "_angle"] = float(rig["hlc_angle_genou_L"])
        print(f"  {variant} -> plis {out['sans']['plis']} | {out['avec']['plis']} ; étir {out['sans']['etirement_max']:.2f} | {out['avec']['etirement_max']:.2f} ; angle pilote {out['avec_angle']:.1f}", flush=True)
