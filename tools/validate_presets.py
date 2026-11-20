"""Verify reproducibility, preset round trips and upgrade without partial changes."""

import copy
import json
import sys
from pathlib import Path
from unittest.mock import patch

import bpy
import numpy as np


def refresh(body):
    body.data.shape_keys.update_tag()
    bpy.context.view_layer.update()


def evaluated_points(body):
    evaluated = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    values = np.empty(len(mesh.vertices) * 3)
    mesh.vertices.foreach_get("co", values)
    evaluated.to_mesh_clear()
    return values


def main():
    from bl_ext.user_default.human_modeling import character_presets as presets
    from bl_ext.user_default.human_modeling.proportions import CONTROLS, CURRENT_SCHEMA, FACE_CONTROLS

    scratch = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
    bpy.ops.human_modeling.create()
    body = bpy.context.object
    original = presets.capture(body)
    assert bpy.ops.human_modeling.randomize(seed=42, strength=.6, scope="FACE") == {"FINISHED"}
    first = presets.capture(body)
    faces = {name for name, _ in FACE_CONTROLS}
    assert all(first["controls"][name] == 0 for name, _ in CONTROLS if name not in faces)
    assert first["morphology"] == original["morphology"]
    assert bpy.ops.human_modeling.randomize(seed=42, strength=.6, scope="FACE") == {"FINISHED"}
    assert presets.capture(body) == first
    assert bpy.ops.human_modeling.randomize(seed=42, strength=.6, scope="ALL") == {"FINISHED"}
    all_zones = presets.capture(body)
    assert all(all_zones["controls"][name] == first["controls"][name] for name in faces)
    assert bpy.ops.human_modeling.randomize(seed=43, strength=.6, scope="FACE") == {"FINISHED"}
    assert presets.capture(body) != first

    keys = body.data.shape_keys
    keys["hm_corpulence"] = .8
    body.scale = (1.1, 1.1, 1.1)
    refresh(body)
    state = presets.capture(body)
    points = evaluated_points(body)
    file = scratch / "test-character.json"
    assert bpy.ops.human_modeling.save_preset(filepath=str(file)) == {"FINISHED"}
    assert presets.read(file) == state

    bpy.ops.human_modeling.create()
    other = bpy.context.object
    other.location.x = 3
    before = presets.capture(other)
    assert bpy.ops.human_modeling.load_preset(filepath=str(file), factor=0) == {"FINISHED"}
    assert presets.capture(other) == before
    assert bpy.ops.human_modeling.load_preset(filepath=str(file), factor=.5) == {"FINISHED"}
    mixed = presets.capture(other)
    assert all(abs(mixed["controls"][name] - value * .5) < 1e-12 for name, value in state["controls"].items())
    assert tuple(other.location) == (3, 0, 0)
    assert bpy.ops.human_modeling.load_preset(filepath=str(file), factor=1) == {"FINISHED"}
    refresh(other)
    assert np.max(np.abs(evaluated_points(other) - points)) < 1e-6
    assert presets.capture(other) == state
    assert tuple(other.location) == (3, 0, 0)
    assert presets.capture(body) == state

    invalid = []
    for key, value in (("version", 99), ("base", "another_base"), ("morphology", 2), ("scale", [1, 1])):
        payload = copy.deepcopy(state)
        payload[key] = value
        invalid.append(payload)
    for value in (True, float("nan"), float("inf"), 2.0, "0.5", 10 ** 400):
        payload = copy.deepcopy(state)
        payload["controls"]["corpulence"] = value
        invalid.append(payload)
    payload = copy.deepcopy(state)
    payload["controls"]["unknown_control"] = .2
    invalid.append(payload)
    for payload in invalid:
        try:
            presets.apply(other, payload)
        except ValueError:
            pass
        else:
            raise AssertionError("An invalid preset was accepted")
        assert presets.capture(other) == state

    saved = file.read_bytes()
    temporary_files = set(scratch.glob("*.tmp"))
    with patch.object(presets.os, "replace", side_effect=OSError("simulated write failure")):
        try:
            presets.write(file, state)
        except OSError:
            pass
        else:
            raise AssertionError("The write failure was swallowed")
    assert file.read_bytes() == saved
    assert set(scratch.glob("*.tmp")) == temporary_files
    original_assign = presets.assign
    assignments = 0

    def fail_first_assignment(target, requested):
        nonlocal assignments
        assignments += 1
        if assignments == 1:
            target.data.shape_keys["hm_waist"] = .99
            target.scale = (2, 2, 2)
            raise RuntimeError("simulated assignment failure")
        original_assign(target, requested)

    with patch.object(presets, "assign", side_effect=fail_first_assignment):
        try:
            presets.apply(other, before)
        except RuntimeError:
            pass
        else:
            raise AssertionError("The assignment failure was swallowed")
    assert presets.capture(other) == state

    with bpy.data.libraries.load(str(scratch / "legacy-03.blend"), link=False) as (_, target):
        target.collections = ["Realistic Human Base"]
    collection = target.collections[0]
    bpy.context.scene.collection.children.link(collection)
    legacy = next(obj for obj in collection.objects if obj.get("human_modeling_body"))
    legacy.data.shape_keys["hm_mouth"] = .4
    legacy.data.shape_keys["hm_shoulders"] = -.6
    refresh(legacy)
    before_geometry = evaluated_points(legacy)
    before_state = presets.capture(legacy)
    bpy.context.view_layer.objects.active = legacy
    counts = (len(bpy.data.objects), len(bpy.data.meshes))
    assert bpy.ops.human_modeling.add_proportions() == {"FINISHED"}
    refresh(legacy)
    assert legacy.data["human_modeling_schema"] == CURRENT_SCHEMA
    assert presets.capture(legacy) == before_state
    assert np.max(np.abs(evaluated_points(legacy) - before_geometry)) < 1e-6
    assert (len(bpy.data.objects), len(bpy.data.meshes)) == counts
    assert all(driver.is_valid for driver in legacy.data.shape_keys.animation_data.drivers)
    print("PASS: seeded variation, preset export/import and blending,",
          len(invalid), "invalid inputs, write and assignment failures, 0.3 upgrade preserving geometry and settings")


if __name__ == "__main__":
    main()
