"""Mesure de la rugosité des bords des vêtements (lot « bords dentelés ») : avant (découpe par sommets du corps) / après (bords ramenés sur le plan de coupe puis lissés).

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/measure_garment_edges.py -- [--out FICHIER.json]

Rugosité = moyenne (mm) du désaccord de chaque sommet de bord avec ses deux voisins de bord (écart à leur milieu) : plus c'est petit, plus le bord est net. Mesurée sur 3 morphologies."""
import json
from pathlib import Path
import sys

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension import garments, human  # noqa: E402
from extension.animation import skeleton  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = ARGS[ARGS.index("--out") + 1] if "--out" in ARGS else None
addon.register()
MORPHOLOGIES = {"defaut": {}, "femme_jeune": {"sex": 1.0, "age": 1.0}, "enfant": {"age": 0.0}}
rows = {}
for label, values in MORPHOLOGIES.items():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.ops.humanloom.create()
    body = bpy.context.object
    for name, value in values.items():
        human.set_value(body, name, value)
    skeleton.install(body)
    for key, definition in garments.GARMENTS.items():
        if definition.get("robe"):
            continue
        before = garments.add_garment(body, key, clean_edges=False)
        r0 = garments.border_roughness(before)
        garments.remove_garment(before)
        after = garments.add_garment(body, key)
        r1 = garments.border_roughness(after)
        garments.remove_garment(after)
        rows.setdefault(key, {})[label] = {"avant_mm": round(r0[0], 2), "apres_mm": round(r1[0], 2), "sommets_de_bord_avant_apres": [r0[1], r1[1]]}
summary = {k: {"avant_mm_moyenne": round(sum(v["avant_mm"] for v in d.values()) / len(d), 2), "apres_mm_moyenne": round(sum(v["apres_mm"] for v in d.values()) / len(d), 2)} for k, d in rows.items()}
print("BORDS", json.dumps(summary, ensure_ascii=False))
if OUT:
    Path(OUT).write_text(json.dumps({"detail": rows, "resume": summary}, indent=1, ensure_ascii=False), encoding="utf-8")
