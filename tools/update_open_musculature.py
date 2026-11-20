"""Upgrade only the active character, preserve its settings, save a sibling file."""

import json
from pathlib import Path

import bpy
from bl_ext.user_default.human_modeling import active_body, character_presets

assert bpy.app.version[:2] == (5, 2)
body = active_body(bpy.context)
assert body is not None
before = character_presets.capture(body)
count = len(bpy.data.objects), len(bpy.data.meshes)
if body.data.get("human_modeling_schema", 0) < 4:
    assert bpy.ops.human_modeling.add_proportions() == {"FINISHED"}
assert character_presets.capture(body) == before
assert count == (len(bpy.data.objects), len(bpy.data.meshes))
assert all(curve.is_valid for curve in body.data.shape_keys.animation_data.drivers)
root = Path(__file__).resolve().parents[1]
output = root / "validation/musculature-09"
(output / "session-migration.json").write_text(json.dumps({"body": body.name,
    "schema": body.data["human_modeling_schema"], "settings_preserved": True,
    "control_count": len(before["controls"]), "no_orphans": True}, indent=2), encoding="utf-8")
if bpy.context.area:
    bpy.context.area.type = "VIEW_3D"

def save_checkpoint():
    bpy.ops.wm.save_as_mainfile(filepath=str(output / "Session-modelisation-09.blend"), compress=True)
    return None

bpy.app.timers.register(save_checkpoint, first_interval=.5)
print("Musculature disponible ; réglages existants conservés.")
