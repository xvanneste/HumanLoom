"""Mesure : part des dents du bas VISIBLES de face (rayons horizontaux contre le corps évalué) pour chaque expression.

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/measure_lower_teeth.py -- [--out FICHIER.json]

Un sommet de dent est visible si le rayon parti de l'avant (même x, z) atteint la dent avant la peau. Résultat : fraction par expression, pour 3 morphologies."""
import json
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension import human  # noqa: E402
from extension.animation import dental, face, skeleton  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = ARGS[ARGS.index("--out") + 1] if "--out" in ARGS else None
addon.register()
MORPHOLOGIES = {"neutre": {}, "femme_jeune": {"sex": 1.0, "age": 1.0}, "homme_age": {"sex": 0.0, "age": 3.0}}
POSES = ["expression:neutre", "expression:joie", "expression:sourire_large", "expression:rire"]


def visible_fraction(body, teeth):
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = body.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    tree = BVHTree.FromPolygons([v.co.copy() for v in mesh.vertices], [p.vertices[:] for p in mesh.polygons])
    matrix = body.matrix_world.inverted() @ evaluated.matrix_world
    evaluated.to_mesh_clear()
    count = visible = 0
    for v in teeth.data.vertices:
        point = body.matrix_world.inverted() @ (teeth.matrix_world @ v.co)
        if point.y > -0.02:
            pass
        origin = Vector((point.x, point.y - 0.3, point.z))
        hit = tree.ray_cast(origin, Vector((0, 1, 0)), 0.3 + 0.0005)
        count += 1
        # visible si le premier obstacle est (quasi) au niveau du sommet ou au-delà
        if hit[0] is None or hit[0].y >= point.y - 0.0004:
            visible += 1
    return visible / max(count, 1)


rows = {}
library = face.builtin_poses()
for label, values in MORPHOLOGIES.items():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.ops.humanloom.create()
    body = bpy.context.object
    for name, value in values.items():
        human.set_value(body, name, value)
    skeleton.install(body)
    lower = next(o for o in dental.parts_of(body) if o.name == "HL Dents basses")
    for pid in POSES:
        face.apply_pose(body, library[pid]["pose"])
        rows.setdefault(label, {})[pid] = round(visible_fraction(body, lower) * 100, 2)
print("DENTS_BASSES_VISIBLES_%", json.dumps(rows))
if OUT:
    Path(OUT).write_text(json.dumps(rows, indent=1), encoding="utf-8")
