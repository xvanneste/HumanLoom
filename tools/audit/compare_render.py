"""Rendu comparatif (Workbench, modificateurs actifs) : asset actuel vs extension-13, sexes et stade donnés. Lecture seule.
Usage : blender --background --factory-startup --python compare_render.py -- <actuel> <ancien> <sortie> <stade> <sexe1,sexe2,...>"""
import sys, math
from pathlib import Path
import bpy, numpy as np

a = sys.argv[sys.argv.index("--") + 1:]
cur_path, old_path, out, stage = Path(a[0]).resolve(), Path(a[1]).resolve(), Path(a[2]).resolve(), float(a[3])
sexes = [float(x) for x in a[4].split(",")]
out.mkdir(parents=True, exist_ok=True)
for o in list(bpy.context.scene.objects):  # scène de démarrage : cube 2 m, lumière, caméra par défaut
    bpy.data.objects.remove(o, do_unlink=True)
sets = {}
for tag, path in (("actuel", cur_path), ("ancien", old_path)):
    with bpy.data.libraries.load(str(path), link=False) as (_, t):
        t.collections = ["Realistic Human Base"]
    col = t.collections[0]; bpy.context.scene.collection.children.link(col)
    body = next(o for o in col.objects if o.get("human_modeling_body"))
    # « Relief de peau » (Displace) : force 0 au stade <= 2 (driver max(0, stade-2)) et rendu corrompu en headless : coupé.
    # Subsurf niveau 2 identique des deux côtés pour un aspect lisse (l'asset n'embarque pas le modificateur Surface).
    for m in body.modifiers:
        m.show_render = False; m.show_viewport = False
    sub = body.modifiers.new("Lissage", "SUBSURF"); sub.levels = sub.render_levels = 2
    sets[tag] = (body, list(col.all_objects))
sc = bpy.context.scene
sc.render.engine = "BLENDER_WORKBENCH"
sh = sc.display.shading
sh.light = "STUDIO"; sh.color_type = "SINGLE"; sh.single_color = (0.80, 0.63, 0.55); sh.show_object_outline = False
sh.show_specular_highlight = False
sc.render.resolution_x, sc.render.resolution_y = 600, 1000
sc.world = bpy.data.worlds.new("w"); sc.world.color = (0.93, 0.93, 0.94)
sc.view_settings.view_transform = "Standard"
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = "ORTHO"
for sex in sexes:
    for tag, (body, objs) in sets.items():
        k = body.data.shape_keys
        k.key_blocks["Morphologie"].value = sex; k["human_modeling_age"] = stage; k.update_tag()
for sex in sexes:
    for tag, (body, objs) in sets.items():
        for t2, (_, objs2) in sets.items():
            for o in objs2:
                o.hide_render = (t2 != tag)
        k = body.data.shape_keys
        k.key_blocks["Morphologie"].value = sex; k["human_modeling_age"] = stage; k.update_tag()
        bpy.context.view_layer.update()
        dg = bpy.context.evaluated_depsgraph_get(); ev = body.evaluated_get(dg); m = ev.to_mesh()
        z = np.array([v.co.z for v in m.vertices]); ev.to_mesh_clear()
        cam.data.ortho_scale = (z.max() - z.min()) * 1.08; zc = (z.max() + z.min()) / 2
        cam.location = (0, -6, zc); cam.rotation_euler = (math.radians(90), 0, 0)
        sc.render.filepath = str(out / f"{tag}_sexe{sex:g}.png"); sc.render.image_settings.file_format = "PNG"
        bpy.ops.render.render(write_still=True)
        print("RENDU", tag, sex, flush=True)
print("COMPARE_DONE", flush=True)
