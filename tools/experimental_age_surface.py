"""Experimental triangle-correspondence age transfer, kept outside the extension.

The source age slider is not a calibrated chronological age. This experiment
uses MPFB CC0 geometry to study our own correspondence and deformation method.
"""

import json
from pathlib import Path
import sys

import addon_utils
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from experimental_age_transfer import STAGES, add_driver, coordinates, reference, write_key


def correspondence(rest, triangles, target):
    tree = BVHTree.FromPolygons([Vector(point) for point in rest], triangles.tolist(), all_triangles=True)
    hits = [tree.find_nearest(Vector(point)) for point in target]
    if any(hit[0] is None for hit in hits):
        raise ValueError("Missing source surface correspondence")
    indices = np.array([hit[2] for hit in hits])
    projected = np.array([tuple(hit[0]) for hit in hits])
    faces = rest[triangles]
    edge1, edge2 = faces[:, 1] - faces[:, 0], faces[:, 2] - faces[:, 0]
    normals = np.cross(edge1, edge2)
    area2 = np.linalg.norm(normals, axis=1)
    if np.any(area2 < 1e-12):
        raise ValueError("Degenerate reference triangle")
    normals /= area2[:, None]
    frames = np.stack((edge1, edge2, normals), axis=-1)
    inverse = np.linalg.inv(frames)
    parameters = np.einsum("nij,nj->ni", inverse[indices], projected - faces[indices, 0])
    return {"indices": indices, "projected": projected, "parameters": parameters, "inverse": inverse,
            "area2": area2, "residual": target - projected,
            "gap_median": float(np.median([hit[3] for hit in hits])), "gap_max": float(max(hit[3] for hit in hits))}


def transfer(changed, triangles, mapping, residual_amount=1.):
    faces = changed[triangles]
    edge1, edge2 = faces[:, 1] - faces[:, 0], faces[:, 2] - faces[:, 0]
    normals = np.cross(edge1, edge2)
    area2 = np.linalg.norm(normals, axis=1)
    if np.any(area2 < 1e-12):
        raise ValueError("Degenerate changed reference triangle")
    normal_scale = np.clip(np.sqrt(area2 / mapping["area2"]), .15, 1.6)
    normals *= (normal_scale / area2)[:, None]
    frames = np.stack((edge1, edge2, normals), axis=-1)
    selected = mapping["indices"]
    surface = faces[selected, 0] + np.einsum("nij,nj->ni", frames[selected], mapping["parameters"])
    relative = np.einsum("nij,nj->ni", mapping["inverse"][selected], mapping["residual"])
    residual = np.einsum("nij,nj->ni", frames[selected], relative)
    return surface + residual * np.asarray(residual_amount).reshape((-1, 1))


def smoothstep(amount):
    amount = np.clip(amount, 0, 1)
    return amount * amount * (3 - 2 * amount)


def align_source_arms(points, adult_joints, current_joints, gender, scale, offset):
    """Put both source ages in the Studio arm pose before finding correspondence."""
    names = ("joint-l-shoulder", "joint-l-elbow", "joint-l-hand", "joint-l-hand-2")
    adult = np.array([adult_joints[name] for name in names]) * scale + offset
    current = np.array([current_joints[name] for name in names]) * scale + offset
    studio = np.array((
        ((.16, 0, 1.32), (.246, .024, 1.05), (.348, -.036, .85), (.38, -.075, .79)),
        ((.18, 0, 1.37), (.287, -.003, 1.10), (.373, -.06, .89), (.404, -.11, .80)),
    )[gender])
    adult_lengths = np.linalg.norm(np.diff(adult, axis=0), axis=1)
    current_lengths = np.linalg.norm(np.diff(current, axis=0), axis=1)
    target = [studio[0] + current[0] - adult[0]]
    for index in range(3):
        target.append(target[-1] + (studio[index + 1] - studio[index]) * current_lengths[index] / adult_lengths[index])
    target = np.array(target)
    result = points.copy()
    for sign in (-1, 1):
        source = current * (sign, 1, 1)
        destination = target * (sign, 1, 1)
        distances, positions = [], []
        for index in range(3):
            vector = source[index + 1] - source[index]
            desired = destination[index + 1] - destination[index]
            rotation = np.array(Vector(vector).rotation_difference(Vector(desired)).to_matrix())
            along = np.clip((points - source[index]) @ vector / (vector @ vector), 0, 1)
            distance = np.linalg.norm(points - (source[index] + along[:, None] * vector), axis=1)
            distances.append(distance)
            positions.append(destination[index] + (points - source[index]) @ rotation.T * np.linalg.norm(desired) / np.linalg.norm(vector))
        distances = np.array(distances)
        weights = 1 / np.maximum(distances, .015) ** 6
        weights /= weights.sum(axis=0)
        mapped = np.sum(np.array(positions) * weights[:, :, None], axis=0)
        radius = np.array((.08, .065, .11)) * (current_lengths / adult_lengths)
        amount = 1 - smoothstep((np.min(distances / radius[:, None], axis=0) - .65) / .65)
        amount *= smoothstep((points[:, 0] * sign - source[0, 0] * sign + .025) / .065)
        result = result * (1 - amount[:, None]) + mapped * amount[:, None]
    return result


def transport_arms(target, result, rest_joints, age_joints, gender, scale):
    landmarks = np.array((
        ((.16, 0, 1.32), (.246, .024, 1.05), (.348, -.036, .85), (.38, -.075, .79)),
        ((.18, 0, 1.37), (.287, -.003, 1.10), (.373, -.06, .89), (.404, -.11, .80)),
    )[gender])
    names = ("joint-l-shoulder", "joint-l-elbow", "joint-l-hand", "joint-l-hand-2")
    adult = np.array([rest_joints[name] for name in names])
    aged = np.array([age_joints[name] for name in names])
    ratios = np.linalg.norm(np.diff(aged, axis=0), axis=1) / np.linalg.norm(np.diff(adult, axis=0), axis=1)
    transformed = [landmarks[0] + (aged[0] - adult[0]) * scale]
    for index, ratio in enumerate(ratios):
        transformed.append(transformed[-1] + (landmarks[index + 1] - landmarks[index]) * ratio)
    transformed = np.array(transformed)
    for sign in (-1, 1):
        original = landmarks * (sign, 1, 1)
        deformed = transformed * (sign, 1, 1)
        distances, candidates = [], []
        for index, ratio in enumerate(ratios):
            start, end = original[index:index + 2]
            direction = end - start
            parameter = np.clip((target - start) @ direction / (direction @ direction), 0, 1)
            closest = start + parameter[:, None] * direction
            distances.append(np.linalg.norm(target - closest, axis=1))
            candidates.append(deformed[index] + (target - start) * ratio)
        distances = np.array(distances)
        weights = 1 / np.maximum(distances, .015) ** 6
        weights /= weights.sum(axis=0)
        arm = np.sum(np.array(candidates) * weights[:, :, None], axis=0)
        relative_distance = np.min(distances / np.array((.075, .065, .105))[:, None], axis=0)
        amount = 1 - smoothstep((relative_distance - .6) / .8)
        amount *= smoothstep((target[:, 0] * sign - .065) / .06)
        result = result * (1 - amount[:, None]) + arm * amount[:, None]
    return result


def relax_displacement(points, changed, edges, height):
    delta = changed - points
    degree = np.bincount(edges.reshape(-1), minlength=len(points)).clip(min=1)
    # Smooth the displacement, preserving the original surface detail.
    mask = smoothstep((points[:, 2] / height - .70) / .07)
    mask *= 1 - smoothstep((points[:, 2] / height - .83) / .07)
    mask *= smoothstep((np.abs(points[:, 0]) / height - .06) / .05)
    for _ in range(22):
        neighbors = np.zeros_like(delta)
        np.add.at(neighbors, edges[:, 0], delta[edges[:, 1]])
        np.add.at(neighbors, edges[:, 1], delta[edges[:, 0]])
        delta += (neighbors / degree[:, None] - delta) * (.45 * mask[:, None])
    return points + delta


def transport_feet(target, candidate, rest, changed, height):
    """Preserve each native foot with an affine regional transport."""
    for sign in (-1, 1):
        source_ids = (rest[:, 2] < rest[:, 2].min() + height * .055) & (rest[:, 0] * sign > .005)
        ratio = np.clip(np.ptp(changed[source_ids], axis=0) / np.ptp(rest[source_ids], axis=0), .35, 1.5)
        ankle_ids = (target[:, 0] * sign > .005) & (target[:, 2] > height * .055) & (target[:, 2] < height * .085)
        anchor = np.median(target[ankle_ids], axis=0)
        destination = np.median(candidate[ankle_ids], axis=0)
        transported = destination + (target - anchor) * ratio
        amount = (1 - smoothstep((target[:, 2] / height - .045) / .045)) * (target[:, 0] * sign > 0)
        candidate = candidate * (1 - amount[:, None]) + transported * amount[:, None]
    return candidate


def move_eye(points, body_rest, body_changed):
    center = points.mean(axis=0)
    distances = np.linalg.norm(body_rest - center, axis=1)
    nearest = np.argsort(distances)[:60]
    weights = 1 / np.maximum(distances[nearest], .005) ** 3
    weights /= weights.sum()
    displacement = np.sum((body_changed[nearest] - body_rest[nearest]) * weights[:, None], axis=0)
    rest_spread = np.linalg.norm(body_rest[nearest] - body_rest[nearest].mean(axis=0), axis=1).mean()
    changed_spread = np.linalg.norm(body_changed[nearest] - body_changed[nearest].mean(axis=0), axis=1).mean()
    radius_scale = np.clip(changed_spread / rest_spread, .65, 1.2)
    return center + displacement + (points - center) * radius_scale


def main():
    asset, output = [Path(value).resolve() for value in sys.argv[sys.argv.index("--") + 1:]]
    output.parent.mkdir(parents=True, exist_ok=True)
    # MPFB needs its preferences entry during register; no preference file is saved.
    addon_utils.enable("bl_ext.user_default.mpfb", default_set=True)
    with bpy.data.libraries.load(str(asset), link=False) as (_, target):
        target.collections = ["Realistic Human Base"]
    collection = target.collections[0]
    body = next(obj for obj in collection.objects if obj.get("human_modeling_body"))
    eyes = list(body.children)
    body.data.shape_keys["human_modeling_age"] = 2.
    edges = np.array([edge.vertices[:] for edge in body.data.edges])
    results, reports = {}, []
    for gender in (0, 1):
        rest, triangles, joints = reference(.5, gender, with_landmarks=True)
        name = "Morphologie" if gender else "Basis"
        original = coordinates(body.data.shape_keys.key_blocks[name])
        scale = float(np.ptp(original[:, 2]) / np.ptp(rest[:, 2]))
        offset = np.array((0, 0, original[:, 2].min() - rest[:, 2].min() * scale))
        rest = rest * scale + offset
        unposed_rest = rest.copy()
        rest = align_source_arms(rest, joints, joints, gender, scale, offset)
        mapping = correspondence(rest, triangles, original)
        identity = transfer(rest, triangles, mapping)
        assert np.max(np.abs(identity - original)) < 1e-8
        for stage, age in STAGES:
            changed, changed_triangles, aged_joints = reference(age, gender, with_landmarks=True)
            # Native tessellation can choose another diagonal for a deformed quad.
            # Reuse the adult triangles on the fixed MPFB vertex ordering.
            assert changed.shape == rest.shape
            assert np.array_equal(np.unique(triangles), np.unique(changed_triangles))
            changed = changed * scale + offset
            unposed_changed = changed.copy()
            changed = align_source_arms(changed, joints, aged_joints, gender, scale, offset)
            height = float(np.ptp(original[:, 2]))
            # Do not carry an adult breast residual onto the juvenile source.
            chest = smoothstep((original[:, 2] / height - .58) / .06)
            chest *= 1 - smoothstep((original[:, 2] / height - .80) / .06)
            chest *= 1 - smoothstep((np.abs(original[:, 0]) / height - .09) / .045)
            amount = 1 - chest * (.95 if stage == "Enfant" else .45 if stage == "Adolescent" else 0)
            candidate = transfer(changed, triangles, mapping, amount)
            candidate = transport_arms(original, candidate, joints, aged_joints, gender, scale)
            candidate = transport_feet(original, candidate, unposed_rest, unposed_changed, height)
            candidate = relax_displacement(original, candidate, edges, height)
            results[gender, stage, body.name] = candidate - original
            for eye in eyes:
                points = coordinates(eye.data.shape_keys.key_blocks[name])
                results[gender, stage, eye.name] = move_eye(points, original, candidate) - points
            reports.append({"gender": gender, "stage": stage, "source_age_parameter": age,
                            "gap_median": mapping["gap_median"], "gap_max": mapping["gap_max"]})
            print("SURFACE_TRANSFER", gender, stage, flush=True)
    for obj in (body, *eyes):
        base = coordinates(obj.data.shape_keys.key_blocks["Basis"])
        for stage, _ in STAGES:
            delta = results[0, stage, obj.name]
            add_driver(write_key(obj, stage, base + delta), body, stage, False)
            key = write_key(obj, stage + " · morphologie", base + results[1, stage, obj.name] - delta)
            key.slider_min = -1
            add_driver(key, body, stage, True)
    body["age_source"] = "Experimental MPFB CC0 triangle correspondence; chronological age not calibrated"
    bpy.data.libraries.write(str(output), {collection, *(obj.data for obj in (body, *eyes))}, fake_user=True, compress=True)
    output.with_suffix(".json").write_text(json.dumps(reports, indent=2), encoding="utf-8")
    print("EXPERIMENTAL_SURFACE_ASSET_READY", flush=True)


if __name__ == "__main__":
    main()
