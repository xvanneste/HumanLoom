"""Test d'intérieur des vêtements importés (audit GRM-014) : références analytiques (sphère, solide en L concave), maillage ouvert, normales inversées, triangle traversant sans sommet intérieur, rapport avant/après.

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/validate_garment_inside.py"""
import math
import sys
from pathlib import Path

import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import extension  # noqa: E402,F401
from extension import garments  # noqa: E402

FAILURES = []


def check(label, condition, detail=""):
    print(("OK   " if condition else "ECHEC"), label, detail, flush=True)
    if not condition:
        FAILURES.append(label)


def sphere(radius=1.0, rings=24, segments=36, flip=False):
    pts = [[0, 0, radius]]
    for i in range(1, rings):
        phi = math.pi * i / rings
        for j in range(segments):
            theta = 2 * math.pi * j / segments
            pts.append([radius * math.sin(phi) * math.cos(theta), radius * math.sin(phi) * math.sin(theta), radius * math.cos(phi)])
    pts.append([0, 0, -radius])
    tris = [[0, 1 + j, 1 + (j + 1) % segments] for j in range(segments)]
    for i in range(rings - 2):
        for j in range(segments):
            a, b = 1 + i * segments + j, 1 + i * segments + (j + 1) % segments
            c, d = a + segments, b + segments
            tris += [[a, c, b], [b, c, d]]
    last = len(pts) - 1
    tris += [[last, 1 + (rings - 2) * segments + (j + 1) % segments, 1 + (rings - 2) * segments + j] for j in range(segments)]
    tris = np.array(tris)
    if flip:
        tris = tris[:, ::-1]
    return np.array(pts), tris


def box_mesh(lo, hi):
    (x0, y0, z0), (x1, y1, z1) = lo, hi
    v = [[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0], [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]]
    f = [[0, 2, 1], [0, 3, 2], [4, 5, 6], [4, 6, 7], [0, 1, 5], [0, 5, 4], [1, 2, 6], [1, 6, 5], [2, 3, 7], [2, 7, 6], [3, 0, 4], [3, 4, 7]]
    return np.array(v, float), np.array(f)


def combine(a, b):
    """Réunion de deux boîtes disjointes en surface (L) : on les juxtapose en recouvrement partiel -> surface auto-intersectée volontairement évitée ; utilisée comme solide en L via test analytique par union."""
    return np.vstack([a[0], b[0]]), np.vstack([a[1], b[1] + len(a[0])])


def tree_of(points, tris):
    return BVHTree.FromPolygons([Vector(p) for p in points], [tuple(t) for t in tris])


rng = np.random.default_rng(4)
points, tris = sphere()
tree = tree_of(points, tris)
samples = rng.uniform(-1.4, 1.4, (600, 3))
samples = samples[np.abs(np.linalg.norm(samples, axis=1) - 1.0) > 0.03]
truth = np.linalg.norm(samples, axis=1) < 1.0
check("GRM-014 fermeture detectee sur la sphere", garments.mesh_is_closed(tris))
flags = np.array(garments.inside_flags(tree, [Vector(p) for p in samples]))
check("GRM-014 sphere : classification = reference analytique", bool((flags == truth).all()), f"{int((flags != truth).sum())} ecarts / {len(samples)}")
flipped_points, flipped_tris = sphere(flip=True)
flags = np.array(garments.inside_flags(tree_of(flipped_points, flipped_tris), [Vector(p) for p in samples]))
check("GRM-014 normales inversees : classification inchangee", bool((flags == truth).all()), f"{int((flags != truth).sum())} ecarts")
# solide concave : deux boîtes qui se recouvrent forment un L ; chaque boîte reste fermée, l'intérieur est leur union
body = combine(box_mesh((0, 0, 0), (3, 1, 1)), box_mesh((0, 2, 0), (1, 3, 1)))  # deux branches disjointes d'un U : l'espace entre elles est EXTERIEUR (concavité)
concave = tree_of(*body)
queries = [Vector(p) for p in ([0.5, 1.5, 0.5], [2.0, 1.5, 0.5], [0.5, 0.5, 0.5], [0.5, 2.5, 0.5], [2.5, 0.5, 0.5], [0.5, 1.5, 1.5], [3.5, 0.5, 0.5])]
expected = [False, False, True, True, True, False, False]
check("GRM-014 concavite : point dans l'entre-deux = exterieur", garments.inside_flags(concave, queries) == expected, str(garments.inside_flags(concave, queries)))
# maillage ouvert : sphere sans son hemisphere sud
open_tris = tris[[i for i, t in enumerate(tris) if points[t][:, 2].mean() > 0]]
check("GRM-014 maillage ouvert : declare non ferme", not garments.mesh_is_closed(open_tris))
# triangle traversant : triangle de vetement dont les 3 sommets sont exterieurs mais qui coupe une sphere
outside = np.array([[-2.0, -0.2, 0.0], [2.0, -0.2, 0.0], [0.0, 2.0, 0.0]])
crossing = garments.crossing_triangles(tree, outside, np.array([[0, 1, 2]]))
check("GRM-014 triangle traversant sans sommet interieur : detecte", crossing == [0], str(crossing))
away = outside + np.array([0.0, 0.0, 3.0])
check("GRM-014 triangle eloigne : non signale", garments.crossing_triangles(tree, away, np.array([[0, 1, 2]])) == [])
print("RESULTAT", "ECHECS " + ", ".join(FAILURES) if FAILURES else "tout OK")
sys.exit(1 if FAILURES else 0)
