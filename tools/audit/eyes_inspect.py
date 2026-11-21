import bpy
bpy.ops.human_modeling.create(); b = bpy.context.object
print("EYE body modifiers", [(m.name, m.type) for m in b.modifiers])
e = [c for c in b.children if c.type == "MESH"][0]
ks = e.data.shape_keys
print("EYE keys", [k.name for k in ks.key_blocks], "n drivers", len(ks.animation_data.drivers))
for d in ks.animation_data.drivers:
    dr = d.driver
    print("EYE driver", d.data_path, "|", dr.expression, "|", [(v.name, v.targets[0].id_type, v.targets[0].id.name if v.targets[0].id else None, v.targets[0].data_path) for v in dr.variables])
print("EYE parent", e.parent.name, e.parent_type, "mesh verts", len(e.data.vertices))
