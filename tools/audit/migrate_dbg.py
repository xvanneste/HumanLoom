import bpy, json, sys
import numpy as np
from pathlib import Path
SP = Path((__import__("os").environ.get("HL_SCRATCHPAD", "scratchpad") + r""))
bpy.ops.wm.open_mainfile(filepath=str(SP / "old" / "Session-modelisation-13.blend"))
bodies = [o for o in bpy.data.objects if o.get("human_modeling_body") and o.type == "MESH"]
out = {"bodies": [b.name for b in bodies]}

def state(b):
    k = b.data.shape_keys
    return {"Morphologie": round(float(k.key_blocks["Morphologie"].value), 3), "age": k.get("human_modeling_age"), "nonzero_keys": {x.name: round(float(x.value), 3) for x in k.key_blocks if abs(x.value) > 1e-6 and x.name != "Basis"}}

def coords(b):
    b.data.shape_keys.update_tag()
    bpy.context.view_layer.update()
    e = b.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = e.to_mesh()
    a = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", a)
    e.to_mesh_clear()
    return a

res = {}
for b in bodies:
    s0 = state(b)
    a0 = coords(b)
    bpy.ops.object.select_all(action="DESELECT")
    b.select_set(True)
    bpy.context.view_layer.objects.active = b
    bpy.ops.human_modeling.add_proportions()
    s1 = state(b)
    a1 = coords(b)
    res[b.name] = {"before": {"Morphologie": s0["Morphologie"], "age": s0["age"], "n_nonzero": len(s0["nonzero_keys"]), "sample": dict(list(s0["nonzero_keys"].items())[:6])},
                   "after": {"Morphologie": s1["Morphologie"], "age": s1["age"], "n_nonzero": len(s1["nonzero_keys"]), "sample": dict(list(s1["nonzero_keys"].items())[:8])},
                   "max_change_mm": round(float(np.abs(a1 - a0).max()) * 1000, 3), "mean_change_mm": round(float(np.abs(a1 - a0).mean()) * 1000, 4)}
    # where is the change? region by z
    d = np.linalg.norm((a1 - a0).reshape(-1, 3), axis=1)
    z = a0.reshape(-1, 3)[:, 2]
    res[b.name]["max_change_z_m"] = round(float(z[d.argmax()]), 3)
    res[b.name]["verts_changed_over_1mm"] = int((d > 0.001).sum())
out["res"] = res
print("MDBG", json.dumps(out, ensure_ascii=False))
