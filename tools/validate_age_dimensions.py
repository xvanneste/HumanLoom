"""Measure the experimental age surface and probe adult facial controls.

This records failures as evidence; only calibrated stature checks are asserted.
It does not approve the candidate for installation.
"""

import json
from pathlib import Path
import sys

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from experimental_growth_field import head_section
from experimental_age_transfer import coordinates

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "extension"))
import geometry_quality


def surface(obj):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    try:
        mesh.calc_loop_triangles()
        return coordinates(mesh), np.array([tri.vertices[:] for tri in mesh.loop_triangles])
    finally:
        evaluated.to_mesh_clear()


def main():
    asset, output = [Path(value).resolve() for value in sys.argv[sys.argv.index("--") + 1:]]
    with bpy.data.libraries.load(str(asset), link=False) as (_, target):
        target.collections = ["Realistic Human Base"]
    collection = target.collections[0]
    bpy.context.scene.collection.children.link(collection)
    body = next(obj for obj in collection.objects if obj.get("human_modeling_body"))
    modifier = body.modifiers.new("QA evaluated surface", "SUBSURF")
    modifier.levels = 1
    keys = body.data.shape_keys
    root = Path(__file__).resolve().parents[1] / "validation/source-growth"
    refs = {0: json.loads((root / "who-60-months.json").read_text(encoding="utf-8")),
            1: json.loads((root / "who-180-months.json").read_text(encoding="utf-8"))}
    dimensions, controls = [], []
    for sex, label in ((0, "F"), (1, "M")):
        keys.key_blocks["Morphologie"].value = sex
        for age, years in enumerate((5, 15, 30, 75)):
            keys["human_modeling_age"] = float(age)
            keys.update_tag()
            bpy.context.view_layer.update()
            points, triangles = surface(body)
            record = {"sex": label, "age_target_years": years, "subdivision": 1,
                      "height_m": float(np.ptp(points[:, 2]))}
            if age in refs:
                expected = refs[age][label]["height"] / 100
                record.update(reference_height_m=expected, height_error_m=record["height_m"]-expected)
                # Subdivision shrinks the cage; the review surface must stay within 2 mm.
                assert abs(record["height_error_m"]) < .002, record
            if age == 0:
                eye_z = float(np.concatenate([surface(eye)[0] for eye in body.children])[:, 2].mean())
                record["head_section_surrogate_m"], record["head_section_z"] = head_section(points, triangles, eye_z)
                record["head_reference_m"] = refs[0][label]["head_circumference"] / 100
                record["head_section_error_m"] = record["head_section_surrogate_m"] - record["head_reference_m"]
                record["head_protocol"] = "Horizontal section surrogate; clinical tape protocol not validated"
            dimensions.append(record)
            if age == 2:
                continue
            for control in ("head_width", "head_height", "eye_spacing", "eye_height"):
                for amount in (-1., 1.):
                    keys["hm_"+control] = amount
                    keys.update_tag()
                    bpy.context.view_layer.update()
                    geometry = geometry_quality.report(body, bpy.context)["geometry"]
                    record = {"sex": label, "age_target_years": years, "control": control,
                              "amount": amount, "crossings": geometry["intersections"].get("crossing_triangle_pairs"),
                              "zero_area_faces": geometry["zero_area_faces"]}
                    controls.append(record)
                    print("AGE_CONTROL", record, flush=True)
                keys["hm_"+control] = 0.
    output.write_text(json.dumps({"asset": str(asset), "dimensions": dimensions,
        "adult_control_probes": controls, "approval": "experimental_only",
        "limits": "Finite geometric probes; no anatomical certification, eye/body collision test or validation of all controls."}, indent=2), encoding="utf-8")
    print("AGE_DIMENSIONS_RECORDED", flush=True)


if __name__ == "__main__":
    main()
