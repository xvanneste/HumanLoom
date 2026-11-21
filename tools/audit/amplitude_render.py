"""T-A2 — rendus comparatifs du visage (Workbench) : neutre, ×1, ×3 pour des contrôles timides, en projection orthographique de face et de 3/4.
Via shim ; sorties PNG dans le dossier donné. Rien n'est sauvegardé ailleurs."""
import sys, math
from pathlib import Path
import bpy, numpy as np
from mathutils import Vector
from extension.proportions import property_name

out = Path(sys.argv[sys.argv.index("--") + 1]).resolve(); out.mkdir(parents=True, exist_ok=True)
assert bpy.ops.human_modeling.create() == {"FINISHED"}
body = bpy.context.object; keys = body.data.shape_keys
sc = bpy.context.scene
sc.render.engine = "BLENDER_WORKBENCH"
sc.display.shading.light = "STUDIO"; sc.display.shading.color_type = "SINGLE"
sc.display.shading.single_color = (0.8, 0.62, 0.55)
sc.display.shading.show_cavity = True
sc.render.resolution_x = sc.render.resolution_y = 700
sc.render.film_transparent = False
w = bpy.data.worlds.new("w"); w.use_nodes = False; w.color = (0.12, 0.12, 0.13); sc.world = w
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = "ORTHO"; cam.data.ortho_scale = 0.20
for o in list(bpy.data.objects):
    if o.type == "EMPTY":
        bpy.data.objects.remove(o, do_unlink=True)
ev = body.evaluated_get(bpy.context.evaluated_depsgraph_get()); zmax = max(v.co.z for v in body.data.vertices)
zc = zmax - 0.112
ANG = {"face": 0.0, "tiers": math.radians(40)}


def shoot(name, view):
    th = ANG[view]
    d = Vector((-math.sin(th), math.cos(th), 0.0))
    tgt = Vector((0.0, 0.0, zc))
    cam.location = tgt - 0.8 * d
    cam.rotation_euler = (math.radians(90), 0.0, th)
    sc.render.image_settings.file_format = "PNG"
    sc.render.filepath = str((out / f"{name}_{view}.png").resolve())
    r = bpy.ops.render.render(write_still=True)
    if not (out / f"{name}_{view}.png").exists():
        print("PNG_ABSENT", name, view, r)


TEST = ["eyelid_aperture", "lip_thickness", "lips", "nose_width", "mouth", "eye_height", "cheeks", "jaw"]
for ident in TEST:
    prop = property_name(ident)
    blocks = [b for b in keys.key_blocks if b.name == "HM · " + ident or b.name.startswith("HM · " + ident + " · ")]
    for b in blocks:
        b.slider_min, b.slider_max = -10.0, 10.0
    for tag, s in (("n", 0.0), ("x1", 1.0), ("x3", 3.0), ("x6", 6.0), ("x10", 10.0)):
        keys[prop] = s; keys.update_tag(); bpy.context.view_layer.update()
        for v in ("face", "tiers"):
            shoot(f"{ident}_{tag}", v)
    keys[prop] = 0.0
print("RENDER_DONE")
