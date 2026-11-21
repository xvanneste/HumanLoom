import sys, types, bpy
from pathlib import Path
ROOT = (__import__("os").environ.get("HL_SCRATCHPAD", "scratchpad") + r"\hl")
OUT = Path((__import__("os").environ.get("HL_SCRATCHPAD", "scratchpad") + r"\ui_out")); OUT.mkdir(exist_ok=True)
sys.path.insert(0, ROOT)
import extension
for n in ("bl_ext", "bl_ext.user_default"): sys.modules.setdefault(n, types.ModuleType(n))
sys.modules["bl_ext.user_default.human_modeling"] = extension
# expand every sub-panel by default for the capture
for name in dir(extension):
    c = getattr(extension, name)
    if isinstance(c, type) and issubclass(c, bpy.types.Panel):
        c.bl_options = set()
from extension import groom
for name in dir(groom):
    c = getattr(groom, name)
    if isinstance(c, type) and issubclass(c, bpy.types.Panel): c.bl_options = set()
extension.register()
state = {"step": 0}
def view3d():
    win = bpy.context.window_manager.windows[0]
    for a in win.screen.areas:
        if a.type == "VIEW_3D": return win, a
def tick():
    win, area = view3d()
    s = state["step"]; state["step"] += 1
    with bpy.context.temp_override(window=win, area=area, region=next(r for r in area.regions if r.type == "WINDOW")):
        if s == 0:
            bpy.ops.human_modeling.create()
            area.spaces[0].show_region_ui = True
            bpy.ops.screen.screen_full_area()
            return 1.0
    win, area = view3d()
    ui = next(r for r in area.regions if r.type == "UI")
    if s == 1:
        ui.active_panel_category = "Humain"
        return 1.0
    if s == 2:
        with bpy.context.temp_override(window=win, area=area, region=ui):
            bpy.ops.screen.screenshot_area(filepath=str(OUT / "panel_top.png"))
        return 1.0
    if s >= 3 and s < 12:
        # scroll the sidebar and capture successive pages
        with bpy.context.temp_override(window=win, area=area, region=ui):
            for _ in range(14): bpy.ops.view2d.scroll_down(deltax=0, deltay=1)
            bpy.ops.screen.screenshot_area(filepath=str(OUT / f"panel_{s:02d}.png"))
        return 1.0
    print("GUI_DONE", [ (p.bl_label) for p in []])
    bpy.ops.wm.quit_blender()
    return None
bpy.app.timers.register(tick, first_interval=2.0)
