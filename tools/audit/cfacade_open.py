import bpy, sys, json
import numpy as np
from pathlib import Path
OUT = Path(sys.argv[-1])
bpy.ops.wm.open_mainfile(filepath=str(OUT / "cfacade.blend"))
saved = json.loads((OUT / "cfacade.json").read_text(encoding="utf-8"))["saved"]
fac = bpy.data.objects[saved["facade"]]
md = fac.modifiers["HL Human"]
ks = fac.data.shape_keys
inv = sum(1 for d in ks.animation_data.drivers if not d.driver.is_valid)
sid = [s.identifier for s in md.node_group.interface.items_tree if s.item_type == "SOCKET" and s.in_out == "INPUT" and s.name == "hm_shoulders"][0]

def coords():
    fac.update_tag()
    ks.update_tag()
    bpy.context.view_layer.update()
    e = fac.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = e.to_mesh()
    a = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", a)
    e.to_mesh_clear()
    return a

base = coords()
getattr(md.properties.inputs, sid).value = -0.8
print("REOPEN_C", json.dumps({"extension_class_available": hasattr(bpy.types.Object, "hl_groom"), "invalid_body_drivers": inv, "responds_to_modifier_input_mm": round(float(np.abs(coords() - base).max()) * 1000, 3),
                              "hair_objects": [(h.name, len(h.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.curves)) for h in fac.children if h.type == "CURVES"]}))
