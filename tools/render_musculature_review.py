"""Full-body clay review of independently adjustable fat and muscle controls."""

import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector


PROFILES = (
    ("Mince", {"corpulence": -1., "adiposity": -.8, "muscles": -.5}),
    ("Référence", {}),
    ("Musclé", {"corpulence": -.15, "adiposity": -.12, "muscles": 1., "muscle_definition": 1.}),
    ("Ample et musclé", {"corpulence": 1., "adiposity": .8, "muscles": 1., "muscle_definition": .3}),
)


def main():
    from bl_ext.user_default.human_modeling import character_presets
    output = Path(sys.argv[sys.argv.index("--")+1]).resolve()
    output.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    for obj in tuple(scene.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    groups = []
    for sex, label in ((0., "Féminine"), (1., "Masculine")):
        objects, bodies = [], []
        for index, (name, settings) in enumerate(PROFILES):
            scene.cursor.location = ((index-1.5)*1.1, 0, 0)
            bpy.ops.human_modeling.create()
            body = bpy.context.object
            body.name = label+" · "+name
            body.data.shape_keys.key_blocks["Morphologie"].value = sex
            for identifier, value in settings.items():
                body.data.shape_keys["hm_"+identifier] = value
            body.data.shape_keys.update_tag()
            character_presets.write(output / (body.name+".json"), character_presets.capture(body))
            bodies.append(body)
            objects.extend((body, *body.children))
            curve = bpy.data.curves.new(name, "FONT")
            curve.body = name
            curve.align_x = "CENTER"
            curve.size = .045
            text = bpy.data.objects.new(name, curve)
            scene.collection.objects.link(text)
            text.location = (body.location.x, -1, -.13)
            text.rotation_euler.x = math.pi/2
            objects.append(text)
        groups.append((label, bodies, objects))
    camera = bpy.data.objects.new("Comparaison musculature", bpy.data.cameras.new("Comparaison musculature"))
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.location = (0, -10, .85)
    camera.rotation_euler = (Vector((0,0,.85))-camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 4.5
    scene.unit_settings.system = "METRIC"
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "SINGLE"
    scene.display.shading.single_color = (.55,.57,.60)
    scene.display.shading.show_shadows = False
    scene.display.shading.show_cavity = False
    scene.render.resolution_x = 2000
    scene.render.resolution_y = 1000
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    for label, bodies, objects in groups:
        for _, _, others in groups:
            for obj in others:
                obj.hide_render = others is not objects
        for view, angle in (("face", 0), ("profil", math.pi/2), ("trois-quarts", math.pi/4), ("dos", math.pi)):
            for body in bodies:
                body.rotation_euler.z = angle
            scene.render.filepath = str(output / f"{label}-{view}.png")
            bpy.ops.render.render(write_still=True)
    for label, bodies, objects in groups:
        for body in bodies:
            body.rotation_euler.z = 0
        for obj in objects:
            obj.hide_render = label != "Masculine"
            obj.hide_set(label != "Masculine")
    bpy.context.view_layer.objects.active = groups[1][1][2]
    for obj in tuple(bpy.context.selected_objects):
        obj.select_set(False)
    groups[1][1][2].select_set(True)
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                area.spaces.active.region_3d.view_perspective = "CAMERA"
                area.spaces.active.show_region_ui = True
    bpy.ops.wm.save_as_mainfile(filepath=str(output / "Morphologies-corporelles.blend"), compress=True)
    print("MUSCLE_REVIEW_READY", flush=True)


if __name__ == "__main__":
    main()
