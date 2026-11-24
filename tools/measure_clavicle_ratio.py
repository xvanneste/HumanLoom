"""Mesure du RATIO de clavicule (rythme scapulo-huméral) : pour chaque ratio r (part de l'élévation portée par la clavicule), plis nouveaux / étirement / aire de section en zone proche (R=0,14) et large (R=0,27), 3 morphologies, plans sagittal et frontal.

  blender --background --factory-startup --offline-mode --python-exit-code 0 --python tools/measure_clavicle_ratio.py -- DOSSIER [--ratios 0,0.1667,0.25,0.3333,0.5] [--angles 90,135,180]
Le bras porte (1−r)·a, la clavicule r·a (axe et sens mesurés). Aucune amplitude publiée lue : le rythme 2:1 est une règle courante de rig, non vérifiée ici."""
import math
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import proto_shoulder_correctives as P  # noqa: E402
import rig_metrics as M  # noqa: E402

ARGS = P.ARGS
RATIOS = [float(v) for v in (ARGS[ARGS.index("--ratios") + 1] if "--ratios" in ARGS else "0,0.1667,0.25,0.3333,0.5").split(",")]
ANGLES = [int(v) for v in (ARGS[ARGS.index("--angles") + 1] if "--angles" in ARGS else "90,135,180").split(",")]
SIDE = "L"
for morph in ("defaut", "femme_jeune", "homme_age"):
    scene = P.Scene(morph)
    arm, cl = f"arm_upper.{SIDE}", f"clavicle.{SIDE}"
    pivot = scene.head(arm)
    bone = scene.rig.data.bones[arm]
    ah, at = np.array(bone.head_local), np.array(bone.tail_local)
    au = (at - ah) / np.linalg.norm(at - ah)
    near = M.Region(scene.rest, scene.tris, scene.edges, pivot, 0.14, ah, au, 0.05)
    far = M.Region(scene.rest, scene.tris, scene.edges, pivot, 0.27, ah, au, 0.05)

    def tail(n):
        return np.array((scene.rig.matrix_world @ scene.rig.pose.bones[n].tail)[:])

    def sign(b, axis, metric):
        sc = {}
        for s in (1.0, -1.0):
            scene.pose({b: P.rot(axis, 40 * s)})
            sc[s] = metric()
        scene.pose({})
        return 1.0 if sc[1.0] <= sc[-1.0] else -1.0

    sg = sign(arm, 0, lambda: float(tail(arm)[1]))
    fr = sign(arm, 2, lambda: -float(tail(arm)[2]))
    cv = {}
    for axis in (0, 2):
        for s in (1.0, -1.0):
            scene.pose({cl: P.rot(axis, 20 * s)})
            cv[(axis, s)] = float(np.array((scene.rig.matrix_world @ scene.rig.pose.bones[arm].head)[:])[2])
    scene.pose({})
    cax, csg = max(cv, key=cv.get)
    for plane, fn in (("sagittal", lambda a, r: {arm: P.rot(0, sg * a * (1 - r)), cl: P.rot(cax, csg * a * r)}), ("frontal", lambda a, r: {arm: P.rot(2, fr * a * (1 - r)), cl: P.rot(cax, csg * a * r)})):
        for a in ANGLES:
            cells = []
            for r in RATIOS:
                scene.pose(fn(a, r))
                pts = P.evaluate_cage(scene.body)
                rot3 = scene.tri_rotations()
                na, fa = near.measure(pts, rot3), far.measure(pts, rot3)
                cells.append(f"r={r:.2f}: plis_large {fa['plis']} etir_large {fa['etirement_max']} sec {na.get('aire_section')} plis_proche {na['plis']}")
            print("RATIO", morph, plane, a, " | ".join(cells), flush=True)
