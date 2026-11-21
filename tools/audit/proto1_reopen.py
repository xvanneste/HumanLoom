import bpy, sys, json
import numpy as np
from pathlib import Path
OUT = Path(sys.argv[-1])
R = {}
bpy.ops.wm.open_mainfile(filepath=str(OUT / "proto1.blend"))
bodies = {o.name: o for o in bpy.data.objects if o.get("human_modeling_body")}

def coords(b):
    b.data.shape_keys.update_tag()
    bpy.context.view_layer.update()
    e = b.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = e.to_mesh()
    a = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", a)
    e.to_mesh_clear()
    return a

R["RNA_hlproto_registered_in_this_session"] = hasattr(bpy.types.Object, "hlproto")
for name in sorted(bodies)[:3]:
    o = bodies[name]
    ks = o.data.shape_keys
    inv = sum(1 for d in ks.animation_data.drivers if not d.driver.is_valid)
    entry = {"has_idprop_hlproto": "hlproto" in o.keys(), "invalid_drivers": inv, "total_drivers": len(ks.animation_data.drivers)}
    if "hlproto" in o.keys():
        entry["idprop_shoulders"] = o["hlproto"].get("shoulders")
    base = coords(o)
    if "hlproto" in o.keys():
        o["hlproto"]["shoulders"] = -0.8
    else:
        ks["hm_shoulders"] = -0.8
    entry["responds_to_change_mm"] = round(float(np.abs(coords(o) - base).max()) * 1000, 3)
    R[name] = entry
print("REOPEN", json.dumps(R, ensure_ascii=False))
