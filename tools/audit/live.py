import sys, types, bpy
sys.path.insert(0, (__import__("os").environ.get("HL_SCRATCHPAD", "scratchpad") + r"\hl"))
import extension
for n in ("bl_ext", "bl_ext.user_default"): sys.modules.setdefault(n, types.ModuleType(n))
sys.modules["bl_ext.user_default.human_modeling"] = extension
extension.register()
def setup():
    win = bpy.context.window_manager.windows[0]
    area = next(a for a in win.screen.areas if a.type == "VIEW_3D")
    area.spaces[0].show_region_ui = True
    next(r for r in area.regions if r.type == "UI").active_panel_category = "Humain"
    return None
bpy.app.timers.register(setup, first_interval=1.5)
