"""Check neutral preservation, control extremes, eye transport and legacy upgrade."""

import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np


def coordinates(obj, evaluated=False):
    if evaluated:
        obj = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = obj.to_mesh()
    values = np.empty(len(mesh.vertices) * 3)
    mesh.vertices.foreach_get("co", values)
    obj.to_mesh_clear()
    return values.reshape((-1, 3))


def refresh(keys):
    keys.update_tag()
    bpy.context.view_layer.update()


def main():
    from bl_ext.user_default.human_modeling.proportions import CONTROLS, CURRENT_SCHEMA, property_name

    scratch = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
    reports = []
    assert bpy.ops.human_modeling.create() == {"FINISHED"}
    body = bpy.context.object
    keys = body.data.shape_keys
    assert body.data["human_modeling_schema"] == CURRENT_SCHEMA
    assert all(driver.is_valid for driver in keys.animation_data.drivers)
    for modifier in body.modifiers:
        modifier.show_viewport = False
    for sex in (0, .5, 1):
        keys.key_blocks["Morphologie"].value = sex
        refresh(keys)
        actual = coordinates(body, True)
        # Attendu : formule générale des shape keys (toutes les clés actives, y compris relief, atlas
        # et raccords d'âge actifs par défaut), pas seulement le mélange de sexe.
        def key_points(key):
            return np.array([tuple(point.co) for point in key.data])
        expected = key_points(keys.reference_key).copy()
        for key in keys.key_blocks:
            if key == keys.reference_key or key.mute or key.vertex_group:
                continue
            value = min(max(key.value, key.slider_min), key.slider_max)
            if value:
                expected += value * (key_points(key) - key_points(key.relative_key))
        assert np.max(np.abs(actual - expected)) < 1e-6
        for identifier, _ in CONTROLS:
            prop = property_name(identifier)
            for value in (-1, 1):
                keys[prop] = value
                refresh(keys)
                evaluated = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
                mesh = evaluated.to_mesh()
                invalid_faces = sum(face.area < 1e-12 for face in mesh.polygons)
                assert invalid_faces == 0, (sex, identifier, value, invalid_faces)
                assert all(math.isfinite(c) for vertex in mesh.vertices for c in vertex.co)
                if identifier == "corpulence" and value == 1:
                    points = np.array([tuple(vertex.co) for vertex in mesh.vertices])
                    inner_legs = (actual[:, 2] > .35) & (actual[:, 2] < .9) & (np.abs(actual[:, 0]) > .0001)
                    assert np.all(actual[inner_legs, 0] * points[inner_legs, 0] >= 0), sex
                evaluated.to_mesh_clear()
                if identifier in ("eye_spacing", "eye_height", "legs", "torso"):
                    for eye in body.children:
                        points = coordinates(eye, True)
                        extent = np.ptp(points, axis=0)
                        assert np.all(extent > .02) and np.all(extent < .03), (identifier, extent)
                reports.append((sex, identifier, value, invalid_faces))
            keys[prop] = 0.0
            refresh(keys)

    keys.key_blocks["Morphologie"].value = .5
    refresh(keys)
    evaluated = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    neutral_normals = np.array([tuple(face.normal) for face in mesh.polygons])
    evaluated.to_mesh_clear()
    rng = np.random.default_rng(178)
    combinations = [np.ones(len(CONTROLS)), -np.ones(len(CONTROLS))]
    combinations.extend(rng.uniform(-1, 1, (30, len(CONTROLS))))
    for index, values in enumerate(combinations):
        for (identifier, _), value in zip(CONTROLS, values):
            keys[property_name(identifier)] = float(value)
        refresh(keys)
        evaluated = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
        mesh = evaluated.to_mesh()
        assert all(face.area > 1e-12 for face in mesh.polygons), index
        normals = np.array([tuple(face.normal) for face in mesh.polygons])
        assert np.all(np.sum(normals * neutral_normals, axis=1) > 0), index
        evaluated.to_mesh_clear()

    for identifier, _ in CONTROLS:
        keys[property_name(identifier)] = .5
    refresh(keys)
    assert bpy.ops.human_modeling.create() == {"FINISHED"}
    second = bpy.context.object
    assert second.data != body.data
    assert all(second.data.shape_keys[property_name(identifier)] == 0 for identifier, _ in CONTROLS)
    assert bpy.ops.human_modeling.reset_proportions() == {"FINISHED"}
    bpy.context.view_layer.objects.active = body
    assert bpy.ops.human_modeling.reset_proportions() == {"FINISHED"}
    refresh(keys)
    assert all(keys[property_name(identifier)] == 0 for identifier, _ in CONTROLS)

    with bpy.data.libraries.load(str(scratch / "adult-original.blend"), link=False) as (_, target):
        target.collections = ["Realistic Human Base"]
    collection = target.collections[0]
    bpy.context.scene.collection.children.link(collection)
    legacy = next(obj for obj in collection.objects if obj.get("human_modeling_body"))
    bpy.context.view_layer.objects.active = legacy
    old_coordinates = coordinates(legacy, True)
    object_count = len(bpy.data.objects)
    assert bpy.ops.human_modeling.add_proportions() == {"FINISHED"}
    refresh(legacy.data.shape_keys)
    assert len(bpy.data.objects) == object_count
    assert np.max(np.abs(coordinates(legacy, True) - old_coordinates)) < 1e-6
    legacy.data.shape_keys["hm_eye_spacing"] = 1.0
    refresh(legacy.data.shape_keys)
    assert all(driver.is_valid for driver in legacy.data.shape_keys.animation_data.drivers)
    legacy_name = legacy.name
    file = str(scratch / "controls-verified.blend")
    bpy.ops.wm.save_as_mainfile(filepath=file)
    bpy.ops.wm.open_mainfile(filepath=file)
    legacy = bpy.context.scene.objects[legacy_name]
    refresh(legacy.data.shape_keys)
    assert legacy.data.shape_keys["hm_eye_spacing"] == 1.0
    assert all(driver.is_valid for driver in legacy.data.shape_keys.animation_data.drivers)
    (scratch / "controls-report.json").write_text(json.dumps(reports, indent=2), encoding="utf-8")
    print("PASS", len(reports), "extremes,", len(combinations),
          "combinations, neutral geometry, independent characters, legacy upgrade, save and reopen")


if __name__ == "__main__":
    main()
