"""Option C, local basis per control + weights compiled from the drivers + attribute removal before subdivision."""
import ast, bpy, json, re, statistics, sys, time
import numpy as np
from collections import defaultdict
from pathlib import Path
from extension.proportions import CONTROLS

OUT = Path(sys.argv[-1])
OUT.mkdir(parents=True, exist_ok=True)
TOL = 1e-4
R = {"tolerance": TOL}
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
drivers = {d.data_path: d.driver for d in keys.animation_data.drivers}

def token(var):
    p = var.targets[0].data_path
    if p.startswith('["hm_'):
        return "hm_" + p[5:-2]
    if p == '["human_modeling_age"]':
        return "age"
    if 'key_blocks["Morphologie"].value' in p:
        return "sex"
    raise ValueError(p)

g = bpy.data.node_groups.new("HL_Human_C2", "GeometryNodeTree")
g.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
g.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
inputs = ["sex", "age"] + ["hm_" + c for c in CTRL]
for n in inputs:
    g.interface.new_socket(n, in_out="INPUT", socket_type="NodeSocketFloat")
gi = g.nodes.new("NodeGroupInput")
go = g.nodes.new("NodeGroupOutput")
sp = g.nodes.new("GeometryNodeSetPosition")
g.links.new(gi.outputs[0], sp.inputs["Geometry"])
sock = {n: gi.outputs[i + 1] for i, n in enumerate(inputs)}
OPS = {ast.Add: "ADD", ast.Sub: "SUBTRACT", ast.Mult: "MULTIPLY", ast.Div: "DIVIDE"}
cnt = {"math": 0}

CACHE = {}
def sid(v):
    return v if isinstance(v, (int, float)) else v.node.name + "|" + v.identifier

def mnode(op, a, b=None):
    key = (op, sid(a), sid(b) if b is not None else None)
    if op in ("ADD", "MULTIPLY", "MAXIMUM", "MINIMUM") and b is not None and str(key[1]) > str(key[2]):
        key = (op, key[2], key[1])
    if key in CACHE:
        return CACHE[key]
    out = _mnode(op, a, b)
    CACHE[key] = out
    return out

def _mnode(op, a, b=None):
    n = g.nodes.new("ShaderNodeMath")
    n.operation = op
    cnt["math"] += 1
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
        if all(isinstance(a, float) for a in args):
            return max(args) if f == "max" else min(args)
        return mnode("MAXIMUM" if f == "max" else "MINIMUM", args[0], args[1])
    raise ValueError(str(type(node)))

t0 = time.perf_counter()
const_offset = np.zeros(nv * 3, np.float64)
groups = defaultdict(list)
for k in blocks:
    path = 'key_blocks["' + k.name + '"].value'
    delta = (co(k) - co(k.relative_key)).astype(np.float64)
    if k.name == "Morphologie":
        w = sock["sex"]
    elif path in drivers:
        dr = drivers[path]
        env = {v.name: sock[token(v)] for v in dr.variables}
        w = comp(ast.parse(dr.expression.strip(), mode="eval"), env)
    else:
        const_offset += float(k.value) * delta
        continue
    if isinstance(w, float):
        const_offset += w * delta
        continue
    if np.abs(delta).max() < 1e-9:
        continue
    w = mnode("MINIMUM", mnode("MAXIMUM", w, float(k.slider_min)), float(k.slider_max))
    m = re.search(r"HM · ([a-z_0-9]+)", k.name)
    groups[m.group(1) if m else "other:" + k.name].append((w, delta))
R["weights_compile_s"] = round(time.perf_counter() - t0, 1)
R["groups"] = len(groups)
R["math_nodes_for_weights"] = cnt["math"]

cmesh = body.data.copy()
cobj = bpy.data.objects.new("HL_C2_body", cmesh)
bpy.context.scene.collection.objects.link(cobj)
cobj.shape_key_clear()
base3 = (base.astype(np.float64) + const_offset).astype(np.float32)
cmesh.vertices.foreach_set("co", base3)
cmesh.update()
t1 = time.perf_counter()
acc = None
nb = 0
for gname, items in groups.items():
    D = np.stack([d for _, d in items])
    U, S, Vt = np.linalg.svd(D, full_matrices=False)
    r = int((S > S[0] * TOL).sum())
    for j in range(r):
        basis = (S[j] * Vt[j]).astype(np.float32)
        a = cmesh.attributes.new("b" + str(nb), "FLOAT_VECTOR", "POINT")
        a.data.foreach_set("vector", basis)
        wj = None
        for i, (w, _) in enumerate(items):
            c = float(U[i, j])
            if abs(c) < 1e-9:
                continue
            term = mnode("MULTIPLY", w, c)
            wj = term if wj is None else mnode("ADD", wj, term)
        na = g.nodes.new("GeometryNodeInputNamedAttribute")
        na.data_type = "FLOAT_VECTOR"
        na.inputs["Name"].default_value = "b" + str(nb)
        sc = g.nodes.new("ShaderNodeVectorMath")
        sc.operation = "SCALE"
        g.links.new(na.outputs["Attribute"], sc.inputs[0])
        g.links.new(wj, sc.inputs[3])
        if acc is None:
            acc = sc.outputs[0]
        else:
            ad = g.nodes.new("ShaderNodeVectorMath")
            ad.operation = "ADD"
            g.links.new(acc, ad.inputs[0])
            g.links.new(sc.outputs[0], ad.inputs[1])
            acc = ad.outputs[0]
        nb += 1
g.links.new(acc, sp.inputs["Offset"])
rm = g.nodes.new("GeometryNodeRemoveAttribute")
rm.inputs["Pattern Mode"].default_value = "Wildcard"
rm.inputs["Name"].default_value = "b*"
g.links.new(sp.outputs["Geometry"], rm.inputs["Geometry"])
g.links.new(rm.outputs["Geometry"], go.inputs[0])
R["basis_attributes"] = nb
R["blend_build_s"] = round(time.perf_counter() - t1, 1)
R["total_nodes"] = len(g.nodes)
md = cobj.modifiers.new("HL Human", "NODES")
md.node_group = g
ids = {s.name: s.identifier for s in g.interface.items_tree if s.item_type == "SOCKET" and s.in_out == "INPUT" and s.name in inputs}

def setkey(n, v):
    if n == "sex":
        keys.key_blocks["Morphologie"].value = v
    elif n == "age":
        keys["human_modeling_age"] = v
    else:
        keys[n] = v

def setgn(n, v):
    getattr(md.properties.inputs, ids[n]).value = float(v)

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

rng = np.random.default_rng(3)
errs = []
for trial in range(15):
    st = {n: float(rng.uniform(-1, 1)) for n in inputs if n.startswith("hm_")}
    st["age"] = float(rng.uniform(0, 3))
    st["sex"] = float(rng.uniform(0, 1))
    for n, v in st.items():
        setkey(n, v)
        setgn(n, v)
    errs.append(float(np.abs(ev(body) - ev(cobj)).max()))
for age in (0.0, 1.0, 2.0, 3.0):
    for sex in (0.0, 1.0):
        for n in inputs:
            if n.startswith("hm_"):
                setkey(n, 1.0)
                setgn(n, 1.0)
        setkey("age", age); setgn("age", age); setkey("sex", sex); setgn("sex", sex)
        errs.append(float(np.abs(ev(body) - ev(cobj)).max()))
R["max_error_mm_over_%d_states" % len(errs)] = round(max(errs) * 1000, 4)
R["median_error_mm"] = round(statistics.median(errs) * 1000, 4)
for n in inputs:
    setkey(n, 0.0 if n != "age" else 2.0)
    setgn(n, 0.0 if n != "age" else 2.0)
setkey("sex", 1.0); setgn("sex", 1.0)

def time_it(setter, obj, n=30):
    ts = []
    r = np.random.default_rng(1)
    for _ in range(n):
        setter("hm_" + CTRL[int(r.integers(len(CTRL)))], float(r.uniform(-1, 1)))
        t = time.perf_counter()
        ev(obj)
        ts.append((time.perf_counter() - t) * 1000)
    return round(statistics.median(ts), 1), round(sorted(ts)[int(.9 * len(ts))], 1)

R["ms_nodes_only"] = time_it(setgn, cobj)
s = cobj.modifiers.new("sub", "SUBSURF")
s.levels = 1
R["ms_nodes_plus_subsurf1"] = time_it(setgn, cobj)
cobj.modifiers.remove(s)
s2 = body.modifiers.new("sub", "SUBSURF")
s2.levels = 1
R["ms_reference_shape_keys_plus_subsurf1"] = time_it(setkey, body)
(OUT / "cproto3_1e4.json").write_text(json.dumps(R, indent=1, ensure_ascii=False), encoding="utf-8")
print("CPROTO2_DONE")
