import sys, types, bpy, json, traceback
from pathlib import Path
SP = Path((__import__("os").environ.get("HL_SCRATCHPAD", "scratchpad") + r""))
sys.path.insert(0, str(SP / "hl"))
import extension
for n in ("bl_ext", "bl_ext.user_default"): sys.modules.setdefault(n, types.ModuleType(n))
sys.modules["bl_ext.user_default.human_modeling"] = extension
from extension import groom
for mod in (extension, groom):
    for name in dir(mod):
        c = getattr(mod, name)
        if isinstance(c, type) and issubclass(c, bpy.types.Panel): c.bl_options = set()
extension.register()
OUT = SP / "ui2_out"; OUT.mkdir(exist_ok=True)
R = {}
def view():
    win = bpy.context.window_manager.windows[0]
    area = next(a for a in win.screen.areas if a.type == "VIEW_3D"); return win, area
def ctx():
    win, area = view(); region = next(r for r in area.regions if r.type == "WINDOW")
    return bpy.context.temp_override(window=win, area=area, region=region)
def shot(name, scroll=0):
    win, area = view(); ui = next(r for r in area.regions if r.type == "UI")
    with bpy.context.temp_override(window=win, area=area, region=ui):
        for _ in range(scroll): bpy.ops.view2d.scroll_down(deltax=0, deltay=1)
        bpy.ops.screen.screenshot_area(filepath=str(OUT / f"{name}.png"))
def keyv(b, k): return round(float(b.data.shape_keys[k]), 4)
S = {}
def s0():
    with ctx():
        bpy.ops.human_modeling.create(); area = view()[1]; area.spaces[0].show_region_ui = True; bpy.ops.screen.screen_full_area()
def s1():
    win, area = view(); next(r for r in area.regions if r.type == "UI").active_panel_category = "Humain"
def s2():   # undo tests
    with ctx():
        b = bpy.context.object; S["b"] = b.name
        R["undo_profile"] = {"before": keyv(b, "hm_muscles")}
        bpy.ops.human_modeling.body_profile(profile="MUSCLE"); R["undo_profile"]["after"] = keyv(b, "hm_muscles")
        try: bpy.ops.ed.undo(); R["undo_profile"]["after_undo"] = keyv(bpy.data.objects[S["b"]], "hm_muscles")
        except Exception as e: R["undo_profile"]["after_undo"] = "ERR " + str(e)[:100]
        try: bpy.ops.ed.redo(); R["undo_profile"]["after_redo"] = keyv(bpy.data.objects[S["b"]], "hm_muscles")
        except Exception as e: R["undo_profile"]["after_redo"] = "ERR " + str(e)[:100]
def s3():
    with ctx():
        b = bpy.data.objects[S["b"]]; bpy.context.view_layer.objects.active = b
        R["undo_height"] = {"before": round(b.scale.z, 4)}
        bpy.ops.human_modeling.set_height(height=1.5); R["undo_height"]["after"] = round(b.scale.z, 4)
        try: bpy.ops.ed.undo(); R["undo_height"]["after_undo"] = round(bpy.data.objects[S["b"]].scale.z, 4)
        except Exception as e: R["undo_height"]["after_undo"] = "ERR " + str(e)[:100]
def s4():
    with ctx():
        b = bpy.data.objects[S["b"]]; bpy.context.view_layer.objects.active = b
        n0 = len(bpy.data.objects); bpy.ops.humanloom.groom_preset(preset="ALL"); n1 = len(bpy.data.objects)
        try: bpy.ops.ed.undo(); n2 = len(bpy.data.objects)
        except Exception as e: n2 = "ERR " + str(e)[:100]
        R["undo_groom_all"] = {"objects_before": n0, "after_preset": n1, "after_undo": n2}
def s5():
    with ctx():
        b = bpy.data.objects[S["b"]]; bpy.context.view_layer.objects.active = b; b.select_set(True)
        n0 = len(bpy.data.objects); bpy.ops.human_modeling.create(); n1 = len(bpy.data.objects)
        try: bpy.ops.ed.undo(); n2 = len(bpy.data.objects)
        except Exception as e: n2 = "ERR " + str(e)[:100]
        R["undo_create"] = {"objects_before": n0, "after": n1, "after_undo": n2}
def s6():   # state: body only, shot top
    with ctx():
        b = bpy.data.objects[S["b"]]; bpy.ops.object.select_all(action="DESELECT"); b.select_set(True); bpy.context.view_layer.objects.active = b
        bpy.ops.humanloom.groom_preset(preset="ALL")
def s7(): shot("groom_panel", scroll=40)
def s8():
    with ctx():   # select eye
        b = bpy.data.objects[S["b"]]; eye = [c for c in b.children if c.type == "MESH"][0]
        bpy.ops.object.select_all(action="DESELECT"); eye.select_set(True); bpy.context.view_layer.objects.active = eye
def s9(): shot("state_eye_active_top")
def s10():
    with ctx():
        bpy.ops.object.select_all(action="DESELECT"); bpy.context.view_layer.objects.active = None
def s11(): shot("state_nothing_selected")
def s12():
    with ctx():
        b = bpy.data.objects[S["b"]]; bpy.context.view_layer.objects.active = b; b.select_set(True); bpy.ops.object.mode_set(mode="EDIT")
def s13(): shot("state_edit_mode_top"); shot("state_edit_mode_bottom", scroll=40)
def s14():
    with ctx(): bpy.ops.object.mode_set(mode="OBJECT")
    json.dump(R, open(OUT / "gui2.json", "w"), indent=1)
    bpy.ops.wm.quit_blender()
steps = [s0, s1, s2, s3, s4, s5, s6, s7, s8, s9, s10, s11, s12, s13, s14]
i = {"n": 0}
def tick():
    n = i["n"]; i["n"] += 1
    if n >= len(steps): return None
    try: steps[n]()
    except Exception as e: R[f"step_{n}_error"] = f"{type(e).__name__}: {str(e)[:200]}"; traceback.print_exc()
    return 1.5
bpy.app.timers.register(tick, first_interval=2.0)
