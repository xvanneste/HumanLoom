import sys, math
from pathlib import Path
import bpy
from extension.proportions import property_name, CONTROLS
LABELS = dict(CONTROLS)
out = Path(sys.argv[sys.argv.index("--") + 1]); out.mkdir(parents=True, exist_ok=True)
sc = bpy.context.scene
sc.render.engine = "BLENDER_WORKBENCH"
sc.display.shading.light = "STUDIO"; sc.display.shading.color_type = "SINGLE"; sc.display.shading.single_color = (0.82, 0.72, 0.66)
sc.world = bpy.data.worlds.new("w"); sc.world.color = (0.16, 0.16, 0.18)
sc.display.render_aa = "8"

def clear():
    for o in tuple(sc.objects): bpy.data.objects.remove(o, do_unlink=True)
def label(text, loc, rot, size=.05):
    c = bpy.data.curves.new("t", "FONT"); c.body = text; c.size = size; c.align_x = "LEFT"
    o = bpy.data.objects.new("t", c); o.location = loc; o.rotation_euler = rot; sc.collection.objects.link(o)
def body_at(loc, controls, sex=1.0, age=2.0):
    sc.cursor.location = loc
    bpy.ops.human_modeling.create(); b = bpy.context.object; k = b.data.shape_keys
    k.key_blocks["Morphologie"].value = sex; k["human_modeling_age"] = age
    for ident, v in controls.items(): k[property_name(ident)] = v
    k.update_tag(); return b
def camera(side, cx, cz, width, height, px_per_m):
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam)
    cam.data.type = "ORTHO"; cam.data.ortho_scale = width
    if side: cam.location = (10, cx, cz); cam.rotation_euler = (math.radians(90), 0, math.radians(90))
    else: cam.location = (cx, -10, cz); cam.rotation_euler = (math.radians(90), 0, 0)
    sc.camera = cam; sc.render.resolution_x = int(width * px_per_m); sc.render.resolution_y = int(height * px_per_m)
def shoot(name):
    sc.render.filepath = str(out / f"{name}.png"); bpy.ops.render.render(write_still=True)

VALS = (-1.0, 0.0, 1.0)
def face_grid(name, idents, side):
    clear(); sp = .5; rowh = .45
    for r, ident in enumerate(idents):
        for c, v in enumerate(VALS):
            if side: loc = (0.35 * r, (c - 1) * sp, -rowh * r)   # rows toward +X (camera side) hide upper torsos
            else: loc = ((c - 1) * sp, -0.35 * r, -rowh * r)
            body_at(loc, {ident: v})
        if side: label(f"{LABELS[ident]}", (0.35 * r, -1.2, 1.5 - rowh * r), (math.radians(90), 0, math.radians(90)), .045)
        else: label(f"{LABELS[ident]}", (-1.4, -0.35 * r, 1.5 - rowh * r), (math.radians(90), 0, 0), .045)
    bpy.context.view_layer.update()
    n = len(idents); zc = 1.55 - rowh * (n - 1) / 2 - 0.02
    camera(side, 0.0, zc, 3.0 if True else 1.6, rowh * n + .3, 520)
    shoot(name)

FACE = {"face_head": ["head_width", "head_height", "forehead"], "face_jaw": ["jaw", "chin", "jaw_angle", "cheeks"],
        "face_nose": ["nose_length", "nose_width", "nose_bridge"], "face_mouth": ["mouth", "lips", "lip_thickness", "mouth_corner"],
        "face_eyes": ["eye_spacing", "eye_height", "eyelid_aperture"], "face_ears": ["ears_size", "ears_angle", "facial_asymmetry"]}
for n, ids in FACE.items():
    for side in (False, True): face_grid(n + ("_side" if side else "_front"), ids, side)

def body_grid(name, idents, side, sex=1.0):
    clear(); sp = .95 if not side else .6
    k = 0
    for ident in idents:
        for v in VALS:
            loc = [0, 0, 0]
            loc[1 if side else 0] = (k - (len(idents) * 3 - 1) / 2) * sp; k += 1
            body_at(tuple(loc), {ident: v}, sex)
    bpy.context.view_layer.update()
    camera(side, 0.0, .86, len(idents) * 3 * sp + .3, 1.95, 260 if not side else 330)
    shoot(name)
BODY = {"body_corp": ["whole_body", "body_mass", "adiposity"], "body_shape_a": ["corpulence", "shoulders", "waist"], "body_shape_b": ["hips", "torso_depth", "neck"],
        "body_shape_c": ["legs", "torso", "muscle_definition"], "fat_a": ["fat_abdomen", "fat_flanks", "fat_hips"], "fat_b": ["fat_thighs", "fat_arms", "fat_face"],
        "mus_a": ["muscles", "muscles_shoulders", "muscles_chest"], "mus_b": ["muscles_back", "muscles_arms", "muscles_abdomen"], "mus_c": ["muscles_glutes", "muscles_thighs", "muscles_calves"]}
for n, ids in BODY.items():
    for side in (False, True): body_grid(n + ("_side" if side else "_front"), ids, side)
for side in (False, True): body_grid("body_corp_F" + ("_side" if side else "_front"), BODY["body_corp"], side, sex=0.0)
print("VIS_DONE")
