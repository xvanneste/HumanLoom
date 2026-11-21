import bpy, numpy as np
from extension import groom
sc = bpy.context.scene
bpy.ops.human_modeling.create(); b = bpy.context.object
bpy.context.view_layer.objects.active = b
bpy.ops.humanloom.groom_preset(preset="SHORT"); hair = groom.find(b, "SCALP")
mod = hair.modifiers["HumanLoom · densité"]
sid = [s.identifier for s in mod.node_group.interface.items_tree if s.item_type == "SOCKET" and s.in_out == "INPUT" and s.name == "Density"][0]
path = f'modifiers["{mod.name}"].properties.inputs.{sid}.value'
def ev(): bpy.context.view_layer.update(); return len(hair.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.curves)
try:
    groom.set_input(mod, "Density", 0.0); ok1 = hair.keyframe_insert(data_path=path, frame=1)
    groom.set_input(mod, "Density", 1800000.0); ok2 = hair.keyframe_insert(data_path=path, frame=101)
    print("ANIM keyframe inserted", ok1, ok2, "path", path)
    out = []
    for f in (1, 26, 51, 101): sc.frame_set(f); out.append((f, round(float(getattr(mod.properties.inputs, sid).value)), ev()))
    print("ANIM hair density over frames (frame, density value, evaluated curves)", out)
except Exception as e: print("ANIM density keyframe ERR", type(e).__name__, str(e)[:200])
# length: build-time property
hair.hl_groom.length = 0.02; hair.hl_groom.keyframe_insert(data_path="length", frame=1)
hair.hl_groom.length = 0.30; hair.hl_groom.keyframe_insert(data_path="length", frame=101)
res = []
for f in (1, 101):
    sc.frame_set(f); bpy.context.view_layer.update(); d = hair.data
    ln = [float(np.linalg.norm(np.diff(np.array([p.position[:] for p in c.points]), axis=0), axis=1).sum()) for c in list(d.curves)[:30]]
    res.append((f, round(float(hair.hl_groom.length), 3), round(float(np.mean(ln)), 4)))
print("ANIM hair length (frame, animated property, actual mean guide length m)", res)
# groom trim candidate: does the stack expose a trim/length input?
print("ANIM native inputs of each modifier", {m.name: [s.name for s in m.node_group.interface.items_tree if s.item_type=="SOCKET" and s.in_out=="INPUT"][:12] for m in hair.modifiers if m.type=="NODES"})
