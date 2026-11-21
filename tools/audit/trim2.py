import bpy, numpy as np, json
from extension import groom
bpy.ops.human_modeling.create(); b = bpy.context.object
bpy.context.view_layer.objects.active = b
bpy.ops.humanloom.groom_preset(preset="SHORT")
h = groom.find(b, "SCALP")
g = bpy.data.node_groups.new("Trim", "GeometryNodeTree")
g.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry"); g.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry"); g.interface.new_socket("Growth", in_out="INPUT", socket_type="NodeSocketFloat")
gi = g.nodes.new("NodeGroupInput"); go = g.nodes.new("NodeGroupOutput"); tr = g.nodes.new("GeometryNodeTrimCurve")
g.links.new(gi.outputs[0], tr.inputs["Curve"]); g.links.new(gi.outputs[1], tr.inputs["End"]); g.links.new(tr.outputs["Curve"], go.inputs[0])
m = h.modifiers.new("Trim", "NODES"); m.node_group = g
h.modifiers.move([x.name for x in h.modifiers].index("Trim"), 0)
sid = [s.identifier for s in g.interface.items_tree if s.item_type == "SOCKET" and s.in_out == "INPUT" and s.name == "Growth"][0]
def stats():
    h.update_tag(); bpy.context.view_layer.update()
    d = h.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
    pos = np.empty(len(d.points) * 3); d.attributes["position"].data.foreach_get("vector", pos); pos = pos.reshape(-1, 3)
    L = [float(np.linalg.norm(np.diff(pos[c.first_point_index:c.first_point_index + c.points_length], axis=0), axis=1).sum()) for c in list(d.curves)[:300]]
    return len(d.curves), round(float(np.mean(L)), 4)
out = {"stack": [x.name for x in h.modifiers]}
for gv in (1.0, 0.5, 0.2, 0.0):
    getattr(m.properties.inputs, sid).value = gv
    out["growth_%s" % gv] = stats()
# with XPBD physics too
cfg = groom.state(h.hl_groom); 
print("TRIM2", json.dumps(out))
