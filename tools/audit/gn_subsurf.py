import bpy, time, statistics, json, sys
import numpy as np
from pathlib import Path
OUT = Path(sys.argv[-1])
OUT.mkdir(parents=True, exist_ok=True)
R = {}
bpy.ops.human_modeling.create()
body = bpy.context.object
keys = body.data.shape_keys
nv = len(body.data.vertices)
blocks = [k for k in keys.key_blocks if k != keys.reference_key]

def co(k):
    a = np.empty(nv * 3, np.float32)
    k.data.foreach_get("co", a)
    return a

base = co(keys.reference_key)
deltas = [co(k) - co(k.relative_key) for k in blocks]

def build(n, remove_pattern):
    mesh = bpy.data.meshes.new("m%d_%s" % (n, remove_pattern))
    src = body.data
    mesh = src.copy()
    mesh.shape_keys and None
    tmp = bpy.data.objects.new("t", mesh)
    bpy.context.scene.collection.objects.link(tmp)
    tmp.shape_key_clear()
    mesh.vertices.foreach_set("co", base)
    for i in range(n):
        a = mesh.attributes.new("d" + str(i), "FLOAT_VECTOR", "POINT")
        a.data.foreach_set("vector", deltas[i])
    g = bpy.data.node_groups.new("G%d_%s" % (n, remove_pattern), "GeometryNodeTree")
    g.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    g.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    for i in range(n):
        g.interface.new_socket("W" + str(i), in_out="INPUT", socket_type="NodeSocketFloat")
    gi = g.nodes.new("NodeGroupInput")
    go = g.nodes.new("NodeGroupOutput")
    sp = g.nodes.new("GeometryNodeSetPosition")
    g.links.new(gi.outputs[0], sp.inputs["Geometry"])
    acc = None
    for i in range(n):
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
    last = sp.outputs["Geometry"]
    info = {}
    if remove_pattern:
        rm = g.nodes.new("GeometryNodeRemoveAttribute")
        info["remove_node_inputs"] = [s.name for s in rm.inputs]
        info["remove_node_props"] = [p for p in dir(rm) if "pattern" in p.lower() or "mode" in p.lower()][:6]
        try:
            rm.inputs["Pattern Mode"].default_value = "Wildcard"; info["enum_items"] = [i.identifier for i in rm.inputs["Pattern Mode"].bl_rna.properties["default_value"].enum_items]
        except Exception as e:
            info["pattern_mode_err"] = str(e)[:100]
        rm.inputs["Name"].default_value = "d*"
        g.links.new(last, rm.inputs["Geometry"])
        last = rm.outputs["Geometry"]
    g.links.new(last, go.inputs[0])
    md = tmp.modifiers.new("gn", "NODES")
    md.node_group = g
    return tmp, md, g, info

def ev(o):
    o.update_tag()
    bpy.context.view_layer.update()
    e = o.evaluated_get(bpy.context.evaluated_depsgraph_get())
    m = e.to_mesh()
    n = len(m.vertices)
    e.to_mesh_clear()
    return n

def timing(o, md, g, n=15):
    ids = [s.identifier for s in g.interface.items_tree if s.item_type == "SOCKET" and s.in_out == "INPUT" and s.name.startswith("W")]
    rng = np.random.default_rng(1)
    ts = []
    for _ in range(n):
        for sid in ids:
            getattr(md.properties.inputs, sid).value = float(rng.uniform(-1, 1))
        t = time.perf_counter()
        nv_ = ev(o)
        ts.append((time.perf_counter() - t) * 1000)
    return round(statistics.median(ts), 1), nv_

for n in (150, 457):
    for rp in (False, True):
        o, md, g, info = build(n, rp)
        a = timing(o, md, g)
        s = o.modifiers.new("sub", "SUBSURF")
        s.levels = 1
        b = timing(o, md, g)
        o.modifiers.remove(s)
        R["R=%d remove_attributes=%s" % (n, rp)] = {"gn_only_ms_median_and_verts": a, "gn_plus_subsurf1_ms_median_and_verts": b, **info}
        bpy.data.objects.remove(o, do_unlink=True)
# reference: shape keys + subsurf
for m in body.modifiers:
    m.show_viewport = False
s = body.modifiers.new("sub", "SUBSURF")
s.levels = 1
ts = []
rng = np.random.default_rng(1)
for _ in range(15):
    keys["hm_shoulders"] = float(rng.uniform(-1, 1))
    keys.update_tag()
    t = time.perf_counter()
    ev(body)
    ts.append((time.perf_counter() - t) * 1000)
R["reference_shape_keys_plus_subsurf1_ms"] = round(statistics.median(ts), 1)
(OUT / "gn_subsurf.json").write_text(json.dumps(R, indent=1), encoding="utf-8")
print("GNSUB_DONE")
