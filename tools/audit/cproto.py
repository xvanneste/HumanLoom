"""Option C end-to-end prototype: body deformation by a Geometry Nodes group whose weights are compiled from the real drivers."""
import ast, bpy, json, statistics, sys, time
import numpy as np
from pathlib import Path
from extension.proportions import CONTROLS
from extension import groom, measurements

OUT = Path(sys.argv[-1])
OUT.mkdir(parents=True, exist_ok=True)
R = {}
bpy.ops.human_modeling.create()
body = bpy.context.object
keys = body.data.shape_keys
for m in body.modifiers:
    m.show_viewport = False
nv = len(body.data.vertices)
CTRL = [c[0] for c in CONTROLS]

def co(k):
    a = np.empty(nv * 3, np.float32)
    k.data.foreach_get("co", a)
    return a

base = co(keys.reference_key)
blocks = [k for k in keys.key_blocks if k != keys.reference_key]
drivers = {}
for d in keys.animation_data.drivers:
    drivers[d.data_path] = d.driver

def token(var):
    t = var.targets[0]
    p = t.data_path
    if p.startswith('["hm_'):
        return "hm_" + p[5:-2]
    if p == '["human_modeling_age"]':
        return "age"
    if 'key_blocks["Morphologie"].value' in p:
        return "sex"
    raise ValueError("unknown target " + p)

# ---- build node group
g = bpy.data.node_groups.new("HL_Human_C", "GeometryNodeTree")
g.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
g.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
inputs = ["sex", "age"] + ["hm_" + c for c in CTRL]
for n in inputs:
    g.interface.new_socket(n, in_out="INPUT", socket_type="NodeSocketFloat")
gi = g.nodes.new("NodeGroupInput")
go = g.nodes.new("NodeGroupOutput")
sp = g.nodes.new("GeometryNodeSetPosition")
g.links.new(gi.outputs[0], sp.inputs["Geometry"])
g.links.new(sp.outputs["Geometry"], go.inputs[0])
sock = {n: gi.outputs[i + 1] for i, n in enumerate(inputs)}
OPS = {ast.Add: "ADD", ast.Sub: "SUBTRACT", ast.Mult: "MULTIPLY", ast.Div: "DIVIDE"}
FUNC = {"max": "MAXIMUM", "min": "MINIMUM", "abs": "ABSOLUTE"}
math_count = {"n": 0}

def mnode(op, a, b=None):
    n = g.nodes.new("ShaderNodeMath")
    n.operation = op
    math_count["n"] += 1
    for i, v in enumerate((a, b)):
        if v is None:
            continue
        if isinstance(v, (int, float)):
            n.inputs[i].default_value = float(v)
        else:
            g.links.new(v, n.inputs[i])
    return n.outputs[0]

def comp(node, env):
    if isinstance(node, ast.Expression):
        return comp(node.body, env)
    if isinstance(node, ast.Constant):
        return float(node.value)
    if isinstance(node, ast.Name):
        return env[node.id]
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        v = comp(node.operand, env)
        return -v if isinstance(v, float) else mnode("MULTIPLY", v, -1.0)
    if isinstance(node, ast.BinOp):
        a = comp(node.left, env)
        b = comp(node.right, env)
        if isinstance(a, float) and isinstance(b, float):
            return {ast.Add: a + b, ast.Sub: a - b, ast.Mult: a * b, ast.Div: a / b}[type(node.op)]
        return mnode(OPS[type(node.op)], a, b)
    if isinstance(node, ast.Call):
        f = node.func.id
        args = [comp(a, env) for a in node.args]
        if f == "abs":
            return abs(args[0]) if isinstance(args[0], float) else mnode("ABSOLUTE", args[0])
        if len(args) == 2:
            if all(isinstance(a, float) for a in args):
                return max(args) if f == "max" else min(args)
            return mnode(FUNC[f], args[0], args[1])
        raise ValueError("arity " + f)
    raise ValueError("node " + str(type(node)))

weights = []
const_offset = np.zeros(nv * 3, np.float64)
used = []
t0 = time.perf_counter()
for k in blocks:
    path = 'key_blocks["' + k.name + '"].value'
    delta = (co(k) - co(k.relative_key)).astype(np.float32)
    if k.name == "Morphologie":
        w = sock["sex"]
    elif path in drivers:
        dr = drivers[path]
        env = {v.name: sock[token(v)] for v in dr.variables}
        w = comp(ast.parse(dr.expression.strip(), mode="eval"), env)
    else:
        const_offset += float(k.value) * delta.astype(np.float64)
        continue
    if isinstance(w, float):
        const_offset += w * delta.astype(np.float64)
        continue
    if np.abs(delta).max() < 1e-9:
        continue
    w = mnode("MAXIMUM", w, float(k.slider_min))
    w = mnode("MINIMUM", w, float(k.slider_max))
    weights.append((len(used), w, delta))
    used.append(k.name)
R["keys_total"] = len(blocks)
R["keys_with_nodes"] = len(used)
R["math_nodes"] = math_count["n"]
R["compile_weights_s"] = round(time.perf_counter() - t0, 2)

# mesh carrier
bm = bpy.data.meshes.new("HL_C_body")
base3 = (base + const_offset.astype(np.float32)).reshape(-1, 3)
bm.from_pydata(base3.tolist(), [], [])
src = body.data
bm.polygons.add(0) if False else None
cobj = None
# copy topology/UV by copying the original mesh and clearing its keys
cmesh = body.data.copy()
cobj = bpy.data.objects.new("HL_C_body", cmesh)
bpy.context.scene.collection.objects.link(cobj)
cobj.shape_key_clear()
cmesh.vertices.foreach_set("co", base3.reshape(-1))
cmesh.update()
for i, w, delta in weights:
    a = cmesh.attributes.new("d" + str(i), "FLOAT_VECTOR", "POINT")
    a.data.foreach_set("vector", delta)
acc = None
t1 = time.perf_counter()
for i, w, delta in weights:
    na = g.nodes.new("GeometryNodeInputNamedAttribute")
    na.data_type = "FLOAT_VECTOR"
    na.inputs["Name"].default_value = "d" + str(i)
    sc = g.nodes.new("ShaderNodeVectorMath")
    sc.operation = "SCALE"
    g.links.new(na.outputs["Attribute"], sc.inputs[0])
    g.links.new(w, sc.inputs[3])
    if acc is None:
        acc = sc.outputs[0]
    else:
        ad = g.nodes.new("ShaderNodeVectorMath")
        ad.operation = "ADD"
        g.links.new(acc, ad.inputs[0])
        g.links.new(sc.outputs[0], ad.inputs[1])
        acc = ad.outputs[0]
g.links.new(acc, sp.inputs["Offset"])
R["blend_nodes_s"] = round(time.perf_counter() - t1, 2)
R["total_nodes"] = len(g.nodes)
md = cobj.modifiers.new("HL Human", "NODES")
md.node_group = g
ids = {s.name: s.identifier for s in g.interface.items_tree if s.item_type == "SOCKET" and s.in_out == "INPUT" and s.name in inputs}

def setkey(name, v):
    if name == "sex":
        keys.key_blocks["Morphologie"].value = v
    elif name == "age":
        keys["human_modeling_age"] = v
    else:
        keys[name] = v

def setgn(name, v):
    getattr(md.properties.inputs, ids[name]).value = float(v)

def ev(o):
    o.update_tag()
    keys.update_tag()
    bpy.context.view_layer.update()
    e = o.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = e.to_mesh()
    a = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", a)
    e.to_mesh_clear()
    return a

# ---- T-C6: compare to the real system
rng = np.random.default_rng(3)
errs = []
for trial in range(12):
    st = {n: float(rng.uniform(-1, 1)) for n in inputs if n.startswith("hm_")}
    st["age"] = float(rng.uniform(0, 3))
    st["sex"] = float(rng.uniform(0, 1))
    for n, v in st.items():
        setkey(n, v)
        setgn(n, v)
    errs.append(float(np.abs(ev(body) - ev(cobj)).max()))
# corner states
for age in (0.0, 1.0, 2.0, 3.0, 0.5, 2.5):
    for sex in (0.0, 1.0):
        for n in inputs:
            if n.startswith("hm_"):
                setkey(n, 1.0)
                setgn(n, 1.0)
        setkey("age", age); setgn("age", age); setkey("sex", sex); setgn("sex", sex)
        errs.append(float(np.abs(ev(body) - ev(cobj)).max()))
for n in inputs:
    if n.startswith("hm_"):
        setkey(n, -1.0); setgn(n, -1.0)
errs.append(float(np.abs(ev(body) - ev(cobj)).max()))
R["T_C6_max_error_mm_over_%d_states" % len(errs)] = round(max(errs) * 1000, 5)
R["T_C6_median_error_mm"] = round(statistics.median(errs) * 1000, 5)

# ---- T-C7 timing
for n in inputs:
    setkey(n, 0.0 if n != "age" else 2.0)
    setgn(n, 0.0 if n != "age" else 2.0)
setkey("sex", 1.0); setgn("sex", 1.0)
def time_it(setter, obj, n=40):
    ts = []
    r = np.random.default_rng(1)
    for _ in range(n):
        name = "hm_" + CTRL[int(r.integers(len(CTRL)))]
        setter(name, float(r.uniform(-1, 1)))
        t = time.perf_counter()
        ev(obj)
        ts.append((time.perf_counter() - t) * 1000)
    return round(statistics.median(ts), 1), round(sorted(ts)[int(.9 * len(ts))], 1)
R["T_C7_slider_ms_median_p90"] = {"shape_keys_and_459_drivers": time_it(setkey, body), "geometry_nodes_group": time_it(setgn, cobj)}
cobj.modifiers.new("sub", "SUBSURF").levels = 1
bpy.context.view_layer.update()
R["T_C7_with_subsurf1_ms_median_p90"] = time_it(setgn, cobj)
cobj.modifiers.remove(cobj.modifiers["sub"])
R["T_C9_measure_height_m"] = {"keys": round(measurements.measure(body, bpy.context)["height_m"], 4), "nodes": round(measurements.measure(cobj, bpy.context)["height_m"], 4)}

# ---- T-C8 eyes retargeted to the node modifier inputs
eyes = [c for c in body.children if c.type == "MESH" and c.data.shape_keys]
new_eyes = []
for e in eyes:
    ne = e.copy()
    ne.data = e.data.copy()
    bpy.context.scene.collection.objects.link(ne)
    ne.parent = cobj
    ne.matrix_parent_inverse = e.matrix_parent_inverse.copy()
    ne.name = "C " + e.name
    nk = ne.data.shape_keys
    for d in nk.animation_data.drivers:
        for v in d.driver.variables:
            t = v.targets[0]
            p = t.data_path
            if p.startswith('["hm_'):
                nm = "hm_" + p[5:-2]
            elif p == '["human_modeling_age"]':
                nm = "age"
            else:
                nm = "sex"
            t.id_type = "OBJECT"
            t.id = cobj
            t.data_path = 'modifiers["HL Human"].properties.inputs.' + ids[nm] + ".value"
    new_eyes.append(ne)
def eye_pos(eobj):
    eobj.data.shape_keys.update_tag()
    bpy.context.view_layer.update()
    ee = eobj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = ee.to_mesh()
    a = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", a)
    ee.to_mesh_clear()
    M = np.array(ee.matrix_world)
    return a.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3]
eerr = []
for trial in range(10):
    st = {n: float(rng.uniform(-1, 1)) for n in inputs if n.startswith("hm_")}
    st["age"] = float(rng.uniform(0, 3))
    st["sex"] = float(rng.uniform(0, 1))
    for n, v in st.items():
        setkey(n, v)
        setgn(n, v)
    bpy.context.view_layer.update()
    for e, ne in zip(eyes, new_eyes):
        # compare in the eye local space relative to the parent: use world positions relative to each body's origin
        a = eye_pos(e) - np.array(body.matrix_world.translation)
        b = eye_pos(ne) - np.array(cobj.matrix_world.translation)
        eerr.append(float(np.abs(a - b).max()))
R["T_C8_eyes_max_error_mm_10_states"] = round(max(eerr) * 1000, 5)
R["T_C8_invalid_eye_drivers"] = sum(1 for ne in new_eyes for d in ne.data.shape_keys.animation_data.drivers if not d.driver.is_valid)

# ---- T-C5 hair on the node-deformed body
for n in inputs:
    setgn(n, 0.0 if n != "age" else 2.0)
setgn("sex", 1.0)
cobj["human_modeling_body"] = True
cmesh["human_modeling_schema"] = 9
bpy.ops.object.select_all(action="DESELECT")
cobj.select_set(True)
bpy.context.view_layer.objects.active = cobj
try:
    r = bpy.ops.humanloom.groom_preset(preset="SHORT")
    R["T_C5_groom_build"] = list(r)[0]
    R["T_C5_body_modifier_stack_after_groom"] = [(m.name, m.type) for m in cobj.modifiers]
    hairs = [c for c in cobj.children if c.type == "CURVES"]
    R["T_C5_hair_objects"] = [(h.name, len(h.data.curves)) for h in hairs]
    from mathutils.bvhtree import BVHTree
    def gaps():
        cobj.update_tag(); bpy.context.view_layer.update()
        ee = cobj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        me = ee.to_mesh()
        t = BVHTree.FromPolygons([tuple(cobj.matrix_world @ v.co) for v in me.vertices], [tuple(p.vertices) for p in me.polygons])
        ee.to_mesh_clear()
        out = []
        for h in hairs:
            he = h.evaluated_get(bpy.context.evaluated_depsgraph_get())
            roots = [h.matrix_world @ c.points[0].position for c in he.data.curves][:300]
            out.append((h.name, round(float(np.median([t.find_nearest(x)[3] for x in roots])) * 1000, 3), round(float(np.max([t.find_nearest(x)[3] for x in roots])) * 1000, 3)))
        return out
    R["T_C5_root_gap_mm_neutral"] = gaps()
    for n in ("hm_head_width", "hm_shoulders", "hm_whole_body", "hm_legs"):
        setgn(n, 1.0)
    setgn("age", 0.0)
    R["T_C5_root_gap_mm_after_morph_and_age0"] = gaps()
except Exception as e:
    R["T_C5_error"] = type(e).__name__ + " " + str(e)[:300]
(OUT / "cproto.json").write_text(json.dumps(R, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
print("CPROTO_DONE")
