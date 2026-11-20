"""Numerical section tests and real Blender modeling/rollback/persistence checks."""

import json
import math
import sys
import time
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector


def refresh(body):
    body.data.shape_keys.update_tag()
    bpy.context.view_layer.update()


def fixture_landmarks(body, anatomy):
    """Approximate test locations, not an anatomically validated landmark atlas."""
    coords = np.array([v.co[:] for v in body.data.shape_keys.key_blocks["Basis"].data])
    height = float(np.ptp(coords[:, 2]))
    eyes = [obj for obj in body.children if obj.type == "MESH"]
    eye_z = np.mean([v.co.z for obj in eyes for v in obj.data.shape_keys.key_blocks["Basis"].data])
    targets = {"pelvis": (0, -.04, height * .48), "waist_level": (.13, 0, height * .60),
               "hips_level": (.15, 0, height * .49), "chest_level": (.13, 0, height * .72)}
    for suffix, sign in (("l", 1), ("r", -1)):
        targets["al_" + suffix] = (sign * .018, -.145, eye_z - .035)
        targets["ch_" + suffix] = (sign * .026, -.145, eye_z - .067)
        targets["en_" + suffix] = (sign * .014, -.13, eye_z)
    indices = {}
    for key, target in targets.items():
        index = int(np.argmin(np.linalg.norm(coords - target, axis=1)))
        anatomy.attach(body, key, index)
        indices[key] = index
    refresh(body)
    return indices


def analytic_sections(anatomy):
    n, radius = 96, .3
    angle = np.arange(n) * 2 * math.pi / n
    points = np.array([(radius * math.cos(a), radius * math.sin(a), z) for z in (-1, 1) for a in angle])
    triangles = np.array([(i, (i + 1) % n, n + i) for i in range(n)] +
                         [((i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)])
    loops, actual = anatomy.section_loops(points, triangles, 0)
    assert actual == 0 and len(loops) == 1 and anatomy.encloses_axis(loops[0])
    perimeter = np.linalg.norm(loops[0] - np.roll(loops[0], 1, axis=0), axis=1).sum()
    expected = n * 2 * radius * math.sin(math.pi / n)
    assert abs(perimeter - expected) < 1e-12
    separate = points + (1, 0, 0)
    loops, _ = anatomy.section_loops(np.vstack((points, separate)), np.vstack((triangles, triangles + len(points))), 0)
    assert len(loops) == 2 and sum(anatomy.encloses_axis(loop) for loop in loops) == 1
    try:
        anatomy.section_loops(points, triangles[1:], 0)
    except ValueError:
        pass
    else:
        raise AssertionError("An open section was accepted")
    # A plane through a complete vertex ring must be displaced consistently.
    loops, actual = anatomy.section_loops(points, triangles, -1)
    assert actual > -1 and len(loops) == 1
    return {"polygon_perimeter_m": float(perimeter), "analytical_polygon_m": expected}


def main():
    from bl_ext.user_default.human_modeling import anatomy, measurements
    output = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
    output.mkdir(parents=True, exist_ok=True)
    results = {"analytic": analytic_sections(anatomy), "characters": []}
    for morph in (0, .5, 1):
        bpy.ops.human_modeling.create()
        body = bpy.context.object
        body.data.shape_keys.key_blocks["Morphologie"].value = morph
        indices = fixture_landmarks(body, anatomy)
        start = time.perf_counter()
        report = anatomy.local_report(body, bpy.context)
        duration = time.perf_counter() - start
        assert len(report["sections"]) == 3 and len(report["distances"]) == 3
        assert all("error" not in entry for group in ("sections", "distances") for entry in report[group].values()), report
        base = anatomy.value(body, bpy.context, "waist_level")
        before_scale = body.scale.copy()
        body.rotation_euler = (.4, -.2, .7)
        body.scale = (1.3, 1.3, 1.3)
        refresh(body)
        rotated = anatomy.value(body, bpy.context, "waist_level")
        assert abs(rotated - base * 1.3) < 1e-6
        body.rotation_euler = (0, 0, 0)
        body.scale = before_scale
        refresh(body)
        if morph == 0:
            body.scale = (1.2, .8, 1.1)
            refresh(body)
            transformed = anatomy.local_report(body, bpy.context, include_paths=True, only="waist_level")
            path = transformed["sections"]["waist_level"]["local_path"]
            points = [body.matrix_world @ Vector(point) for point in path]
            expected = sum((a - b).length for a, b in zip(points, points[1:] + points[:1]))
            assert abs(transformed["sections"]["waist_level"]["perimeter_m"] - expected) < 1e-6
            body.scale = before_scale
            refresh(body)
        fits = {}
        for identifier, control in anatomy.FIT_CONTROLS.items():
            prop = "hm_" + control
            original = body.data.shape_keys[prop]
            body.data.shape_keys[prop] = .35
            refresh(body)
            target = anatomy.value(body, bpy.context, identifier)
            body.data.shape_keys[prop] = original
            refresh(body)
            obtained = anatomy.fit(body, bpy.context, identifier, target)
            assert abs(obtained - target) <= 1e-5
            assert abs(body.data.shape_keys[prop] - .35) < .03
            fits[identifier] = {"target_m": target, "obtained_m": obtained}
            body.data.shape_keys[prop] = original
            refresh(body)
        original = body.data.shape_keys["hm_waist"]
        try:
            anatomy.fit(body, bpy.context, "waist_level", 20.)
        except ValueError:
            pass
        else:
            raise AssertionError("Out-of-range target was accepted")
        assert body.data.shape_keys["hm_waist"] == original
        results["characters"].append({"morphology": morph, "report": report, "fits": fits, "measurement_seconds": duration})
        print("PASS: morphology", morph, "seven dimension fits; measurement", round(duration, 4), "s", flush=True)

    # The actual edit-mode operator replaces one marker, without creating duplicates.
    body.hm_landmark = "al_l"
    bpy.ops.object.mode_set(mode="EDIT")
    bm = bmesh.from_edit_mesh(body.data)
    bm.verts.ensure_lookup_table()
    for face in bm.faces:
        face.select_set(False)
    for edge in bm.edges:
        edge.select_set(False)
    for vertex in bm.verts:
        vertex.select_set(False)
    bm.verts[indices["al_l"]].select_set(True)
    bmesh.update_edit_mesh(body.data)
    assert bpy.ops.human_modeling.mark_anatomy() == {"FINISHED"}
    bpy.ops.object.mode_set(mode="OBJECT")
    refresh(body)
    assert len([obj for obj in body.children if obj.get(anatomy.LANDMARK_KEY) == "al_l"]) == 1
    marker = next(obj for obj in body.children if obj.get(anatomy.LANDMARK_KEY) == "al_l")
    marker.location.x = .01
    bpy.context.view_layer.update()
    try:
        anatomy.local_report(body, bpy.context)
    except ValueError:
        pass
    else:
        raise AssertionError("Detached landmark accepted")
    marker.location.x = 0
    refresh(body)
    bpy.context.scene.unit_settings.scale_length = .01
    assert abs(anatomy.value(body, bpy.context, "waist_level") - results["characters"][-1]["report"]["sections"]["waist_level"]["perimeter_m"] * .01) < 1e-6
    bpy.context.scene.unit_settings.scale_length = 1
    refresh(body)
    exported = measurements.report(body, bpy.context)
    assert exported["version"] == 2 and len(exported["local_anatomy"]["landmarks"]) == 10
    name = body.name
    before = anatomy.value(body, bpy.context, "nose_width")
    target = before * 1.01
    assert bpy.ops.human_modeling.fit_measurement(measurement="nose_width", target_cm=target * 100) == {"FINISHED"}
    assert abs(anatomy.value(body, bpy.context, "nose_width") - target) < 1e-5
    before = anatomy.value(body, bpy.context, "nose_width")
    bpy.ops.wm.save_as_mainfile(filepath=str(output / "Controle-reperes.blend"), compress=True)
    bpy.ops.wm.open_mainfile(filepath=str(output / "Controle-reperes.blend"))
    body = bpy.data.objects[name]
    assert abs(anatomy.value(body, bpy.context, "nose_width") - before) < 1e-8
    (output / "tests-anatomie.json").write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print("PASS: analytic sections, separate arms, open contour rejection, 21 fits, bounds rollback, edit operator, detached marker, units, report and reopen", flush=True)


if __name__ == "__main__":
    main()
