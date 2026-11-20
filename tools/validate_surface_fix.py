"""Verify the inner-eyelid correction on new and existing character meshes."""

import json
from pathlib import Path
import sys

import bpy
import numpy as np


def refresh(body):
    body.data.shape_keys.update_tag()
    bpy.context.view_layer.update()


def main():
    from bl_ext.user_default.human_modeling import surface_fix, geometry_quality as qa, character_presets
    old_asset, output = [Path(value).resolve() for value in sys.argv[sys.argv.index("--") + 1:]]
    output.mkdir(parents=True, exist_ok=True)
    bpy.ops.human_modeling.create()
    body = bpy.context.object
    results = []
    for sex in (0, .25, .5, .75, 1):
        body.data.shape_keys.key_blocks["Morphologie"].value = sex
        refresh(body)
        result = qa.report(body, bpy.context)["geometry"]
        assert result["intersections"]["crossing_triangle_pairs"] == 0, sex
        assert result["zero_area_faces"] == 0 and result["non_manifold_edges"] == 0
        results.append({"morphology": sex, "result": result})
    with bpy.data.libraries.load(str(old_asset), link=False) as (_, target):
        target.collections = ["Realistic Human Base"]
    collection = target.collections[0]
    bpy.context.scene.collection.children.link(collection)
    old = next(obj for obj in collection.objects if obj.get("human_modeling_body"))
    old.data.shape_keys.key_blocks["Morphologie"].value = 0
    modifier = old.modifiers.new("Test subdivision", "SUBSURF")
    modifier.levels = 1
    bpy.context.view_layer.objects.active = old
    refresh(old)
    assert qa.report(old, bpy.context)["geometry"]["intersections"]["crossing_triangle_pairs"] == 82
    before_state = character_presets.capture(old)
    count = len(bpy.data.objects), len(bpy.data.meshes)
    assert bpy.ops.human_modeling.repair_surface() == {"FINISHED"}
    refresh(old)
    assert (len(bpy.data.objects), len(bpy.data.meshes)) == count
    assert character_presets.capture(old) == before_state
    assert qa.report(old, bpy.context)["geometry"]["intersections"]["crossing_triangle_pairs"] == 0
    assert bpy.ops.human_modeling.repair_surface() == {"FINISHED"}
    assert (len(bpy.data.objects), len(bpy.data.meshes)) == count
    base = np.array([point.co[:] for point in old.data.shape_keys.key_blocks[0].data])
    corrected = np.array([point.co[:] for point in old.data.shape_keys.key_blocks[surface_fix.KEY].data])
    assert np.linalg.norm(corrected-base, axis=1).max() < .0009
    active_controls = ("head_width", "head_height", "eye_spacing", "eye_height")
    extremes = []
    for sex in (0, .5, 1):
        old.data.shape_keys.key_blocks["Morphologie"].value = sex
        for control in active_controls:
            for amount in (-1, 1):
                old.data.shape_keys["hm_"+control] = amount
                refresh(old)
                result = qa.report(old, bpy.context)["geometry"]
                extremes.append({"sex": sex, "control": control, "amount": amount,
                                 "crossings": result["intersections"]["crossing_triangle_pairs"]})
                assert result["intersections"]["crossing_triangle_pairs"] == 0, extremes[-1]
                assert result["zero_area_faces"] == 0
            old.data.shape_keys["hm_"+control] = 0.
    refresh(old)
    name = old.name
    bpy.ops.wm.save_as_mainfile(filepath=str(output / "Correction-paupieres-verifiee.blend"), compress=True)
    bpy.ops.wm.open_mainfile(filepath=str(output / "Correction-paupieres-verifiee.blend"))
    old = bpy.data.objects[name]
    assert old.data.get("human_modeling_surface_revision") == 1
    assert all(curve.is_valid for curve in old.data.shape_keys.animation_data.drivers)
    (output / "tests-correction-paupieres.json").write_text(json.dumps({"neutral_morphologies": results,
        "eye_control_extremes": extremes, "max_displacement_m": float(np.linalg.norm(corrected-base, axis=1).max())}, indent=2), encoding="utf-8")
    print("PASS: zero crossings on five neutral morphologies, 82 to zero on old body, idempotent correction, no orphan meshes, controls preserved, 24 ocular extremes, reopen", flush=True)


if __name__ == "__main__":
    main()
