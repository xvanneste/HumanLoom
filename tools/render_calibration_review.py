"""Create an adult stature comparison using the published NCHS percentiles."""

import sys
from pathlib import Path

import bpy
from mathutils import Vector


def main():
    from bl_ext.user_default.human_modeling import character_presets, measurements

    output = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
    output.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1
    for obj in tuple(scene.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    clay = bpy.data.materials.new("Argile")
    clay.diffuse_color = (.55, .57, .60, 1)
    white = bpy.data.materials.new("Légendes")
    white.diffuse_color = (.9, .9, .9, 1)
    bodies = []
    reports = []
    for index, (sex, percentile) in enumerate(
        (sex, percentile) for sex in ("F", "M") for percentile in ("P05", "P50", "P95")
    ):
        scene.cursor.location = ((index - 2.5) * 1.1, 0, 0)
        bpy.ops.human_modeling.create()
        body = bpy.context.object
        body.name = sex + " · " + percentile
        body.data.shape_keys.key_blocks["Morphologie"].value = float(sex == "M")
        body.data.shape_keys.update_tag()
        body.hm_reference_sex = sex
        body.hm_reference_group = "20_29"
        body.hm_reference_percentile = percentile
        bpy.context.view_layer.update()
        assert bpy.ops.human_modeling.reference_height() == {"FINISHED"}
        bpy.context.view_layer.update()
        graph = bpy.context.evaluated_depsgraph_get()
        evaluated = body.evaluated_get(graph)
        bottom = min((evaluated.matrix_world @ Vector(corner)).z for corner in evaluated.bound_box)
        body.location.z -= bottom
        for obj in (body, *body.children):
            obj.data.materials.clear()
            obj.data.materials.append(clay)
        bpy.context.view_layer.update()
        report = measurements.report(body, bpy.context)
        assert abs(report["height_difference_cm"]) < .0001
        reports.append(report)
        bodies.append(body)
        text = bpy.data.curves.new("Stature publiée", type="FONT")
        text.body = f"{sex} · {percentile[1:]}\n{measurements.target(body):.1f} cm"
        text.size = .055
        text.align_x = "CENTER"
        obj = bpy.data.objects.new(text.name, text)
        scene.collection.objects.link(obj)
        obj.location = (body.location.x, -.15, -.17)
        obj.rotation_euler.x = 1.57079632679
        obj.data.materials.append(white)
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = False
    scene.display.shading.show_cavity = False
    scene.render.resolution_x = 2400
    scene.render.resolution_y = 1000
    scene.render.resolution_percentage = 100
    camera = bpy.data.objects.new("Référence de stature", bpy.data.cameras.new("Référence de stature"))
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.location = (0, -10, .88)
    camera.rotation_euler = (Vector((0, 0, .88)) - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 6.8
    scene.render.filepath = str(output / "stature-adultes-20-29.png")
    bpy.ops.render.render(write_still=True)
    character_presets.write_json(output / "references-et-mesures.json", {"characters": reports})
    for obj in tuple(bpy.context.selected_objects):
        obj.select_set(False)
    bodies[0].select_set(True)
    bpy.context.view_layer.objects.active = bodies[0]
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                area.spaces.active.show_region_ui = True
                area.spaces.active.region_3d.view_perspective = "CAMERA"
    bpy.ops.wm.save_as_mainfile(filepath=str(output / "Calibration-stature.blend"), compress=True)
    print("PASS: six adult models match their published stature percentile", flush=True)


if __name__ == "__main__":
    main()
