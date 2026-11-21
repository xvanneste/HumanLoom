"""T-S1 — Principled BSDF 5.2 : méthodes de subsurface disponibles, et rendu Cycles d'un matériau de peau minimal à 3 teintes (modèle Donner 2008 réduit).
Via shim ; rendu Cycles CPU ; rien n'est sauvegardé hors du dossier de sortie."""
import sys, json, math
from pathlib import Path
import bpy, numpy as np
from mathutils import Vector
sys.path.insert(0, str(Path(__file__).resolve().parent))
import skin_color

out = Path(sys.argv[sys.argv.index("--") + 1]).resolve(); out.mkdir(parents=True, exist_ok=True)
R = {}
P = bpy.types.ShaderNodeBsdfPrincipled.bl_rna.properties
R["subsurface_methods"] = [(i.identifier, i.name) for i in P["subsurface_method"].enum_items]
R["distributions"] = [i.identifier for i in P["distribution"].enum_items]
assert bpy.ops.human_modeling.create() == {"FINISHED"}
body = bpy.context.object
sc = bpy.context.scene
sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = 48; sc.cycles.use_denoising = False
sc.render.resolution_x = sc.render.resolution_y = 520
w = bpy.data.worlds.new("w"); w.use_nodes = True
w.node_tree.nodes["Background"].inputs[1].default_value = 1.2; sc.world = w
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = "ORTHO"; cam.data.ortho_scale = 0.26
zmax = max(v.co.z for v in body.data.vertices); zc = zmax - 0.105
cam.location = (0.0, -0.8, zc); cam.rotation_euler = (math.radians(90), 0, 0)
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); sc.collection.objects.link(sun)
sun.data.energy = 3.0; sun.rotation_euler = (math.radians(55), 0, math.radians(-30))

mat = bpy.data.materials.new("HL Skin test"); mat.use_nodes = True
nt = mat.node_tree; bsdf = nt.nodes["Principled BSDF"]
body.data.materials.clear(); body.data.materials.append(mat)
body.display_type = "TEXTURED"


def skin_color_rgb(melanin, hemoglobin):
    return skin_color.skin_rgb(melanin, hemoglobin)


tones = {"clair": (0.004, 0.03), "moyen": (0.02, 0.03), "mat": (0.05, 0.03), "fonce": (0.12, 0.03), "tres_fonce": (0.25, 0.03)}
R["methodes_testees"] = {}
for name, (mel, hb) in tones.items():
    bsdf.inputs["Base Color"].default_value = (*skin_color_rgb(mel, hb), 1.0)
    bsdf.subsurface_method = "RANDOM_WALK_SKIN" if "RANDOM_WALK_SKIN" in [i[0] for i in R["subsurface_methods"]] else R["subsurface_methods"][0][0]
    bsdf.inputs["Subsurface Weight"].default_value = 1.0
    bsdf.inputs["Subsurface Radius"].default_value = (1.0, 0.35, 0.2)
    bsdf.inputs["Subsurface Scale"].default_value = 0.012
    bsdf.inputs["Roughness"].default_value = 0.45
    sc.render.filepath = str(out / f"peau_{name}.png"); sc.render.image_settings.file_format = "PNG"
    bpy.ops.render.render(write_still=True)
    R["methodes_testees"][name] = {"couleur": [round(x, 3) for x in bsdf.inputs["Base Color"].default_value[:3]], "png": (out / f"peau_{name}.png").exists()}
(out / "skin_probe.json").write_text(json.dumps(R, indent=1, ensure_ascii=False), encoding="utf-8")
print("SKIN_DONE")
