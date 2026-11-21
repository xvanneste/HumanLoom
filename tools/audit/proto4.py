import bpy, json, sys
import numpy as np
from pathlib import Path
from mathutils.bvhtree import BVHTree
from extension import groom, anatomy
OUT = Path(sys.argv[-1])
OUT.mkdir(parents=True, exist_ok=True)
R = {}
bpy.ops.human_modeling.create()
b = bpy.context.object
bpy.context.view_layer.objects.active = b
bpy.ops.humanloom.groom_preset(preset="SHORT")
anatomy.attach(b, "pelvis", 5000)
kids = [c.name for c in b.children]
R["original_children"] = kids
bpy.ops.object.select_all(action="DESELECT")
b.select_set(True)
for c in b.children:
    c.select_set(True)
bpy.context.view_layer.objects.active = b
bpy.ops.object.duplicate()
new = bpy.context.object
R["new_body"] = new.name
R["new_body_children"] = [c.name for c in new.children]
R["new_body_children_types"] = sorted(c.type for c in new.children)
R["new_mesh_is_copy"] = new.data != b.data
R["new_keys_is_copy"] = new.data.shape_keys != b.data.shape_keys
# eyes follow the new body?
eyes = [c for c in new.children if c.type == "MESH" and not c.get("hm_measurement_landmark")]
out_eyes = []
for e in eyes:
    ks = e.data.shape_keys
    if ks and ks.animation_data and ks.animation_data.drivers:
        d = ks.animation_data.drivers[0].driver
        t = d.variables[0].targets[0]
        out_eyes.append({"eye": e.name, "driver_target": (t.id.name if t.id else None), "target_is_new_body_keys": t.id == new.data.shape_keys, "target_is_orig_body_keys": t.id == b.data.shape_keys})
R["eye_driver_targets"] = out_eyes
# hair copy
hairs = [c for c in new.children if c.type == "CURVES"]
hr = []
for h in hairs:
    s = h.data.surface
    hr.append({"hair": h.name, "surface": s.name if s else None, "surface_is_new_body": s == new, "surface_is_orig_body": s == b, "hl_region": h.get("hl_groom_region"),
               "shares_curves_data_with_original": h.data == groom.find(b, h.get("hl_groom_region")).data if groom.find(b, h.get("hl_groom_region")) else None,
               "material_shared_with_original": (h.active_material == groom.find(b, h.get("hl_groom_region")).active_material) if groom.find(b, h.get("hl_groom_region")) else None})
R["hair_copies"] = hr
# morph the copy; does the copy's hair follow the copy and not the original?
new.data.shape_keys["hm_head_width"] = 1.0
new.data.shape_keys["hm_shoulders"] = 1.0
new.data.shape_keys.update_tag()
bpy.context.view_layer.update()
def surf_bvh(o):
    ev = o.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = ev.to_mesh()
    t = BVHTree.FromPolygons([tuple(o.matrix_world @ v.co) for v in me.vertices], [tuple(p.vertices) for p in me.polygons])
    ev.to_mesh_clear()
    return t
tn = surf_bvh(new)
to = surf_bvh(b)
res = []
for h in hairs:
    he = h.evaluated_get(bpy.context.evaluated_depsgraph_get())
    roots = [h.matrix_world @ c.points[0].position for c in he.data.curves][:300]
    res.append({"hair": h.name, "median_gap_to_new_body_mm": round(float(np.median([tn.find_nearest(r)[3] for r in roots])) * 1000, 3), "median_gap_to_orig_body_mm": round(float(np.median([to.find_nearest(r)[3] for r in roots])) * 1000, 3)})
R["after_morphing_copy_hair_gaps"] = res
# landmark marker copy
marks = [c for c in new.children if c.get("hm_measurement_landmark")]
R["landmark_copies"] = [{"name": m.name, "parent": m.parent.name if m.parent else None, "parent_is_new": m.parent == new} for m in marks]
# eye shape key follow: set Morphologie on the new body, eyes' value follows?
new.data.shape_keys.key_blocks["Morphologie"].value = 0.25
new.data.shape_keys.update_tag()
bpy.context.view_layer.update()
R["eye_copy_morph_value_follows_new_body"] = [round(float(e.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.shape_keys.key_blocks["Morphologie"].value), 3) for e in eyes if e.data.shape_keys]
R["orig_body_morph_value_unchanged"] = round(float(b.data.shape_keys.key_blocks["Morphologie"].value), 3)
(OUT / "proto4.json").write_text(json.dumps(R, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
print("PROTO4_DONE")
