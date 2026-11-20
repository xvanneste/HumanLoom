"""Locate strict transverse intersections in the adult base or an age candidate."""

import json
from pathlib import Path
import sys

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "extension"))
import geometry_quality


def main():
    arguments = sys.argv[sys.argv.index("--") + 1:]
    asset, output = [Path(value).resolve() for value in arguments[:2]]
    with bpy.data.libraries.load(str(asset), link=False) as (_, target):
        target.collections = ["Realistic Human Base"]
    collection = target.collections[0]
    bpy.context.scene.collection.children.link(collection)
    body = next(obj for obj in collection.objects if obj.get("human_modeling_body"))
    if len(arguments) > 2:
        modifier = body.modifiers.new("QA evaluated surface", "SUBSURF")
        modifier.levels = int(arguments[2])
    results = []
    for sex in (0, .5, 1):
        body.data.shape_keys.key_blocks["Morphologie"].value = sex
        body.data.shape_keys.update_tag()
        bpy.context.view_layer.update()
        evaluated = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
        mesh = evaluated.to_mesh()
        data = geometry_quality.inspect_mesh(mesh)
        mesh.calc_loop_triangles()
        locations = []
        for a, b in data["intersections"]["sample_triangle_pairs"]:
            triangles = [mesh.loop_triangles[index] for index in (a, b)]
            points = np.array([mesh.vertices[index].co[:] for tri in triangles for index in tri.vertices])
            locations.append({"center": points.mean(axis=0).tolist(), "polygons": [tri.polygon_index for tri in triangles]})
        evaluated.to_mesh_clear()
        results.append({"sex": sex, "report": data, "locations": locations})
        print("ADULT_CROSSINGS", sex, data["intersections"]["approximate_regions"], flush=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(results, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
