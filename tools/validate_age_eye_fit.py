"""Record strict eye/body crossings separately from body self-intersections."""

import json
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_age_dimensions import surface
import geometry_quality


def crossings(body_points, body_faces, eye_points, eye_faces):
    body_tree = BVHTree.FromPolygons([Vector(p) for p in body_points], body_faces.tolist(), all_triangles=True)
    eye_tree = BVHTree.FromPolygons([Vector(p) for p in eye_points], eye_faces.tolist(), all_triangles=True)
    pairs = np.array(sorted(set(body_tree.overlap(eye_tree))), dtype=np.int32).reshape((-1, 2))
    hits = np.zeros(len(pairs), dtype=bool)
    if len(pairs):
        a = body_points[body_faces[pairs[:, 0]]]
        b = eye_points[eye_faces[pairs[:, 1]]]
        for first, second in ((a, b), (b, a)):
            for edge in range(3):
                hits |= geometry_quality.segment_hits(first[:, edge], first[:, (edge+1) % 3], second)
        centers = np.concatenate((a[hits], b[hits]), axis=1).mean(axis=1)
    else:
        centers = np.empty((0, 3))
    center = eye_points.mean(axis=0)
    return {"crossing_pairs": int(hits.sum()),
            "pairs_anterior_to_eye_center": int((centers[:, 1] < center[1]).sum()),
            "sample_crossing_centers_m": centers[:30].tolist()}


def main():
    asset, output = [Path(value).resolve() for value in sys.argv[sys.argv.index("--")+1:]]
    with bpy.data.libraries.load(str(asset), link=False) as (_, target):
        target.collections = ["Realistic Human Base"]
    collection = target.collections[0]
    bpy.context.scene.collection.children.link(collection)
    body = next(obj for obj in collection.objects if obj.get("human_modeling_body"))
    body.modifiers.new("QA surface", "SUBSURF").levels = 1
    results = []
    for sex in (0, 1):
        body.data.shape_keys.key_blocks["Morphologie"].value = sex
        for age in range(4):
            body.data.shape_keys["human_modeling_age"] = float(age)
            body.data.shape_keys.update_tag()
            bpy.context.view_layer.update()
            body_points, body_faces = surface(body)
            for eye in body.children:
                eye_points, eye_faces = surface(eye)
                # All evaluated meshes are expressed in world coordinates before comparison.
                body_world = (np.array(body.matrix_world)[:3, :3] @ body_points.T).T + np.array(body.matrix_world)[:3, 3]
                eye_world = (np.array(eye.matrix_world)[:3, :3] @ eye_points.T).T + np.array(eye.matrix_world)[:3, 3]
                record = {"sex": sex, "age_parameter": age, "eye": eye.name,
                          **crossings(body_world, body_faces, eye_world, eye_faces)}
                results.append(record)
                print("EYE_BODY", sex, age, eye.name, record["crossing_pairs"], flush=True)
    output.write_text(json.dumps({"results": results, "scope": "Strict transverse intersections, including internal orbital geometry; anterior is a geometric half-space, not a visibility classification. Coplanar tangency excluded."}, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
