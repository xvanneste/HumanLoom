"""Build a reversible candidate correction for the female inner orbital surface."""

import json
from pathlib import Path
import sys

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "extension"))
import geometry_quality
from surface_fix import KEY, bind

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_modeling_controls import deformations


def main():
    source, output = [Path(value).resolve() for value in sys.argv[sys.argv.index("--") + 1:]]
    with bpy.data.libraries.load(str(source), link=False) as (_, target):
        target.collections = ["Realistic Human Base"]
    collection = target.collections[0]
    bpy.context.scene.collection.children.link(collection)
    body = next(obj for obj in collection.objects if obj.get("human_modeling_body"))
    keys = body.data.shape_keys
    original_morphology = keys.key_blocks["Morphologie"].value
    keys.key_blocks["Morphologie"].value = 0
    modifier = body.modifiers.new("QA surface", "SUBSURF")
    modifier.levels = 1
    bpy.context.view_layer.update()
    evaluated = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    report = geometry_quality.inspect_mesh(mesh)
    pairs = report["intersections"]["sample_triangle_pairs"]
    mesh.calc_loop_triangles()
    centers = np.array([np.mean([mesh.vertices[vertex].co[:] for index in pair for vertex in mesh.loop_triangles[index].vertices], axis=0) for pair in pairs])
    evaluated.to_mesh_clear()
    if not len(centers) or np.any(centers[:, 2] < 1.5):
        raise ValueError("Unexpected collision region; do not apply this targeted repair")
    original = np.array([point.co[:] for point in keys.key_blocks[0].data])
    distances = np.linalg.norm(original[:, None, :] - centers[None, :, :], axis=-1).min(axis=1)
    mask = np.exp(-(distances/.006)**2)
    mask[distances > .014] = 0
    edges = np.array([edge.vertices[:] for edge in body.data.edges])
    degree = np.bincount(edges.reshape(-1), minlength=len(original)).clip(min=1)
    repair = body.shape_key_add(name=KEY)
    repair.value = 1
    candidate, best, count = original.copy(), original.copy(), report["intersections"]["crossing_triangle_pairs"]
    steps = []
    for iteration in range(1, 61):
        neighbors = np.zeros_like(candidate)
        np.add.at(neighbors, edges[:, 0], candidate[edges[:, 1]])
        np.add.at(neighbors, edges[:, 1], candidate[edges[:, 0]])
        candidate += (neighbors/degree[:, None]-candidate) * (.28*mask[:, None])
        delta = candidate-original
        lengths = np.linalg.norm(delta, axis=1)
        delta *= np.minimum(1, .0025 / np.maximum(lengths, 1e-12))[:, None]
        candidate = original+delta
        repair.data.foreach_set("co", candidate.reshape(-1))
        keys.update_tag()
        bpy.context.view_layer.update()
        current = geometry_quality.report(body, bpy.context)["geometry"]
        remaining = current["intersections"]["crossing_triangle_pairs"]
        steps.append({"iteration": iteration, "remaining": remaining, "max_displacement_m": float(np.linalg.norm(candidate-original, axis=1).max())})
        print("EYELID_REPAIR", steps[-1], flush=True)
        if remaining < count:
            best, count = candidate.copy(), remaining
        if count == 0:
            break
    repair.data.foreach_set("co", best.reshape(-1))
    bind(repair, body)
    eye_z = np.mean([point.co.z for eye in body.children for point in eye.data.shape_keys.key_blocks[0].data])
    before_fields = deformations(original, float(np.ptp(original[:, 2])), eye_z)
    after_fields = deformations(best, float(np.ptp(original[:, 2])), eye_z)
    for identifier, field in before_fields.items():
        difference = after_fields[identifier] - field
        if np.max(np.abs(difference)) < 1e-10:
            continue
        poles = (("gain", 1.), ("perte", -.65)) if identifier == "corpulence" else ((None, 1.),)
        for pole, factor in poles:
            key = body.shape_key_add(name=KEY + " · " + identifier + (" · " + pole if pole else ""))
            key.data.foreach_set("co", (original + difference*factor).reshape(-1))
            key.slider_min = -1
            bind(key, body, identifier, pole)
    body.modifiers.remove(modifier)
    body.data["human_modeling_surface_revision"] = 1
    keys.key_blocks["Morphologie"].value = original_morphology
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.data.libraries.write(str(output), {collection, body.data, *(obj.data for obj in body.children)}, fake_user=True, compress=True)
    output.with_suffix(".json").write_text(json.dumps({"initial_crossings": len(pairs), "best_remaining": count, "steps": steps,
        "scope": "Female inner orbital surface, evaluated subdivision 1; separate eyeballs excluded"}, indent=2), encoding="utf-8")
    print("EYELID_CANDIDATE", count, flush=True)


if __name__ == "__main__":
    main()
