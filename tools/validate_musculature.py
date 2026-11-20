"""Check muscle saturation, neutral identity, mixed corpulence and saved drivers."""

import json
from pathlib import Path
import sys

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "extension"))
import geometry_quality
from proportions import MUSCLE_CONTROLS


def main():
    asset, old_asset, output = [Path(p).resolve() for p in sys.argv[sys.argv.index("--")+1:]]
    bodies = []
    for path in (asset, old_asset):
        with bpy.data.libraries.load(str(path), link=False) as (_, target):
            target.collections = ["Realistic Human Base"]
        collection = target.collections[0]
        bpy.context.scene.collection.children.link(collection)
        body = next(obj for obj in collection.objects if obj.get("human_modeling_body"))
        body.modifiers.new("QA surface", "SUBSURF").levels = 1
        bodies.append(body)
    body, old = bodies
    keys = body.data.shape_keys

    def refresh():
        keys.update_tag()
        old.data.shape_keys.update_tag()
        bpy.context.view_layer.update()

    def coordinates(obj):
        evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        mesh = evaluated.to_mesh()
        result = np.array([v.co[:] for v in mesh.vertices])
        evaluated.to_mesh_clear()
        return result

    records = []
    for sex in (0., .5, 1.):
        keys.key_blocks["Morphologie"].value = sex
        old.data.shape_keys.key_blocks["Morphologie"].value = sex
        refresh()
        assert np.max(np.abs(coordinates(body)-coordinates(old))) < 1e-6
        for identifier, _ in MUSCLE_CONTROLS:
            for amount in (-1., 1.):
                keys["hm_"+identifier] = amount
                refresh()
                data = geometry_quality.report(body, bpy.context)["geometry"]
                records.append({"sex": sex, "control": identifier, "amount": amount,
                                "crossings": data["intersections"].get("crossing_triangle_pairs"),
                                "zero_area_faces": data["zero_area_faces"]})
            keys["hm_"+identifier] = 0.
        # Same regional saturation must give exactly the same surface.
        keys["hm_muscles"] = 1.
        refresh()
        saturated = coordinates(body)
        for identifier, _ in MUSCLE_CONTROLS[1:]:
            keys["hm_"+identifier] = 1.
        refresh()
        assert np.max(np.abs(coordinates(body)-saturated)) < 1e-6
        for identifier, _ in MUSCLE_CONTROLS:
            keys["hm_"+identifier] = 0.
        for fat in (-1., 0., 1.):
            for muscle in (-1., 1.):
                keys["hm_corpulence"] = fat
                keys["hm_muscles"] = muscle
                refresh()
                data = geometry_quality.report(body, bpy.context)["geometry"]
                records.append({"sex": sex, "corpulence": fat, "muscles": muscle,
                                "crossings": data["intersections"].get("crossing_triangle_pairs"),
                                "zero_area_faces": data["zero_area_faces"]})
        keys["hm_corpulence"] = keys["hm_muscles"] = 0.
    refresh()
    assert all(curve.is_valid for curve in keys.animation_data.drivers)
    output.write_text(json.dumps(records, indent=2), encoding="utf-8")
    failures = [r for r in records if r["crossings"] != 0 or r["zero_area_faces"] != 0]
    print("MUSCLE_QA", len(records), "cases; failures:", failures, flush=True)
    assert not failures, failures


if __name__ == "__main__":
    main()
