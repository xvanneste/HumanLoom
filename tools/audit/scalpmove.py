import bpy
from extension import groom
bpy.ops.human_modeling.create(); b = bpy.context.object
bpy.context.view_layer.objects.active = b
bpy.ops.humanloom.groom_preset(preset="ALL")
for r in ("SCALP", "BROWS", "ARMS"):
    h = groom.find(b, r)
    g = bpy.data.node_groups.new("T" + r, "GeometryNodeTree")
    g.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry"); g.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    gi = g.nodes.new("NodeGroupInput"); go = g.nodes.new("NodeGroupOutput"); g.links.new(gi.outputs[0], go.inputs[0])
    m = h.modifiers.new("Probe", "NODES"); m.node_group = g
    before = [x.name for x in h.modifiers]
    idx = [x.name for x in h.modifiers].index("Probe"); h.modifiers.move(idx, 0)
    print("MOVE", r, before, "->", [x.name for x in h.modifiers])
