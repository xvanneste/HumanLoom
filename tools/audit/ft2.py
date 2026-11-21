import sys, json, time
from pathlib import Path
import bpy, numpy as np
from mathutils.bvhtree import BVHTree
from extension.proportions import CONTROLS, property_name
out = Path(sys.argv[sys.argv.index("--") + 1]); out.mkdir(parents=True, exist_ok=True)
rep = {}
bpy.ops.human_modeling.create(); body = bpy.context.object; keys = body.data.shape_keys
def coords(obj=None, mods=True):
    obj = obj or body
    keys.update_tag(); bpy.context.view_layer.update()
    ev = obj.evaluated_get(bpy.context.evaluated_depsgraph_get()); me = ev.to_mesh()
    a = np.empty(len(me.vertices) * 3); me.vertices.foreach_get("co", a); ev.to_mesh_clear(); return a.reshape(-1, 3)
def setmods(on):
    for m in body.modifiers: m.show_viewport = on

# 1. skin_relief with modifiers on
base = coords()
rows = {}
for v in (0.0, 1.0, -1.0):
    keys[property_name("skin_relief")] = v
    c = coords(); rows[str(v)] = {"max_mm_vs_0": round(float(np.linalg.norm(c - base, axis=1).max()) * 1000, 3) if v else 0.0}
rep["skin_relief_mods_on"] = rows
keys[property_name("skin_relief")] = 0.0
rep["modifiers"] = [(m.name, m.type, {"levels": getattr(m, "levels", None), "render_levels": getattr(m, "render_levels", None), "strength": getattr(m, "strength", None)}) for m in body.modifiers]

# 2. preset roundtrip
setmods(False)
bpy.ops.human_modeling.randomize(seed=7, strength=.8, scope="ALL")
saved = coords(); p = out / "preset.json"
r1 = bpy.ops.human_modeling.save_preset(filepath=str(p))
bpy.ops.human_modeling.reset_proportions(); zero = coords()
r2 = bpy.ops.human_modeling.load_preset(filepath=str(p), factor=1.0); loaded = coords()
r3 = bpy.ops.human_modeling.load_preset(filepath=str(p), factor=0.5); half = coords()
rep["preset"] = {"save": list(r1)[0], "load": list(r2)[0], "load_half": list(r3)[0],
                 "roundtrip_max_mm": round(float(np.linalg.norm(loaded - saved, axis=1).max()) * 1000, 4),
                 "half_vs_expected_mm": round(float(np.linalg.norm(half - (saved + zero) / 2, axis=1).max()) * 1000, 3),
                 "json_keys": list(json.loads(p.read_text(encoding="utf-8")).keys())}
bpy.ops.human_modeling.reset_proportions()

# 3. geometry check neutral and extreme
def geom():
    r = bpy.ops.human_modeling.check_geometry(); rep_ = json.loads(body["hm_geometry_report"])
    return list(r)[0], {k: rep_[k] for k in list(rep_)[:14]}
rep["geometry_neutral"] = geom()
for ident, _ in CONTROLS:
    pn = property_name(ident)
    if pn in keys: keys[pn] = 1.0
keys.update_tag(); bpy.context.view_layer.update()
rep["geometry_all_plus1"] = geom()
bpy.ops.human_modeling.reset_proportions()

# 4. set_height range
rows = []
for h in (0.5, 1.2, 1.75, 2.2, 3.0):
    r = bpy.ops.human_modeling.set_height(height=h); bpy.context.view_layer.update()
    rows.append({"asked": h, "result": list(r)[0], "scale": round(body.scale.z, 4), "height": round(float(np.ptp(coords()[:, 2])) * body.scale.z, 4)})
body.scale = (1, 1, 1)
rep["set_height"] = rows

# 5. age calibration
rows = []
for stage in range(4):
    for sex in ("F", "M"):
        body.scale = (1, 1, 1); bpy.ops.human_modeling.age_reference(stage=stage)
        try:
            r = bpy.ops.human_modeling.calibrate_age_height(sex=sex); status = list(r)[0]
        except Exception as e:
            status = "ERR " + str(e)[:80]
        bpy.context.view_layer.update()
        rows.append({"stage": stage, "sex": sex, "status": status, "scale": round(body.scale.z, 4), "height_m": round(float(np.ptp(coords()[:, 2])) * body.scale.z, 4)})
body.scale = (1, 1, 1); bpy.ops.human_modeling.age_reference(stage=2)
rep["age_calibration"] = rows

# 6. groom integration
bpy.context.view_layer.objects.active = body
t = time.perf_counter(); r = bpy.ops.humanloom.groom_preset(preset="SHORT"); dt = time.perf_counter() - t
hairs = [o for o in body.children if o.type == "CURVES"]
rep["groom_short"] = {"result": list(r)[0], "seconds": round(dt, 2), "objects": [(h.name, len(h.data.curves)) for h in hairs]}
def root_gap():
    keys.update_tag(); bpy.context.view_layer.update()
    ev = body.evaluated_get(bpy.context.evaluated_depsgraph_get()); me = ev.to_mesh()
    verts = [body.matrix_world @ v.co for v in me.vertices]
    bvh = BVHTree.FromPolygons([tuple(v) for v in verts], [tuple(p.vertices) for p in me.polygons]); ev.to_mesh_clear()
    res = {}
    for h in hairs:
        he = h.evaluated_get(bpy.context.evaluated_depsgraph_get()); d = he.data
        roots = [h.matrix_world @ c.points[0].position for c in d.curves]
        gaps = [bvh.find_nearest(r)[3] for r in roots]
        res[h.name] = {"curves_eval": len(d.curves), "root_gap_mm_median": round(float(np.median(gaps)) * 1000, 3), "root_gap_mm_max": round(float(np.max(gaps)) * 1000, 3)}
    return res
setmods(True)
rep["groom_roots_neutral"] = root_gap()
for ident in ("corpulence", "head_width", "whole_body", "legs"):
    keys[property_name(ident)] = 1.0
rep["groom_roots_after_morph"] = root_gap()
bpy.ops.human_modeling.set_height(height=1.5)
rep["groom_roots_after_scale"] = root_gap()
t = time.perf_counter(); r = bpy.ops.humanloom.groom_preset(preset="ALL"); rep["groom_all"] = {"result": list(r)[0], "seconds": round(time.perf_counter() - t, 2),
    "objects": [(h.name, len(h.data.curves)) for h in body.children if h.type == "CURVES"]}
(out / "ft2.json").write_text(json.dumps(rep, indent=1, ensure_ascii=False), encoding="utf-8"); print("FT2_DONE")
