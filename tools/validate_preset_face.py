"""Commandes faciales dans le format personnage et le rapport de mesure (audit SCI-001).

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/validate_preset_face.py"""
import sys
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension import character_presets as presets, human, measurements  # noqa: E402
from extension.animation import skeleton  # noqa: E402
from extension.proportions import FACE_COMMANDS  # noqa: E402

addon.register()
FAILURES = []
COMMANDS = [c for c in FACE_COMMANDS if c != "mouth_open"]


def check(label, condition, detail=""):
    print(("OK   " if condition else "ECHEC"), label, detail, flush=True)
    if not condition:
        FAILURES.append(label)


def fresh():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.ops.humanloom.create()
    return bpy.context.object


def points(body):
    evaluated = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    result = np.array([v.co[:] for v in mesh.vertices])
    evaluated.to_mesh_clear()
    return result


def setup_face(body):
    for index, name in enumerate(COMMANDS):
        human.set_value(body, name, 0.15 + 0.8 * ((index * 7) % 10) / 10)
    bpy.context.view_layer.update()


def face(body):
    return {name: human.get_value(body, name) for name in COMMANDS}


def close(a, b, tol=1e-5):
    return all(abs(a[k] - b[k]) < tol for k in a)


def reset_face(body):
    for name in COMMANDS:
        human.set_value(body, name, 0.0)
    bpy.context.view_layer.update()


for rigged in (False, True):
    tag = "avec rig" if rigged else "sans rig"
    body = fresh()
    if rigged:
        skeleton.install(body, correctives=False)
    setup_face(body)
    expected, shape = face(body), points(body)
    try:
        payload = presets.capture(body)
    except Exception as error:  # noqa: BLE001
        payload = {}
        check(f"SCI-001 {tag} : capture", False, str(error))
    commands = payload.get("facial_commands")
    check(f"SCI-001 {tag} : toutes les commandes exportees", isinstance(commands, dict) and set(commands) == set(COMMANDS), str(sorted(set(COMMANDS) - set(commands or {}))[:4]))
    reset_face(body)
    try:
        presets.apply(body, payload)
    except Exception as error:  # noqa: BLE001
        check(f"SCI-001 {tag} : application", False, str(error))
    bpy.context.view_layer.update()
    check(f"SCI-001 {tag} : valeurs restaurees", close(face(body), expected))
    check(f"SCI-001 {tag} : geometrie restauree", float(np.abs(points(body) - shape).max()) < 1e-5)
    report = measurements.report(body, bpy.context)
    check(f"SCI-001 {tag} : rapport de mesure avec commandes", isinstance(report["model"].get("facial_commands"), dict) and close(report["model"].get("facial_commands", {}), expected) if isinstance(report["model"].get("facial_commands"), dict) else False)

body = fresh()
setup_face(body)
payload = presets.capture(body)
legacy = {k: v for k, v in payload.items() if k != "facial_commands"}
reset_face(body)
human.set_value(body, "smile_L", 0.4)
try:
    presets.apply(body, legacy)
    ok = abs(human.get_value(body, "smile_L") - 0.4) < 1e-6
except Exception as error:  # noqa: BLE001
    ok = False
check("SCI-001 version 1 sans bloc facial : rétrolecture sans toucher au visage", ok)
bad = dict(payload, facial_commands=dict(payload.get("facial_commands", {}), inconnue=0.5))
try:
    presets.validate(bad)
    refused = False
except ValueError:
    refused = True
check("SCI-001 commande inconnue : refus", refused)
bad = dict(payload, facial_commands=dict(payload.get("facial_commands", {}), smile_L=3.0))
try:
    presets.validate(bad)
    refused = False
except ValueError:
    refused = True
check("SCI-001 valeur hors bornes : refus", refused)
body_state = face(body)
try:
    presets.apply(body, dict(payload, facial_commands=dict(payload.get("facial_commands", {}), smile_L=float("nan"))))
    refused = False
except ValueError:
    refused = True
check("SCI-001 NaN : refus sans mutation", refused and close(face(body), body_state))
reset_face(body)
presets.apply(body, payload, factor=0.5)
half = face(body)
check("SCI-001 intensite 0.5 : interpolation des commandes", all(abs(half[k] - 0.5 * payload["facial_commands"][k]) < 1e-5 for k in COMMANDS), str(max(abs(half[k] - 0.5 * payload["facial_commands"][k]) for k in COMMANDS)))
print("RESULTAT", "ECHECS " + ", ".join(FAILURES) if FAILURES else "tout OK")
sys.exit(1 if FAILURES else 0)
