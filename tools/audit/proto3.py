import bpy, json, sys
import numpy as np
from pathlib import Path
from extension import groom
OUT = Path(sys.argv[-1])
OUT.mkdir(parents=True, exist_ok=True)
R = {}
bpy.ops.human_modeling.create()
b = bpy.context.object
bpy.context.view_layer.objects.active = b
bpy.ops.humanloom.groom_preset(preset="SHORT")
hair = groom.find(b, "SCALP")
R["modifier_order_before"] = [m.name for m in hair.modifiers]
sc = bpy.context.scene

g = bpy.data.node_groups.new("HL_Trim_Proto", "GeometryNodeTree")
g.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
g.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
g.interface.new_socket("Growth", in_out="INPUT", socket_type="NodeSocketFloat")
gi = g.nodes.new("NodeGroupInput")
go = g.nodes.new("NodeGroupOutput")
tr = g.nodes.new("GeometryNodeTrimCurve")
R["trim_node_inputs"] = [s.name for s in tr.inputs]
g.links.new(gi.outputs[0], tr.inputs["Curve"])
g.links.new(gi.outputs[1], tr.inputs["End"])
g.links.new(tr.outputs["Curve"], go.inputs[0])
md = hair.modifiers.new("HL Trim Proto", "NODES")
md.node_group = g
hair.modifiers.move(len(hair.modifiers) - 1, 0)
if False:
    pass
R["modifier_order_after"] = [m.name for m in hair.modifiers]
sid = [s.identifier for s in g.interface.items_tree if s.item_type == "SOCKET" and s.in_out == "INPUT" and s.name == "Growth"][0]
path = 'modifiers["' + md.name + '"].properties.inputs.' + sid + '.value'

def curve_stats():
    bpy.context.view_layer.update()
    d = hair.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
    n = len(d.curves)
    pos = np.empty(len(d.points) * 3)
    d.attributes["position"].data.foreach_get("vector", pos)
    pos = pos.reshape(-1, 3)
    lens = []
    for c in list(d.curves)[:200]:
        p = pos[c.first_point_index:c.first_point_index + c.points_length]
        lens.append(float(np.linalg.norm(np.diff(p, axis=0), axis=1).sum()))
    return n, round(float(np.mean(lens)), 4)

rows = []
for gval in (1.0, 0.5, 0.2, 0.0):
    getattr(md.properties.inputs, sid).value = gval
    rows.append((gval, curve_stats()))
R["growth_factor_vs_(evaluated_curves, mean_length_m)"] = rows
try:
    getattr(md.properties.inputs, sid).value = 0.0
    ok1 = hair.keyframe_insert(data_path=path, frame=1)
    getattr(md.properties.inputs, sid).value = 1.0
    ok2 = hair.keyframe_insert(data_path=path, frame=101)
    out = []
    for fr in (1, 26, 51, 76, 101):
        sc.frame_set(fr)
        out.append((fr, round(float(getattr(md.properties.inputs, sid).value), 3), curve_stats()))
    R["animation_frames_(frame, growth, (curves, mean_length_m))"] = out
    R["keyframe_ok"] = [ok1, ok2]
except Exception as e:
    R["animation_err"] = type(e).__name__ + " " + str(e)[:200]
(OUT / "proto3.json").write_text(json.dumps(R, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
print("PROTO3_DONE")
