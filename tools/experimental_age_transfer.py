"""Experimental age transfer. Hand correspondence is unresolved.

Write only to a disposable candidate asset. This experiment is excluded from
the extension build and has not been accepted for the installed human base.
"""

import sys
from pathlib import Path

import addon_utils
import bpy
import numpy as np
from mathutils import Vector
from mathutils.kdtree import KDTree


STAGES = (("Enfant", .1875), ("Adolescent", .35), ("Senior", 1.0))


def coordinates(mesh):
    vertices = mesh.vertices if isinstance(mesh, bpy.types.Mesh) else mesh.data
    values = np.empty(len(vertices) * 3)
    vertices.foreach_get("co", values)
    return values.reshape((-1, 3))


def reference(age, gender, with_landmarks=False, landmark_names=None):
    from bl_ext.user_default.mpfb.services import HumanService, TargetService
    settings = TargetService.get_default_macro_info_dict()
    settings.update(age=age, gender=gender)
    obj = HumanService.create_human(macro_detail_dict=settings)
    graph = bpy.context.evaluated_depsgraph_get()
    bpy.context.view_layer.update()
    evaluated = obj.evaluated_get(graph)
    mesh = evaluated.to_mesh()
    # The evaluated mask removes MakeHuman's clothing and joint helpers.
    verts = coordinates(mesh)
    mesh.calc_loop_triangles()
    triangles = np.array([tuple(face.vertices) for face in mesh.loop_triangles])
    evaluated.to_mesh_clear()
    landmarks = {}
    if with_landmarks:
        for modifier in obj.modifiers:
            modifier.show_viewport = False
        bpy.context.view_layer.update()
        evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        full_mesh = evaluated.to_mesh()
        for name in landmark_names or ("joint-l-shoulder", "joint-l-elbow", "joint-l-hand", "joint-l-hand-2"):
            group = obj.vertex_groups[name]
            indices = [vertex.index for vertex in obj.data.vertices
                       if any(item.group == group.index for item in vertex.groups)]
            landmarks[name] = np.array([tuple(full_mesh.vertices[index].co) for index in indices]).mean(axis=0)
        evaluated.to_mesh_clear()
    bpy.data.objects.remove(obj, do_unlink=True)
    if with_landmarks:
        return verts, triangles, landmarks
    return verts, triangles


def transfer(rest, triangles, changed, target):
    tree = KDTree(len(rest))
    for index, vertex in enumerate(rest):
        tree.insert(Vector(vertex), index)
    tree.balance()
    displacement = changed - rest
    result = np.empty_like(target)
    distances = []
    for index, vertex in enumerate(target):
        nearby = tree.find_n(Vector(vertex), 24)
        indices = [item[1] for item in nearby]
        gaps = np.array([item[2] for item in nearby])
        weights = 1 / np.maximum(gaps, .005) ** 2
        weights /= weights.sum()
        result[index] = vertex + np.sum(displacement[indices] * weights[:, None], axis=0)
        distances.append(float(gaps.min()))
    return result, (float(np.median(distances)), float(max(distances)))


def transport_arms(target, result, rest_joints, age_joints, gender, scale):
    """Transport each arm using measured limb ratios and explicit rest landmarks."""
    landmarks = (
        np.array(((.16, 0, 1.32), (.246, .024, 1.05), (.348, -.036, .85), (.38, -.075, .79))),
        np.array(((.18, 0, 1.37), (.287, -.003, 1.10), (.373, -.06, .89), (.404, -.11, .80))),
    )[gender]
    names = ("joint-l-shoulder", "joint-l-elbow", "joint-l-hand", "joint-l-hand-2")
    rest_source = np.array([rest_joints[name] for name in names])
    age_source = np.array([age_joints[name] for name in names])
    ratios = np.linalg.norm(np.diff(age_source, axis=0), axis=1) / np.linalg.norm(np.diff(rest_source, axis=0), axis=1)
    changed = [landmarks[0] + (age_source[0] - rest_source[0]) * scale]
    for index, ratio in enumerate(ratios):
        changed.append(changed[-1] + (landmarks[index + 1] - landmarks[index]) * ratio)
    changed = np.array(changed)
    for side in (-1, 1):
        original = landmarks * np.array((side, 1, 1))
        deformed = changed * np.array((side, 1, 1))
        distances = []
        transformed = []
        for index, ratio in enumerate(ratios):
            start, end = original[index:index + 2]
            direction = end - start
            projection = np.clip((target - start) @ direction / (direction @ direction), 0, 1)
            closest = start + projection[:, None] * direction
            distances.append(np.linalg.norm(target - closest, axis=1))
            transformed.append(deformed[index] + (target - start) * ratio)
        weights = 1 / np.maximum(np.array(distances), .015) ** 4
        weights /= weights.sum(axis=0)
        arm = np.sum(np.array(transformed) * weights[:, :, None], axis=0)
        amount = np.clip((target[:, 0] * side - landmarks[0, 0] + .025) / .085, 0, 1)
        amount *= np.clip((target[:, 2] - .55) / .15, 0, 1)
        amount *= np.clip((1.48 - target[:, 2]) / .10, 0, 1)
        amount = amount * amount * (3 - 2 * amount)
        result = result * (1 - amount[:, None]) + arm * amount[:, None]
    return result


def write_key(obj, name, coords):
    key = obj.data.shape_keys.key_blocks.get(name)
    if key is None:
        key = obj.shape_key_add(name=name)
    key.data.foreach_set("co", coords.reshape(-1))
    return key


def add_driver(key, body, stage, corrective):
    driver = key.driver_add("value").driver
    driver.type = "SCRIPTED"
    for name, path in (("age", '["human_modeling_age"]'), ("sex", 'key_blocks["Morphologie"].value')):
        var = driver.variables.new()
        var.name = name
        var.type = "SINGLE_PROP"
        var.targets[0].id_type = "KEY"
        var.targets[0].id = body.data.shape_keys
        var.targets[0].data_path = path
    index = {"Enfant": 0, "Adolescent": 1, "Senior": 3}[stage]
    driver.expression = f"max(0, 1-abs(age-{index}))" + ("*sex" if corrective else "")


def main():
    asset = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
    print("EXPERIMENTAL: validate hand correspondence before packaging this candidate", flush=True)
    addon_utils.enable("bl_ext.user_default.mpfb", default_set=True)
    with bpy.data.libraries.load(str(asset), link=False) as (_, target):
        target.collections = ["Realistic Human Base"]
    collection = target.collections[0]
    body = next(obj for obj in collection.objects if obj.get("human_modeling_body"))
    body.data.shape_keys["human_modeling_age"] = 2.0
    body.data.shape_keys.id_properties_ui("human_modeling_age").update(
        min=0.0, max=3.0, default=2.0,
        description="0 enfant, 1 adolescent, 2 adulte, 3 senior",
    )
    objects = [body, *body.children]
    results = {}
    for gender in (0, 1):
        source, triangles, rest_joints = reference(.5, gender, with_landmarks=True)
        key_name = "Morphologie" if gender else "Basis"
        targets = {obj.name: coordinates(obj.data.shape_keys.key_blocks[key_name]) for obj in objects}
        bounds = targets[body.name]
        scale = (bounds[:, 2].max() - bounds[:, 2].min()) / (source[:, 2].max() - source[:, 2].min())
        offset = np.array((0.0, 0.0, bounds[:, 2].min() - source[:, 2].min() * scale))
        rest = source * scale + offset
        for stage, age in STAGES:
            changed, _, age_joints = reference(age, gender, with_landmarks=True)
            if changed.shape != source.shape:
                raise ValueError("MPFB age vertex count changed")
            changed = changed * scale + offset
            for obj in objects:
                deformed, distances = transfer(rest, triangles, changed, targets[obj.name])
                if obj is body:
                    deformed = transport_arms(targets[obj.name], deformed, rest_joints, age_joints, gender, scale)
                if not np.isfinite(deformed).all():
                    raise ValueError("Non-finite age deformation")
                results[gender, stage, obj.name] = deformed - targets[obj.name]
                print("TRANSFER", gender, stage, obj.name, "median/max gap", distances, flush=True)

    for obj in objects:
        basis = coordinates(obj.data.shape_keys.key_blocks["Basis"])
        for stage, _ in STAGES:
            delta = results[0, stage, obj.name]
            key = write_key(obj, stage, basis + delta)
            add_driver(key, body, stage, False)
            correction = results[1, stage, obj.name] - delta
            key = write_key(obj, stage + " · morphologie", basis + correction)
            key.slider_min = -1
            add_driver(key, body, stage, True)
    body["age_source"] = "MPFB 2.0.18 macro targets, surface deformation transfer (CC0)"
    bpy.data.libraries.write(str(asset), {collection}, fake_user=True, compress=True)
    print("AGE_ASSET_READY", flush=True)


if __name__ == "__main__":
    main()
