"""Verify stature references, transformed models, scene units and vertex landmarks."""

import copy
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector


def refresh(body):
    body.data.shape_keys.update_tag()
    bpy.context.view_layer.update()


def main():
    from bl_ext.user_default.human_modeling import character_presets, measurements

    output = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
    output.mkdir(parents=True, exist_ok=True)
    assert bpy.ops.human_modeling.create() == {"FINISHED"}
    body = bpy.context.object
    refresh(body)
    original = measurements.measure(body, bpy.context)["height_m"]
    body.rotation_euler = (.37, .18, .55)
    body.scale = (1.2, .8, 1.4)
    refresh(body)
    assert abs(measurements.measure(body, bpy.context)["height_m"] - original * 1.4) < 1e-6
    body.hm_reference_group = "20_29"
    body.hm_reference_sex = "M"
    body.hm_reference_percentile = "P50"
    assert measurements.target(body) == 176.1
    assert bpy.ops.human_modeling.reference_height() == {"FINISHED"}
    refresh(body)
    assert abs(measurements.measure(body, bpy.context)["height_m"] - 1.761) < 1e-6
    parent = bpy.data.objects.new("Parent de contrôle", None)
    bpy.context.scene.collection.objects.link(parent)
    parent.rotation_euler = (.2, .4, .15)
    parent.scale = (1.3, .9, 1.1)
    body.parent = parent
    refresh(body)
    assert bpy.ops.human_modeling.reference_height() == {"FINISHED"}
    refresh(body)
    assert abs(measurements.measure(body, bpy.context)["height_m"] - 1.761) < 1e-6

    bpy.context.scene.unit_settings.scale_length = .01
    assert bpy.ops.human_modeling.reference_height() == {"FINISHED"}
    refresh(body)
    assert abs(measurements.measure(body, bpy.context)["height_m"] - 1.761) < 1e-6
    assert bpy.ops.human_modeling.set_height(height=180) == {"FINISHED"}
    refresh(body)
    assert abs(measurements.measure(body, bpy.context)["height_m"] - 1.8) < 1e-6
    body.hm_reference_sex = "F"
    assert measurements.target(body) == 163.3
    assert bpy.ops.human_modeling.reference_height() == {"FINISHED"}
    refresh(body)
    assert abs(measurements.report(body, bpy.context)["height_difference_cm"]) < .0001

    state = character_presets.capture(body)
    assert state["measurement_reference"]["sex"] == "F"
    assert bpy.ops.human_modeling.create() == {"FINISHED"}
    other = bpy.context.object
    character_presets.apply(other, state)
    assert other.hm_reference_sex == "F"
    assert other.hm_reference_group == "20_29"
    legacy_preset = copy.deepcopy(state)
    del legacy_preset["measurement_reference"]
    character_presets.apply(other, legacy_preset)
    assert other.hm_reference_sex == "F"

    other.hm_reference_group = "80_PLUS"
    other.hm_reference_percentile = "P95"
    before = tuple(other.scale)
    try:
        bpy.ops.human_modeling.reference_height()
    except RuntimeError:
        pass
    else:
        raise AssertionError("An unpublished percentile was applied")
    assert tuple(other.scale) == before
    assert measurements.report(other, bpy.context)["height_difference_cm"] is None

    bpy.context.scene.unit_settings.scale_length = 1
    assert bpy.ops.human_modeling.create() == {"FINISHED"}
    marked = bpy.context.object
    bpy.ops.object.mode_set(mode="EDIT")
    mesh = bmesh.from_edit_mesh(marked.data)
    mesh.verts.ensure_lookup_table()
    for face in mesh.faces:
        face.select_set(False)
    for edge in mesh.edges:
        edge.select_set(False)
    for vertex in mesh.verts:
        vertex.select_set(False)
    vertex = min(mesh.verts, key=lambda point: (point.co - Vector((0, .03, .8))).length)
    vertex.select_set(True)
    mesh.select_history.clear()
    mesh.select_history.add(vertex)
    bmesh.update_edit_mesh(marked.data)
    assert bpy.ops.human_modeling.mark_pelvis() == {"FINISHED"}
    bpy.ops.object.mode_set(mode="OBJECT")
    refresh(marked)
    result = measurements.measure(marked, bpy.context)
    segments = result["segments"]
    assert 0 < segments["lower_fraction"] < 1
    assert abs(segments["below_landmark_m"] + segments["above_landmark_m"] - result["height_m"]) < 1e-9
    marked.data.shape_keys["hm_legs"] = 1
    refresh(marked)
    changed = measurements.measure(marked, bpy.context)
    assert changed["segments"]["below_landmark_m"] > segments["below_landmark_m"] + .02
    marker = next(obj for obj in marked.children if obj.get(measurements.LANDMARK_KEY) == "pelvis")
    assert marker.parent_type == "VERTEX"
    name = marked.name
    report_file = output / "controle-dimensionnel.json"
    assert bpy.ops.human_modeling.measurement_report(filepath=str(report_file)) == {"FINISHED"}
    report = json.loads(report_file.read_text(encoding="utf-8"))
    assert report["reference"]["table"] == 7
    assert report["reference"]["source_url"].endswith("cdc_174595_DS1.pdf")
    assert len(report["reference"]["sha256"]) == 64
    assert report["model"]["base"] == "blender_studio_realistic_v1"
    assert report["model"]["controls"]["hm_legs"] == 1
    assert report["model"]["scene_unit_scale_m"] == 1
    scene_file = str(output / "Mesures-verifiees.blend")
    bpy.ops.wm.save_as_mainfile(filepath=scene_file, compress=True)
    bpy.ops.wm.open_mainfile(filepath=scene_file)
    marked = bpy.data.objects[name]
    refresh(marked)
    reopened = measurements.measure(marked, bpy.context)
    assert abs(reopened["segments"]["below_landmark_m"] - changed["segments"]["below_landmark_m"]) < 1e-6
    assert all(math.isfinite(value) for key, value in reopened.items() if key != "segments")
    print("PASS: published medians, rotation and nonuniform scale, centimetre scenes,",
          "transformed parent, missing percentile, legacy preset, reference persistence, moving vertex landmark and reopen")


if __name__ == "__main__":
    main()
