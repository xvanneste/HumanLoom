"""Full body and face review of manual landmarks and measured mesh sections."""

import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_anatomy import fixture_landmarks, refresh


def material(name, color):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    return mat


def path_object(parent, points, name, mat, radius, closed=False):
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = radius
    curve.bevel_resolution = 2
    line = curve.splines.new("POLY")
    line.points.add(len(points) - 1)
    for point, coords in zip(line.points, points):
        point.co = (*coords, 1)
    line.use_cyclic_u = closed
    obj = bpy.data.objects.new(name, curve)
    parent.users_collection[0].objects.link(obj)
    obj.parent = parent
    obj["review_snapshot"] = True
    curve.materials.append(mat)
    return obj


def main():
    from bl_ext.user_default.human_modeling import anatomy, character_presets, measurements
    output = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
    output.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    for obj in tuple(scene.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    scene.unit_settings.system = "METRIC"
    clay = material("Argile neutre", (.48, .50, .53))
    cyan = material("Coupes du buste", (.1, .8, .85))
    pink = material("Repères du visage", (.95, .3, .5))
    white = material("Texte", (.9, .9, .9))
    bodies, labels, face_labels, reports = [], [], [], []
    for morph, name in ((0, "Féminin"), (1, "Masculin")):
        bpy.ops.human_modeling.create()
        body = bpy.context.object
        body.name = name
        body.data.shape_keys.key_blocks["Morphologie"].value = morph
        fixture_landmarks(body, anatomy)
        for obj in (body, *body.children):
            if obj.type == "MESH":
                obj.data.materials.clear()
                obj.data.materials.append(clay)
        local = anatomy.local_report(body, bpy.context, include_paths=True)
        for key, entry in local["sections"].items():
            assert "error" not in entry
            points = [(point[0] * 1.003, point[1] * 1.003, point[2]) for point in entry["local_path"]]
            path_object(body, points, "Aperçu figé · " + key, cyan, .0015, True)
        inverse = body.matrix_world.inverted()
        for key, entry in local["distances"].items():
            points = [inverse @ Vector(local["landmarks"][endpoint]["world_position_m"]) for endpoint in entry["endpoints"]]
            # Move lines slightly in front of the face for visual inspection.
            for point in points:
                point.y -= .003
            path_object(body, points, "Aperçu figé · " + key, pink, .0006)
            for index, point in enumerate(points):
                bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=8, radius=.0016, location=point)
                sphere = bpy.context.object
                sphere.name = "Aperçu figé · " + key + str(index)
                sphere.parent = body
                sphere.data.materials.append(pink)
                sphere["review_snapshot"] = True
        report = measurements.report(body, bpy.context)
        report["review_note"] = "Approximate test landmark placement, to be anatomically reviewed. Colored geometry is a static review snapshot."
        reports.append(report)
        for face in (False, True):
            text = bpy.data.curves.new("Légende", "FONT")
            text.align_x = "CENTER"
            text.size = .012 if face else .055
            if face:
                text.body = (name + "\nNez " + f"{local['distances']['nose_width']['distance_m'] * 100:.2f} cm"
                             + " · Bouche " + f"{local['distances']['mouth_width']['distance_m'] * 100:.2f} cm")
            else:
                text.body = name + "\nRepères et coupes · placement à vérifier"
                text.size = .032
            obj = bpy.data.objects.new(text.name, text)
            scene.collection.objects.link(obj)
            obj.data.materials.append(white)
            (face_labels if face else labels).append(obj)
        bodies.append(body)
    camera = bpy.data.objects.new("Revue anatomie", bpy.data.cameras.new("Revue anatomie"))
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.type = "ORTHO"
    scene.render.engine = "BLENDER_WORKBENCH"
    shading = scene.display.shading
    shading.light = "STUDIO"
    shading.color_type = "MATERIAL"
    shading.show_shadows = False
    shading.show_cavity = False
    scene.render.resolution_percentage = 100
    for shot, yaw, face in (("corps-face", 0, False), ("corps-profil", math.pi / 2, False),
                            ("corps-trois-quarts", math.pi / 5, False), ("visages-reperes", 0, True)):
        horizontal = Vector((math.cos(yaw), math.sin(yaw), 0))
        center = Vector((0, 0, 1.60 if face else .82))
        camera.location = center + Vector((math.sin(yaw) * 10, -math.cos(yaw) * 10, 0))
        camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
        camera.data.ortho_scale = .64 if face else 2.55
        scene.render.resolution_x = 1600
        scene.render.resolution_y = 1100 if face else 1400
        for i, body in enumerate(bodies):
            offset = (i - .5) * (.32 if face else 1.2)
            body.location = horizontal * offset
            labels[i].hide_render = face
            face_labels[i].hide_render = not face
            text = face_labels[i] if face else labels[i]
            text.location = body.location + Vector((0, -.22 if face else -.2, 1.43 if face else -.10))
            text.rotation_euler = (math.pi / 2, 0, yaw)
        bpy.context.view_layer.update()
        scene.render.filepath = str(output / (shot + ".png"))
        bpy.ops.render.render(write_still=True)
    # Save the editable review in a full-body front view.
    camera.location = (0, -10, .82)
    camera.rotation_euler = (Vector((0, 0, .82)) - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.ortho_scale = 2.55
    scene.render.resolution_y = 1400
    for i, body in enumerate(bodies):
        body.location = ((i - .5) * 1.2, 0, 0)
        labels[i].hide_render = False
        labels[i].location = body.location + Vector((0, -.2, -.1))
        labels[i].rotation_euler = (math.pi / 2, 0, 0)
        face_labels[i].hide_render = True
    for obj in tuple(bpy.context.selected_objects):
        obj.select_set(False)
    bodies[0].select_set(True)
    bpy.context.view_layer.objects.active = bodies[0]
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                area.spaces.active.show_region_ui = True
                area.spaces.active.region_3d.view_perspective = "CAMERA"
    bpy.context.view_layer.update()
    reports = [measurements.report(body, bpy.context) for body in bodies]
    for report in reports:
        report["review_note"] = "Approximate test landmark placement, to be anatomically reviewed. Colored geometry is a static review snapshot."
    character_presets.write_json(output / "mesures-revue.json", {"characters": reports})
    bpy.ops.wm.save_as_mainfile(filepath=str(output / "Revue-anatomie-06.blend"), compress=True)
    print("PASS: full body front, profile, three-quarter and facial landmark review saved", flush=True)


if __name__ == "__main__":
    main()
