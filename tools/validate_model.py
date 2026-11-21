"""Exercise the modeling operators and render a five-morphology comparison."""

import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def smooth_height(body):
    """Hauteur monde de la surface lissée évaluée (et non de la cage, que renvoie Object.dimensions)."""
    graph = bpy.context.evaluated_depsgraph_get()
    evaluated = body.evaluated_get(graph)
    mesh = evaluated.to_mesh()
    try:
        values = [(evaluated.matrix_world @ vertex.co).z for vertex in mesh.vertices]
    finally:
        evaluated.to_mesh_clear()
    return max(values) - min(values)


def main():
    output = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
    output.mkdir(parents=True, exist_ok=True)
    assert bpy.app.version[:2] == (5, 2)
    for obj in tuple(bpy.context.scene.objects):
        bpy.data.objects.remove(obj, do_unlink=True)

    bodies = []
    for index, value in enumerate((0, .25, .5, .75, 1)):
        bpy.context.scene.cursor.location = ((index - 2) * 1.1, 0, 0)
        assert bpy.ops.human_modeling.create() == {"FINISHED"}
        body = bpy.context.object
        body.name = f"Morphologie {value:.0%}"
        body.data.shape_keys.key_blocks["Morphologie"].value = value
        bpy.context.view_layer.update()
        assert len(body.data.vertices) == 10582
        assert len(body.data.uv_layers) == 1
        assert len(body.children) == 2
        assert bpy.ops.human_modeling.set_height(height=1.75) == {"FINISHED"}
        bpy.context.view_layer.update()
        assert abs(smooth_height(body) - 1.75) < 1e-5
        assert bpy.ops.human_modeling.set_height(height=1.75) == {"FINISHED"}
        bpy.context.view_layer.update()
        assert abs(smooth_height(body) - 1.75) < 1e-5
        graph = bpy.context.evaluated_depsgraph_get()
        for eye in body.children:
            evaluated_key = eye.evaluated_get(graph).data.shape_keys.key_blocks["Morphologie"]
            assert abs(evaluated_key.value - value) < 1e-6
        mesh = body.evaluated_get(graph).to_mesh()
        assert all(math.isfinite(c) for vertex in mesh.vertices for c in vertex.co)
        assert all(face.area > 1e-12 for face in mesh.polygons)
        body.evaluated_get(graph).to_mesh_clear()
        bodies.append(body)

    assert len({body.data.as_pointer() for body in bodies}) == 5
    assert len({body.data.shape_keys.as_pointer() for body in bodies}) == 5
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.studiolight_rotate_z = .4
    scene.display.shading.color_type = "SINGLE"
    scene.display.shading.single_color = (.55, .57, .6)
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "BOTH"
    scene.display.shading.background_type = "WORLD"
    scene.world.color = (.065, .065, .065)
    scene.render.resolution_x = 1700
    scene.render.resolution_y = 650
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    camera_data = bpy.data.cameras.new("Comparaison orthographique")
    camera = bpy.data.objects.new(camera_data.name, camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.location = (0, -10, .88)
    camera.rotation_euler = (Vector((0, 0, .88)) - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = 5.8
    for name, angle in (("face", 0), ("trois-quarts", math.pi / 4), ("profil", math.pi / 2)):
        for body in bodies:
            body.rotation_euler.z = angle
        scene.render.filepath = str(output / f"{name}.png")
        bpy.ops.render.render(write_still=True)

    checker_material = bpy.data.materials.new("Contrôle UV · damier")
    checker_material.use_nodes = True
    nodes = checker_material.node_tree.nodes
    nodes.clear()
    uv = nodes.new("ShaderNodeUVMap")
    uv.uv_map = "UVMap"
    checker = nodes.new("ShaderNodeTexChecker")
    checker.inputs["Scale"].default_value = 40
    checker.inputs["Color1"].default_value = (.03, .08, .15, 1)
    checker.inputs["Color2"].default_value = (.8, .85, .9, 1)
    emission = nodes.new("ShaderNodeEmission")
    material_output = nodes.new("ShaderNodeOutputMaterial")
    links = checker_material.node_tree.links
    links.new(uv.outputs["UV"], checker.inputs["Vector"])
    links.new(checker.outputs["Color"], emission.inputs["Color"])
    links.new(emission.outputs[0], material_output.inputs["Surface"])
    for body in bodies:
        body.data.materials.append(checker_material)
        body.rotation_euler.z = math.pi / 4
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 8
    scene.render.filepath = str(output / "damier-uv.png")
    bpy.ops.render.render(write_still=True)
    scene.render.engine = "BLENDER_WORKBENCH"

    for body in bodies:
        body.rotation_euler.z = 0
    filename = str(output / "Comparaison-morphologies.blend")
    bpy.ops.wm.save_as_mainfile(filepath=filename)
    bpy.ops.wm.open_mainfile(filepath=filename)
    reloaded = [obj for obj in bpy.context.scene.objects if obj.get("human_modeling_body")]
    assert len(reloaded) == 5
    bpy.context.view_layer.update()
    assert all(abs(smooth_height(body) - 1.75) < 1e-5 for body in reloaded)
    print("PASS: five morphologies, height, independent meshes and eyes, subdivision, save/reopen")


if __name__ == "__main__":
    main()
