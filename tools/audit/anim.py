import bpy, numpy as np
from extension import groom
sc = bpy.context.scene
bpy.ops.human_modeling.create(); b = bpy.context.object; k = b.data.shape_keys
for m in b.modifiers: m.show_viewport = False
def height():
    k.update_tag(); bpy.context.view_layer.update()
    e = b.evaluated_get(bpy.context.evaluated_depsgraph_get()); me = e.to_mesh(); a = np.empty(len(me.vertices)*3); me.vertices.foreach_get("co", a); e.to_mesh_clear(); a = a.reshape(-1,3)
    return round(float(np.ptp(a[:,2])),4), round(float(np.ptp(a[:,1])),4)
# 1. body keyframes on key custom properties
k["human_modeling_age"] = 0.0; k.keyframe_insert(data_path='["human_modeling_age"]', frame=1)
k["human_modeling_age"] = 3.0; k.keyframe_insert(data_path='["human_modeling_age"]', frame=101)
k["hm_whole_body"] = -1.0; k.keyframe_insert(data_path='["hm_whole_body"]', frame=1)
k["hm_whole_body"] = 1.0; k.keyframe_insert(data_path='["hm_whole_body"]', frame=101)
rows = []
for f in (1, 26, 51, 76, 101):
    sc.frame_set(f); rows.append({"frame": f, "age_stage": round(float(k["human_modeling_age"]), 3), "whole_body": round(float(k["hm_whole_body"]), 3), "height_depth_m": height()})
print("ANIM body", rows)
# 2. fcurve interpolation type and animation data location
# 3. hair modifier input keyframes
bpy.context.view_layer.objects.active = b
bpy.ops.humanloom.groom_preset(preset="SHORT"); hair = groom.find(b, "SCALP")
mod = hair.modifiers["HumanLoom · densité"]
ids = {}
for it in mod.node_group.interface.items_tree:
    if getattr(it, "in_out", "") == "INPUT": ids[it.name] = it.identifier
print("ANIM density inputs", {n: i for n, i in ids.items() if n in ("Density", "Viewport Amount")})
sid = ids["Density"]
mod[sid] = 0.0; mod.keyframe_insert(data_path=f'["{sid}"]', frame=1)
mod[sid] = 1800000.0; mod.keyframe_insert(data_path=f'["{sid}"]', frame=101)
res = []
for f in (1, 51, 101):
    sc.frame_set(f); bpy.context.view_layer.update(); res.append((f, len(hair.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.curves)))
print("ANIM hair density animated -> evaluated curves", res)
# 4. hair length (build-time property): keyframe and check effect
hair.hl_groom.length = 0.02; hair.hl_groom.keyframe_insert(data_path="length", frame=1)
hair.hl_groom.length = 0.30; hair.hl_groom.keyframe_insert(data_path="length", frame=101)
lens = []
for f in (1, 101):
    sc.frame_set(f); bpy.context.view_layer.update(); d = hair.data
    ln = [float(np.linalg.norm(np.diff(np.array([p.position[:] for p in c.points]), axis=0), axis=1).sum()) for c in list(d.curves)[:30]]
    lens.append((f, round(float(hair.hl_groom.length), 3), round(float(np.mean(ln)), 4)))
print("ANIM hair length property (frame, property, mean guide length m)", lens)
