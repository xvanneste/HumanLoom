"""Validation des échelles de préréglage (SCI-005) : une échelle nulle, négative, non finie ou démesurée est REFUSÉE (elle rendait la stature non mesurable et le corps dégénéré) ; une échelle normale passe.

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/validate_preset_scale.py"""
import json
from pathlib import Path
import sys

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension import character_presets  # noqa: E402

addon.register()
bpy.ops.humanloom.create()
body = bpy.context.object
good = character_presets.capture(body)
rows, failures = {}, []
for label, scale in (("nulle", [0.0, 1.0, 1.0]), ("negative", [1.0, -1.0, 1.0]), ("trop_petite", [0.001, 1.0, 1.0]), ("demesuree", [1.0, 1.0, 1000.0]), ("non_finie", [1.0, float("nan"), 1.0]), ("normale", [1.0, 1.2, 0.9]), ("limite_basse", [0.01, 0.01, 0.01])):
    payload = json.loads(json.dumps(good))
    payload["scale"] = scale
    try:
        character_presets.validate(payload)
        accepted = True
    except ValueError:
        accepted = False
    rows[label] = accepted
    expected = label in ("normale", "limite_basse")
    if accepted != expected:
        failures.append(label)
print(("OK  " if not failures else "KO  ") + "S5_echelles_singulieres_refusees", json.dumps(rows, ensure_ascii=False))
print("RESULT", "PASS" if not failures else "FAIL " + ", ".join(failures))
sys.exit(1 if failures else 0)
