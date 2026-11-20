"""Build the editable source collection from the CC0 Human Base Meshes bundle."""

import sys
from pathlib import Path

import bpy
from mathutils import Matrix


def topology(mesh):
    edges = {tuple(sorted(edge.vertices)) for edge in mesh.edges}
    faces = {tuple(sorted(face.vertices)) for face in mesh.polygons}
    return len(mesh.vertices), edges, faces


def add_morph(collection, name, female, male, female_space, male_space):
    if topology(female.data) != topology(male.data):
        raise ValueError(f"Connectivity differs for {name}")

    mesh = female.data.copy()
    mesh.name = name
    mesh.transform(female_space)
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    obj.shape_key_add(name="Basis")
    morph = obj.shape_key_add(name="Morphologie")
    coords = [coordinate for vertex in male.data.vertices for coordinate in male_space @ vertex.co]
    morph.data.foreach_set("co", coords)
    return obj, morph


def main():
    output = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
    bpy.context.view_layer.update()
    female = bpy.data.objects["GEO-body_female_realistic"]
    male = bpy.data.objects["GEO-body_male_realistic"]
    collection = bpy.data.collections.new("Realistic Human Base")
    body, _ = add_morph(collection, "Corps", female, male, Matrix.Identity(4), Matrix.Identity(4))
    body["human_modeling_body"] = True
    body["source"] = "Blender Studio Human Base Meshes v1.4.1 (CC0)"

    # The base coordinates follow the source object's local pose. Store each
    # eyeball as a body-local morph so insertion and interpolation share a frame.
    for side, name in (("L", "Œil gauche"), ("R", "Œil droit")):
        female_eye = bpy.data.objects[f"{female.name}.eye.{side}"]
        male_eye = bpy.data.objects[f"{male.name}.eye.{side}"]
        eye, morph = add_morph(
            collection, name, female_eye, male_eye,
            female.matrix_world.inverted() @ female_eye.matrix_world,
            male.matrix_world.inverted() @ male_eye.matrix_world,
        )
        eye.parent = body
        driver = morph.driver_add("value").driver
        driver.type = "AVERAGE"
        variable = driver.variables.new()
        variable.type = "SINGLE_PROP"
        variable.targets[0].id = body
        variable.targets[0].data_path = 'data.shape_keys.key_blocks["Morphologie"].value'

    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.data.libraries.write(str(output), {collection}, fake_user=True, compress=True)


if __name__ == "__main__":
    main()
