import sys, types, bpy, json
from pathlib import Path
SP = Path((__import__("os").environ.get("HL_SCRATCHPAD", "scratchpad") + r""))
sys.path.insert(0, str(SP / "hl")); import extension
for n in ("bl_ext", "bl_ext.user_default"): sys.modules.setdefault(n, types.ModuleType(n))
sys.modules["bl_ext.user_default.human_modeling"] = extension; extension.register()
R = {}; st = {"n": 0}
def ov():
    win = bpy.context.window_manager.windows[0]; area = next(a for a in win.screen.areas if a.type == "VIEW_3D")
    return bpy.context.temp_override(window=win, screen=win.screen, area=area, region=next(r for r in area.regions if r.type == "WINDOW"))
def tryundo(tag):
    try:
        with ov(): bpy.ops.ed.undo()
        return "ok"
    except Exception as e: return "ERR " + str(e)[:90]
def tick():
    n = st["n"]; st["n"] += 1
    try:
      with ov():
        if n == 0: bpy.ops.human_modeling.create(); bpy.ops.ed.undo_push(message="after create")
        elif n == 1:
            b = bpy.context.object; R["profile_before"] = float(b.data.shape_keys["hm_muscles"]); bpy.ops.human_modeling.body_profile(profile="MUSCLE"); R["profile_after"] = float(b.data.shape_keys["hm_muscles"])
        elif n == 2:
            R["names_before_undo"] = [o.name for o in bpy.data.objects]; R["undo_result"] = tryundo("p"); R["names_after_undo"] = [o.name for o in bpy.data.objects]; b = next((o for o in bpy.data.objects if o.get("human_modeling_body")), None); R["profile_after_undo"] = float(b.data.shape_keys["hm_muscles"]) if b else None
        elif n == 3:
            b = next((o for o in bpy.data.objects if o.get("human_modeling_body")), None); bpy.context.view_layer.objects.active = b; b.select_set(True)
            R["scale_before"] = b.scale.z; bpy.ops.human_modeling.set_height(height=1.5); R["scale_after"] = b.scale.z
        elif n == 4:
            R["undo_height_result"] = tryundo("h"); b = next((o for o in bpy.data.objects if o.get("human_modeling_body")), None); R["scale_after_undo"] = b.scale.z if b else None
        elif n == 5:
            b = next((o for o in bpy.data.objects if o.get("human_modeling_body")), None); bpy.context.view_layer.objects.active = b; R["objs0"] = len(bpy.data.objects); bpy.ops.humanloom.groom_preset(preset="SHORT"); R["objs1"] = len(bpy.data.objects)
        elif n == 6:
            R["undo_groom_result"] = tryundo("g"); R["objs2"] = len(bpy.data.objects)
        elif n == 7:
            R["names"] = [o.name for o in bpy.data.objects]; json.dump(R, open(SP / "ui2_out" / "gui3.json", "w"), indent=1); bpy.ops.wm.quit_blender(); return None
    except Exception as e: R[f"err_{n}"] = f"{type(e).__name__}: {str(e)[:150]}"
    return 1.5
bpy.app.timers.register(tick, first_interval=2.0)
