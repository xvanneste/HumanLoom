import bpy, sys, json
import numpy as np
from pathlib import Path
OUT = Path(sys.argv[-1])
R = {}
bpy.ops.wm.open_mainfile(filepath=str(OUT / "proto1b.blend"))
saved = json.loads((OUT / "proto1b.json").read_text(encoding="utf-8"))["saved"]

def coords(b):
    b.data.shape_keys.update_tag()
    bpy.context.view_layer.update()
    e = b.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = e.to_mesh()
    a = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", a)
    e.to_mesh_clear()
    return a

R["facade_registered_in_this_session"] = hasattr(bpy.types.Object, "hlface")
for label in ("C", "D"):
    o = bpy.data.objects[saved[label]]
    ks = o.data.shape_keys
    inv = sum(1 for d in ks.animation_data.drivers if not d.driver.is_valid)
    base = coords(o)
    if label == "C":
        o["hl_shoulders"] = -0.8
    else:
        ks["hm_shoulders"] = -0.8
    R[label] = {"invalid_drivers": inv, "responds_mm": round(float(np.abs(coords(o) - base).max()) * 1000, 3), "custom_prop_value_kept": o.get("hl_shoulders")}
print("REOPEN_B", json.dumps(R, ensure_ascii=False))
