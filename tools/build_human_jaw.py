"""Génère `extension/data/human_jaw_weights.npz` : poids de la mâchoire (os `jaw`) sur la cage native, par RÈGLE GÉOMÉTRIQUE (pas de donnée publiée).

  blender --background --factory-startup --offline-mode --python tools/build_human_jaw.py

Règle (calculée une fois sur la cage du corps par défaut ; la topologie est fixe, les poids valent pour toute morphologie) :
- plan d'occlusion : hauteur de la fente labiale à chaque |x| (paires de sommets lèvre haute / lèvre basse proches et non voisins) ; tout ce qui est SOUS ce plan suit la mâchoire, tout ce
  qui est au-dessus reste sur la tête. Rampe étroite (1 mm) près de la fente pour que les deux lèvres se séparent franchement, large (8 mm) ailleurs (joues, cavité) ;
- estompage vers l'arrière (peau devant l'oreille seulement) et vers le bas (sous le menton, jusqu'à 65 mm sous le gnathion) ;
- les sommets de la fente reçoivent exactement 0 (haut) et 1 (bas).
Tous les paramètres numériques ci-dessous sont PROVISOIRES et propres à ce modèle : aucune valeur n'est tirée d'une publication (D-35 : « non vérifié »)."""
from pathlib import Path
import sys

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension.animation import skeleton  # noqa: E402

import os  # noqa: E402
OUT = Path(os.environ["HL_JAW_OUT"]) if os.environ.get("HL_JAW_OUT") else ROOT / "extension" / "data" / "human_jaw_weights.npz"
WIDE = os.environ.get("HL_JAW_WIDE", "1") == "1"  # estompage large (menton 150 mm, oreille 75 mm) : essai conjoint avec des poids du cou lissés
addon.register()
bpy.ops.humanloom.create()
body = bpy.context.object
P = skeleton.cage_points(body)
mesh = body.data
n = len(P)
neighbors = [set() for _ in range(n)]
for e in mesh.edges:
    a, b = e.vertices
    neighbors[a].add(b)
    neighbors[b].add(a)
top = P[:, 2].max()
slit_ref = (P[skeleton.JAW_SLIT[0], 2] + P[skeleton.JAW_SLIT[1], 2]) / 2
chin_z = P[skeleton.JAW_CHIN, 2]
j = skeleton.joints(P, skeleton.load_anchors())
hinge_y = float(j["jaw_hinge"][1])
# paires de la fente (lèvre haute, lèvre basse)
zone = np.where((np.abs(P[:, 0]) < 0.07) & (P[:, 1] < -0.10) & (P[:, 2] < top - 0.16) & (P[:, 2] > top - 0.20))[0]
D = np.linalg.norm(P[zone][:, None, :] - P[zone][None, :, :], axis=2)
pairs = []
for a, b in zip(*np.where(np.triu(D < 0.0035, 1))):
    u, v = zone[a], zone[b]
    if v in neighbors[u] or (neighbors[u] & neighbors[v]):
        continue
    pairs.append((u, v) if P[u, 2] > P[v, 2] else (v, u))
assert len(pairs) > 50, len(pairs)
upper = {a for a, _ in pairs}
lower = {b for _, b in pairs}
slit_vertices = np.array(sorted(upper | lower))
mid_x = np.array([abs(P[a, 0] + P[b, 0]) / 2 for a, b in pairs])
mid_z = np.array([(P[a, 2] + P[b, 2]) / 2 for a, b in pairs])
order = np.argsort(mid_x)
# hauteur de fente en fonction de |x| : médiane par intervalles de 4 mm, interpolée
edges = np.arange(0, mid_x.max() + 0.004, 0.004)
centers, heights = [], []
for lo, hi in zip(edges[:-1], edges[1:]):
    sel = (mid_x >= lo) & (mid_x < hi)
    if sel.any():
        centers.append((lo + hi) / 2)
        heights.append(float(np.median(mid_z[sel])))


def smooth(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


s = np.interp(np.abs(P[:, 0]), centers, heights)
d_slit = np.min(np.linalg.norm(P[:, None, :] - P[slit_vertices][None, :, :], axis=2), axis=1)
ramp = 0.001 + 0.007 * smooth((d_slit - 0.004) / 0.012)
corner_x = float(np.abs(P[slit_vertices, 0]).max())  # commissure : au-delà, la peau des joues relie les deux lèvres ; une rampe large évite le « rail » tendu entre elles
lateral = smooth((np.abs(P[:, 0]) - (corner_x - 0.014)) / 0.024)  # transition progressive : l'ouverture doit être ovale, pas rectangulaire
ramp = ramp * (1 - lateral) + 0.022 * lateral
w = smooth(0.5 + (s - P[:, 2]) / (2 * ramp))
if WIDE:
    w *= 1.0 - smooth((P[:, 1] - (hinge_y - 0.035)) / 0.075)
    w *= smooth((P[:, 2] - (chin_z - 0.150)) / 0.130)
else:
    w *= 1.0 - smooth((P[:, 1] - (hinge_y - 0.010)) / 0.030)  # estompage vers l'oreille (élargi à 75 mm : la torsion du cou à 45° retournait 190 triangles, R6)
    w *= smooth((P[:, 2] - (chin_z - 0.065)) / 0.055)  # sous le menton : 65 mm (à 100 et 150 mm la torsion du cou à 45°, R6, retournait 190 triangles)
# les sommets de la fente : 0 / 1 au milieu des lèvres, mais les commissures suivent la mâchoire À MOITIÉ (le muscle orbiculaire et les muscles des joues les retiennent) : les deux lèvres
# convergent vers 0,5 au coin, ce qui donne une ouverture en lentille et non un rectangle
ellipse = np.sqrt(np.clip(1.0 - (np.abs(P[:, 0]) / corner_x) ** 2, 0.0, 1.0))  # écart des deux lèvres à x : e(x) = sqrt(1 - (x / x_coin)^2), soit une ouverture en LENTILLE (ellipse)
UPPER_FOLLOW = 0.0  # essayé à 0,12 : la lèvre haute DESCEND avec la mâchoire et recouvre les dents (exposition 3,3 -> -0,6 mm à 20°) : à 0, elle reste en place
for v in upper:
    w[v] = 0.5 - (0.5 - UPPER_FOLLOW) * ellipse[v]
for v in lower:
    w[v] = 0.5 + 0.5 * ellipse[v]
# la peau voisine de la fente est lissée (graphe du maillage, sommets de la fente fixes) pour que le profil elliptique se propage aux lèvres et aux joues sans arête tendue
slit_set = upper | lower
region = [v for v in range(n) if d_slit[v] < 0.03 and v not in slit_set]
for _ in range(60):
    updated = w.copy()
    for v in region:
        near = [w[u] for u in neighbors[v]]
        updated[v] = 0.5 * w[v] + 0.5 * (sum(near) / len(near))
    w = updated
keep = np.where(w > 0.002)[0]
OUT.parent.mkdir(parents=True, exist_ok=True)
np.savez_compressed(OUT, idx=keep.astype(np.int32), w=w[keep].astype(np.float32), slit_upper=np.array(sorted(upper), np.int32), slit_lower=np.array(sorted(lower), np.int32),
                    source=np.array("règle géométrique de tools/build_human_jaw.py ; paramètres provisoires, non vérifiés dans la littérature"))
print("JAW_OK sommets", len(keep), "paires de fente", len(pairs), "poids 1:", int((w > 0.999).sum()), "hauteur de fente (mm sous le sommet)", round((np.interp(0, centers, heights) - top) * 1000, 1))
