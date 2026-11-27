"""Symétrise les poids de peau stockés du rig (`extension/data/human_rig_weights.npz`) : les poids du côté GAUCHE (x > 0) sont reportés sur le côté DROIT (x < 0) par la correspondance de sommets miroir (la topologie est fixe et symétrique),
os gauches ↔ droits échangés ; les sommets de la ligne médiane sont symétrisés (moyenne d'un sommet et de son image avec os échangés). Les poids d'origine donnaient jusqu'à 50 mm d'écart gauche/droite (mesuré : 288 sommets de la tête/mâchoire
portaient de la clavicule à gauche contre 400 à droite).

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/mirror_rig_weights.py -- [--check] [--out FICHIER.npz]
`--check` : n'écrit rien, affiche l'asymétrie avant/après. Sans `--out` : réécrit `extension/data/human_rig_weights.npz` (retour arrière : `git checkout -- extension/data/human_rig_weights.npz` ; garder VERSION et les poids ensemble).
Au plus 4 influences par sommet (conservé), poids normalisés."""
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Vector, kdtree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension.animation import skeleton  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
CHECK = "--check" in ARGS
OUT = Path(ARGS[ARGS.index("--out") + 1]) if "--out" in ARGS else skeleton.WEIGHTS_FILE
addon.register()
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
bpy.ops.humanloom.create()
body = bpy.context.object
points = skeleton.cage_points(body).astype(np.float64)
data = np.load(skeleton.WEIGHTS_FILE, allow_pickle=False)
names = [str(n) for n in data["names"]]
idx, w = data["idx"].astype(np.int64), data["w"].astype(np.float64)
n = len(points)
index = {name: i for i, name in enumerate(names)}


def swapped(name):
    if name.endswith(".L"):
        return name[:-2] + ".R"
    if name.endswith(".R"):
        return name[:-2] + ".L"
    return name


swap = np.array([index[swapped(name)] for name in names])
dense = np.zeros((n, len(names)))
for slot in range(idx.shape[1]):
    np.add.at(dense, (np.arange(n), idx[:, slot]), w[:, slot])

tree = kdtree.KDTree(n)
for i, p in enumerate(points):
    tree.insert(Vector(p), i)
tree.balance()
mirror = np.empty(n, np.int64)
gap = np.empty(n)
for i, p in enumerate(points):
    _co, j, distance = tree.find(Vector((-p[0], p[1], p[2])))
    mirror[i], gap[i] = j, distance
print("ECART MIROIR (mm) : max", round(gap.max() * 1000, 2), "; > 1 mm :", int((gap > 1e-3).sum()), "; involutif :", bool((mirror[mirror] == np.arange(n)).all()), "; non involutifs :", int((mirror[mirror] != np.arange(n)).sum()))
assert gap.max() < 6e-3, "maillage non symétrique"



def asymmetry(matrix):
    return float(np.abs(matrix - matrix[mirror][:, swap]).max()), int((np.abs(matrix - matrix[mirror][:, swap]).max(1) > 1e-3).sum())


before = asymmetry(dense)
left = points[:, 0] > 2e-3
out = dense.copy()
right = points[:, 0] < -2e-3
out[right] = dense[mirror[right]][:, swap]
centre = ~(left | right)
out[centre] = 0.5 * (dense[centre] + dense[mirror[centre]][:, swap])
after = asymmetry(out)
print("ASYMETRIE max (poids), sommets > 1e-3 : avant", before, "après", after, "; sommets droite/gauche/centre", int(right.sum()), int(left.sum()), int(centre.sum()), "; écart miroir max (mm)", round(gap.max() * 1000, 4))
print("SYMETRIE OK" if after[1] == 0 else "SYMETRIE RESIDUELLE", after)

new_idx = np.zeros_like(idx)
new_w = np.zeros_like(w)
for v in range(n):
    order = np.argsort(-out[v])[: idx.shape[1]]
    keep = order[out[v, order] > 1e-9]
    total = out[v].sum()
    weights = out[v, keep]
    weights = weights * (total / weights.sum()) if weights.sum() > 0 else weights
    new_idx[v, : len(keep)] = keep
    new_w[v, : len(keep)] = weights
    new_idx[v, len(keep):] = keep[0] if len(keep) else 0
lost = np.abs(out - np.array([np.bincount(new_idx[v], weights=new_w[v], minlength=len(names)) for v in range(n)])).max()
print("perte de troncature à 4 influences (poids max) :", float(lost))
if CHECK:
    print("MIRROR CHECK seulement : rien écrit")
else:
    np.savez_compressed(OUT, names=np.array(names), idx=new_idx.astype(np.int16), w=new_w.astype(np.float32), mirror=mirror.astype(np.int32))  # `mirror` : sommet miroir (x → −x) de chaque sommet, pour symétriser les calculs géométriques du rig
    print("ECRIT", OUT)
