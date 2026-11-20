"""Create age reference meshes from MPFB for comparison before retopology transfer."""

from pathlib import Path
import sys

import bpy
import addon_utils
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from experimental_age_transfer import reference


def main():
    output = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
    output.mkdir(parents=True, exist_ok=True)
    addon_utils.enable("bl_ext.user_default.mpfb", default_set=True)
    for obj in tuple(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    scene = bpy.context.scene
    families = []
    for gender, name in ((0, "Féminine"), (1, "Masculine")):
        collection = bpy.data.collections.new(name)
        scene.collection.children.link(collection)
        families.append(collection)
        for index, (stage, value) in enumerate((
            ("Enfant", .1875), ("Adolescent", .35), ("Adulte", .5), ("Senior", 1.0),
        )):
            vertices, triangles = reference(value, gender)
            mesh = bpy.data.meshes.new(stage + " · référence MPFB")
            mesh.from_pydata(vertices.tolist(), [], triangles.tolist())
            mesh.update()
            obj = bpy.data.objects.new(stage + " · " + name, mesh)
            collection.objects.link(obj)
            obj["source"] = "MPFB 2.0.18, MakeHuman macro targets (CC0)"
            obj["source_age_parameter"] = value
            obj["source_gender_parameter"] = gender
            obj["height_m"] = float(vertices[:, 2].max() - vertices[:, 2].min())
            # Align crowns for the portrait comparison only.
            obj.location = ((index - 1.5) * .36, 0, 1.7 - float(vertices[:, 2].max()))
            for polygon in mesh.polygons:
                polygon.use_smooth = True
            print("REFERENCE", name, stage, "height", obj["height_m"], flush=True)
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "SINGLE"
    scene.display.shading.single_color = (.55, .57, .6)
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "BOTH"
    scene.render.resolution_x = 2000
    scene.render.resolution_y = 500
    scene.render.resolution_percentage = 100
    cam = bpy.data.objects.new("Comparaison des visages", bpy.data.cameras.new("Portraits"))
    scene.collection.objects.link(cam)
    scene.camera = cam
    cam.location = (0, -10, 1.54)
    cam.rotation_euler = (Vector((0, 0, 1.54)) - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 1.50
    for current in families:
        for collection in families:
            collection.hide_render = collection is not current
        scene.render.filepath = str(output / (current.name + ".png"))
        bpy.ops.render.render(write_still=True)
    families[1].hide_viewport = True
    families[0].hide_render = False
    families[1].hide_render = True
    bpy.ops.wm.save_as_mainfile(filepath=str(output / "References-age.blend"))
    print("AGE_REFERENCES_SAVED", flush=True)


if __name__ == "__main__":
    main()
