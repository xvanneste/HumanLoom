"""Check portable landmarks, exact topology, symmetry and transactional presets."""

import copy
import json
import sys
from pathlib import Path
from unittest.mock import patch

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_anatomy import fixture_landmarks, refresh


def main():
    from bl_ext.user_default.human_modeling import anatomy, landmark_sets as atlas, character_presets as presets
    output = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
    output.mkdir(parents=True, exist_ok=True)
    bpy.ops.human_modeling.create()
    source = bpy.context.object
    source.name = "Source féminine · repères de travail"
    source.data.shape_keys.key_blocks["Morphologie"].value = 0
    fixture_landmarks(source, anatomy)
    portable = atlas.capture(source)
    atlas_file = output / "reperes-adultes-travail.json"
    assert bpy.ops.human_modeling.save_landmarks(filepath=str(atlas_file)) == {"FINISHED"}
    assert atlas.validate(json.loads(atlas_file.read_text(encoding="utf-8"))) == portable

    bpy.ops.human_modeling.create()
    target = bpy.context.object
    target.name = "Destination masculine · topologie commune"
    target.data.shape_keys.key_blocks["Morphologie"].value = 1
    target.location.x = 1.2
    refresh(target)
    assert atlas.topology(target) == portable["topology_sha256"]
    assert bpy.ops.human_modeling.load_landmarks(filepath=str(atlas_file)) == {"FINISHED"}
    assert atlas.capture(target) == portable
    assert target.data.shape_keys.key_blocks["Morphologie"].value == 1
    assert len(anatomy.local_report(target, bpy.context)["distances"]) == 3

    # Mixing shapes does not blend or replace vertex identities.
    state = presets.capture(source)
    preset_file = output / "personnage-avec-reperes.json"
    presets.write(preset_file, state)
    assert presets.read(preset_file) == state
    marker = anatomy.attach(target, "waist_level", portable["points"]["hips_level"]["vertex"])
    before = atlas.capture(target)
    presets.apply(target, state, factor=.5)
    assert atlas.capture(target) == before
    presets.apply(target, state, factor=1)
    assert atlas.capture(target) == portable
    old = copy.deepcopy(state)
    del old["landmarks"]
    presets.apply(target, old)
    assert atlas.capture(target) == portable

    invalid = []
    for value in (True, -1, portable["vertex_count"], 1.5, "1"):
        bad = copy.deepcopy(portable)
        bad["points"]["al_l"]["vertex"] = value
        invalid.append(bad)
    for value in ([], "validated", True):
        bad = copy.deepcopy(portable)
        bad["points"]["al_l"]["status"] = value
        invalid.append(bad)
    bad = copy.deepcopy(portable)
    bad["points"]["al_r"]["vertex"] = bad["points"]["al_l"]["vertex"]
    invalid.append(bad)
    bad = copy.deepcopy(portable)
    bad["points"]["unknown"] = {"vertex": 0}
    invalid.append(bad)
    for bad in invalid:
        try:
            atlas.apply(target, bad)
        except ValueError:
            pass
        else:
            raise AssertionError("Invalid atlas was accepted")
        assert atlas.capture(target) == portable

    # A mesh with the same vertex count but different polygon indexing is refused.
    mesh = bpy.data.meshes.new("Topologie incompatible de contrôle")
    faces = [tuple(polygon.vertices) for polygon in target.data.polygons]
    faces[0] = tuple(reversed(faces[0]))
    mesh.from_pydata([vertex.co[:] for vertex in target.data.vertices], [], faces)
    mesh["human_modeling_base"] = portable["base"]
    incompatible = bpy.data.objects.new("Refus de topologie", mesh)
    bpy.context.scene.collection.objects.link(incompatible)
    assert len(mesh.vertices) == portable["vertex_count"] and atlas.topology(incompatible) != portable["topology_sha256"]
    try:
        atlas.apply(incompatible, portable)
    except ValueError:
        pass
    else:
        raise AssertionError("Incompatible indexed topology accepted")
    assert not incompatible.children
    bpy.data.objects.remove(incompatible, do_unlink=True)
    bpy.data.meshes.remove(mesh)

    # Only missing partners are proposed, and their status stays explicit.
    for obj in tuple(target.children):
        if obj.get(anatomy.LANDMARK_KEY) in ("al_r", "ch_r", "en_r"):
            bpy.data.objects.remove(obj, do_unlink=True)
    refresh(target)
    left_before = atlas.capture(target)
    assert bpy.ops.human_modeling.mirror_landmarks() == {"FINISHED"}
    mirrored = atlas.capture(target)
    assert len(mirrored["points"]) == 10
    assert all(mirrored["points"][key] == value for key, value in left_before["points"].items())
    assert all(mirrored["points"][key]["status"] == "mirrored_review" for key in ("al_r", "ch_r", "en_r"))
    assert bpy.ops.human_modeling.mirror_landmarks() == {"CANCELLED"}
    assert atlas.capture(target) == mirrored

    # Failure after creating a new marker restores object count and custom appearance.
    for obj in tuple(target.children):
        if obj.get(anatomy.LANDMARK_KEY) == "al_r":
            bpy.data.objects.remove(obj, do_unlink=True)
    before = atlas.capture(target)
    marker = next(obj for obj in target.children if obj.get(anatomy.LANDMARK_KEY) == "waist_level")
    marker.empty_display_size = .023
    count = len(bpy.data.objects)
    original_attach = anatomy.attach
    calls = 0

    def fail_after_attach(*args):
        nonlocal calls
        obj = original_attach(*args)
        calls += 1
        if calls == len(portable["points"]):
            raise RuntimeError("Simulated marker assignment failure")
        return obj

    with patch.object(anatomy, "attach", fail_after_attach):
        try:
            atlas.apply(target, portable)
        except RuntimeError:
            pass
        else:
            raise AssertionError("Simulated failure did not propagate")
    assert atlas.capture(target) == before and len(bpy.data.objects) == count
    assert abs(marker.empty_display_size - .023) < 1e-7

    # Fail after the entire preset assignment, including creation of missing points.
    previous = presets.capture(target)
    original_assign = presets.assign
    calls = 0

    def fail_after_assignment(*args):
        nonlocal calls
        original_assign(*args)
        calls += 1
        if calls == 1:
            raise RuntimeError("Simulated final preset failure")

    with patch.object(presets, "assign", fail_after_assignment):
        try:
            presets.apply(target, state)
        except RuntimeError:
            pass
        else:
            raise AssertionError("Preset failure did not propagate")
    assert presets.capture(target) == previous and len(bpy.data.objects) == count
    assert abs(marker.empty_display_size - .023) < 1e-7
    atlas.apply(target, portable)
    refresh(target)
    name = target.name
    bpy.ops.wm.save_as_mainfile(filepath=str(output / "Reperes-portables.blend"), compress=True)
    bpy.ops.wm.open_mainfile(filepath=str(output / "Reperes-portables.blend"))
    assert atlas.capture(bpy.data.objects[name]) == portable
    (output / "tests-reperes.json").write_text(json.dumps({"passed": True, "invalid_inputs": len(invalid),
        "topology_sha256": portable["topology_sha256"], "landmark_count": len(portable["points"]),
        "checks": ["native export/import", "cross morphology transfer", "preset roundtrip and legacy", "partial mix preserves landmarks",
                   "same count changed connectivity rejected", "mirror missing only", "marker rollback and no orphans",
                   "full preset rollback including custom appearance", "scene reopen"]}, indent=2), encoding="utf-8")
    print("PASS: landmark IO, topology guard, 10 invalid atlases, missing-pair symmetry, both rollback paths, presets and reopen", flush=True)


if __name__ == "__main__":
    main()
