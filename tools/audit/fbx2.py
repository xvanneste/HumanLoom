import bpy, os, time, sys
from pathlib import Path
OUT = Path(sys.argv[-1]); OUT.mkdir(exist_ok=True, parents=True)
bpy.ops.human_modeling.create()
b = bpy.context.object
b.data.shape_keys["hm_shoulders"] = 0.4
bpy.ops.object.select_all(action="DESELECT"); b.select_set(True); bpy.context.view_layer.objects.active = b
for tag, mods in (("fbx_no_modifiers", False), ("fbx_with_modifiers", True)):
    p = str(OUT / (tag + ".fbx")); t = time.perf_counter()
    try:
        r = bpy.ops.export_scene.fbx(filepath=p, use_selection=True, use_mesh_modifiers=mods, object_types={"MESH"})
        print("FBX2", tag, list(r)[0], round(time.perf_counter() - t, 1), "s", round(os.path.getsize(p) / 1e6, 1), "MB")
    except Exception as e:
        print("FBX2", tag, "ERR", str(e)[:200])
# re-import in a clean scene
for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
try:
    bpy.ops.wm.fbx_import(filepath=str(OUT / "fbx_no_modifiers.fbx"))
    m = [o for o in bpy.data.objects if o.type == "MESH"]
    print("FBX2 import objects", [(o.name, len(o.data.vertices), len(o.data.shape_keys.key_blocks) if o.data.shape_keys else 0) for o in m])
except Exception as e:
    print("FBX2 import ERR", str(e)[:200])
