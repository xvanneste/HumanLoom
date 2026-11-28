"""Animation des paramètres par la façade (audit INT-003) : conversion des courbes `humanloom.<nom>` en chemins natifs des sockets, lecture identique SANS l'extension (action active, bande NLA, driver), sans doublon.

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/validate_facade_animation.py"""
import sys
import tempfile
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension import human  # noqa: E402

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
scene = bpy.context.scene
identifier = human.sockets()["shoulders"][0]
identifier_age = human.sockets()["age"][0]
body.humanloom.shoulders = 0.0
body.humanloom.keyframe_insert("shoulders", frame=1)
body.humanloom.shoulders = 1.0
body.humanloom.keyframe_insert("shoulders", frame=21)
body.humanloom.age = 1.0
body.humanloom.keyframe_insert("age", frame=1)
body.humanloom.age = 3.0
body.humanloom.keyframe_insert("age", frame=21)
for curve in bpy.data.actions[0].layers[0].strips[0].channelbags[0].fcurves:
    for point in curve.keyframe_points:
        point.interpolation = "LINEAR"
frames = (1, 3, 5.25, 10, 15.5, 21)
expected = {}
for frame in frames:
    scene.frame_set(int(frame), subframe=frame % 1)
    expected[frame] = (human.get_value(body, "shoulders"), human.get_value(body, "age"))
check("INT-003 reference : la facade anime bien l'epaule", abs(expected[10][0] - 0.45) < 1e-4 and abs(expected[10][1] - 1.9) < 1e-4, str(expected[10]))
convert = getattr(human, "bake_facade_animation", None)
check("INT-003 API de conversion presente", convert is not None)
report = convert(body) if convert else {}
check("INT-003 conversion : 2 courbes converties", report.get("converted") == 2, str(report))
paths = [c.data_path for c in bpy.data.actions[0].layers[0].strips[0].channelbags[0].fcurves]
check("INT-003 plus aucun chemin facade dans l'action", not any(p.startswith("humanloom.") for p in paths), str(paths))
check("INT-003 chemins natifs (pas de doublon)", len(paths) == 2 and len(set(paths)) == 2, str(paths))
if convert:
    again = convert(body)
    check("INT-003 conversion idempotente", again.get("converted") == 0, str(again))
directory = Path(tempfile.mkdtemp(prefix="hl_facade_"))
path = str(directory / "anime.blend")
bpy.ops.wm.save_as_mainfile(filepath=path)
# lecture SANS l'extension : on la desenregistre puis on rouvre le fichier
addon.unregister()
bpy.ops.wm.open_mainfile(filepath=path)
check("INT-003 extension absente : la facade n'existe plus", not hasattr(bpy.types.Object, "humanloom"))
body = next(o for o in bpy.data.objects if "HL Human" in o.modifiers)
modifier = body.modifiers["HL Human"]
worst = 0.0
for frame in frames:
    bpy.context.scene.frame_set(int(frame), subframe=frame % 1)
    got = (float(getattr(modifier.properties.inputs, identifier).value), float(getattr(modifier.properties.inputs, identifier_age).value))
    worst = max(worst, abs(got[0] - expected[frame][0]), abs(got[1] - expected[frame][1]))
check("INT-003 valeurs identiques sans extension (images et sous-images)", worst < 1e-5, f"ecart max {worst:.2e}")
print("RESULTAT", "ECHECS " + ", ".join(FAILURES) if FAILURES else "tout OK")
sys.exit(1 if FAILURES else 0)
