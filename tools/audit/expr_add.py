import bpy, json, sys, os, time
import numpy as np
from pathlib import Path
OUT = Path(sys.argv[-1])
OUT.mkdir(parents=True, exist_ok=True)
R = {}
bpy.ops.human_modeling.create()
src = bpy.context.object
k = src.data.shape_keys
nv = len(src.data.vertices)

def co(x):
    a = np.empty(nv * 3, np.float32)
    x.data.foreach_get("co", a)
    return a

base = co(k.reference_key)
# identity morph = a few real deltas stored as attributes, blended by a tiny node group
names = ["HM · head_width", "HM · jaw", "HM · nose_width", "HM · mouth"]
deltas = [co(k.key_blocks[n]) - co(k.key_blocks[n].relative_key) for n in names]
mesh = src.data.copy()
obj = bpy.data.objects.new("body_nodes", mesh)
bpy.context.scene.collection.objects.link(obj)
obj.shape_key_clear()
mesh.vertices.foreach_set("co", base)
mesh.update()
for i, d in enumerate(deltas):
    a = mesh.attributes.new("d" + str(i), "FLOAT_VECTOR", "POINT")
    a.data.foreach_set("vector", d)
g = bpy.data.node_groups.new("Mini", "GeometryNodeTree")
g.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
g.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
for i in range(len(deltas)):
    g.interface.new_socket("W" + str(i), in_out="INPUT", socket_type="NodeSocketFloat")
gi = g.nodes.new("NodeGroupInput")
go = g.nodes.new("NodeGroupOutput")
sp = g.nodes.new("GeometryNodeSetPosition")
g.links.new(gi.outputs[0], sp.inputs["Geometry"])
acc = None
for i in range(len(deltas)):
    na = g.nodes.new("GeometryNodeInputNamedAttribute")
    na.data_type = "FLOAT_VECTOR"
    na.inputs["Name"].default_value = "d" + str(i)
    sc = g.nodes.new("ShaderNodeVectorMath")
    sc.operation = "SCALE"
    g.links.new(na.outputs["Attribute"], sc.inputs[0])
    g.links.new(gi.outputs[i + 1], sc.inputs[3])
    if acc is None:
        acc = sc.outputs[0]
    else:
        ad = g.nodes.new("ShaderNodeVectorMath")
        ad.operation = "ADD"
        g.links.new(acc, ad.inputs[0])
        g.links.new(sc.outputs[0], ad.inputs[1])
        acc = ad.outputs[0]
g.links.new(acc, sp.inputs["Offset"])
rm = g.nodes.new("GeometryNodeRemoveAttribute")
rm.inputs["Pattern Mode"].default_value = "Wildcard"
rm.inputs["Name"].default_value = "d*"
g.links.new(sp.outputs["Geometry"], rm.inputs["Geometry"])
g.links.new(rm.outputs["Geometry"], go.inputs[0])
md = obj.modifiers.new("HL Human", "NODES")
md.node_group = g
ids = [s.identifier for s in g.interface.items_tree if s.item_type == "SOCKET" and s.in_out == "INPUT" and s.name.startswith("W")]

def ev():
    obj.update_tag()
    bpy.context.view_layer.update()
    e = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = e.to_mesh()
    a = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", a)
    n = len(me.vertices)
    e.to_mesh_clear()
    return a, n

for i, sid in enumerate(ids):
    getattr(md.properties.inputs, sid).value = [0.7, -0.5, 0.9, 0.4][i]
w = np.array([0.7, -0.5, 0.9, 0.4])
identity_only, n0 = ev()
# an artist expression as a shape key on the base mesh (e.g. a smile-like delta on the mouth region)
obj.shape_key_add(name="Basis", from_mix=False)
expr = obj.shape_key_add(name="Smile", from_mix=False)
pts = np.array([v.co[:] for v in mesh.vertices])
mask = (np.abs(pts[:, 0]) < 0.06) & (pts[:, 2] > 1.50) & (pts[:, 2] < 1.60) & (pts[:, 1] < 0.0)
delta = np.zeros_like(pts)
delta[mask] = [0.0, -0.004, 0.006]
expr.data.foreach_set("co", (pts + delta).reshape(-1))
mesh.update()
expr.value = 1.0
with_expr, n1 = ev()
R["verts_touched_by_expression"] = int(mask.sum())
exp_total = identity_only + delta.reshape(-1)
R["additive_error_mm"] = round(float(np.abs(with_expr - exp_total).max()) * 1000, 6)
R["expression_effect_mm"] = round(float(np.abs(with_expr - identity_only).max()) * 1000, 3)
# identity change after the expression: still additive
getattr(md.properties.inputs, ids[0]).value = -0.8
with_expr2, _ = ev()
getattr(md.properties.inputs, ids[0]).value = 0.7
R["identity_change_keeps_expression_mm"] = round(float(np.abs((with_expr2 - with_expr) - (-1.5) * deltas[0].astype(np.float64)).max()) * 1000, 6)
# subsurf on top
s = obj.modifiers.new("sub", "SUBSURF")
s.levels = 1
sub, n2 = ev()
R["with_subsurf_vertices"] = n2
obj.modifiers.remove(s)
# export: glTF with morph targets (expression), modifiers applied?
for o in list(bpy.data.objects):
    if o != obj:
        bpy.data.objects.remove(o, do_unlink=True)
bpy.ops.object.select_all(action="DESELECT")
obj.select_set(True)
bpy.context.view_layer.objects.active = obj
for tag, kw in (("gltf_apply_with_morph", dict(export_apply=False, export_morph=True)), ("gltf_apply_modifiers", dict(export_apply=True, export_morph=False))):
    p = str(OUT / ("expr_" + tag + ".glb"))
    try:
        r = bpy.ops.export_scene.gltf(filepath=p, use_selection=True, **kw)
        R[tag] = {"result": list(r)[0], "MB": round(os.path.getsize(p) / 1e6, 2)}
    except Exception as e:
        R[tag] = "ERR " + str(e)[:200]
for tag, mods in (("fbx_no_modifiers", False), ("fbx_modifiers", True)):
    p = str(OUT / ("expr_" + tag + ".fbx"))
    try:
        r = bpy.ops.export_scene.fbx(filepath=p, use_selection=True, use_mesh_modifiers=mods, object_types={"MESH"})
        R[tag] = {"result": list(r)[0], "MB": round(os.path.getsize(p) / 1e6, 2)}
    except Exception as e:
        R[tag] = "ERR " + str(e)[:200]
# re-import fbx with modifiers applied: does it keep the shape key and the identity?
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)
try:
    bpy.ops.wm.fbx_import(filepath=str(OUT / "expr_fbx_modifiers.fbx"))
    m = [o for o in bpy.data.objects if o.type == "MESH"][0]
    R["fbx_modifiers_reimport"] = {"verts": len(m.data.vertices), "shape_keys": [x.name for x in m.data.shape_keys.key_blocks] if m.data.shape_keys else []}
except Exception as e:
    R["fbx_modifiers_reimport"] = "ERR " + str(e)[:200]
(OUT / "expr_add.json").write_text(json.dumps(R, indent=1, ensure_ascii=False), encoding="utf-8")
print("EXPR_DONE")
