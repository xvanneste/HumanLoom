"""Validation d'entrée des API de vêtements et préconditions de mode (audit GRM-016) : valeurs non finies ou hors bornes refusées sans mutation de scène, opérateurs inactifs hors mode Objet, erreurs inattendues traduites au lieu d'un traceback.

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/validate_garment_inputs.py"""
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension import garments  # noqa: E402
from extension.animation import skeleton  # noqa: E402

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
skeleton.install(body, correctives=False)
nan, inf = float("nan"), float("inf")


def snapshot():
    return (sorted(o.name for o in bpy.data.objects), sorted(m.name for m in bpy.data.materials), sorted(m.name for m in bpy.data.meshes))


def refuses(label, call):
    before = snapshot()
    try:
        call()
        outcome = "aucune erreur"
    except ValueError:
        outcome = "ok"
    except Exception as error:  # noqa: BLE001
        outcome = f"{type(error).__name__}: {str(error)[:60]}"
    check(label, outcome == "ok" and snapshot() == before, outcome if outcome != "ok" else "scene inchangee" if snapshot() == before else "scene modifiee")


for bad in (nan, inf, -1.0, 500.0):
    refuses(f"GRM-016 decalage {bad}", lambda bad=bad: garments.add_garment(body, "chemise", offset_mm=bad))
for bad in ((nan, 0, 0), (2.0, 0, 0), (-0.1, 0, 0), (0.5, 0.5), (0.5, 0.5, 0.5, 0.5, 0.5), "rouge", None.__class__):
    refuses(f"GRM-016 couleur {bad}", lambda bad=bad: garments.add_garment(body, "chemise", color=bad))
refuses("GRM-016 piece inconnue", lambda: garments.add_garment(body, "inexistante"))
piece = garments.add_garment(body, "chemise")
before_color = garments.color_of(piece)
for bad in ((nan, 0, 0), (2.0, 0, 0), (0.5, 0.5)):
    try:
        garments.set_color(piece, bad)
        outcome = "aucune erreur"
    except ValueError:
        outcome = "ok"
    except Exception as error:  # noqa: BLE001
        outcome = type(error).__name__
    check(f"GRM-016 set_color {bad}", outcome == "ok" and garments.color_of(piece) == before_color, outcome)
# modes : opérateurs inactifs hors mode Objet
bpy.context.view_layer.objects.active = body
body.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
polls = {name: getattr(bpy.ops.humanloom, name).poll() for name in ("garment_add", "garment_color", "garment_remove", "garment_update", "garment_import") if hasattr(bpy.ops.humanloom, name)}
bpy.ops.object.mode_set(mode="OBJECT")
check("GRM-016 operateurs de vetements inactifs en mode Edition", polls and not any(polls.values()), str(polls))
# erreur inattendue d'une ressource : message d'erreur, pas de traceback
original = garments.add_garment
garments.add_garment = lambda *a, **k: (_ for _ in ()).throw(KeyError("ressource absente"))
try:
    bpy.context.view_layer.objects.active = body
    result = bpy.ops.humanloom.garment_add(piece="pull")
    check("GRM-016 KeyError interne : operation annulee proprement", result == {"CANCELLED"}, str(result))
except RuntimeError as error:  # un rapport {'ERROR'} d'opérateur remonte à bpy.ops sous forme de RuntimeError ; un vrai traceback contient « Traceback »
    check("GRM-016 KeyError interne : operation annulee proprement", "Traceback" not in str(error) and "ressource absente" in str(error), str(error)[:80])
finally:
    garments.add_garment = original
print("RESULTAT", "ECHECS " + ", ".join(FAILURES) if FAILURES else "tout OK")
sys.exit(1 if FAILURES else 0)
