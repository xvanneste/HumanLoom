import sys, types, json, os
import bpy
from pathlib import Path

SP = Path((__import__("os").environ.get("HL_SCRATCHPAD", "scratchpad") + r""))
sys.path.insert(0, str(SP / "hl"))
import extension
for n in ("bl_ext", "bl_ext.user_default"):
    sys.modules.setdefault(n, types.ModuleType(n))
sys.modules["bl_ext.user_default.human_modeling"] = extension
extension.register()
OUT = SP / "proto_ui3"
OUT.mkdir(exist_ok=True)
RES = {}
st = {"n": 0}

def view(kind):
    win = bpy.context.window_manager.windows[0]
    for a in win.screen.areas:
        if a.type == kind:
            return win, a

def shot(name):
    w, a = view("VIEW_3D")
    ui = next(r for r in a.regions if r.type == "UI")
    with bpy.context.temp_override(window=w, area=a, region=ui):
        bpy.ops.screen.screenshot_area(filepath=str(OUT / (name + ".png")))

def tick():
    n = st["n"]
    st["n"] += 1
    try:
        if n == 0:
            w, a = view("VIEW_3D")
            with bpy.context.temp_override(window=w, area=a, region=next(r for r in a.regions if r.type == "WINDOW")):
                bpy.ops.human_modeling.create()
                bpy.ops.humanloom.groom_preset(preset="SHORT")
            a.spaces[0].show_region_ui = True
            return 1.5
        if n == 1:
            w, a = view("VIEW_3D")
            next(r for r in a.regions if r.type == "UI").active_panel_category = "Humain"
            return 1.5
        if n == 2:
            shot("dark_default")
            return 0.5
        if n == 3:
            bpy.context.preferences.view.ui_scale = 1.5
            return 1.5
        if n == 4:
            shot("dark_scale_1_5")
            return 0.5
        if n == 5:
            bpy.context.preferences.view.ui_scale = 1.0
            paths = bpy.utils.preset_paths("interface_theme")
            found = None
            for p in paths:
                for f in os.listdir(p):
                    if "light" in f.lower():
                        found = os.path.join(p, f)
            RES["light_preset"] = found
            if found:
                bpy.ops.script.execute_preset(filepath=found, menu_idname="USERPREF_MT_interface_theme_presets")
            return 2.0
        if n == 6:
            shot("light_default")
            RES["done"] = True
            (OUT / "res.json").write_text(json.dumps(RES, indent=1), encoding="utf-8")
            return 0.5
        if n == 7:
            bpy.ops.wm.quit_blender()
            return None
    except Exception as e:
        RES["err_%d" % n] = str(e)[:200]
        (OUT / "res.json").write_text(json.dumps(RES, indent=1), encoding="utf-8")
    return None

bpy.app.timers.register(tick, first_interval=2.5)
