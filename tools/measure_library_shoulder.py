"""Mesure de l'épaule sur les animations RÉELLES de la bibliothèque locale (lecture seule ; seuls des NOMBRES sont écrits) : pour chaque image où un bras est élevé (≥ 60° sous la verticale), critères de zone proche / large
(plis nouveaux, étirement, aire de section) et rotation de la clavicule en fonction de l'élévation (rythme scapulo-huméral réel de la bibliothèque).

  blender --background --factory-startup --offline-mode --python-exit-code 0 --python tools/measure_library_shoulder.py -- --library DOSSIER [--actions 30] [--morph defaut]"""
import json
import math
from pathlib import Path
import re
import sys

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import proto_shoulder_correctives as P  # noqa: E402
import rig_metrics as M  # noqa: E402
from extension.animation import mapping, retarget, retarget_bpy  # noqa: E402

ARGS = P.ARGS
LIB = ARGS[ARGS.index("--library") + 1]
COUNT = int(ARGS[ARGS.index("--actions") + 1]) if "--actions" in ARGS else 30
SCALES = [float(v) for v in (ARGS[ARGS.index("--clav-scales") + 1] if "--clav-scales" in ARGS else "1.0").split(",")]  # facteurs sur la rotation de la clavicule (arm_upper compensé : orientation du bras conservée)
MORPH = ARGS[ARGS.index("--morph") + 1] if "--morph" in ARGS else "defaut"
scene = P.Scene(MORPH)
rig = scene.rig
for b in rig.pose.bones:
    b.rotation_mode = "QUATERNION"
target = retarget.rig_from_armature(rig)
from mathutils import Matrix, Quaternion  # noqa: E402


def rest_rel(side):
    pc, cc = rig.data.bones[f"clavicle.{side}"].matrix_local.to_3x3(), rig.data.bones[f"arm_upper.{side}"].matrix_local.to_3x3()
    return (pc.inverted() @ cc).to_quaternion()


REL = {side: rest_rel(side) for side in ("L", "R")}


def limit_clavicle(quats, scale):
    """Copie de `quats` (n_os, 4) avec la clavicule réduite d'un facteur `scale` (slerp depuis l'identité) et arm_upper recalculé pour garder l'orientation du bras : Qa' = rel⁻¹ Qc'⁻¹ Qc rel Qa."""
    out = np.array(quats)
    for side in ("L", "R"):
        ci, ai = target.index[f"clavicle.{side}"], target.index[f"arm_upper.{side}"]
        qc, qa = Quaternion(quats[ci]), Quaternion(quats[ai])
        qc2 = Quaternion((1, 0, 0, 0)).slerp(qc, scale)
        rel = REL[side]
        qa2 = rel.inverted() @ qc2.inverted() @ qc @ rel @ qa
        out[ci], out[ai] = tuple(qc2), tuple(qa2)
    return out
target_map = mapping.from_armature(rig)
library = sorted(Path(LIB).glob("*.blend"))[0]
with bpy.data.libraries.load(str(library), link=False) as (names, _):
    armature_names, action_names = list(names.armatures), list(names.actions)
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
regions = {}
for side in ("L", "R"):
    arm = f"arm_upper.{side}"
    pivot = scene.head(arm)
    bone = scene.rig.data.bones[arm]
    ah, at = np.array(bone.head_local), np.array(bone.tail_local)
    au = (at - ah) / np.linalg.norm(at - ah)
    regions[side] = (M.Region(scene.rest, scene.tris, scene.edges, pivot, 0.14, ah, au, 0.05), M.Region(scene.rest, scene.tris, scene.edges, pivot, 0.27, ah, au, 0.05))
tested = 0
frames = []
worst = {"plis": -1}
for name in candidates:
    if tested >= COUNT:
        break
    with bpy.data.libraries.load(str(library), link=False) as (_, wanted):
        wanted.actions = [name]
    action = wanted.actions[0]
    try:
        motion, _first = retarget_bpy.read_action(action, source)
        animated = len({m.group(1) for layer in action.layers for strip in layer.strips for bag in strip.channelbags for c in bag.fcurves for m in [re.match(r'pose\.bones\["(.+?)"\]', c.data_path)] if m})
    finally:
        bpy.data.actions.remove(action)
    if animated < 60 or motion.frames < 8:
        continue
    tested += 1
    result = retarget.retarget(source, target, links, motion, retarget.Options(pose_mode=retarget.ABSOLUTE_IK, root_motion=retarget.KEEP, ik_limbs=("leg",)))
    for f in range(0, motion.frames, 3):
        base_quat = np.array(result.quat[f])
        for side in ("L", "R"):
            pass
        for i, nme in enumerate(target.names):
            pb = rig.pose.bones[nme]
            pb.rotation_quaternion = tuple(base_quat[i])
            pb.location = tuple(result.loc[f, i])
        bpy.context.view_layer.update()
        for side in ("L", "R"):
            head = np.array((rig.matrix_world @ rig.pose.bones[f"arm_upper.{side}"].head)[:])
            tail = np.array((rig.matrix_world @ rig.pose.bones[f"arm_upper.{side}"].tail)[:])
            d = (tail - head) / np.linalg.norm(tail - head)
            elevation = math.degrees(math.acos(float(np.clip(-d[2], -1, 1))))
            if elevation < 60:
                continue
            for scale in SCALES:
                quats = limit_clavicle(base_quat, scale) if scale != 1.0 else base_quat
                for i, nme in enumerate(target.names):
                    rig.pose.bones[nme].rotation_quaternion = tuple(quats[i])
                bpy.context.view_layer.update()
                q = rig.pose.bones[f"clavicle.{side}"].rotation_quaternion
                clav = math.degrees(2 * math.acos(min(1.0, abs(q.w))))
                pts = P.evaluate_cage(scene.body)
                rot3 = scene.tri_rotations()
                near, far = regions[side]
                a, b = near.measure(pts, rot3), far.measure(pts, rot3)
                hand_rel = np.array((rig.matrix_world @ rig.pose.bones[f"hand.{side}"].head)[:]) - np.array((rig.matrix_world @ rig.pose.bones[f"arm_upper.{side}"].head)[:])
                if b["plis"] > worst["plis"] and scale == 1.0:
                    worst = {"plis": b["plis"], "elev": elevation, "quat": np.array([tuple(rig.pose.bones[n].rotation_quaternion) for n in target.names]), "loc": np.array([tuple(rig.pose.bones[n].location) for n in target.names])}
                frames.append({"scale": scale, "action": tested, "elev": elevation, "clav": clav, "bad": bool(M.failures(a)) or b["plis"] > 2 or b["etirement_max"] >= 3, "plis_large": b["plis"], "etir_large": b["etirement_max"], "sec": a.get("aire_section"), "plis_near": a["plis"], "hand_rel": hand_rel.tolist(), "key": (tested, f, side)})
            for i, nme in enumerate(target.names):
                rig.pose.bones[nme].rotation_quaternion = tuple(base_quat[i])
print("ACTIONS", tested, "images de bras élevé", len(frames), flush=True)
if frames:
    for scale in SCALES:
        sel_all = [f for f in frames if f["scale"] == scale]
        print(f"ECHELLE {scale} : {len(sel_all)} images de bras élevé ; clavicule médiane {np.median([f['clav'] for f in sel_all]):.1f}° ; plis zone large médiane {np.median([f['plis_large'] for f in sel_all]):.0f} moyenne {np.mean([f['plis_large'] for f in sel_all]):.1f} max {max(f['plis_large'] for f in sel_all)} ; plis proche médiane {np.median([f['plis_near'] for f in sel_all]):.0f} ; étirement large médian {np.median([f['etir_large'] for f in sel_all]):.2f} ; aire de section médiane {np.median([f['sec'] for f in sel_all]):.2f} ; hors critère {sum(f['bad'] for f in sel_all)}", flush=True)
    ref = {f["key"]: np.array(f["hand_rel"]) for f in frames if f["scale"] == 1.0}
    for scale in SCALES:
        if scale == 1.0:
            continue
        diffs = [np.linalg.norm(np.array(f["hand_rel"]) - ref[f["key"]]) for f in frames if f["scale"] == scale and f["key"] in ref]
        print(f"ECART main/épaule (position relative à la racine du bras) échelle {scale} : médiane {np.median(diffs) * 1000:.2f} mm, max {max(diffs) * 1000:.2f} mm", flush=True)

if worst["plis"] >= 0:
    P.OUT.mkdir(parents=True, exist_ok=True)
    np.savez(P.OUT / "pose_pire.npz", names=np.array(target.names), quat=worst["quat"], loc=worst["loc"])
    print("PIRE image : plis zone large", worst["plis"], "élévation", round(worst["elev"], 1))
