import bpy, sys, json
import numpy as np
from pathlib import Path
OUT = Path(sys.argv[-1])
R = {}
bpy.ops.wm.open_mainfile(filepath=str(OUT / "proto5.blend"))
R["extension_registered_in_this_session"] = hasattr(bpy.ops, "human_modeling") and hasattr(bpy.ops.human_modeling, "create") and bpy.ops.human_modeling.create.poll() is not None if False else "bl_ext" in sys.modules
body = next(o for o in bpy.data.objects if o.get("human_modeling_body"))
k = body.data.shape_keys
R["body_drivers_invalid"] = sum(1 for d in k.animation_data.drivers if not d.driver.is_valid)
R["body_drivers_total"] = len(k.animation_data.drivers)

def coords():
    k.update_tag()
    bpy.context.view_layer.update()
    e = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = e.to_mesh()
    a = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", a)
    e.to_mesh_clear()
    return a

base = coords()
k["hm_shoulders"] = 1.0
R["body_responds_to_slider_mm_without_extension"] = round(float(np.abs(coords() - base).max()) * 1000, 3)
hairs = [c for c in body.children if c.type == "CURVES"]
out = []
for h in hairs:
    bpy.context.view_layer.update()
    d = h.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
    out.append({"hair": h.name, "evaluated_curves": len(d.curves), "modifiers": [m.name for m in h.modifiers], "node_groups_linked_from_library": [m.node_group.library is not None for m in h.modifiers if m.type == "NODES" and m.node_group]})
R["hair_objects"] = out
R["eyes_follow"] = [c.name for c in body.children if c.type == "MESH" and c.data.shape_keys]
R["hl_groom_settings_stored_as_idprops_on_hair"] = [("hl_groom" in h.keys()) for h in hairs][:3]
R["rna_hl_groom_available"] = hasattr(bpy.types.Object, "hl_groom")
print("OPEN5", json.dumps(R, ensure_ascii=False))
