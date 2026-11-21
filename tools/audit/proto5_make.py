import bpy, sys
from pathlib import Path
OUT = Path(sys.argv[-1])
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.human_modeling.create()
b = bpy.context.object
bpy.context.view_layer.objects.active = b
bpy.ops.humanloom.groom_preset(preset="ALL")
b.data.shape_keys["hm_waist"] = 0.6
b.data.shape_keys["human_modeling_age"] = 1.0
b.data.shape_keys.update_tag()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "proto5.blend"))
print("PROTO5_MADE")
