"""Verify profile operators, 0.8 upgrade and persisted muscle drivers."""

import json
from pathlib import Path
import sys

import bpy
import numpy as np


def main():
    from bl_ext.user_default.human_modeling import body_profiles, character_presets, geometry_quality
    from bl_ext.user_default.human_modeling.proportions import MUSCLE_CONTROLS
    old_asset, output = [Path(p).resolve() for p in sys.argv[sys.argv.index("--")+1:]]
    bpy.ops.human_modeling.create()
    body = bpy.context.object
    keys = body.data.shape_keys
    keys["hm_nose_width"] = .4
    keys["hm_legs"] = .25
    keys["hm_muscles_arms"] = .7
    records = []
    for sex in (0., .5, 1.):
        keys.key_blocks["Morphologie"].value = sex
        for identifier, (_, fat, muscle) in body_profiles.PROFILES.items():
            assert bpy.ops.human_modeling.body_profile(profile=identifier) == {"FINISHED"}
            assert keys["hm_nose_width"] == .4 and keys["hm_legs"] == .25
            assert keys["hm_corpulence"] == fat and keys["hm_muscles"] == muscle
            assert all(keys["hm_"+name] == 0 for name, _ in MUSCLE_CONTROLS[1:])
            bpy.context.view_layer.update()
            geometry = geometry_quality.report(body, bpy.context)["geometry"]
            assert geometry["intersections"]["crossing_triangle_pairs"] == 0, (sex, identifier)
            records.append({"sex": sex, "profile": identifier, "crossings": 0})
    with bpy.data.libraries.load(str(old_asset), link=False) as (_, target):
        target.collections = ["Realistic Human Base"]
    collection = target.collections[0]
    bpy.context.scene.collection.children.link(collection)
    old = next(obj for obj in collection.objects if obj.get("human_modeling_body"))
    bpy.context.view_layer.objects.active = old
    old.data.shape_keys["hm_waist"] = .25
    old.data.shape_keys["hm_nose_width"] = -.3
    old.data.shape_keys.key_blocks["Basis"].data[100].co.z += .0002
    before = character_presets.capture(old)
    base = np.array([v.co[:] for v in old.data.shape_keys.key_blocks[0].data])
    count = len(bpy.data.objects), len(bpy.data.meshes)
    assert bpy.ops.human_modeling.add_proportions() == {"FINISHED"}
    assert count == (len(bpy.data.objects), len(bpy.data.meshes))
    assert character_presets.capture(old) == before
    assert np.array_equal(base, np.array([v.co[:] for v in old.data.shape_keys.key_blocks[0].data]))
    # A 0.8 JSON omits new controls and must load with neutral new values.
    legacy = dict(before)
    legacy["controls"] = {key: value for key, value in before["controls"].items() if not key.startswith("muscles")}
    character_presets.apply(old, legacy, 1.)
    assert all(old.data.shape_keys["hm_"+name] == 0 for name, _ in MUSCLE_CONTROLS)
    old.data.shape_keys["hm_muscles"] = .6
    old.data.shape_keys["hm_muscles_arms"] = -.8
    old.data.shape_keys.update_tag()
    bpy.context.view_layer.update()
    assert all(curve.is_valid for curve in old.data.shape_keys.animation_data.drivers)
    old_name = old.name
    file = output / "Migration-musculature-09.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(file), compress=True)
    bpy.ops.wm.open_mainfile(filepath=str(file))
    old = bpy.data.objects[old_name]
    assert abs(old.data.shape_keys["hm_muscles"]-.6) < 1e-6
    assert all(curve.is_valid for curve in old.data.shape_keys.animation_data.drivers)
    (output / "workflow-muscles.json").write_text(json.dumps({"profiles": records,
        "upgrade_08_preserves_settings_and_sculpt": True, "old_presets": True,
        "saved_drivers": True, "no_orphans": True}, indent=2), encoding="utf-8")
    print("PASS: 18 profiles, 0.8 upgrade, custom sculpt preserved, legacy JSON, drivers after reopen", flush=True)


if __name__ == "__main__":
    main()
