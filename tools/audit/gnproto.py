import bpy, time, statistics, numpy as np
bpy.ops.human_modeling.create(); body = bpy.context.object; keys = body.data.shape_keys
nv = len(body.data.vertices)
blocks = [k for k in keys.key_blocks if k != keys.reference_key]
def co(k): 
    a = np.empty(nv*3, np.float32); k.data.foreach_get("co", a); return a
base = co(keys.reference_key)
D = np.stack([co(k) - co(k.relative_key) for k in blocks]).astype(np.float32)
nz = [i for i in range(len(blocks)) if np.abs(D[i]).max() > 1e-7]
print("GN keys", len(blocks), "nonzero deltas", len(nz), "matrix MB", round(D.nbytes/1e6,1))
Dn = D[nz]
s = np.linalg.svd(Dn, compute_uv=False)
for tol in (1e-3, 1e-4, 1e-5):
    print("GN effective rank at", tol, "of max singular:", int((s > s[0]*tol).sum()))
by = {}
for k in blocks: by.setdefault(k.name.split(" · ")[0], []).append(k.name)
print("GN keys by prefix", {p: len(v) for p, v in by.items()})
# Prototype: blend R attribute morphs in Geometry Nodes
R = 100
hm = [k for k in blocks if k.name.startswith("HM · ")][:R]
R = len(hm)
mesh = bpy.data.meshes.new("gn_test"); mesh.from_pydata([v.co[:] for v in body.data.vertices], [], [])
for i, k in enumerate(hm):
    a = mesh.attributes.new(f"d{i}", "FLOAT_VECTOR", "POINT"); a.data.foreach_set("vector", co(k) - co(k.relative_key))
obj = bpy.data.objects.new("gn_test", mesh); bpy.context.scene.collection.objects.link(obj)
g = bpy.data.node_groups.new("HL_Blend", "GeometryNodeTree")
g.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry"); g.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
for i in range(R): g.interface.new_socket(f"W{i}", in_out="INPUT", socket_type="NodeSocketFloat")
gi = g.nodes.new("NodeGroupInput"); go = g.nodes.new("NodeGroupOutput"); sp = g.nodes.new("GeometryNodeSetPosition")
g.links.new(gi.outputs[0], sp.inputs["Geometry"]); g.links.new(sp.outputs["Geometry"], go.inputs[0])
acc = None
for i in range(R):
    na = g.nodes.new("GeometryNodeInputNamedAttribute"); na.data_type = "FLOAT_VECTOR"; na.inputs["Name"].default_value = f"d{i}"
    sc = g.nodes.new("ShaderNodeVectorMath"); sc.operation = "SCALE"
    g.links.new(na.outputs["Attribute"], sc.inputs[0]); g.links.new(gi.outputs[i+1], sc.inputs[3])
    if acc is None: acc = sc.outputs[0]
    else:
        ad = g.nodes.new("ShaderNodeVectorMath"); ad.operation = "ADD"; g.links.new(acc, ad.inputs[0]); g.links.new(sc.outputs[0], ad.inputs[1]); acc = ad.outputs[0]
g.links.new(acc, sp.inputs["Offset"])
md = obj.modifiers.new("gn", "NODES"); md.node_group = g
ids = [s.identifier for s in g.interface.items_tree if s.item_type == "SOCKET" and s.in_out == "INPUT" and s.name.startswith("W")]
rng = np.random.default_rng(1)
def evaluate():
    bpy.context.view_layer.update()
    e = obj.evaluated_get(bpy.context.evaluated_depsgraph_get()); m = e.to_mesh(); a = np.empty(nv*3); m.vertices.foreach_get("co", a); e.to_mesh_clear(); return a
times = []
for it in range(25):
    for sid in ids: getattr(md.properties.inputs, sid).value = float(rng.uniform(-1, 1)) if it % 2 == 0 else 0.0
    t = time.perf_counter(); r = evaluate(); times.append((time.perf_counter()-t)*1000)
print("GN blend", R, "targets via nodes: median ms", round(statistics.median(times),1), "max", round(max(times),1), "nodes", len(g.nodes))
# correctness: compare with numpy for last random state
for sid in ids: getattr(md.properties.inputs, sid).value = 0.5
r = evaluate().reshape(-1,3); exp = (base.reshape(-1,3) + 0.5*sum((co(k)-co(k.relative_key)).reshape(-1,3) for k in hm))
print("GN max error vs numpy mm", round(float(np.abs(r-exp).max())*1000,4), "attr MB", round(R*nv*12/1e6,1))
print("GN debug |r-base| mm", round(float(np.abs(r - base.reshape(-1,3)).max())*1000,3), "expected offset mm", round(float(np.abs(exp-base.reshape(-1,3)).max())*1000,3))
print("GN debug first socket value", getattr(md.properties.inputs, ids[0]).value, "ids sample", ids[:3], "inputs attrs", [a for a in dir(md.properties.inputs) if not a.startswith('_')][:6])
obj.update_tag(); bpy.context.view_layer.update()
e = obj.evaluated_get(bpy.context.evaluated_depsgraph_get()); print("GN debug evaluated modifiers", [m.name for m in e.modifiers], "verts", len(e.data.vertices))
r2 = evaluate().reshape(-1,3); print("GN debug2 |r2-base| mm", round(float(np.abs(r2 - base.reshape(-1,3)).max())*1000,3))
a0 = np.empty(nv*3, np.float32); mesh.attributes["d0"].data.foreach_get("vector", a0); print("GN debug attr d0 max", float(np.abs(a0).max()))
