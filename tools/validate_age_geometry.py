"""Diagnose every age/morphology mixture on a candidate, without installing it."""

import json
from pathlib import Path
import sys

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "extension"))
import geometry_quality


def main():
    arguments = sys.argv[sys.argv.index("--") + 1:]
    asset, output = [Path(value).resolve() for value in arguments[:2]]
    subdivision = int(arguments[2]) if len(arguments) > 2 else 0
    with bpy.data.libraries.load(str(asset), link=False) as (_, target):
        target.collections = ["Realistic Human Base"]
    collection = target.collections[0]
    bpy.context.scene.collection.children.link(collection)
    body = next(obj for obj in collection.objects if obj.get("human_modeling_body"))
    if subdivision:
        modifier = body.modifiers.new("QA evaluated surface", "SUBSURF")
        modifier.levels = subdivision
    records = []
    for sex in (0, .5, 1):
        body.data.shape_keys.key_blocks["Morphologie"].value = sex
        for age in (0, .5, 1, 1.5, 2, 2.5, 3):
            body.data.shape_keys["human_modeling_age"] = age
            body.data.shape_keys.update_tag()
            bpy.context.view_layer.update()
            data = geometry_quality.report(body, bpy.context)
            records.append({"morphology": sex, "age_parameter": age, "subdivision": subdivision, **data})
            print("AGE_QA", sex, age, data["geometry"]["intersections"].get("crossing_triangle_pairs"), flush=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(records, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
