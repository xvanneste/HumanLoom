"""Génère les données du rig corps (lot A2) : ancres sur la cage du corps natif et poids de peau, à partir du seul maillage de HumanLoom.

  blender --background --factory-startup --offline-mode --python tools/build_human_rig.py -- [--check]

Écrit `extension/data/human_rig_anchors.json` et `extension/data/human_rig_weights.npz` (aucune donnée tierce : les positions viennent de la cage
neutre et de proportions anthropométriques publiées — Winter, « Biomechanics and Motor Control of Human Movement » : longueurs des segments en
fraction de la stature —, les poids d'une diffusion de chaleur sur le maillage, d'après Baran et Popović 2007 « Automatic Rigging and Animation of
3D Characters »). `--check` ne régénère pas : il recalcule en mémoire et compare aux fichiers existants.
"""
import json
import os
from pathlib import Path
import sys

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension.animation import skeleton  # noqa: E402

CHECK = "--check" in sys.argv
HEAT = float(os.environ.get("HL_RIG_HEAT", 2.4e-5))      # raideur de l'ancrage de chaleur : h = HEAT / d² (d = distance du sommet à l'os le plus proche, en m)
METHOD = os.environ.get("HL_RIG_METHOD", "blender")  # « blender » : liaison automatique par chaleur de Blender (référence) ; « heat » : diffusion maison (essais)
ITERATIONS = int(os.environ.get("HL_RIG_ITERATIONS", 400))
MAX_INFLUENCES = 4

addon.register()
bpy.ops.humanloom.create()
body = bpy.context.object
P = skeleton.cage_points(body)
zmin, zmax = float(P[:, 2].min()), float(P[:, 2].max())
H = zmax - zmin
print("RIG neutre : sommets", len(P), "stature", round(H, 4))


def near(center, radius, mask, plane=None):
    delta = P - center
    if plane is not None:
        along = delta @ plane
        perp = np.linalg.norm(delta - np.outer(along, plane), axis=1)
        return np.nonzero(mask & (perp < radius))[0], along
    return np.nonzero(mask & (np.linalg.norm(delta[:, :2], axis=1) < radius))[0], None


anchors = {}


def add(name, indices, kind="centroid", **extra):
    anchors[name] = {"kind": kind, "vertices": [int(i) for i in indices], **extra}


def horizontal_slab(fraction, half=0.01):
    return np.abs(P[:, 2] - (zmin + fraction * H)) < half * H


# --- colonne, cou, tête ---------------------------------------------------------------------------------------------------------------------------
strip = lambda width: np.abs(P[:, 0]) < width * H
add("spine_0", np.nonzero(horizontal_slab(0.52) & strip(0.08))[0], "back", fraction=0.5)
add("neck_base", np.nonzero(horizontal_slab(0.818, 0.008) & strip(0.04))[0], "mid")
add("head_base", np.nonzero(horizontal_slab(0.86, 0.008) & strip(0.05))[0], "back", fraction=0.62)
add("head_top", np.nonzero(P[:, 2] > zmax - 0.004 * H)[0], "mid")

# --- jambes (gauche = +x) ---------------------------------------------------------------------------------------------------------------------------
for side, sign in (("L", 1.0), ("R", -1.0)):
    s = f".{side}"
    leg = sign * P[:, 0] > 0.02
    for name, fraction, radius in (("ankle", 0.075, 0.07), ("knee", 0.285, 0.09), ("thigh_hi", 0.40, 0.12), ("thigh_lo", 0.34, 0.12)):
        slab = horizontal_slab(fraction) & leg
        center = np.array([P[slab, 0].mean(), P[slab, 1].mean(), zmin + fraction * H])
        for _ in range(4):
            chosen, _ = near(center, radius, slab)
            center = np.array([P[chosen, 0].mean(), P[chosen, 1].mean(), center[2]])
        add(name + s, chosen)
    foot = np.nonzero(leg & (P[:, 2] < zmin + 0.06 * H))[0]
    heel_y, toe_y = P[foot, 1].max(), P[foot, 1].min()
    ball_y = toe_y + 0.27 * (heel_y - toe_y)
    add("ball" + s, foot[(np.abs(P[foot, 1] - ball_y) < 0.012 * H) & (P[foot, 2] < zmin + 0.05 * H)])
    add("toe_tip" + s, foot[np.argsort(P[foot, 1])[:6]])

# --- bras (A-pose) ---------------------------------------------------------------------------------------------------------------------------------
HAND, FOREARM, UPPER = 0.108 * H, 0.146 * H, 0.186 * H  # longueurs de segments (fractions de la stature, Winter)
for side, sign in (("L", 1.0), ("R", -1.0)):
    s = f".{side}"
    arm_mask = (sign * P[:, 0] > 0.25 * H * 0.5) & (P[:, 2] > zmin + 0.3 * H)
    tip_vertex = np.nonzero(arm_mask)[0][np.argmax(sign * P[arm_mask, 0])]
    E = P[tip_vertex]
    shoulder_guess = np.array([sign * 0.10 * H, float(np.median(P[:, 1])), zmin + 0.80 * H])
    d = (E - shoulder_guess) / np.linalg.norm(E - shoulder_guess)
    sets, centers = {}, {}
    for _pass in range(3):
        for name, distance, radius in (("wrist", HAND, 0.05), ("elbow", HAND + FOREARM, 0.06)):
            p = E - d * distance
            for factor in (3.0, 2.2, 1.6, 1.2, 1.0, 1.0):  # rayon dégressif : la direction initiale du bras n'est qu'une estimation
                delta = P - p
                along = delta @ d
                perp = delta - np.outer(along, d)
                chosen = np.nonzero((np.abs(along) < 0.012 * H) & (np.linalg.norm(perp, axis=1) < radius * factor))[0]
                if len(chosen) == 0:
                    raise RuntimeError(f"Aucun sommet de bras trouvé pour {name}{s} (revoir l'estimation initiale)")
                p = p + perp[chosen].mean(0)
            sets[name], centers[name] = chosen, p
        d = (centers["wrist"] - centers["elbow"]) / np.linalg.norm(centers["wrist"] - centers["elbow"])
    for name in sets:
        add(name + s, sets[name])
    # main : bout du majeur, repère de la main, deux côtés des articulations des doigts (côté a = pouce, vers l'avant du personnage)
    along_tip = (P - centers["wrist"]) @ d
    hand = np.nonzero(arm_mask & (along_tip > 0) & (np.linalg.norm((P - centers["wrist"]) - np.outer(along_tip, d), axis=1) < 0.07))[0]
    add("hand_tip" + s, hand[np.argsort(-along_tip[hand])[:8]])
    print('RIG main', side, 'sommets', len(hand), 'E', E.round(3), 'd', d.round(3), 'poignet', centers['wrist'].round(3), 'coude', centers['elbow'].round(3), 'sets', {k: len(v) for k, v in sets.items()})
    perp = (P[hand] - centers["wrist"]) - np.outer(along_tip[hand], d)
    covariance = np.cov(perp.T)
    values, vectors = np.linalg.eigh(covariance)
    lateral = vectors[:, -1] - d * float(vectors[:, -1] @ d)
    lateral /= np.linalg.norm(lateral)
    if lateral[1] > 0:  # le côté « a » regarde vers l'avant du personnage (-y)
        lateral = -lateral
    hand_length = float(along_tip[hand].max())
    zone = hand[(along_tip[hand] > 0.35 * hand_length) & (along_tip[hand] < 0.55 * hand_length)]
    projection = P[zone] @ lateral
    thumb_zone = hand[(along_tip[hand] > 0.10 * hand_length) & (along_tip[hand] < 0.75 * hand_length)]
    add("thumb_tip" + s, thumb_zone[np.argsort(-(P[thumb_zone] @ lateral))[:6]])
    add("hand_side_a" + s, zone[np.argsort(-projection)[:6]])
    add("hand_side_b" + s, zone[np.argsort(projection)[:6]])
    anchors["_upper_length" + s] = {"value": UPPER}

constants = {"clavicle_x": 0.022, "clavicle_y": 0.03, "clavicle_z": 0.02, "ankle_z": 0.04, "shoulder_x": 0.095, "shoulder_y": 0.012, "shoulder_z": 0.805}
positions = skeleton.anchor_positions(P, {"anchors": {k: v for k, v in anchors.items() if not k.startswith("_")}})
constants["hip_k"] = float((0.52 - 0.40) / (0.40 - 0.34))
data = {"version": 1, "stature_neutre_m": round(H, 4), "constants": constants, "anchors": {k: v for k, v in anchors.items() if not k.startswith("_")}}

# --- os et poids de chaleur ---------------------------------------------------------------------------------------------------------------------
joint_points = skeleton.joints(P, data)
table = skeleton.bone_table(joint_points)
names = [b["name"] for b in table]
deformers = [i for i, n in enumerate(names) if "_twist" not in n and n not in skeleton.NON_DEFORMING]
heads = np.array([table[i]["head"] for i in deformers])
tails = np.array([table[i]["tail"] for i in deformers])


mesh = body.data
mesh.calc_loop_triangles()
triangles = np.array([t.vertices[:] for t in mesh.loop_triangles])
face_normals = np.cross(P[triangles[:, 1]] - P[triangles[:, 0]], P[triangles[:, 2]] - P[triangles[:, 0]])
vertex_normals = np.zeros_like(P)
for corner in range(3):
    np.add.at(vertex_normals, triangles[:, corner], face_normals)
vertex_normals /= np.linalg.norm(vertex_normals, axis=1, keepdims=True) + 1e-18
VISIBILITY = float(os.environ.get("HL_RIG_VISIBILITY", 0.2))


def segment_distance(points, a, b):
    """Distance de chaque sommet au segment, et « visibilité » : la direction os → sommet est-elle du côté de la normale de la surface ?
    (un sommet du torse contre le bras regarde vers le bras : il ne « voit » pas l'os du bras ; critère de visibilité de Pinocchio, version peu coûteuse)."""
    ab = b - a
    t = np.clip(((points - a) @ ab) / (ab @ ab + 1e-12), 0.0, 1.0)
    offset = points - (a + np.outer(t, ab))
    length = np.linalg.norm(offset, axis=1)
    facing = np.einsum("ij,ij->i", offset / (length[:, None] + 1e-12), vertex_normals)
    return length, facing


raw = [segment_distance(P, heads[k], tails[k]) for k in range(len(deformers))]
distance = np.stack([r[0] for r in raw], axis=1)
facing = np.stack([r[1] for r in raw], axis=1)
visible_distance = np.where(facing > VISIBILITY, distance, np.inf)
fallback = ~np.isfinite(visible_distance).any(1)
visible_distance[fallback] = distance[fallback]
nearest = visible_distance.argmin(1)
dmin = visible_distance.min(1)
print("RIG visibilité : sommets sans os visible", int(fallback.sum()))
edges = np.array([e.vertices[:] for e in mesh.edges])
N = len(P)
neighbours = [[] for _ in range(N)]
for a, b in edges:
    neighbours[a].append(b)
    neighbours[b].append(a)
width = max(len(n) for n in neighbours)
nbr = np.zeros((N, width), dtype=np.int64)
mask = np.zeros((N, width), dtype=np.float32)
for v, n in enumerate(neighbours):
    nbr[v, :len(n)] = n
    mask[v, :len(n)] = 1.0
degree = mask.sum(1)
h = (HEAT / (dmin + 0.004) ** 2).astype(np.float32)
indicator = np.zeros((N, len(deformers)), dtype=np.float32)
indicator[np.arange(N), nearest] = 1.0
W = indicator.copy()
for _ in range(ITERATIONS):
    summed = (W[nbr] * mask[..., None]).sum(1)
    W = (summed + h[:, None] * indicator) / (degree + h)[:, None]
W /= W.sum(1, keepdims=True)
SMOOTH = int(os.environ.get("HL_RIG_SMOOTH", 0))
for _ in range(SMOOTH):  # lissage final : adoucit les passages brusques entre os voisins (évite les arêtes très étirées au pli)
    mean = (W[nbr] * mask[..., None]).sum(1) / degree[:, None]
    W = 0.5 * W + 0.5 * mean
W /= W.sum(1, keepdims=True)

index = index_of = {n: i for i, n in enumerate(names)}
full = np.zeros((N, len(names)), dtype=np.float32)
for column, bone in enumerate(deformers):
    full[:, bone] = W[:, column]
if METHOD == "blender":
    # Poids par la liaison automatique de Blender (diffusion de chaleur) sur NOTRE maillage et NOS os, os twist exclus (répartis ensuite par rampe) :
    # c'est la mesure de référence de la qualité (cf. rapport A2 : les critères 0 face retournée / étirement 2,0 ne sont atteints par aucune méthode à 90°).
    tmp_data = bpy.data.armatures.new("tmp_rig")
    tmp_rig = bpy.data.objects.new("tmp_rig", tmp_data)
    bpy.context.scene.collection.objects.link(tmp_rig)
    bpy.context.view_layer.objects.active = tmp_rig
    tmp_rig.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    skeleton._set_bones(tmp_rig, table)
    for edit_bone in tmp_data.edit_bones:
        edit_bone.use_deform = "_twist" not in edit_bone.name and edit_bone.name not in skeleton.NON_DEFORMING
    bpy.ops.object.mode_set(mode="OBJECT")
    bench_mesh = bpy.data.meshes.new("tmp_bench")
    bench_mesh.from_pydata([tuple(p) for p in P], [tuple(e.vertices) for e in body.data.edges], [tuple(p.vertices) for p in body.data.polygons])
    bench_mesh.update()
    bench = bpy.data.objects.new("tmp_bench", bench_mesh)
    bpy.context.scene.collection.objects.link(bench)
    for other in bpy.context.view_layer.objects:
        other.select_set(False)
    bench.select_set(True)
    tmp_rig.select_set(True)
    bpy.context.view_layer.objects.active = tmp_rig
    bpy.ops.object.parent_set(type="ARMATURE_AUTO")
    group_names = {g.index: g.name for g in bench.vertex_groups}
    full[:] = 0
    for v in bench_mesh.vertices:
        for g in v.groups:
            full[v.index, index_of[group_names[g.group]]] = g.weight
    sums = full.sum(1, keepdims=True)
    full /= np.where(sums > 0, sums, 1)
    print("RIG poids Blender : sommets sans poids", int((sums[:, 0] == 0).sum()))
# os twist : le poids de l'os de membre est réparti par une rampe en chapeau le long du segment (1/3 et 2/3)
for limb in ("arm_upper", "arm_lower", "leg_upper", "leg_lower"):
    for side in ("L", "R"):
        base = index[f"{limb}.{side}"]
        head, tail = np.array(table[base]["head"]), np.array(table[base]["tail"])
        t = np.clip(((P - head) @ (tail - head)) / ((tail - head) @ (tail - head)), 0.0, 1.0)
        hat1, hat2 = np.maximum(0, 1 - np.abs(t - 1 / 3) * 3), np.maximum(0, 1 - np.abs(t - 2 / 3) * 3)
        original = full[:, base].copy()
        full[:, index[f"{limb}_twist.01.{side}"]] = original * hat1
        full[:, index[f"{limb}_twist.02.{side}"]] = original * hat2
        full[:, base] = original * np.clip(1 - hat1 - hat2, 0, 1)
order = np.argsort(-full, axis=1)[:, :MAX_INFLUENCES]
chosen = np.take_along_axis(full, order, axis=1)
chosen /= chosen.sum(1, keepdims=True)
print("RIG poids : somme", float(chosen.sum(1).min()), float(chosen.sum(1).max()), "influences moyennes", float((chosen > 1e-4).sum(1).mean()),
      "poids max moyen", float(chosen[:, 0].mean()))

if CHECK:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import rig_check
    stored = json.loads(skeleton.ANCHORS_FILE.read_text(encoding="utf-8"))
    old = np.load(skeleton.WEIGHTS_FILE)
    comparison = rig_check.compare(stored["anchors"], data["anchors"], old["names"], old["idx"], old["w"], np.array(names), order, chosen)
    print("RIG vérification :", json.dumps(comparison, ensure_ascii=False)[:2000])
    if not comparison["identique"]:
        print("RIG vérification : DIFFÉRENCE (voir le rapport ci-dessus)", file=sys.stderr)
        sys.exit(1)
elif os.environ.get("HL_RIG_WEIGHTS_OUT"):  # essais de paramètres : poids seulement, vers un fichier temporaire
    np.savez_compressed(os.environ["HL_RIG_WEIGHTS_OUT"], names=np.array(names), idx=order.astype(np.int16), w=chosen.astype(np.float32))
    print("RIG écrit (essai)", os.environ["HL_RIG_WEIGHTS_OUT"])
else:
    skeleton.ANCHORS_FILE.write_text(json.dumps(data, indent=0), encoding="utf-8")
    np.savez_compressed(skeleton.WEIGHTS_FILE, names=np.array(names), idx=order.astype(np.int16), w=chosen.astype(np.float32))
    print("RIG écrit", skeleton.ANCHORS_FILE.stat().st_size, skeleton.WEIGHTS_FILE.stat().st_size, "octets,", len(names), "os")
