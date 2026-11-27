"""Mesure (lecture seule de la bibliothèque ; seuls des NOMBRES sont écrits) de l'effet des poids de cou/clavicule sur les actions RÉELLES retargetées : plis du cou (zone de 16 cm autour de neck.02) et déformation du visage
(écart des sommets de la tête à leur mouvement RIGIDE par l'os head, en mm). `--variant v1` : poids d'origine (fichier donné par `--v1-weights`) ; `--variant v2` : poids livrés (symétrisés). Mesuré sur 30 actions : plis du cou 5957 (v1) → 4068 (v2), visage identique ; un adoucissement des poids de clavicule au cou, essayé, donnait 22399 (abandonné).

  blender --background --factory-startup --offline-mode --python-exit-code 0 --python tools/measure_library_neck_weights.py -- --library DOSSIER --variant v1|v2 [--v1-weights human_rig_weights_v1.npz] [--actions 30] [--out FICHIER.json]"""
import json
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


def arg(name, default=None):
    return ARGS[ARGS.index(name) + 1] if name in ARGS else default


LIB, VARIANT, COUNT = arg("--library"), arg("--variant", "v2"), int(arg("--actions", 30))
if VARIANT == "v1":
    skeleton.WEIGHTS_FILE = Path(arg("--v1-weights"))
addon.register()
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
bpy.ops.humanloom.create()
body = bpy.context.object
rig = skeleton.install(body, correctives=False)
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
dominant = np.array(dominant)
tri_bone = dominant[tris[:, 0]]
rest_local = {b.name: np.array(b.matrix_local.to_3x3()) for b in rig.data.bones}
lookup = {b.name: i for i, b in enumerate(rig.pose.bones)}
for b in rig.pose.bones:
    b.rotation_quaternion = (1, 0, 0, 0)
bpy.context.view_layer.update()
rest = correctives._evaluate(body)
neck_pivot = np.array(rig.data.bones["neck.02"].head_local)
region = M.Region(rest, tris, edges, neck_pivot, 0.16, neck_pivot, np.array([0.0, 0.0, 1.0]), 0.0)
head_bone = rig.data.bones["head"]
face = np.where((dominant == "head") & (rest[:, 2] > head_bone.head_local[2] + 0.03))[0]
rest_head = np.array(rig.data.bones["head"].matrix_local)

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
neck_plis, neck_stretch, face_dev, shoulder_up = [], [], [], []
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
        except ValueError:
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
        points = correctives._evaluate(body)
        rot3 = np.array([np.array(b.matrix.to_3x3()) @ np.linalg.inv(rest_local[b.name]) for b in rig.pose.bones])
        tri_rot = np.array([rot3[lookup[n]] if n in lookup else np.eye(3) for n in tri_bone])
        measure = region.measure(points, tri_rot)
        neck_plis.append(measure["plis"])
        neck_stretch.append(measure["etirement_max"])
        pose_head = np.array(rig.pose.bones["head"].matrix)
        rigid = (pose_head @ np.linalg.inv(rest_head) @ np.c_[rest[face], np.ones(len(face))].T).T[:, :3]
        face_dev.append(float(np.linalg.norm(points[face] - rigid, axis=-1).max()) * 1000)
print("ACTIONS", tested, "images", len(neck_plis), flush=True)
summary = {"variant": VARIANT, "actions": tested, "images": len(neck_plis), "plis_cou_total": int(sum(neck_plis)), "plis_cou_max": int(max(neck_plis)), "plis_cou_images_avec_plis": int(sum(p > 0 for p in neck_plis)),
           "etirement_cou_max": round(float(max(neck_stretch)), 2), "visage_ecart_au_mouvement_rigide_mm": {"mediane": round(float(np.median(face_dev)), 2), "p95": round(float(np.percentile(face_dev, 95)), 2), "max": round(float(max(face_dev)), 2)}}
print("MESURE", json.dumps(summary, ensure_ascii=False))
if arg("--out"):
    Path(arg("--out")).write_text(json.dumps(summary, indent=1, ensure_ascii=False), encoding="utf-8")
