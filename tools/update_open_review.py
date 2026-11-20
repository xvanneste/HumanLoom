"""Apply the tested maintenance correction and checkpoint the open review copy."""

from datetime import datetime
from pathlib import Path

import bpy
from bl_ext.user_default.human_modeling import active_body, character_presets, geometry_quality


root = Path(__file__).resolve().parents[1]
body = active_body(bpy.context)
assert body is not None
state = character_presets.capture(body)
assert bpy.ops.human_modeling.repair_surface() == {"FINISHED"}
assert character_presets.capture(body) == state
assert bpy.ops.human_modeling.check_geometry() == {"FINISHED"}
report = geometry_quality.report(body, bpy.context)
assert report["geometry"]["intersections"]["crossing_triangle_pairs"] == 0
character_presets.write_json(root / "validation/qualite-08/controle-session-interface.json", report)
destination = root / "validation/qualite-08/Session-modelisation-08.blend"
if destination.exists():
    destination = destination.with_stem(destination.stem + "-" + datetime.now().strftime("%Y%m%d-%H%M%S"))


def save_checkpoint():
    bpy.ops.wm.save_as_mainfile(filepath=str(destination), compress=True)
    return None


bpy.context.area.type = "VIEW_3D"
bpy.app.timers.register(save_checkpoint, first_interval=.3)
