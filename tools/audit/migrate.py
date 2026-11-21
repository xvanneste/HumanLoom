import bpy, json, sys, time
import numpy as np
from pathlib import Path
SP = Path((__import__("os").environ.get("HL_SCRATCHPAD", "scratchpad") + r""))
R = {}

def coords(b):
    if b.data.shape_keys:
        b.data.shape_keys.update_tag()
    bpy.context.view_layer.update()
    e = b.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = e.to_mesh()
    a = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", a)
    e.to_mesh_clear()
    return a

for f in sorted((SP / "old").glob("*.blend")):
    entry = {}
    try:
        bpy.ops.wm.open_mainfile(filepath=str(f))
        bodies = [o for o in bpy.data.objects if o.get("human_modeling_body") and o.type == "MESH"]
        entry["bodies"] = len(bodies)
        if not bodies:
            entry["note"] = "no HumanLoom body"
            R[f.name] = entry
            continue
        b = bodies[0]
        ks = b.data.shape_keys
        entry["schema_before"] = b.data.get("human_modeling_schema")
        entry["keys_before"] = len(ks.key_blocks) if ks else 0
        entry["drivers_before"] = (len(ks.animation_data.drivers) if ks and ks.animation_data else 0)
        entry["invalid_drivers_before"] = sum(1 for d in ks.animation_data.drivers if not d.driver.is_valid) if ks and ks.animation_data else 0
        entry["modifiers_before"] = [m.name for m in b.modifiers]
        a0 = coords(b)
        entry["finite_before"] = bool(np.isfinite(a0).all())
        bpy.ops.object.select_all(action="DESELECT")
        b.select_set(True)
        bpy.context.view_layer.objects.active = b
        poll = bpy.ops.human_modeling.add_proportions.poll()
        entry["upgrade_poll"] = bool(poll)
        if poll:
            t = time.perf_counter()
            r = bpy.ops.human_modeling.add_proportions()
            entry["upgrade_result"] = list(r)[0]
            entry["upgrade_s"] = round(time.perf_counter() - t, 2)
            ks = b.data.shape_keys
            a1 = coords(b)
            entry["schema_after"] = b.data.get("human_modeling_schema")
            entry["keys_after"] = len(ks.key_blocks)
            entry["invalid_drivers_after"] = sum(1 for d in ks.animation_data.drivers if not d.driver.is_valid)
            entry["max_mm_change_at_neutral"] = round(float(np.abs(a1 - a0).max()) * 1000, 4) if len(a1) == len(a0) else "vertex count differs"
            entry["finite_after"] = bool(np.isfinite(a1).all())
            # working after upgrade: a control moves the body
            ks["hm_shoulders"] = 0.8
            a2 = coords(b)
            entry["control_moves_body_mm_after_upgrade"] = round(float(np.abs(a2 - a1).max()) * 1000, 3)
            entry["eyes_invalid_drivers"] = sum(1 for c in b.children if c.type == "MESH" and c.data.shape_keys and c.data.shape_keys.animation_data for d in c.data.shape_keys.animation_data.drivers if not d.driver.is_valid)
    except Exception as e:
        entry["error"] = type(e).__name__ + " " + str(e)[:200]
    R[f.name] = entry
(SP / "proto" / "migrate.json").write_text(json.dumps(R, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
print("MIGRATE_DONE")
