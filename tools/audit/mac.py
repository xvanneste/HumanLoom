import sys, math, json
from pathlib import Path
import bpy, numpy as np
out = Path(sys.argv[sys.argv.index("--") + 1]); out.mkdir(parents=True, exist_ok=True)
sc = bpy.context.scene
sc.render.engine = "BLENDER_WORKBENCH"; sc.display.shading.light = "STUDIO"; sc.display.shading.color_type = "MATERIAL"
sc.world = bpy.data.worlds.new("w"); sc.world.color = (0.16, 0.16, 0.18); sc.display.render_aa = "8"
info = {}
def cam(theta, cx, cz, w, h, ppm):
    c = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(c); c.data.type = "ORTHO"; c.data.ortho_scale = w
    d = 10; c.location = (cx + d * math.sin(theta), -d * math.cos(theta), cz); c.rotation_euler = (math.radians(90), 0, theta)
    sc.camera = c; sc.render.resolution_x = int(w * ppm); sc.render.resolution_y = int(h * ppm); return c
def shoot(n): sc.render.filepath = str(out / f"{n}.png"); bpy.ops.render.render(write_still=True)
def fresh(sex):
    for o in tuple(sc.objects): bpy.data.objects.remove(o, do_unlink=True)
    sc.cursor.location = (0, 0, 0); bpy.ops.human_modeling.create(); b = bpy.context.object
    b.data.shape_keys.key_blocks["Morphologie"].value = sex; b.data.shape_keys.update_tag(); bpy.context.view_layer.update(); return b
b = fresh(1.0)
info["body"] = {"materials": [m.name if m else None for m in b.data.materials], "uv_layers": [u.name for u in b.data.uv_layers], "vertex_groups": [g.name for g in b.vertex_groups][:20],
                "n_vertex_groups": len(b.vertex_groups), "attributes": [a.name for a in b.data.attributes][:20], "polys": len(b.data.polygons), "vertices": len(b.data.vertices),
                "n_shape_keys": len(b.data.shape_keys.key_blocks), "shape_key_prefixes": sorted({k.name.split(" · ")[0] for k in b.data.shape_keys.key_blocks}),
                "custom_props": list(b.keys()), "mesh_props": list(b.data.keys())[:20], "key_props": [k for k in b.data.shape_keys.keys()][:80]}
info["eyes"] = [{"name": c.name, "verts": len(c.data.vertices), "materials": [m.name if m else None for m in c.data.materials], "uv": [u.name for u in c.data.uv_layers]} for c in b.children]
mat = b.data.materials[0] if b.data.materials else None
if mat and mat.use_nodes: info["skin_material_nodes"] = [n.bl_idname for n in mat.node_tree.nodes][:30]
mnames = {}
for ob in b.children:
    for m in ob.data.materials:
        if m and m.use_nodes: mnames[m.name] = [n.bl_idname for n in m.node_tree.nodes][:20]
info["eye_materials_nodes"] = mnames
# is there an interior mouth / teeth ? count verts by name groups not available; test: any vertex hidden behind lips -> skip
(out / "info.json").write_text(json.dumps(info, indent=1, ensure_ascii=False), encoding="utf-8")
for sex, tag in ((1.0, "M"), (0.0, "F")):
    fresh(sex)
    for name, th in (("front", 0), ("tq", math.radians(35)), ("profile", math.radians(90))):
        cam(th, 0, 1.58 if sex else 1.52, .34, .40, 3000); shoot(f"face_{tag}_{name}")
fresh(1.0)
cam(0, 0, 1.585, .14, .06, 9000); shoot("eyes_M")
cam(0, 0, 1.52, .12, .07, 9000); shoot("mouth_M")
cam(math.radians(90), 0, 1.58, .10, .12, 9000); shoot("ear_M")
fresh(1.0); cam(0, 0.62, .95, .50, .30, 1800); shoot("hand_M")   # arm lowered region approx
cam(0, 0.0, .05, .40, .20, 3000); shoot("feet_M")
cam(math.radians(90), 0, .05, .40, .20, 3000); shoot("feet_side_M")
print("MAC_DONE")
