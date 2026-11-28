"""Validation du garde d'unicité des UUID après REMPLACEMENT d'objet à nombre constant (INT-002) : copier un humain et supprimer un autre dans la même opération laisse le nombre d'objets inchangé ; le garde (qui ne regardait que ce nombre)
manquait le doublon d'UUID.

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/validate_uuid_replacement.py"""
import json
from pathlib import Path
import sys

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension import human  # noqa: E402

addon.register()
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
bpy.ops.humanloom.create()
first = bpy.context.object
bpy.ops.humanloom.create()
second = bpy.context.object
human.mark_objects_current()
count_before = len(bpy.data.objects)
copy = first.copy()  # même UUID que `first`
bpy.context.scene.collection.objects.link(copy)
bpy.data.objects.remove(second, do_unlink=True)  # nombre d'objets identique à celui d'avant
same_count = len(bpy.data.objects) == count_before
duplicated = copy.humanloom.uuid == first.humanloom.uuid
human._on_depsgraph(bpy.context.scene)
uuids = [o.humanloom.uuid for o in bpy.data.objects if o.humanloom.is_human]
ok = same_count and duplicated and len(uuids) == len(set(uuids)) and len(uuids) >= 2
print(("OK  " if ok else "KO  ") + "I2_uuid_unique_apres_remplacement_a_nombre_constant", json.dumps({"nombre_constant": same_count, "doublon_avant": duplicated, "uuid_uniques_apres": len(set(uuids)) == len(uuids), "humains": len(uuids)}))
print("RESULT", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
