"""Before/after neutral-body and facial review of the inner-eyelid repair."""

import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector


def main():
    from bl_ext.user_default.human_modeling import add_smooth_preview, geometry_quality
    old_asset, output = [Path(value).resolve() for value in sys.argv[sys.argv.index("--") + 1:]]
    output.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    for obj in tuple(scene.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    with bpy.data.libraries.load(str(old_asset), link=False) as (_, target):
        target.collections = ["Realistic Human Base"]
    scene.collection.children.link(target.collections[0])
    before = next(obj for obj in target.collections[0].objects if obj.get("human_modeling_body"))
    add_smooth_preview(before)
    bpy.ops.human_modeling.create()
    after = bpy.context.object
    gray = bpy.data.materials.new("Argile neutre")
    gray.diffuse_color = (.55, .57, .60, 1)
    white = bpy.data.materials.new("Légendes")
    white.diffuse_color = (.9, .9, .9, 1)
    bodies, labels = (before, after), []
    for body, name, expected in ((before, "Avant", 82), (after, "Après", 0)):
        body.name = name + " · paupières internes"
        body.data.shape_keys.key_blocks["Morphologie"].value = 0.
        body.data.shape_keys.update_tag()
        bpy.context.view_layer.update()
        assert geometry_quality.report(body, bpy.context)["geometry"]["intersections"]["crossing_triangle_pairs"] == expected
        for obj in (body, *body.children):
            if obj.type == "MESH":
                obj.data.materials.clear()
                obj.data.materials.append(gray)
        text = bpy.data.curves.new(name, "FONT")
        text.align_x = "CENTER"
        text.body = name + f" · {expected} croisements internes"
        obj = bpy.data.objects.new(name, text)
        scene.collection.objects.link(obj)
        text.materials.append(white)
        labels.append(obj)
    camera = bpy.data.objects.new("Revue", bpy.data.cameras.new("Revue"))
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.type = "ORTHO"
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = False
    scene.display.shading.show_cavity = False
    scene.render.resolution_x = 1600
    scene.render.resolution_percentage = 100
    for shot, close, yaw in (("corps-entiers-avant-apres", False, 0), ("visages-avant-apres", True, 0),
                             ("visages-trois-quarts-avant-apres", True, math.pi/4)):
        horizontal = Vector((math.cos(yaw), math.sin(yaw), 0))
        center = Vector((0, 0, 1.535 if close else .82))
        camera.location = center + Vector((math.sin(yaw)*10, -math.cos(yaw)*10, 0))
        camera.rotation_euler = (center-camera.location).to_track_quat("-Z", "Y").to_euler()
        camera.data.ortho_scale = .60 if close else 2.6
        scene.render.resolution_y = 900 if close else 1300
        for index, body in enumerate(bodies):
            body.location = horizontal * ((index-.5) * (.30 if close else 1.2))
            labels[index].location = body.location + Vector((math.sin(yaw)*.2, -math.cos(yaw)*.2, 1.40 if close else -.1))
            labels[index].rotation_euler = (math.pi/2, 0, yaw)
            labels[index].data.size = .012 if close else .033
        bpy.context.view_layer.update()
        scene.render.filepath = str(output / (shot + ".png"))
        bpy.ops.render.render(write_still=True)
    camera.location = (0, -10, .82)
    camera.rotation_euler = (Vector((0, 0, .82))-camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.ortho_scale = 2.6
    scene.render.resolution_y = 1300
    for index, body in enumerate(bodies):
        body.location = ((index-.5)*1.2, 0, 0)
        labels[index].location = body.location + Vector((0, -.2, -.1))
        labels[index].rotation_euler = (math.pi/2, 0, 0)
        labels[index].data.size = .033
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                area.spaces.active.region_3d.view_perspective = "CAMERA"
                area.spaces.active.overlay.show_relationship_lines = False
    bpy.ops.wm.save_as_mainfile(filepath=str(output / "Paupieres-avant-apres.blend"), compress=True)
    print("SURFACE_FIX_REVIEW_READY", flush=True)


if __name__ == "__main__":
    main()
