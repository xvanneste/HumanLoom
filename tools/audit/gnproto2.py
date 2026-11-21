import bpy, time, statistics, numpy as np
bpy.ops.human_modeling.create(); body = bpy.context.object; keys = body.data.shape_keys
nv = len(body.data.vertices)
blocks = [k for k in keys.key_blocks if k != keys.reference_key]
def co(k): a = np.empty(nv*3, np.float32); k.data.foreach_get("co", a); return a
base = co(keys.reference_key)
deltas = [co(k) - co(k.relative_key) for k in blocks]
def run(R):
    mesh = bpy.data.meshes.new(f"gn{R}"); mesh.from_pydata(base.reshape(-1,3).tolist(), [], [])
    for i in range(R):
        a = mesh.attributes.new(f"d{i}", "FLOAT_VECTOR", "POINT"); a.data.foreach_set("vector", deltas[i])
    obj = bpy.data.objects.new(f"gn{R}", mesh); bpy.context.scene.collection.objects.link(obj)
    g = bpy.data.node_groups.new(f"G{R}", "GeometryNodeTree")
    g.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry"); g.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    for i in range(R): g.interface.new_socket(f"W{i}", in_out="INPUT", socket_type="NodeSocketFloat")
    gi = g.nodes.new("NodeGroupInput"); go = g.nodes.new("NodeGroupOutput"); sp = g.nodes.new("GeometryNodeSetPosition")
    g.links.new(gi.outputs[0], sp.inputs["Geometry"]); g.links.new(sp.outputs["Geometry"], go.inputs[0]); acc = None
    for i in range(R):
        na = g.nodes.new("GeometryNodeInputNamedAttribute"); na.data_type = "FLOAT_VECTOR"; na.inputs["Name"].default_value = f"d{i}"
        sc = g.nodes.new("ShaderNodeVectorMath"); sc.operation = "SCALE"; g.links.new(na.outputs["Attribute"], sc.inputs[0]); g.links.new(gi.outputs[i+1], sc.inputs[3])
        if acc is None: acc = sc.outputs[0]
        else: ad = g.nodes.new("ShaderNodeVectorMath"); ad.operation = "ADD"; g.links.new(acc, ad.inputs[0]); g.links.new(sc.outputs[0], ad.inputs[1]); acc = ad.outputs[0]
    g.links.new(acc, sp.inputs["Offset"])
    md = obj.modifiers.new("gn", "NODES"); md.node_group = g
    ids = [s.identifier for s in g.interface.items_tree if s.item_type == "SOCKET" and s.in_out == "INPUT" and s.name.startswith("W")]
    def ev(): 
        obj.update_tag(); bpy.context.view_layer.update(); e = obj.evaluated_get(bpy.context.evaluated_depsgraph_get()); m = e.to_mesh(); a = np.empty(nv*3, np.float32); m.vertices.foreach_get("co", a); e.to_mesh_clear(); return a
    rng = np.random.default_rng(2); times = []
    for it in range(30):
        w = rng.uniform(-1, 1, R)
        for sid, v in zip(ids, w): getattr(md.properties.inputs, sid).value = float(v)
        t = time.perf_counter(); r = ev(); times.append((time.perf_counter()-t)*1000)
    exp = base + sum(float(w[i])*deltas[i] for i in range(R))
    print("GN R=", R, "median ms", round(statistics.median(times),1), "p90 ms", round(sorted(times)[int(.9*len(times))],1), "max err mm", round(float(np.abs(r-exp).max())*1000,5), "attr MB", round(R*nv*12/1e6,1), "nodes", len(g.nodes))
for R in (50, 150, 300, 457): run(R)
