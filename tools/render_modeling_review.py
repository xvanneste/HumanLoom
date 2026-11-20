"""Render face and body variation examples through the installed extension."""

import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


VARIANTS = (
    ("Féminine · référence", 0.0, {}),
    ("Féminine · proportions A", 0.0, {
        "head_width": -.65, "jaw": -.55, "nose_length": -.4, "lips": .5,
        "eye_spacing": .4, "waist": -.7, "hips": .7, "legs": .6,
    }),
    ("Féminine · proportions B", 0.0, {
        "head_width": .7, "jaw": .7, "chin": .6, "cheeks": .6,
        "nose_width": .5, "shoulders": .6, "waist": .5, "torso_depth": .6,
    }),
    ("Masculine · référence", 1.0, {}),
    ("Masculine · proportions A", 1.0, {
        "head_height": .8, "chin": .7, "nose_length": .5, "mouth": -.5,
        "forehead": .4, "legs": .7, "torso": -.5, "neck": -.3,
    }),
    ("Masculine · proportions B", 1.0, {
        "jaw": -.7, "cheeks": .4, "nose_width": -.4, "head_height": -.3,
        "lips": .7, "eye_spacing": -.3, "shoulders": .8, "waist": .4,
        "torso_depth": .7, "legs": -.4,
    }),
)


def aim(camera, location, point, scale):
    camera.location = location
    camera.rotation_euler = (Vector(point) - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.ortho_scale = scale


def main():
    output = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
    output.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    for obj in tuple(scene.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bodies = []
    for index, (name, sex, settings) in enumerate(VARIANTS):
        scene.cursor.location = ((index - 2.5) * 1.1, 0, 0)
        bpy.ops.human_modeling.create()
        body = bpy.context.object
        body.name = name
        keys = body.data.shape_keys
        keys.key_blocks["Morphologie"].value = sex
        for identifier, value in settings.items():
            keys["human_modeling_age" if identifier == "age_stage" else "hm_" + identifier] = value
        keys.update_tag()
        bodies.append(body)
    bpy.context.view_layer.update()
    scene.unit_settings.system = "METRIC"
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "SINGLE"
    scene.display.shading.single_color = (.55, .57, .60)
    scene.display.shading.show_cavity = False
    scene.display.shading.show_shadows = False
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    camera = bpy.data.objects.new("Comparaison", bpy.data.cameras.new("Comparaison"))
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.type = "ORTHO"
    scene.render.resolution_x = 2400
    scene.render.resolution_y = 850
    aim(camera, (0, -10, .85), (0, 0, .85), 6.6)
    for name, angle in (("corps-face", 0), ("corps-trois-quarts", math.pi / 4), ("corps-profil", math.pi / 2)):
        for body in bodies:
            body.rotation_euler.z = angle
        scene.render.filepath = str(output / f"{name}.png")
        bpy.ops.render.render(write_still=True)

    scene.render.resolution_x = 2400
    scene.render.resolution_y = 450
    aim(camera, (0, -10, 1.58), (0, 0, 1.58), 1.85)
    for index, body in enumerate(bodies):
        body.location.x = (index - 2.5) * .27
        body.rotation_euler.z = 0
        # Align eye centres in world space for a readable head comparison.
        bpy.context.view_layer.update()
        graph = bpy.context.evaluated_depsgraph_get()
        eye = body.children[0].evaluated_get(graph)
        eye_z = sum(vertex.co.z for vertex in eye.data.vertices) / len(eye.data.vertices)
        body.location.z = 1.55 - eye_z
    for name, angle in (("visage-face", 0), ("visage-trois-quarts", math.pi / 4), ("visage-profil", math.pi / 2)):
        for body in bodies:
            body.rotation_euler.z = angle
        scene.render.filepath = str(output / f"{name}.png")
        bpy.ops.render.render(write_still=True)
    for index, body in enumerate(bodies):
        body.location = ((index - 2.5) * 1.1, 0, 0)
        body.rotation_euler.z = 0
    aim(camera, (0, -10, .85), (0, 0, .85), 6.6)
    scene.render.resolution_y = 850
    for obj in tuple(bpy.context.selected_objects):
        obj.select_set(False)
    bodies[0].select_set(True)
    bpy.context.view_layer.objects.active = bodies[0]
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                area.spaces.active.show_region_ui = True
                area.spaces.active.region_3d.view_perspective = "CAMERA"
    bpy.ops.wm.save_as_mainfile(filepath=str(output / "Modelisation-corps-visage.blend"), compress=True)
    (output / "variantes.json").write_text(json.dumps(VARIANTS, ensure_ascii=False, indent=2), encoding="utf-8")
    print("MODELING_REVIEW_READY", flush=True)


if __name__ == "__main__":
    main()
