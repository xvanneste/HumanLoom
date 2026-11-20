"""Known intersection fixtures and native geometry-report operators."""

import json
from pathlib import Path
import sys

import bpy
import numpy as np


def main():
    from bl_ext.user_default.human_modeling import geometry_quality as qa
    output = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
    output.mkdir(parents=True, exist_ok=True)
    points = np.array(((-1, -1, 0), (1, -1, 0), (0, 1, 0),
                       (0, -.5, -1), (0, -.5, 1), (.6, .5, .3)), dtype=float)
    triangles = np.array(((0, 1, 2), (3, 4, 5)))
    crossing = qa.intersections(points, triangles)
    assert crossing["crossing_triangle_pairs"] == 1
    shifted = points.copy()
    shifted[3:] += (5, 0, 0)
    assert qa.intersections(shifted, triangles)["crossing_triangle_pairs"] == 0
    coplanar = points.copy()
    coplanar[3:, 2] = 0
    assert qa.intersections(coplanar, triangles)["crossing_triangle_pairs"] == 0
    assert qa.intersections(points, np.array(((0, 1, 2), (0, 3, 4))))["crossing_triangle_pairs"] == 0
    assert qa.intersections(points, np.zeros((250001, 3), dtype=int))["status"] == "not_computed"
    # Nested shells are outside this surface-crossing test's scope.
    mesh = bpy.data.meshes.new("Fixture ouverte")
    mesh.from_pydata(points[:3].tolist(), [], [(0, 1, 2)])
    topology = qa.inspect_mesh(mesh)
    assert topology["boundary_edges"] == 3 and topology["components"] == 1
    mesh.vertices[0].co.x = float("nan")
    assert not qa.inspect_mesh(mesh)["finite_coordinates"]
    bpy.data.meshes.remove(mesh)
    bpy.ops.human_modeling.create()
    body = bpy.context.object
    assert bpy.ops.human_modeling.check_geometry() == {"FINISHED"}
    report = json.loads(body["hm_geometry_report"])
    assert report["geometry"]["finite_coordinates"]
    assert report["geometry"]["components"] == 1
    assert report["geometry"]["boundary_edges"] == 0
    assert report["geometry"]["zero_area_faces"] == 0
    assert report["geometry"]["intersections"]["status"] == "computed"
    path = output / "controle-maillage-evalue.json"
    assert bpy.ops.human_modeling.export_geometry_report(filepath=str(path)) == {"FINISHED"}
    exported = json.loads(path.read_text(encoding="utf-8"))
    assert exported["geometry"]["geometry_sha256"] == report["geometry"]["geometry_sha256"]
    summaries = []
    for sex in (0, .5, 1):
        body.data.shape_keys.key_blocks["Morphologie"].value = sex
        body.data.shape_keys.update_tag()
        bpy.context.view_layer.update()
        result = qa.report(body, bpy.context)
        summaries.append({"morphology": sex, "geometry": result["geometry"]})
        assert result["geometry"]["zero_area_faces"] == 0
        print("EVALUATED_ADULT", sex, result["geometry"]["intersections"].get("crossing_triangle_pairs"), flush=True)
    (output / "adultes-surface-evaluee.json").write_text(json.dumps(summaries, indent=2), encoding="utf-8")
    print("PASS: known crossing, separated and coplanar fixtures, adjacency exclusion, boundaries, NaN, native evaluated-body check and atomic JSON export", flush=True)


if __name__ == "__main__":
    main()
