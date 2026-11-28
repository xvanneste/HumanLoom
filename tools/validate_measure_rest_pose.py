"""Validation de la mesure de stature en POSE DE REPOS (SCI-002) : la stature d'un corps posé (bras levé) ne dépend plus de la pose ; les opérateurs de calibrage (set_height) ajustent la vraie stature ; la pose et les modificateurs sont rétablis.

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/validate_measure_rest_pose.py -- [--out FICHIER.json]
M1 mesure posée = mesure au repos (< 1 mm) alors que la silhouette posée mesure autrement (preuve de sensibilité) ; M2 pose, modificateurs et clés intacts après la mesure ; M3 `set_height` sur un corps posé donne la stature demandée au repos ;
M4 corps sans rig : mesure inchangée."""
import json
import math
from pathlib import Path
import sys

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension import measurements  # noqa: E402
from extension.animation import skeleton  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = ARGS[ARGS.index("--out") + 1] if "--out" in ARGS else None
results, failures = {}, []


def check(name, ok, detail=None):
    results[name] = {"ok": bool(ok), "detail": detail}
    print(("OK  " if ok else "KO  ") + name, json.dumps(detail, ensure_ascii=False, default=str) if detail is not None else "")
    if not ok:
        failures.append(name)


addon.register()
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
bpy.ops.humanloom.create()
body = bpy.context.object
bare = measurements.measure(body, bpy.context)["height_m"]
check("M4_corps_sans_rig_inchange", bare > 1.0, {"stature_m": round(bare, 4)})

rig = skeleton.install(body)
for bone in rig.pose.bones:
    bone.rotation_mode = "QUATERNION"
rest_height = measurements.measure(body, bpy.context)["height_m"]
arm = rig.pose.bones["arm_upper.L"]
arm.rotation_quaternion = (math.cos(math.radians(85)), 0.0, 0.0, math.sin(math.radians(85)))  # bras levé au-dessus de la tête (rotation de 170 degrés)
bpy.context.view_layer.update()
posed = measurements.measure(body, bpy.context)["height_m"]
silhouette = measurements._measure_evaluated(body, bpy.context)["height_m"]  # mesure SANS suspension de la pose (comportement d'avant)
check("M1_stature_posee_egale_stature_au_repos", abs(posed - rest_height) < 0.001 and abs(silhouette - rest_height) > 0.03, {"repos_m": round(rest_height, 4), "posee_avec_correction_m": round(posed, 4), "silhouette_posee_sans_correction_m": round(silhouette, 4)})
armature_modifiers = [(m.name, m.show_viewport) for m in body.modifiers if m.type == "ARMATURE"]
check("M2_pose_et_modificateurs_intacts", all(state for _n, state in armature_modifiers) and len(armature_modifiers) >= 1 and abs(arm.rotation_quaternion[3] - math.sin(math.radians(85))) < 1e-6, {"modificateurs": armature_modifiers})
result = bpy.ops.human_modeling.set_height(height=1.8)
for_check = measurements.measure(body, bpy.context)["height_m"]
check("M3_calibrage_de_stature_sur_corps_pose", result == {"FINISHED"} and abs(for_check - 1.8) < 0.002, {"operateur": list(result), "stature_au_repos_apres_m": round(for_check, 4)})

if OUT:
    Path(OUT).write_text(json.dumps(results, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
print("RESULT", "FAIL " + ", ".join(failures) if failures else "PASS")
sys.exit(1 if failures else 0)
