import bpy, json, sys
import numpy as np
from pathlib import Path
OUT = Path(sys.argv[-1])
R = {}
lib = str(OUT / "assets_lib.blend")

def coords(b):
    if b.data.shape_keys:
        b.data.shape_keys.update_tag()
    bpy.context.view_layer.update()
    e = b.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = e.to_mesh()
    a = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", a)
    e.to_mesh_clear()
    return a

# 1) append from the asset file (Asset Browser 'Append')
with bpy.data.libraries.load(lib, assets_only=True, link=False) as (src, dst):
    R["assets_in_file"] = list(src.collections)
    dst.collections = list(src.collections)
col = dst.collections[0]
bpy.context.scene.collection.children.link(col)
body = [o for o in col.all_objects if o.get("human_modeling_body")][0]
ks = body.data.shape_keys
R["appended"] = {"objects": len(col.all_objects), "drivers_invalid": sum(1 for d in ks.animation_data.drivers if not d.driver.is_valid)}
a = coords(body)
ks["hm_shoulders"] = 0.8
R["appended"]["responds_mm"] = round(float(np.abs(coords(body) - a).max()) * 1000, 3)
hair = [o for o in col.all_objects if o.type == "CURVES"]
R["appended"]["hair_evaluated_curves"] = [len(h.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.curves) for h in hair]
# 2) link + library override
try:
    with bpy.data.libraries.load(lib, assets_only=True, link=True) as (src, dst):
        dst.collections = list(src.collections)
    lcol = dst.collections[0]
    inst = bpy.data.objects.new("inst", None)
    inst.instance_type = "COLLECTION"
    inst.instance_collection = lcol
    bpy.context.scene.collection.objects.link(inst)
    R["link"] = {"linked_collection": lcol.name, "library": lcol.library.filepath[-20:] if lcol.library else None}
    ov = lcol.override_hierarchy_create(bpy.context.scene, bpy.context.view_layer, do_fully_editable=True)
    R["override"] = {"created": ov is not None, "collection": ov.name if ov else None}
    if ov:
        ob = [o for o in ov.all_objects if o.get("human_modeling_body")][0]
        oks = ob.data.shape_keys
        R["override"]["body_is_override"] = ob.override_library is not None
        R["override"]["keys_is_override"] = oks.override_library is not None
        R["override"]["drivers_invalid"] = sum(1 for d in oks.animation_data.drivers if not d.driver.is_valid)
        b0 = coords(ob)
        try:
            oks["hm_shoulders"] = 0.9
            R["override"]["edit_custom_prop_on_override_moves_mm"] = round(float(np.abs(coords(ob) - b0).max()) * 1000, 3)
        except Exception as e:
            R["override"]["edit_custom_prop_err"] = str(e)[:150]
except Exception as e:
    R["link_override_err"] = type(e).__name__ + " " + str(e)[:200]
print("USEASSET", json.dumps(R, ensure_ascii=False))
