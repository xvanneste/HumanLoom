"""Formes faciales cuites : le maillage exporté conserve UV, matériaux, indices de faces et attributs (audit ANI-011).

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/validate_face_bake_mesh.py"""
import re
import sys
import tempfile
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension.animation import face  # noqa: E402

addon.register()
FAILURES = []


def check(label, condition, detail=""):
    print(("OK   " if condition else "ECHEC"), label, detail, flush=True)
    if not condition:
        FAILURES.append(label)


for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
bpy.ops.humanloom.create()
body = bpy.context.object
source = body.data
for index, color in enumerate(((0.8, 0.2, 0.2, 1), (0.2, 0.2, 0.8, 1))):
    material = bpy.data.materials.new(f"Peau test {index}")
    material.diffuse_color = color
    source.materials.append(material)
for polygon in source.polygons:
    polygon.material_index = polygon.index % 2
exported, report = face.bake_shapes(body)
mesh = exported.data
check("ANI-011 meme topologie", len(mesh.vertices) == len(source.vertices) and len(mesh.polygons) == len(source.polygons) and len(mesh.loops) == len(source.loops))
check("ANI-011 sources non vides (UV, materiaux)", len(source.uv_layers) > 0 and len(source.materials) > 0, f"UV {len(source.uv_layers)}, materiaux {len(source.materials)}")
check("ANI-011 calques UV conserves", [u.name for u in mesh.uv_layers] == [u.name for u in source.uv_layers])
if source.uv_layers and mesh.uv_layers:
    a = np.array([d.uv[:] for d in source.uv_layers.active.data]); b = np.array([d.uv[:] for d in mesh.uv_layers.active.data]) if len(mesh.uv_layers) else np.zeros(0)
    check("ANI-011 coordonnees UV identiques (ordre des loops)", a.shape == b.shape and float(np.abs(a - b).max()) < 1e-7)
else:
    check("ANI-011 coordonnees UV identiques (ordre des loops)", False, "aucun UV")
check("ANI-011 emplacements de materiaux conserves", [m.name if m else None for m in mesh.materials] == [m.name if m else None for m in source.materials])
check("ANI-011 indices de materiaux par face identiques", [p.material_index for p in mesh.polygons] == [p.material_index for p in source.polygons])
compatible = [a.name for a in source.attributes if not a.name.startswith(".") and a.domain in ("POINT", "FACE", "CORNER", "EDGE") and a.name not in ("position", ".edge_verts", ".corner_vert", ".corner_edge") and not a.is_internal and not re.fullmatch(r"b(_u)?\d+", a.name)]
missing = [n for n in compatible if n not in mesh.attributes and n not in [u.name for u in mesh.uv_layers]]
check("ANI-011 attributs compatibles conserves", not missing, str(missing[:5]))
check("ANI-011 formes presentes", len(mesh.shape_keys.key_blocks) > 10, str(len(mesh.shape_keys.key_blocks)))
directory = Path(tempfile.mkdtemp(prefix="hl_bake_"))
path = str(directory / "visage.glb")
try:
    for o in bpy.context.view_layer.objects:
        o.select_set(o is exported)
    bpy.ops.export_scene.gltf(filepath=path, use_selection=True, export_morph=True)
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    imported = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
    data = imported[0].data if imported else None
    check("ANI-011 glTF reimporte : UV et materiaux", data is not None and len(data.uv_layers) > 0 and len(data.materials) > 0 and data.shape_keys is not None and len(data.shape_keys.key_blocks) > 10,
          "" if data is None else f"UV {len(data.uv_layers)}, mat {len(data.materials)}, formes {len(data.shape_keys.key_blocks) if data.shape_keys else 0}")
except Exception as error:  # noqa: BLE001
    check("ANI-011 glTF reimporte : UV et materiaux", False, f"{type(error).__name__}: {error}"[:200])
print("RESULTAT", "ECHECS " + ", ".join(FAILURES) if FAILURES else "tout OK")
sys.exit(1 if FAILURES else 0)
