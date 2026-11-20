"""Save a review scene for the experimental landmark-guided age transfer."""

import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    asset, output = (Path(value).resolve() for value in args)
    output.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    for obj in tuple(scene.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    families = []
    captions = {}
    gray = bpy.data.materials.new("Argile de revue")
    gray.diffuse_color = (.55, .57, .60, 1)
    white = bpy.data.materials.new("Légendes")
    white.diffuse_color = (.9, .9, .9, 1)
    for sex, label in ((0, "Féminine"), (1, "Masculine")):
        objects = []
        for index, stage in enumerate(("Enfant", "Adolescent", "Adulte", "Senior")):
            with bpy.data.libraries.load(str(asset), link=False) as (_, target):
                target.collections = ["Realistic Human Base"]
            collection = target.collections[0]
            scene.collection.children.link(collection)
            body = next(obj for obj in collection.objects if obj.get("human_modeling_body"))
            body.name = label + " · " + stage
            body.location.x = (index - 1.5) * 1.1
            keys = body.data.shape_keys
            keys.key_blocks["Morphologie"].value = float(sex)
            keys["human_modeling_age"] = float(index)
            keys.update_tag()
            for obj in (body, *body.children):
                for polygon in obj.data.polygons:
                    polygon.use_smooth = True
                obj.data.materials.clear()
                obj.data.materials.append(gray)
            surface = body.modifiers.new("Aperçu", "SUBSURF")
            surface.levels = 1
            surface.render_levels = 1
            body.modifiers.move(list(body.modifiers).index(surface),0)
            objects.append(body)
            caption = bpy.data.curves.new("Âge cible", "FONT")
            targets = body.get("human_modeling_age_targets")
            caption.body = f"{int(targets[index])} ans · étude" if targets is not None else stage + " · étude"
            caption.align_x = "CENTER"
            caption.size = .055
            caption.materials.append(white)
            text = bpy.data.objects.new(caption.name, caption)
            scene.collection.objects.link(text)
            text.location = (body.location.x, -.1, -.14)
            text.rotation_euler.x = math.pi/2
            captions[body.name] = text
        families.append((label, objects))
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.single_color = (.55, .57, .60)
    scene.display.shading.show_shadows = False
    scene.display.shading.show_cavity = False
    scene.render.resolution_x = 2000
    scene.render.resolution_y = 1000
    scene.render.resolution_percentage = 100
    camera = bpy.data.objects.new("Revue du transfert", bpy.data.cameras.new("Revue du transfert"))
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.location = (0, -10, .86)
    camera.rotation_euler = (Vector((0, 0, .86)) - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 4.5
    for label, current in families:
        for _, objects in families:
            for body in objects:
                for obj in (body, *body.children):
                    obj.hide_render = objects is not current
                captions[body.name].hide_render = objects is not current
        for view, angle in (("face", 0), ("profil", math.pi / 2), ("trois-quarts", math.pi / 4)):
            for body in current:
                body.rotation_euler.z = angle
            scene.render.filepath = str(output / f"{label}-{view}.png")
            bpy.ops.render.render(write_still=True)
        camera.data.ortho_scale = 1.6
        camera.location.z = 1.55
        scene.render.resolution_y = 800
        for index, body in enumerate(current):
            body.rotation_euler.z = 0
            bpy.context.view_layer.update()
            evaluated = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
            mesh = evaluated.to_mesh()
            crown = max(vertex.co.z for vertex in mesh.vertices)
            evaluated.to_mesh_clear()
            body.location = ((index-1.5)*.37, 0, 1.72-crown)
            text = captions[body.name]
            text.location = (body.location.x, -1.5, 1.28)
            text.data.size = .025
        camera.rotation_euler = (Vector((0,0,1.55))-camera.location).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = str(output / f"{label}-visages.png")
        bpy.ops.render.render(write_still=True)
        for index, body in enumerate(current):
            body.location = ((index-1.5)*1.1, 0, 0)
            text = captions[body.name]
            text.location = (body.location.x, -.1, -.14)
            text.data.size = .055
        camera.data.ortho_scale = 4.5
        camera.location.z = .86
        camera.rotation_euler = (Vector((0,0,.86))-camera.location).to_track_quat("-Z", "Y").to_euler()
        scene.render.resolution_y = 1000
    for label, objects in families:
        for body in objects:
            body.rotation_euler.z = 0
            for obj in (body, *body.children):
                obj.hide_render = label != "Féminine"
                obj.hide_set(label != "Féminine")
            captions[body.name].hide_render = label != "Féminine"
            captions[body.name].hide_set(label != "Féminine")
    bpy.ops.wm.save_as_mainfile(filepath=str(output / "Transfert-age-experimental.blend"), compress=True)
    print("EXPERIMENTAL_AGE_REVIEW_READY", flush=True)


if __name__ == "__main__":
    main()
