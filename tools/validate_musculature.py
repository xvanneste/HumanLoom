"""Check muscle saturation, neutral shape equal to the frozen reference of the current asset (D-19), mixed corpulence and saved drivers."""

import json
from pathlib import Path
import sys

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "extension"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import geometry_quality
import neutral_reference as neutral
from proportions import MUSCLE_CONTROLS


def main():
    asset, output = [Path(p).resolve() for p in sys.argv[sys.argv.index("--")+1:]]
    reference = neutral.load()
    with bpy.data.libraries.load(str(asset), link=False) as (_, target):
        target.collections = ["Realistic Human Base"]
    collection = target.collections[0]
    bpy.context.scene.collection.children.link(collection)
    body = next(obj for obj in collection.objects if obj.get("human_modeling_body"))
    body.modifiers.new("QA surface", "SUBSURF").levels = 1
    keys = body.data.shape_keys

    def refresh():
        keys.update_tag()
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
        refresh()
        # Neutral shape at the asset's default age equals the frozen reference of the current asset.
        neutral.check(body, reference, sex, keys["human_modeling_age"])
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
        # `muscle_definition` n'est pas une région : il ajoute du détail (0,36 à 0,50 mm sur 440 à 556 sommets, mesuré),
        # il est donc exclu de la saturation régionale et vérifié à part (I-34 bis).
        regional = [name for name, _ in MUSCLE_CONTROLS[1:] if name != "muscle_definition"]
        for identifier in regional:
            keys["hm_"+identifier] = 1.
        refresh()
        assert np.max(np.abs(coordinates(body)-saturated)) < 1e-6
        keys["hm_muscle_definition"] = 1.
        refresh()
        definition = float(np.max(np.abs(coordinates(body)-saturated)))
        assert definition > 1e-4, definition  # la définition musculaire doit modifier la surface (> 0,1 mm)
        keys["hm_muscle_definition"] = 0.
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
