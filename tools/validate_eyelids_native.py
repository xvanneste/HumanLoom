"""Correction des paupières internes sur le corps NATIF (lot F0-a) : remplace `validate_surface_fix` (OBSOLÈTE : asset de l'ancien moteur non reproductible).

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/validate_eyelids_native.py -- [--out FICHIER.json]

Le corps natif est construit sur la base déjà corrigée ; le critère est mesuré sur la cage évaluée : zéro paire de triangles qui se croisent (hors triangles partageant un sommet)
AUTOUR DES YEUX (rayon 3 cm), sur cinq morphologies, aux extrêmes d'âge et avec les contrôles de paupières et de regard poussés à ±1. Les amplitudes du lot 4 sont incluses.
Les autres croisements de la cage (pieds : 31 en permanence ; tête hors des yeux : jusqu'à 49 pour un homme de 3 d'âge) sont RAPPORTÉS comme constats, pas comptés ici : ils ne sont pas des paupières.
"""
import json
from pathlib import Path
import sys

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = ARGS[ARGS.index("--out") + 1] if "--out" in ARGS else None
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension import geometry_quality, human  # noqa: E402
from extension.animation import skeleton  # noqa: E402

addon.register()
bpy.ops.humanloom.create()
body = bpy.context.object
mesh = body.data
mesh.calc_loop_triangles()
triangles = np.array([t.vertices[:] for t in mesh.loop_triangles])
rows = []
failures = []
cases = [("défaut", {}), ("homme âgé", {"sex": 0.0, "age": 3.0}), ("femme jeune", {"sex": 1.0, "age": 1.0}), ("enfant", {"sex": 0.5, "age": 0.0}), ("sexe 1 âge 3", {"sex": 1.0, "age": 3.0})]
for control in ("eyelid_aperture", "eye_height", "eye_spacing", "brow"):
    if human.has_control(body, control):
        for sign in (1.0, -1.0):
            cases.append((f"{control} {sign:+.0f}", {"sex": 0.5, "age": 2.0, control: sign}))
for label, values in cases:
    for name in list(human.sockets()):
        if name not in ("sex", "age"):
            human.set_value(body, name, 0.0)
    human.set_value(body, "sex", 0.5)
    human.set_value(body, "age", 2.0)
    for name, value in values.items():
        human.set_value(body, name, value)
    points = skeleton.cage_points(body)
    result = geometry_quality.intersections(points, triangles)
    head = result.get("approximate_regions", {}).get("head", 0)
    centers = np.array([[float(v) for v in points[triangles[list(pair)].reshape(-1)].mean(0)] for pair in result["sample_triangle_pairs"]]).reshape(-1, 3)
    eye_positions = []
    for eye in skeleton.eyes_of(body):
        eye_mesh = eye.data
        eye_positions.append(np.mean([np.array(eye.matrix_world @ v.co) for v in eye_mesh.vertices], axis=0))
    near_eyes = int(sum(1 for c in centers if any(np.linalg.norm(c - e) < 0.03 for e in eye_positions)))
    rows.append({"cas": label, "croisements_total": result["crossing_triangle_pairs"], "croisements_tete": head, "croisements_a_moins_de_3_cm_d_un_oeil": near_eyes})
    if near_eyes != 0:
        failures.append(label)
    print("PAUPIERES", json.dumps(rows[-1], ensure_ascii=False))
ok = not failures
print(("OK  " if ok else "KO  ") + "P1_zero_croisement_sur_la_cage_native", {"cas": len(rows), "en_echec": failures})
if OUT:
    Path(OUT).write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
print("RESULT", "PASS" if ok else "FAIL " + ", ".join(failures))
sys.exit(0 if ok else 1)
