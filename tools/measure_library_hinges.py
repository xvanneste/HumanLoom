"""Mesure des creux articulaires (coude, genou, hanche, poignet, cou) sur les animations RÉELLES de la bibliothèque locale (lecture seule ; seuls des NOMBRES sont écrits) : distribution des angles de flexion et critères (plis nouveaux,
étirement, aire de section, zone proche) aux images où l'angle dépasse 60°, avec et sans correctifs de flexion (clés muettes) pour le coude et le genou.

  blender --background --factory-startup --offline-mode --python-exit-code 0 --python tools/measure_library_hinges.py -- --library DOSSIER [--actions 30] [--min-angle 60]"""
import math
from pathlib import Path
import re
import sys

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import extension as addon  # noqa: E402
from extension.animation import correctives, mapping, retarget, retarget_bpy, skeleton  # noqa: E402
import rig_metrics as M  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:]
LIB = ARGS[ARGS.index("--library") + 1]
COUNT = int(ARGS[ARGS.index("--actions") + 1]) if "--actions" in ARGS else 30
MIN_ANGLE = float(ARGS[ARGS.index("--min-angle") + 1]) if "--min-angle" in ARGS else 60.0
addon.register()
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
bpy.ops.humanloom.create()
body = bpy.context.object
rig = skeleton.install(body)
body.modifiers["Human Modeling · Surface"].show_viewport = False
for b in rig.pose.bones:
    b.rotation_mode = "QUATERNION"
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
rest_local = {b.name: np.array(b.matrix_local.to_3x3()) for b in rig.data.bones}
names = [b.name for b in rig.pose.bones]
lookup = {n: i for i, n in enumerate(names)}


def mute(state):
    for k in correctives.keys_of(body.data):
        k.mute = state
    bpy.context.view_layer.update()


mute(False)
for b in rig.pose.bones:
    b.rotation_quaternion = (1, 0, 0, 0)
bpy.context.view_layer.update()
rest = correctives._evaluate(body)
JOINTS = {  # nom : (os pivot, rayon de région, os dont la rotation locale (autour de X) s'additionne pour l'angle)
    "coude": ("arm_lower", 0.12, ("arm_lower",)), "genou": ("leg_lower", 0.14, ("leg_lower",)), "hanche": ("leg_upper", 0.16, ("leg_upper",)),
    "poignet": ("hand", 0.07, ("hand",)), "cou": ("neck.01", 0.10, ("neck.01", "neck.02", "head")),
}
regions = {}
for joint, (bone_base, radius, _) in JOINTS.items():
    for side in ((".L", ".R") if joint != "cou" else ("",)):
        bone = rig.data.bones[bone_base + side]
        pivot, tail = np.array(bone.head_local), np.array(bone.tail_local)
        axis = (tail - pivot) / np.linalg.norm(tail - pivot)
        regions[(joint, side)] = M.Region(rest, tris, edges, pivot, radius, pivot, axis, 0.0)


def flexion_deg(joint, side):
    total = 0.0
    for base in JOINTS[joint][2]:
        q = rig.pose.bones[base + side if joint != "cou" else base].rotation_quaternion
        w = q.w if q.w != 0 else 1e-9
        total += math.degrees(2 * math.atan2(q.x * math.copysign(1, w), abs(w)))
    return total


target = retarget.rig_from_armature(rig)
target_map = mapping.from_armature(rig)
library = sorted(Path(LIB).glob("*.blend"))[0]
with bpy.data.libraries.load(str(library), link=False) as (n_, _):
    armature_names, action_names = list(n_.armatures), list(n_.actions)
best = None
for name in armature_names:
    with bpy.data.libraries.load(str(library), link=False) as (_, wanted):
        wanted.armatures = [name]
    data = wanted.armatures[0]
    if len(data.bones) < 80:
        bpy.data.armatures.remove(data)
        continue
    pairs, report = mapping.auto_map(target_map, mapping.from_armature(data))
    score = (report.coverage, -len(report.low_confidence))
    if best is None or score > best[0]:
        best = (score, name, {t: p.source for t, p in pairs.items()})
    bpy.data.armatures.remove(data)
with bpy.data.libraries.load(str(library), link=False) as (_, wanted):
    wanted.armatures = [best[1]]
source = retarget.rig_from_armature(wanted.armatures[0])
links = best[2]
candidates = action_names[:: max(1, len(action_names) // (COUNT * 3))]
rows = []
worst_knee = {"gap": -1}
all_angles = {}
ANGLES_ONLY = "--angles-only" in ARGS
tested = 0
for name in candidates:
    if tested >= COUNT:
        break
    with bpy.data.libraries.load(str(library), link=False) as (_, wanted):
        wanted.actions = [name]
    action = wanted.actions[0]
    try:
        try:
            motion, _first = retarget_bpy.read_action(action, source)
        except ValueError as error:  # action refusée par le lecteur strict (échelle non unitaire, contrainte…) : ignorée et comptée
            print('ACTION IGNOREE', name, str(error)[:80], flush=True)
            continue
        animated = len({m.group(1) for layer in action.layers for strip in layer.strips for bag in strip.channelbags for c in bag.fcurves for m in [re.match(r'pose\.bones\["(.+?)"\]', c.data_path)] if m})
    finally:
        bpy.data.actions.remove(action)
    if animated < 60 or motion.frames < 8:
        continue
    tested += 1
    result = retarget.retarget(source, target, links, motion, retarget.Options(pose_mode=retarget.ABSOLUTE_IK, root_motion=retarget.KEEP, ik_limbs=("leg",)))
    for f in range(0, motion.frames, 3):
        for i, nme in enumerate(target.names):
            pb = rig.pose.bones[nme]
            pb.rotation_quaternion = tuple(result.quat[f, i])
            pb.location = tuple(result.loc[f, i])
        bpy.context.view_layer.update()
        for (j, s) in regions:
            all_angles.setdefault(j, []).append(flexion_deg(j, s))
        todo = [(j, s) for (j, s) in regions if abs(flexion_deg(j, s)) >= MIN_ANGLE]
        if ANGLES_ONLY or not todo:
            continue
        angles = {(j, s): abs(flexion_deg(j, s)) for (j, s) in todo}
        outcomes = {}
        for state, muted in (("avec", False), ("sans", True)):
            mute(muted)
            points = correctives._evaluate(body)
            rot3 = np.array([np.array(b.matrix.to_3x3()) @ np.linalg.inv(rest_local[b.name]) for b in rig.pose.bones])
            tri_rot = np.array([rot3[lookup[n]] if n in lookup else np.eye(3) for n in tri_bone])
            for (j, s) in todo:
                outcomes[(j, s, state)] = regions[(j, s)].measure(points, tri_rot)
        mute(False)
        for (j, s) in todo:
            a, b = outcomes[(j, s, "avec")], outcomes[(j, s, "sans")]
            if j == "genou" and a["plis"] - b["plis"] > worst_knee["gap"]:
                worst_knee = {"gap": a["plis"] - b["plis"], "side": s, "quat": np.array([tuple(rig.pose.bones[n].rotation_quaternion) for n in target.names]), "loc": np.array([tuple(rig.pose.bones[n].location) for n in target.names])}
            rows.append({"joint": j, "side": s, "angle": angles[(j, s)], "plis_avec": a["plis"], "plis_sans": b["plis"], "etir_avec": a["etirement_max"], "etir_sans": b["etirement_max"],
                         "hip": abs(flexion_deg("hanche", s)) if s in (".L", ".R") else 0.0, "q": tuple(round(v, 3) for v in rig.pose.bones[JOINTS[j][0] + s].rotation_quaternion) if j != "cou" else None, "loc": tuple(round(v, 4) for v in rig.pose.bones[JOINTS[j][0] + s].location) if j != "cou" else None, "locup": tuple(round(v, 4) for v in rig.pose.bones["leg_upper" + s].location) if j == "genou" else None, "qup": tuple(round(v, 3) for v in rig.pose.bones["leg_upper" + s].rotation_quaternion) if j == "genou" else None, "bad_avec": bool(M.failures(a)) or a["etirement_max"] >= 3, "bad_sans": bool(M.failures(b)) or b["etirement_max"] >= 3})
print("ACTIONS", tested, "mesures", len(rows), flush=True)
for j, v in all_angles.items():
    v = np.array(v)
    print(f"ANGLES {j} (toutes images, signé) : n {len(v)} ; médiane {np.median(v):.0f}° ; p5 {np.percentile(v, 5):.0f}° ; p95 {np.percentile(v, 95):.0f}° ; part |angle| ≥ 60° {100 * np.mean(np.abs(v) >= 60):.0f} %", flush=True)
for joint in JOINTS:
    sel = [r for r in rows if r["joint"] == joint]
    if not sel:
        print(f"JOINT {joint} : aucune image à ≥ {MIN_ANGLE:g}°")
        continue
    corrected = joint in ("coude", "genou")
    print(f"JOINT {joint} : {len(sel)} mesures ≥ {MIN_ANGLE:g}° (angle médian {np.median([r['angle'] for r in sel]):.0f}°, max {max(r['angle'] for r in sel):.0f}°) ; plis médiane sans {np.median([r['plis_sans'] for r in sel]):.0f} avec {np.median([r['plis_avec'] for r in sel]):.0f} ; "
          f"plis total sans {sum(r['plis_sans'] for r in sel)} avec {sum(r['plis_avec'] for r in sel)} ; hors critère sans {sum(r['bad_sans'] for r in sel)} avec {sum(r['bad_avec'] for r in sel)} ; étirement max sans {max(r['etir_sans'] for r in sel):.2f} avec {max(r['etir_avec'] for r in sel):.2f}"
          + ("" if corrected else " (pas de correctifs : colonnes identiques)"), flush=True)

sel = [r for r in rows if r["joint"] == "genou"]
for lo, hi in ((0, 30), (30, 60), (60, 200)):
    part = [r for r in sel if lo <= r["hip"] < hi]
    if part:
        print(f"GENOU hanche {lo}-{hi}° : {len(part)} mesures ; plis sans {sum(r['plis_sans'] for r in part)} avec {sum(r['plis_avec'] for r in part)} ; étirement max sans {max(r['etir_sans'] for r in part):.2f} avec {max(r['etir_avec'] for r in part):.2f}", flush=True)
for lo, hi in ((60, 90), (90, 120), (120, 160)):
    part = [r for r in sel if lo <= r["angle"] < hi]
    if part:
        print(f"GENOU angle {lo}-{hi}° : {len(part)} mesures ; plis sans {sum(r['plis_sans'] for r in part)} avec {sum(r['plis_avec'] for r in part)}", flush=True)

worse = sorted(sel, key=lambda r: r["plis_avec"] - r["plis_sans"], reverse=True)[:8]
for r in worse:
    w, x, y, z = r["q"]
    print(f"PIRE genou{r['side']} angle {r['angle']:.0f}° plis {r['plis_sans']} -> {r['plis_avec']} ; quaternion locale (w,x,y,z) = {r['q']} ; part hors axe X = {math.degrees(2 * math.atan2(math.hypot(y, z), abs(w))):.0f}° ; hanche {r['hip']:.0f}° ; loc genou {r['loc']} loc cuisse {r['locup']} q cuisse {r['qup']}", flush=True)

if worst_knee["gap"] >= 0:
    np.savez(Path(ARGS[ARGS.index("--out") + 1]) / "pose_genou_pire.npz" if "--out" in ARGS else Path("pose_genou_pire.npz"), names=np.array(target.names), quat=worst_knee["quat"], loc=worst_knee["loc"], side=worst_knee["side"])
    print("POSE PIRE GENOU enregistrée, écart de plis", worst_knee["gap"], flush=True)
