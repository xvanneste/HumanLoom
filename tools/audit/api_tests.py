import bpy, json, sys, time, os
import numpy as np
from pathlib import Path
from extension import groom
OUT = Path(sys.argv[-1])
OUT.mkdir(parents=True, exist_ok=True)
R = {}

def step(name, fn):
    t = time.perf_counter()
    try:
        v = fn()
        R[name] = {"ok": True, "value": v, "s": round(time.perf_counter() - t, 2)}
    except Exception as e:
        R[name] = {"ok": False, "error": type(e).__name__ + " " + str(e)[:300], "s": round(time.perf_counter() - t, 2)}

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

bpy.ops.human_modeling.create()
body = bpy.context.object
bpy.context.view_layer.objects.active = body
bpy.ops.humanloom.groom_preset(preset="SHORT")
for m in body.modifiers:
    m.show_viewport = False

# A2: Alt+D linked duplicate
def linked_dup():
    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.duplicate(linked=True)
    d = bpy.context.object
    res = {"shares_mesh": d.data == body.data, "shares_keys": d.data.shape_keys == body.data.shape_keys, "children_copied": len(d.children)}
    b0 = coords(body)
    body.data.shape_keys["hm_shoulders"] = 0.9
    res["changing_original_moves_linked_copy_mm"] = round(float(np.abs(coords(d) - b0).max()) * 1000, 3)
    body.data.shape_keys["hm_shoulders"] = 0.0
    bpy.data.objects.remove(d, do_unlink=True)
    return res
step("A2_linked_duplicate_Alt_D", linked_dup)

# A4: mask painting then rebuild
def mask_test():
    body.hl_groom_region = "SCALP"
    hair = groom.find(body, "SCALP")
    vg = body.vertex_groups.get("hl_density_scalp")
    res = {"has_mask_group": vg is not None}
    co = np.array([v.co[:] for v in body.data.vertices])
    left = [i for i in range(len(co)) if co[i][0] > 0.0]
    vg.add(left, 0.0, "REPLACE")
    bpy.context.view_layer.objects.active = body
    r = bpy.ops.humanloom.groom_build()
    hair = groom.find(body, "SCALP")
    roots = np.array([[p for p in c.points[0].position] for c in hair.data.curves])
    res["rebuild_result"] = list(r)[0]
    res["guides_after"] = len(hair.data.curves)
    res["roots_on_masked_side_x_gt_0.002"] = int((roots[:, 0] > 0.002).sum())
    res["roots_on_open_side"] = int((roots[:, 0] < -0.002).sum())
    # fully empty mask
    allv = list(range(len(co)))
    vg.add(allv, 0.0, "REPLACE")
    try:
        r2 = bpy.ops.humanloom.groom_build()
        res["empty_mask_result"] = list(r2)[0]
    except Exception as e:
        res["empty_mask_result"] = "ERR " + str(e)[:100]
    res["guides_after_empty_mask_attempt"] = len(groom.find(body, "SCALP").data.curves)
    vg.add(allv, 1.0, "REPLACE")
    return res
step("A4_mask_paint_rebuild", mask_test)

# A5: XPBD at rest, default parameters
def xpbd():
    body.hl_groom_region = "SCALP"
    hair = groom.find(body, "SCALP")
    cfg = groom.state(hair.hl_groom)
    cfg["physics"] = "XPBD"
    groom.build(body, "SCALP", cfg)
    hair = groom.find(body, "SCALP")
    bpy.context.scene.frame_set(1)
    ts = []
    for f in range(2, 14):
        t = time.perf_counter()
        bpy.context.scene.frame_set(f)
        bpy.context.view_layer.update()
        hair.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
        ts.append(time.perf_counter() - t)
    bpy.context.scene.frame_set(1)
    return {"guides": len(hair.data.curves), "per_frame_s": [round(x, 2) for x in ts], "mean_s": round(sum(ts) / len(ts), 2), "substeps": cfg["substeps"], "iterations": cfg["iterations"]}
step("A5_xpbd_at_rest_850_guides", xpbd)

# A6: modifier order for a trim-like module
def order():
    hair = groom.find(body, "BROWS")
    g = bpy.data.node_groups.new("T", "GeometryNodeTree")
    g.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    g.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    gi = g.nodes.new("NodeGroupInput")
    go = g.nodes.new("NodeGroupOutput")
    g.links.new(gi.outputs[0], go.inputs[0])
    m = hair.modifiers.new("TrimProbe", "NODES")
    m.node_group = g
    res = {"before": [x.name for x in hair.modifiers]}
    hair.modifiers.move(len(hair.modifiers) - 1, 0)
    res["after_move_API"] = [x.name for x in hair.modifiers]
    try:
        bpy.context.view_layer.objects.active = hair
        with bpy.context.temp_override(object=hair, active_object=hair):
            bpy.ops.object.modifier_move_to_index(modifier=m.name, index=0)
        res["after_move_to_index_op"] = [x.name for x in hair.modifiers]
    except Exception as e:
        res["move_to_index_err"] = str(e)[:150]
    hair.modifiers.remove(m)
    return res
step("A6_modifier_order", order)

# A3: exports
def exports():
    res = {}
    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    body.data.shape_keys["hm_shoulders"] = 0.4
    for tag, fn in (
        ("fbx_with_shapekeys", lambda p: bpy.ops.export_scene.fbx(filepath=p, use_selection=True, apply_modifiers=False)),
        ("fbx_apply_modifiers", lambda p: bpy.ops.export_scene.fbx(filepath=p, use_selection=True, apply_modifiers=True)),
        ("gltf_morph", lambda p: bpy.ops.export_scene.gltf(filepath=p, use_selection=True, export_apply=False, export_morph=True)),
        ("gltf_apply_no_morph", lambda p: bpy.ops.export_scene.gltf(filepath=p, use_selection=True, export_apply=True, export_morph=False)),
    ):
        ext = ".fbx" if tag.startswith("fbx") else ".glb"
        p = str(OUT / ("exp_" + tag + ext))
        t = time.perf_counter()
        try:
            r = fn(p)
            res[tag] = {"result": list(r)[0], "s": round(time.perf_counter() - t, 1), "MB": round(os.path.getsize(p) / 1e6, 1) if os.path.exists(p) else None}
        except Exception as e:
            res[tag] = "ERR " + type(e).__name__ + " " + str(e)[:160]
    body.data.shape_keys["hm_shoulders"] = 0.0
    return res
step("A3_exports", exports)

# A1: assets (collection) saved to a file, used from another session
def assets():
    col = bpy.data.collections.new("Human Asset Test")
    bpy.context.scene.collection.children.link(col)
    for o in [body] + list(body.children):
        for c in o.users_collection:
            c.objects.unlink(o)
        col.objects.link(o)
    col.asset_mark()
    col.asset_data.description = "HumanLoom asset test"
    col.asset_data.tags.new("human")
    p = OUT / "assets_lib.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(p))
    return {"marked_asset": col.asset_data is not None, "saved": str(p.name)}
step("A1_mark_collection_as_asset_and_save", assets)
(OUT / "api_tests.json").write_text(json.dumps(R, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
print("API_DONE")
