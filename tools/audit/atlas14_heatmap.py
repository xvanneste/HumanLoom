"""Carte de chaleur de l'écart de cage entre l'asset actuel et extension-13 (sexe/stade donnés). Lecture seule, Workbench.
Usage : blender --background --factory-startup --python atlas14_heatmap.py -- <actuel> <ancien> <dossier_sortie> <sexe> <stade> <max_mm>"""
import sys, math
from pathlib import Path
import bpy, numpy as np

a = sys.argv[sys.argv.index("--") + 1:]
cur_path, old_path, out = Path(a[0]).resolve(), Path(a[1]).resolve(), Path(a[2]).resolve()
sex, stage, vmax = float(a[3]), float(a[4]), float(a[5])
out.mkdir(parents=True, exist_ok=True)
bodies = []
for path in (cur_path, old_path):
    with bpy.data.libraries.load(str(path), link=False) as (_, t):
        t.collections = ["Realistic Human Base"]
    col = t.collections[0]; bpy.context.scene.collection.children.link(col)
    obj = next(o for o in col.objects if o.get("human_modeling_body"))
    for m in obj.modifiers:
        m.show_viewport = False
    k = obj.data.shape_keys
    k.key_blocks["Morphologie"].value = sex; k["human_modeling_age"] = stage; k.update_tag()
    bodies.append(obj)
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()


def pts(obj):
    ev = obj.evaluated_get(dg); m = ev.to_mesh()
    r = np.array([v.co[:] for v in m.vertices]); ev.to_mesh_clear(); return r


cur, old = bodies
pc, po = pts(cur), pts(old)
d = np.linalg.norm(pc - po, axis=1) * 1000
print("ECART max %.2f mm, median %.2f mm" % (d.max(), np.median(d)), flush=True)
dg2 = bpy.context.evaluated_depsgraph_get()
mesh = bpy.data.meshes.new_from_object(cur.evaluated_get(dg2))
mesh.materials.clear()
t = np.clip(d / vmax, 0, 1)
# bleu -> cyan -> vert -> jaune -> rouge
stops = np.array([(0.12, 0.25, 0.75), (0.1, 0.7, 0.85), (0.2, 0.75, 0.3), (0.95, 0.85, 0.15), (0.85, 0.12, 0.1)])
pos = np.linspace(0, 1, len(stops))
rgb = np.stack([np.interp(t, pos, stops[:, i]) for i in range(3)], axis=1)
attr = mesh.color_attributes.new("ecart", "FLOAT_COLOR", "POINT")
attr.data.foreach_set("color", np.concatenate([rgb, np.ones((len(rgb), 1))], axis=1).ravel())
mesh.color_attributes.active_color = attr
hm = bpy.data.objects.new("heat", mesh); bpy.context.scene.collection.objects.link(hm)
hm.matrix_world = cur.matrix_world
for o in bpy.context.scene.objects:
    if o is not hm and o.type in {"MESH"}:
        o.hide_render = True; o.hide_viewport = True
for o in cur.children_recursive:
    o.hide_render = True
zmax = pc[:, 2].max(); zmin = pc[:, 2].min(); h = zmax - zmin
sc = bpy.context.scene
sc.render.engine = "BLENDER_WORKBENCH"
sc.display.shading.light = "FLAT"; sc.display.shading.color_type = "VERTEX"
sc.display.shading.show_object_outline = False
sc.render.resolution_x, sc.render.resolution_y = 700, 1000
sc.render.film_transparent = False
sc.world = bpy.data.worlds.new("w"); sc.world.color = (0.93, 0.93, 0.94)
sc.view_settings.view_transform = "Standard"
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = "ORTHO"; cam.data.ortho_scale = h * 1.08
zc = (zmax + zmin) / 2
for name, loc, rot in (("face", (0, -6, zc), (math.radians(90), 0, 0)), ("profil", (6, 0, zc), (math.radians(90), 0, math.radians(90)))):
    cam.location = loc; cam.rotation_euler = rot
    sc.render.filepath = str(out / f"{name}.png"); sc.render.image_settings.file_format = "PNG"
    bpy.ops.render.render(write_still=True)
print("HEATMAP_DONE", flush=True)
