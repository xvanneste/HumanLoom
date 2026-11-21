"""Option C-facade: a Geometry Nodes group is the control surface (inputs); shape-key drivers read the modifier inputs."""
import bpy, json, statistics, sys, time
import numpy as np
from pathlib import Path
from mathutils.bvhtree import BVHTree
from extension.proportions import CONTROLS

OUT = Path(sys.argv[-1])
OUT.mkdir(parents=True, exist_ok=True)
R = {}
CTRL = [c[0] for c in CONTROLS]
inputs = ["sex", "age"] + ["hm_" + c for c in CTRL]

def new_body(loc):
    bpy.context.scene.cursor.location = loc
    bpy.ops.human_modeling.create()
    return bpy.context.object

ref = new_body((0, 0, 0))
fac = new_body((4, 0, 0))
for o in (ref, fac):
    for m in o.modifiers:
        m.show_viewport = False

g = bpy.data.node_groups.new("HL_Human_Controls", "GeometryNodeTree")
g.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
g.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
for n in inputs:
    s = g.interface.new_socket(n, in_out="INPUT", socket_type="NodeSocketFloat")
    s.default_value = 2.0 if n == "age" else (1.0 if n == "sex" else 0.0)
    s.min_value = -1.0 if n.startswith("hm_") else 0.0
    s.max_value = 3.0 if n == "age" else 1.0
gi = g.nodes.new("NodeGroupInput")
go = g.nodes.new("NodeGroupOutput")
g.links.new(gi.outputs[0], go.inputs[0])
md = fac.modifiers.new("HL Human", "NODES")
md.node_group = g
ids = {s.name: s.identifier for s in g.interface.items_tree if s.item_type == "SOCKET" and s.in_out == "INPUT" and s.name in inputs}
# put the facade modifier first in the stack
fac.modifiers.move(len(fac.modifiers) - 1, 0)
R["modifier_stack"] = [m.name for m in fac.modifiers]

def path_for(name):
    return 'modifiers["HL Human"].properties.inputs.' + ids[name] + ".value"

def nm_of(p):
    if p.startswith('["hm_'):
        return "hm_" + p[5:-2]
    if p == '["human_modeling_age"]':
        return "age"
    return "sex"

def rewire(keyblock_owner_drivers, body):
    n = 0
    for d in keyblock_owner_drivers:
        for v in d.driver.variables:
            t = v.targets[0]
            t.id_type = "OBJECT"
            t.id = body
            t.data_path = path_for(nm_of(t.data_path))
            n += 1
    return n

keys = fac.data.shape_keys
R["rewired_variables_body"] = rewire(keys.animation_data.drivers, fac)
# the Morphologie key itself follows the 'sex' input through a new driver
dm = keys.key_blocks["Morphologie"].driver_add("value").driver
dm.type = "AVERAGE"
v = dm.variables.new()
v.name = "sex"
v.type = "SINGLE_PROP"
v.targets[0].id_type = "OBJECT"
v.targets[0].id = fac
v.targets[0].data_path = path_for("sex")
eyes_ref = [c for c in ref.children if c.type == "MESH" and c.data.shape_keys]
eyes_fac = [c for c in fac.children if c.type == "MESH" and c.data.shape_keys]
n_eye = 0
for e in eyes_fac:
    ks = e.data.shape_keys
    for d in ks.animation_data.drivers:
        for v in d.driver.variables:
            t = v.targets[0]
            if t.id_type == "OBJECT":
                t.data_path = path_for("sex")
                t.id = fac
            else:
                t.id_type = "OBJECT"
                t.id = fac
                t.data_path = path_for(nm_of(t.data_path))
            n_eye += 1
R["rewired_variables_eyes"] = n_eye
R["invalid_drivers"] = {"body": sum(1 for d in keys.animation_data.drivers if not d.driver.is_valid), "eyes": sum(1 for e in eyes_fac for d in e.data.shape_keys.animation_data.drivers if not d.driver.is_valid)}

def setref(n, v):
    if n == "sex":
        ref.data.shape_keys.key_blocks["Morphologie"].value = v
    elif n == "age":
        ref.data.shape_keys["human_modeling_age"] = v
    else:
        ref.data.shape_keys[n] = v

def setfac(n, v):
    getattr(md.properties.inputs, ids[n]).value = float(v)

def coords(o):
    o.update_tag()
    if o.data.shape_keys:
        o.data.shape_keys.update_tag()
    bpy.context.view_layer.update()
    e = o.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = e.to_mesh()
    a = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", a)
    e.to_mesh_clear()
    M = np.array(e.matrix_world)
    return a.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3] - np.array(o.matrix_world.translation) if o.type == "MESH" else a

rng = np.random.default_rng(9)
berr = []
eerr = []
for trial in range(20):
    st = {n: float(rng.uniform(-1, 1)) for n in inputs if n.startswith("hm_")}
    st["age"] = float(rng.uniform(0, 3))
    st["sex"] = float(rng.uniform(0, 1))
    for n, v in st.items():
        setref(n, v)
        setfac(n, v)
    berr.append(float(np.abs(coords(ref) - coords(fac)).max()))
    for a_, b_ in zip(eyes_ref, eyes_fac):
        eerr.append(float(np.abs(coords(a_) - coords(b_)).max()))
R["body_max_error_mm_20_states"] = round(max(berr) * 1000, 5)
R["eyes_max_error_mm_20_states"] = round(max(eerr) * 1000, 5)

def timing(setter, obj, n=40):
    ts = []
    r = np.random.default_rng(1)
    for _ in range(n):
        setter("hm_" + CTRL[int(r.integers(len(CTRL)))], float(r.uniform(-1, 1)))
        t = time.perf_counter()
        coords(obj)
        ts.append((time.perf_counter() - t) * 1000)
    return round(statistics.median(ts), 1), round(sorted(ts)[int(.9 * len(ts))], 1)

R["slider_ms_cage"] = {"reference_key_props": timing(setref, ref), "facade_modifier_inputs": timing(setfac, fac)}
for o in (ref, fac):
    for m in o.modifiers:
        if m.type == "SUBSURF":
            m.show_viewport = True
R["slider_ms_with_subsurf"] = {"reference_key_props": timing(setref, ref), "facade_modifier_inputs": timing(setfac, fac)}
for o in (ref, fac):
    for m in o.modifiers:
        if m.type == "SUBSURF":
            m.show_viewport = False

# keyframes on modifier inputs (growth)
sc = bpy.context.scene
for n, v in (("age", 0.0), ("hm_whole_body", -1.0)):
    setfac(n, v)
    fac.keyframe_insert(data_path=path_for(n), frame=1)
for n, v in (("age", 3.0), ("hm_whole_body", 1.0)):
    setfac(n, v)
    fac.keyframe_insert(data_path=path_for(n), frame=101)
rows = []
for fr in (1, 51, 101):
    sc.frame_set(fr)
    c = coords(fac).reshape(-1, 3)
    rows.append((fr, round(float(np.ptp(c[:, 2])), 3), round(float(np.ptp(c[:, 1])), 3)))
R["keyframes_on_modifier_inputs_(frame, height, depth)"] = rows
sc.frame_set(1)
fac.animation_data_clear()
for n in inputs:
    setfac(n, 0.0 if n not in ("age", "sex") else (2.0 if n == "age" else 1.0))

# hair on the facade body
bpy.ops.object.select_all(action="DESELECT")
fac.select_set(True)
bpy.context.view_layer.objects.active = fac
bpy.ops.humanloom.groom_preset(preset="SHORT")
hairs = [c for c in fac.children if c.type == "CURVES"]
for n in ("hm_head_width", "hm_shoulders", "hm_whole_body", "hm_legs"):
    setfac(n, 1.0)
setfac("age", 0.0)
coords(fac)
ee = fac.evaluated_get(bpy.context.evaluated_depsgraph_get())
me = ee.to_mesh()
t = BVHTree.FromPolygons([tuple(fac.matrix_world @ v.co) for v in me.vertices], [tuple(p.vertices) for p in me.polygons])
ee.to_mesh_clear()
gaps = []
for h in hairs:
    he = h.evaluated_get(bpy.context.evaluated_depsgraph_get())
    roots = [h.matrix_world @ c.points[0].position for c in he.data.curves][:300]
    gaps.append((h.name, round(float(np.median([t.find_nearest(x)[3] for x in roots])) * 1000, 3)))
R["hair_root_gap_mm_after_morph_age0"] = gaps

for n in inputs:
    setfac(n, 0.0 if n not in ("age", "sex") else (2.0 if n == "age" else 1.0))
# duplication of the whole hierarchy
bpy.ops.object.select_all(action="DESELECT")
fac.select_set(True)
for c in fac.children:
    c.select_set(True)
bpy.context.view_layer.objects.active = fac
bpy.ops.object.duplicate()
dup = bpy.context.object
dmod = dup.modifiers["HL Human"]
shares_group = dmod.node_group == g
tgt = dup.data.shape_keys.animation_data.drivers[5].driver.variables[0].targets[0]
b0 = coords(fac)
d0 = coords(dup)
getattr(dmod.properties.inputs, ids["hm_shoulders"]).value = 1.0
R["duplicate"] = {"copy": dup.name, "driver_target": tgt.id.name if tgt.id else None, "modifier_group_shared_with_original": shares_group,
                  "copy_moves_mm": round(float(np.abs(coords(dup) - d0).max()) * 1000, 3), "orig_moves_mm": round(float(np.abs(coords(fac) - b0).max()) * 1000, 3)}
getattr(dmod.properties.inputs, ids["hm_shoulders"]).value = 0.0
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "cfacade.blend"))
R["saved"] = {"facade": fac.name}
(OUT / "cfacade.json").write_text(json.dumps(R, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
print("CFACADE_DONE")
