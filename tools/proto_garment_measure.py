"""PROTOTYPE JETABLE de mesure (lot V0) : un vêtement « surface décalée » accroché à la topologie fixe du corps, avec les poids de peau du corps, sous poses.

  blender --background --factory-startup --offline-mode --python tools/proto_garment_measure.py -- [--out FICHIER.json]

Principe mesuré : région du corps (sommets dont l'os dominant est dans un ensemble) décalée le long de la normale de `offset` mètres ; au repos et sur toute morphologie le vêtement est
à `offset` de la peau PAR CONSTRUCTION (aucun ajustement à recalculer) ; sous pose (poids du corps, mélange linéaire) on mesure la pénétration dans le corps posé.
Aucun code de production, aucune donnée tierce.
"""
import json
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = ARGS[ARGS.index("--out") + 1] if "--out" in ARGS else None
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension import human  # noqa: E402
from extension.animation import retarget, skeleton  # noqa: E402

addon.register()
weights = np.load(skeleton.WEIGHTS_FILE)
weight_names = [str(n) for n in weights["names"]]
idx, wts = weights["idx"].astype(int), weights["w"].astype(float)
REGIONS = {
    "haut (torse + bras)": lambda n: n.startswith(("spine", "clavicle", "arm_")) or n in ("pelvis",) and False,
    "bas (bassin + jambes)": lambda n: n.startswith(("pelvis", "leg_")),
}
POSES = {"coude 90°": [("arm_lower.L", 0, 90), ("arm_lower.R", 0, 90)], "épaule levée 90°": [("arm_upper.L", 2, 90)], "épaule fléchie 90°": [("arm_upper.L", 0, 90)],
         "genou 90°": [("leg_lower.L", 0, -90)], "hanche 60°": [("leg_upper.L", 0, 60)], "torsion du buste 45°": [("spine.03", 1, 25), ("spine.04", 1, 20)]}
MORPHOLOGIES = {"défaut": {}, "homme âgé": {"sex": 0.0, "age": 3.0}, "femme jeune": {"sex": 1.0, "age": 1.0}, "enfant": {"sex": 0.5, "age": 0.0}, "gabarit modifié": {"sex": 0.0, "age": 2.0, "legs": 1.0, "torso": -1.0}}
OFFSETS = (0.005, 0.010, 0.020)


def lbs(rig, rest_points, pose):
    """Mélange linéaire des poids du corps : points au repos → points posés."""
    count = len(rig.names)
    quat = np.zeros((1, count, 4))
    quat[..., 0] = 1
    for bone, axis, degrees in pose:
        angle = np.radians(degrees) / 2
        q = np.zeros(4)
        q[0] = np.cos(angle)
        q[1 + axis] = np.sin(angle)
        quat[0, rig.index[bone]] = q
    world = retarget.forward_kinematics(rig, np.zeros((1, count, 3)), quat)[0]
    skin = np.einsum("nij,njk->nik", world, np.linalg.inv(rig.rest))  # (N, 4, 4) : repos → posé
    homogeneous = np.hstack([rest_points, np.ones((len(rest_points), 1))])
    out = np.zeros_like(rest_points)
    for slot in range(idx.shape[1]):
        out += wts[:, slot, None] * np.einsum("nij,nj->ni", skin[[rig.index[weight_names[i]] for i in idx[:, slot]]], homogeneous)[:, :3]
    return out


report = {}
for label, values in MORPHOLOGIES.items():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.ops.humanloom.create()
    body = bpy.context.object
    for name, value in values.items():
        human.set_value(body, name, value)
    rig_object = skeleton.install(body)
    rig = retarget.rig_from_armature(rig_object)
    rest = skeleton.cage_points(body)
    mesh = body.data
    mesh.calc_loop_triangles()
    triangles = np.array([t.vertices[:] for t in mesh.loop_triangles])
    face_normals = np.cross(rest[triangles[:, 1]] - rest[triangles[:, 0]], rest[triangles[:, 2]] - rest[triangles[:, 0]])
    normals = np.zeros_like(rest)
    for corner in range(3):
        np.add.at(normals, triangles[:, corner], face_normals)
    normals /= np.linalg.norm(normals, axis=1, keepdims=True) + 1e-18
    dominant = np.array([weight_names[idx[v, np.argmax(wts[v])]] for v in range(len(rest))])
    row = {}
    for region, test in REGIONS.items():
        mask = np.array([test(n) for n in dominant])
        for offset in OFFSETS:
            garment_rest = rest[mask] + normals[mask] * offset
            tree_rest = BVHTree.FromPolygons([Vector(p) for p in rest], [tuple(t) for t in triangles])
            rest_depth = min((Vector(p) - tree_rest.find_nearest(Vector(p))[0]).dot(tree_rest.find_nearest(Vector(p))[1]) for p in garment_rest[::40])
            worst = {}
            for pose_name, pose in POSES.items():
                posed_body = lbs(rig, rest, pose)
                posed_garment = np.zeros_like(rest)
                posed_all = lbs(rig, rest + normals * offset, pose)[mask]
                tree = BVHTree.FromPolygons([Vector(p) for p in posed_body], [tuple(t) for t in triangles])
                depths = []
                for p in posed_all:
                    nearest = tree.find_nearest(Vector(p))
                    sign = 1.0 if (Vector(p) - nearest[0]).dot(nearest[1]) >= 0 else -1.0
                    depths.append(sign * nearest[3])
                depths = np.array(depths)
                worst[pose_name] = {"part_en_penetration_pourcent": round(float((depths < -0.001).mean()) * 100, 2), "profondeur_max_mm": round(float(-depths.min()) * 1000, 1) if depths.min() < 0 else 0.0}
            row[f"{region} · décalage {int(offset * 1000)} mm"] = {"sommets": int(mask.sum()), "distance_au_repos_mm": round(float(rest_depth) * 1000, 2), "poses": worst}
    report[label] = row
    print("PROTO", label, json.dumps({k: {"sommets": v["sommets"], "pire_pose": max(v["poses"].items(), key=lambda kv: kv[1]["profondeur_max_mm"])} for k, v in row.items()}, ensure_ascii=False))
if OUT:
    Path(OUT).write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
print("PROTO_OK")
