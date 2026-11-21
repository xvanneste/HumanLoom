import bpy, sys, json
import numpy as np
from pathlib import Path
OUT = Path(sys.argv[-1])
bpy.ops.wm.open_mainfile(filepath=str(OUT / "cfacade.blend"))
saved = json.loads((OUT / "cfacade.json").read_text(encoding="utf-8"))["saved"]
fac = bpy.data.objects[saved["facade"]]
md = fac.modifiers["HL Human"]
ks = fac.data.shape_keys
sid = [s.identifier for s in md.node_group.interface.items_tree if s.item_type == "SOCKET" and s.in_out == "INPUT" and s.name == "hm_shoulders"][0]

def kv():
    return round(float(ks.key_blocks["HM · shoulders"].value), 4)

def evalpos():
    bpy.context.view_layer.update()
    e = fac.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = e.to_mesh()
    a = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", a)
    e.to_mesh_clear()
    return a

out = {"before": {"input": getattr(md.properties.inputs, sid).value, "key": kv()}}
base = evalpos()
getattr(md.properties.inputs, sid).value = 1.0
out["after_set_no_update"] = {"input": getattr(md.properties.inputs, sid).value, "key": kv()}
p1 = evalpos()
out["after_update"] = {"key": kv(), "moved_mm": round(float(np.abs(p1 - base).max()) * 1000, 3)}
for tag, action in (("tag_object", lambda: fac.update_tag()), ("tag_data", lambda: fac.data.update_tag()), ("tag_keys", lambda: ks.update_tag()), ("tag_nodegroup", lambda: md.node_group.update_tag())):
    action()
    p = evalpos()
    out["after_" + tag] = {"key": kv(), "moved_mm": round(float(np.abs(p - base).max()) * 1000, 3)}
# frame change forces re-evaluation of drivers
bpy.context.scene.frame_set(2)
bpy.context.scene.frame_set(1)
p = evalpos()
out["after_frame_change"] = {"key": kv(), "moved_mm": round(float(np.abs(p - base).max()) * 1000, 3)}
# read the driver variable directly
d = [d for d in ks.animation_data.drivers if d.data_path == 'key_blocks["HM · shoulders"].value'][0]
out["driver_expression"] = d.driver.expression
out["driver_vars"] = [(v.name, v.targets[0].id.name if v.targets[0].id else None, v.targets[0].data_path, v.is_name_valid) for v in d.driver.variables]
out["driver_is_valid"] = d.driver.is_valid
out["driver_error_flag"] = getattr(d.driver, "is_simple_expression", None)
print("DBG", json.dumps(out, ensure_ascii=False))
