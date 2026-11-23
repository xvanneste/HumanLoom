"""Prototype jetable (lot paupières / I-49) : les croisements de triangles de la tête (paupières, commissures) peuvent-ils être levés par un LISSAGE LOCAL (Laplacien) des sommets concernés, avec un déplacement faible ?

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/proto_unfold_head_crossings.py -- [--out FICHIER.json]

Pour une grille de 5 sexes x 7 âges (contrôles à 0) : cage évaluée, paires de triangles qui se croisent dans la tête (z > 1,3 m ; les 31 des pieds sont hors sujet), sommets concernés + 2 anneaux voisins,
lissage (λ = 0,5, jusqu'à 300 itérations) tant qu'il reste des croisements dans la tête. Rapporte : croisements avant / après, déplacement maximal (mm), nombre de sommets touchés. Aucune donnée n'est
modifiée : c'est une mesure de faisabilité (une correction par couches interpolées en dépendrait)."""
import json
from pathlib import Path
import sys

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension import geometry_quality, human  # noqa: E402
from extension.animation import skeleton  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = ARGS[ARGS.index("--out") + 1] if "--out" in ARGS else None
addon.register()
bpy.ops.humanloom.create()
body = bpy.context.object
mesh = body.data
mesh.calc_loop_triangles()
triangles = np.array([t.vertices[:] for t in mesh.loop_triangles])
neighbors = [set() for _ in range(len(mesh.vertices))]
for e in mesh.edges:
    a, b = e.vertices
    neighbors[a].add(b)
    neighbors[b].add(a)


def head_pairs(points):
    result = geometry_quality.intersections(points, triangles)
    pairs = [p for p in result["sample_triangle_pairs"] if points[triangles[list(p)].reshape(-1)].mean(0)[2] > 1.3]
    return pairs, result["crossing_triangle_pairs"]


def cage(sex, age):
    for name in human.sockets():
        if name not in ("sex", "age"):
            human.set_value(body, name, 0.0)
    human.set_value(body, "sex", sex)
    human.set_value(body, "age", age)
    return skeleton.cage_points(body)


rows = []
for sex in (0.0, 0.25, 0.5, 0.75, 1.0):
    for age in (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0):
        points = cage(sex, age)
        pairs, total = head_pairs(points)
        row = {"sexe": sex, "age": age, "croisements_tete_avant": len(pairs)}
        if pairs:
            seed = {int(v) for p in pairs for t in p for v in triangles[t]}
            region = set(seed)
            for _ in range(2):
                region |= {n for v in list(region) for n in neighbors[v]}
            region = sorted(region)
            moved = points.copy()
            iterations = 0
            for iterations in range(1, 301):
                updated = moved.copy()
                for v in region:
                    mean = np.mean([moved[n] for n in neighbors[v]], axis=0)
                    updated[v] = moved[v] + 0.5 * (mean - moved[v])
                moved = updated
                if iterations % 10 == 0 and not head_pairs(moved)[0]:
                    break
            after = len(head_pairs(moved)[0])
            row.update({"croisements_tete_apres": after, "iterations": iterations, "sommets_touches": len(region), "deplacement_max_mm": round(float(np.linalg.norm(moved - points, axis=1).max()) * 1000, 2)})
        rows.append(row)
        print("PROTO", json.dumps(row, ensure_ascii=False))
if OUT:
    Path(OUT).write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
