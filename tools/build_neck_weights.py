"""Lisse les poids du rig dans une BANDE LARGE autour du cou pour répartir la torsion le long du cou (lot cou) ; produit une COPIE de `human_rig_weights.npz`.

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/build_neck_weights.py -- <entree.npz> <sortie.npz> [--below 70] [--above 10] [--iterations 80] [--half-width 130] [--lambda 0.5]

Constat (tools/diagnose_neck.py, planches de poids) : la peau du cou est surtout pondérée sur les clavicules et la colonne ; la transition vers la tête est étroite, donc une rotation axiale de 60° replie la peau
(5 à 11 triangles retournés, 7 à 44 à 80°). Méthode : pour les sommets dont la hauteur est comprise entre (base du cou - `below` mm) et (hauteur du menton + `above` mm) et |x| < `half-width` mm, les poids (matrice
sommets x os, renormalisée) sont diffusés sur le graphe du maillage (Laplacien, `lambda`, `iterations` pas) ; les sommets hors bande sont des conditions aux limites fixes ; 4 influences au plus. Aucune donnée tierce."""
from pathlib import Path
import sys

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension.animation import skeleton  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:]
SOURCE, OUT = Path(ARGS[0]), Path(ARGS[1])


def option(name, default):
    return float(ARGS[ARGS.index(name) + 1]) if name in ARGS else default


BELOW, ABOVE, ITERATIONS, HALF_WIDTH, LAMBDA = option("--below", 70.0), option("--above", 10.0), int(option("--iterations", 80)), option("--half-width", 130.0), option("--lambda", 0.5)
addon.register()
bpy.ops.humanloom.create()
body = bpy.context.object
points = skeleton.cage_points(body)
anchors = skeleton.load_anchors()
joints = skeleton.joints(points, anchors)
base_z, chin_z = float(joints["P6"][2]), float(points[skeleton.JAW_CHIN, 2])
data = np.load(SOURCE, allow_pickle=False)
names = [str(n) for n in data["names"]]
idx, w = data["idx"], data["w"]
count = len(points)
dense = np.zeros((count, len(names)))
for slot in range(idx.shape[1]):
    dense[np.arange(count), idx[:, slot]] += w[:, slot]
band = (points[:, 2] > base_z - BELOW * 1e-3) & (points[:, 2] < chin_z + ABOVE * 1e-3) & (np.abs(points[:, 0]) < HALF_WIDTH * 1e-3)
edges = np.array([e.vertices[:] for e in body.data.edges])
src = np.concatenate([edges[:, 0], edges[:, 1]])
dst = np.concatenate([edges[:, 1], edges[:, 0]])
degree = np.bincount(src, minlength=count).astype(float)
for _ in range(ITERATIONS):
    total = np.zeros_like(dense)
    np.add.at(total, src, dense[dst])
    mean = total / np.maximum(degree, 1)[:, None]
    dense[band] = (1 - LAMBDA) * dense[band] + LAMBDA * mean[band]
if "--ramp" in ARGS:  # mode « rampe » : poids de la colonne du cou par la HAUTEUR seule (chaque anneau tourne comme un bloc : la torsion est répartie le long du cou), fondus avec les poids d'origine sur les côtés
    index = {n: i for i, n in enumerate(names)}
    z_base, z_mid, z_head = float(joints["P6"][2]), float(joints["neck_mid"][2]), float(joints["head_base"][2])
    length = z_mid - z_base
    nodes = [z_base - length, (z_base + z_mid) / 2, (z_mid + z_head) / 2, z_head + option("--head-ramp", 1.0) * length]
    bones = ["spine.05", "neck.01", "neck.02", "head"]
    x_in, x_out = option("--x-in", 60.0) * 1e-3, option("--x-out", 95.0) * 1e-3
    z = points[:, 2]
    ramp = np.zeros((count, len(names)))
    ramp[z <= nodes[0], index[bones[0]]] = 1.0
    ramp[z >= nodes[-1], index[bones[-1]]] = 1.0
    for k in range(len(nodes) - 1):
        inside = (z > nodes[k]) & (z < nodes[k + 1])
        t = (z[inside] - nodes[k]) / (nodes[k + 1] - nodes[k])
        ramp[inside, index[bones[k]]] = 1 - t
        ramp[inside, index[bones[k + 1]]] = t
    zone = (z > nodes[0] - 0.02) & (z < nodes[-1])
    alpha = np.clip(1 - (np.abs(points[:, 0]) - x_in) / (x_out - x_in), 0.0, 1.0)
    alpha = alpha * zone * (np.clip((z - (nodes[0] - 0.02)) / 0.02, 0, 1))  # fondu vers le bas (les épaules gardent leurs poids)
    dense = alpha[:, None] * ramp + (1 - alpha[:, None]) * dense
dense /= np.maximum(dense.sum(1, keepdims=True), 1e-12)
order = np.argsort(-dense, axis=1)[:, :4]
chosen = np.take_along_axis(dense, order, axis=1)
chosen /= chosen.sum(1, keepdims=True)
np.savez_compressed(OUT, names=np.array(names), idx=order.astype(np.int16), w=chosen.astype(np.float32))
print("NECK_WEIGHTS_OK sommets dans la bande", int(band.sum()), "base_z_mm", round(base_z * 1000), "menton_z_mm", round(chin_z * 1000), "options", BELOW, ABOVE, ITERATIONS, HALF_WIDTH, LAMBDA)
