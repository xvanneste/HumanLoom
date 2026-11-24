"""Construit les CORRECTIFS DE FORME d'épaule (palier 1 : élévation jusqu'à 135°) : cibles par optimisation, encodage en espace de repos, bases cardinales RBF (Sloan) — `extension/data/human_rig_correctives.npz`.

  blender --background --factory-startup --offline-mode --python-exit-code 0 --python tools/build_shoulder_correctives.py -- DOSSIER_DE_SORTIE [--write 1] [--validate 1]

Côtés gauche et droit générés SÉPARÉMENT (signes de rotation mesurés pour chacun : aucune hypothèse de symétrie des repères d'os). Caractéristiques de pose : (x, y, z) du quaternion LOCAL de `arm_upper` canonisé (w ≥ 0), sans décomposition d'Euler.
Cibles générées sur le corps par défaut (cage de repos) ; l'application à d'autres morphologies passe par la morphologie du groupe de nœuds (à valider par mesure). Aucune donnée tierce."""
import json
import math
from pathlib import Path
import sys
import time

import numpy as np
from mathutils import Euler

sys.path.insert(0, str(Path(__file__).resolve().parent))
import proto_shoulder_correctives as P  # noqa: E402
import rig_metrics as M  # noqa: E402
import rig_solver as S  # noqa: E402
from extension.animation import skeleton  # noqa: E402

ARGS = P.ARGS
ANGLES = (30, 60, 90, 120, 135)
RADIUS = 0.30
LP = 5.0
SIGMA_SCALE = float(ARGS[ARGS.index('--sigma') + 1]) if '--sigma' in ARGS else 1.0
SOLVE = {'la': float(ARGS[ARGS.index('--la') + 1]) if '--la' in ARGS else 150.0, 'ls': float(ARGS[ARGS.index('--ls') + 1]) if '--ls' in ARGS else 2.0, 'lf': float(ARGS[ARGS.index('--lf') + 1]) if '--lf' in ARGS else 1.0}


def side_samples(scene, side):
    arm = f"arm_upper.{side}"

    def tail(name):
        return np.array((scene.rig.matrix_world @ scene.rig.pose.bones[name].tail)[:])

    def sign(axis, metric):
        scores = {}
        for s in (1.0, -1.0):
            scene.pose({arm: P.rot(axis, 40 * s)})
            scores[s] = metric()
        scene.pose({})
        return 1.0 if scores[1.0] <= scores[-1.0] else -1.0

    sg = sign(0, lambda: float(tail(arm)[1]))
    fr = sign(2, lambda: -float(tail(arm)[2]))
    train = []
    for a in ANGLES:
        train += [(f"sagittal_{a}", {arm: P.rot(0, sg * a)}), (f"scapulaire_{a}", {arm: P.euler(sg * a * 0.7071, 0, fr * a * 0.7071)}), (f"frontal_{a}", {arm: P.rot(2, fr * a)})]
    train += [("extension_30", {arm: P.rot(0, -sg * 30)}), ("extension_60", {arm: P.rot(0, -sg * 60)}),
              ("rotation_levee90_m60", {arm: P.euler(0, -60, fr * 90)}), ("rotation_levee90_p60", {arm: P.euler(0, 60, fr * 90)})]
    test = []
    for a in (45, 75, 105):
        test += [(f"sagittal_{a}", {arm: P.rot(0, sg * a)}), (f"scapulaire_{a}", {arm: P.euler(sg * a * 0.7071, 0, fr * a * 0.7071)}), (f"frontal_{a}", {arm: P.rot(2, fr * a)})]
    rng = np.random.default_rng(11)
    for i in range(10):
        e, az, ax = rng.uniform(20, 135), rng.uniform(0, 90), rng.uniform(-45, 60)
        test.append((f"aleatoire_{i}", {arm: P.euler(sg * e * math.cos(math.radians(az)), ax, fr * e * math.sin(math.radians(az)))}))
    return train, test


def features(values, arm):
    e = values[arm]
    q = Euler(e, "XYZ").to_quaternion()
    if q.w < 0:
        q = -q
    return np.array([q.x, q.y, q.z])


def main():
    scene = P.Scene("defaut")
    names = scene.bone_names
    n = len(scene.rest)
    dqs = np.zeros(n, bool)
    dqs[[v.index for v in scene.body.data.vertices if any(scene.body.vertex_groups[g.group].name == skeleton.GROUP_DQS for g in v.groups)]] = True
    head_w = scene.W[:, names.index("head")] + scene.W[:, names.index("jaw")]
    locked = head_w > 0.4
    payload = {}
    report = {}
    for side in ("L", "R"):
        arm = f"arm_upper.{side}"
        pivot = scene.head(arm)
        bone = scene.rig.data.bones[arm]
        axis_head, axis_tail = np.array(bone.head_local), np.array(bone.tail_local)
        axis_unit = (axis_tail - axis_head) / np.linalg.norm(axis_tail - axis_head)
        dist = np.linalg.norm(scene.rest - pivot, axis=1)
        free = np.where((dist < RADIUS) & ~dqs)[0]
        fade = np.clip((dist[free] - 0.12) / (RADIUS - 0.12), 0.0, 1.0)
        fade = fade * fade * (3 - 2 * fade)
        pull = LP * 0.2 + 60.0 * LP * fade
        pull = np.where(locked[free], np.maximum(pull, 400.0 * LP), pull)
        region = np.zeros(n, bool)
        region[free] = True
        sections = []
        for d in (0.03, 0.05, 0.08):
            sel = M.section_selection(scene.rest, axis_head, axis_unit, pivot, d)
            if len(sel) >= 8 and region[sel].all():
                sections.append((sel, M.section_area(scene.rest, sel)))
        protect = S.hop_protection(n, scene.edges, locked)[free]
        problem = S.Problem(scene.rest, scene.edges, scene.tris, free, sections, protect, pull)
        train, test = side_samples(scene, side)
        if '--only' in ARGS:
            keep = ARGS[ARGS.index('--only') + 1].split(',')
            train = [t for t in train if t[0] in keep]
            test = [t for t in test if t[0] in keep]
            if side == 'R':
                break
        feats, deltas = [], []
        t0 = time.perf_counter()
        for name, values in train:
            scene.pose(values)
            start = P.evaluate_cage(scene.body)
            target = problem.solve(start, **SOLVE)
            mats = scene.bone_matrices()
            M3 = np.einsum("vb,bij->vij", scene.W[free], mats[:, :3, :3])
            d_pose = (target - start)[free]
            d_rest = np.linalg.solve(M3, d_pose[:, :, None])[:, :, 0]
            feats.append(features(values, arm))
            deltas.append(d_rest)
        print("côté", side, len(free), "sommets libres,", len(train), "cibles en", round(time.perf_counter() - t0), "s", flush=True)
        feats = np.array([np.zeros(3)] + feats)  # exemple de repos (correctif nul) : le poids du repos absorbe la partition de l'unité
        deltas = np.array([np.zeros_like(deltas[0])] + deltas)  # (J, nfree, 3)
        nn = np.linalg.norm(feats[:, None] - feats[None], axis=2)
        np.fill_diagonal(nn, 1e9)
        sigma = SIGMA_SCALE * nn.min(1)
        active = np.where(np.abs(deltas).max(axis=(0, 2)) > 2e-5)[0]
        payload[f"{side}_vertices"] = free[active].astype(np.int32)
        payload[f"{side}_delta"] = deltas[:, active].astype(np.float32)
        payload[f"{side}_features"] = feats
        payload[f"{side}_sigma"] = sigma
        report[side] = {"sommets_actifs": int(len(active)), "delta_max_mm": round(float(np.abs(deltas).max()) * 1000, 1)}
        print("côté", side, report[side], flush=True)
        if "--validate" in ARGS:
            near = M.Region(scene.rest, scene.tris, scene.edges, pivot, 0.14, axis_head, axis_unit, 0.05)
            far = M.Region(scene.rest, scene.tris, scene.edges, pivot, 0.27, axis_head, axis_unit, 0.05)
            face = locked
            rows = {"entrainement": train, "test": test}
            for label, poses in rows.items():
                base_fail, new_fail = [0, 0], [0, 0]
                worst = {"visage_mm": 0.0}
                for name, values in poses:
                    scene.pose(values)
                    start = P.evaluate_cage(scene.body)
                    mats = scene.bone_matrices()
                    w = S.shepard_weights(features(values, arm), feats, sigma)
                    d_rest = np.einsum("k,knj->nj", w, deltas)
                    rest_c = scene.rest.copy()
                    rest_c[free] += d_rest
                    lbs_c = scene.lbs(rest_c, mats)
                    x = start.copy()
                    x[free] = lbs_c[free]
                    rot3 = mats[scene.tri_bone][:, :3, :3]
                    for k, pts in enumerate((start, x)):
                        a, b = near.measure(pts, rot3), far.measure(pts, rot3)
                        bad = bool(M.failures(a)) or b["plis"] > 2 or b["etirement_max"] >= 3
                        if "--debug" in ARGS and side == "L" and label in ("entrainement", "test"):
                            print("  ", label, name, "LBS" if k == 0 else "CORR", "proche", a, M.failures(a), "| large plis", b["plis"], "etir", b["etirement_max"], flush=True)
                        (base_fail if k == 0 else new_fail)[0] += int(bad)
                        (base_fail if k == 0 else new_fail)[1] += int(b["plis"])
                    worst["visage_mm"] = max(worst["visage_mm"], float(np.linalg.norm(x - start, axis=1)[face].max()) * 1000)
                print(f"VALIDATION {side} {label} ({len(poses)} poses) : hors critère {base_fail[0]} -> {new_fail[0]} ; plis zone large cumulés {base_fail[1]} -> {new_fail[1]} ; écart max visage {worst['visage_mm']:.3f} mm", flush=True)
    out = P.OUT
    out.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out / "human_rig_correctives.npz", **payload)
    (out / "correctifs_rapport.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    if "--write" in ARGS and ARGS[ARGS.index("--write") + 1] == "1":
        target = Path(__file__).resolve().parents[1] / "extension" / "data" / "human_rig_correctives.npz"
        np.savez_compressed(target, **payload)
        print("écrit :", target, round(target.stat().st_size / 1024), "Ko")


main()
