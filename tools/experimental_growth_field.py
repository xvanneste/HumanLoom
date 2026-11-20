"""Continuous growth field: monotone height and positive transverse scaling.

Unlike nearest-surface displacement this map is one-to-one in the continuum:
z'=F(z), x'=sx(z)*x, y'=sy(x,z,sign(y))*y, with F increasing and sx,sy positive.
Discrete polygon intersections and anatomical quality still require validation.
"""

import json
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from experimental_age_transfer import add_driver, coordinates, write_key

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "extension"))
import anatomy


def endpoint(obj, sex):
    points = coordinates(obj.data.shape_keys.key_blocks["Morphologie" if sex else "Basis"])
    correction = obj.data.shape_keys.key_blocks.get("Surface · Paupières internes")
    if correction and sex == 0:
        points += coordinates(correction) - coordinates(obj.data.shape_keys.key_blocks[0])
    return points


def head_section(points, triangles, eye_z):
    measurements = []
    for level in np.linspace(eye_z+.008, eye_z+.045, 24):
        loops, actual = anatomy.section_loops(points, triangles, level)
        central = [loop for loop in loops if anatomy.encloses_axis(loop)]
        if len(central) == 1:
            perimeter = float(np.linalg.norm(central[0]-np.roll(central[0], 1, axis=0), axis=1).sum())
            measurements.append((perimeter, actual))
    if not measurements:
        raise ValueError("No measurable head contour")
    return max(measurements)


def soften_juvenile_torso(points, edges):
    result = points.copy()
    height = float(np.ptp(points[:, 2]))
    relative = (points[:, 2]-points[:, 2].min())/height
    mask = smooth((relative-.43)/.09) * (1-smooth((relative-.79)/.065))
    mask *= 1-smooth((np.abs(points[:, 0])/height-.09)/.065)
    mask *= smooth((-points[:, 1]-.005)/.035)
    degree = np.bincount(edges.reshape(-1), minlength=len(points)).clip(min=1)
    for _ in range(36):
        neighbors = np.zeros_like(result)
        np.add.at(neighbors, edges[:, 0], result[edges[:, 1]])
        np.add.at(neighbors, edges[:, 1], result[edges[:, 0]])
        result += (neighbors/degree[:, None]-result)*(.28*mask[:, None])
    return result


def juvenile_face(points, eye_z):
    result = points.copy()
    x, y, z = points.T
    front = smooth((-y-.045)/.035)
    cheeks = np.exp(-((np.abs(x)-.035)/.022)**2-((z-(eye_z-.035))/.025)**2)*front
    nose = np.exp(-(x/.018)**2-((z-(eye_z-.025))/.024)**2)*front
    chin = np.exp(-(x/.025)**2-((z-(eye_z-.078))/.02)**2)*front
    result[:, 0] += np.sign(x)*.002*cheeks
    result[:, 1] += .0025*nose+.002*chin-.003*cheeks
    result[:, 2] += .001*chin
    return result


def aged_face(points, eye_centers, mouth_center):
    """Artistic regional aging cues. Amplitudes are not fitted clinical norms."""
    result = points.copy()
    x, y, z = points.T
    eye_z = float(np.mean([point[2] for point in eye_centers]))
    eye_y = float(np.mean([point[1] for point in eye_centers]))
    # Aging the visible eyelid must not compress the posterior orbital wall.
    front = smooth((-y-.025)/.05)
    eyelid_front = smooth((eye_y-.002-y)/.010)
    for center in eye_centers:
        eye = np.exp(-((x-center[0])/.018)**4-((z-center[2])/.022)**4)*eyelid_front
        result[:, 2] -= (z-center[2])*.16*eye
        bag = np.exp(-((x-center[0])/.017)**2-((z-(center[2]-.017))/.007)**2)*eyelid_front
        result[:, 1] -= .0012*bag
    mouth_z = mouth_center[2]
    lips = np.exp(-(x/.033)**4-((z-mouth_z)/.015)**4)*front
    result[:, 2] -= (z-mouth_z)*.18*lips
    nose = np.exp(-(x/.022)**2-((z-(eye_z-.032))/.031)**2)*front
    result[:, 0] += x*.035*nose
    result[:, 1] -= .0015*nose
    result[:, 2] -= .0018*nose
    cheek = np.exp(-((np.abs(x)-.046)/.025)**2-((z-(mouth_z+.014))/.030)**2)*front
    jowl = np.exp(-((np.abs(x)-.043)/.022)**2-((z-(mouth_z-.032))/.025)**2)*front
    result[:, 0] += np.sign(x)*(.0012*cheek+.002*jowl)
    result[:, 1] -= .0013*jowl
    result[:, 2] -= .004*cheek+.008*jowl
    # A broad nasolabial crease is supported by the modeling density; fine skin
    # wrinkles remain a future displacement/material task.
    line_x = .020+np.clip((eye_z-.04-z)/.035, 0, 1)*.011
    fold = np.exp(-((np.abs(x)-line_x)/.003)**2)
    fold *= smooth((z-(mouth_z-.01))/.012)*(1-smooth((z-(eye_z-.044))/.012))*front
    result[:, 1] += .0018*fold
    forehead = np.exp(-(x/.065)**4)*front
    for offset in (.029,.047,.063):
        result[:,1] += .0008*forehead*np.exp(-((z-(eye_z+offset))/.0055)**2)
    return result


def smooth(values):
    values = np.clip(values, 0, 1)
    return values * values * (3 - 2 * values)


def monotone(x, knots, values):
    widths = np.diff(knots)
    slopes = np.diff(values) / widths
    if np.any(slopes <= 0):
        raise ValueError("Non-increasing height anchors")
    derivatives = np.r_[slopes[0], 2 / (1 / slopes[:-1] + 1 / slopes[1:]), slopes[-1]]
    # Clamp derivatives to the monotone cubic bound for either adjacent interval.
    for index, slope in enumerate(slopes):
        derivatives[index:index + 2] = np.minimum(derivatives[index:index + 2], 3 * slope)
    index = np.clip(np.searchsorted(knots, x, side="right") - 1, 0, len(widths) - 1)
    t = np.clip((x - knots[index]) / widths[index], 0, 1)
    result = ((2*t**3 - 3*t**2 + 1) * values[index] + (t**3 - 2*t**2 + t) * widths[index] * derivatives[index]
              + (-2*t**3 + 3*t**2) * values[index+1] + (t**3 - t**2) * widths[index] * derivatives[index+1])
    return result


def tree(points, triangles):
    return BVHTree.FromPolygons([Vector(point) for point in points], triangles.tolist(), all_triangles=True)


def ray_y(surface, x, z, front):
    start = Vector((x, -3 if front else 3, z))
    hit = surface.ray_cast(start, Vector((0, 1 if front else -1, 0)), 6)[0]
    return abs(hit.y) if hit is not None else None


def radius_x(surface, z):
    # Ray from the torso axis, so detached arms cannot replace its first boundary.
    hits = [surface.ray_cast(Vector((0, .01, z)), Vector((sign, 0, 0)), 2)[0] for sign in (-1, 1)]
    if any(hit is None for hit in hits):
        return None
    return sum(abs(hit.x) for hit in hits) / 2


def blur(values, passes=2):
    for _ in range(passes):
        padded = np.pad(values, ((1, 1), (1, 1)), mode="edge")
        values = (padded[1:-1, 1:-1] * 4 + padded[:-2, 1:-1] + padded[2:, 1:-1]
                  + padded[1:-1, :-2] + padded[1:-1, 2:]) / 8
    return values


def bilinear(grid, xs, zs, x, z):
    ix = np.clip(np.searchsorted(xs, x) - 1, 0, len(xs) - 2)
    iz = np.clip(np.searchsorted(zs, z) - 1, 0, len(zs) - 2)
    tx = np.clip((x - xs[ix]) / (xs[ix+1] - xs[ix]), 0, 1)
    tz = np.clip((z - zs[iz]) / (zs[iz+1] - zs[iz]), 0, 1)
    return (grid[iz, ix] * (1-tx) * (1-tz) + grid[iz, ix+1] * tx * (1-tz)
            + grid[iz+1, ix] * (1-tx) * tz + grid[iz+1, ix+1] * tx * tz)


def make_field(studio, eye_z, adult, juvenile, triangles_adult, triangles_juvenile, joint_adult, joint_juvenile):
    height = float(np.ptp(studio[:, 2]))
    floor = float(studio[:, 2].min())
    scale = height / np.ptp(adult[:, 2])
    offset = np.array((0, 0, floor - adult[:, 2].min() * scale))
    adult, juvenile = adult * scale + offset, juvenile * scale + offset
    joint_adult, joint_juvenile = joint_adult * scale + offset, joint_juvenile * scale + offset
    knots = np.array((floor, floor + height*.055, floor + height*.28, floor + height*.48,
                      floor + height*.81, floor + height*.86, floor + height*.895, eye_z, floor + height))
    source = np.r_[adult[:, 2].min(), joint_adult[:, 2], adult[:, 2].max()]
    destination = np.r_[juvenile[:, 2].min(), joint_juvenile[:, 2], juvenile[:, 2].max()]
    values = knots + destination - source
    # Keep the reference soles on the floor, independently of the source's ground helper.
    values -= values[0] - floor
    y_shift = np.r_[0., (joint_juvenile-joint_adult)[:, 1], (joint_juvenile-joint_adult)[-1, 1]]
    probe = np.linspace(knots[0], knots[-1], 2001)
    assert np.all(np.diff(monotone(probe, knots, values)) > 0)
    adult_tree, young_tree = tree(adult, triangles_adult), tree(juvenile, triangles_juvenile)
    return {"height": height, "floor": floor, "knots": knots, "values": values,
            "source": source, "destination": destination, "adult_tree": adult_tree, "young_tree": young_tree,
            "y_shift": np.clip(y_shift*.65, -.04, .04),
            "stage_ratio": float(np.ptp(juvenile[:, 2]) / height)}


def prepare_profiles(field, studio, studio_triangles):
    height, floor = field["height"], field["floor"]
    zs = np.linspace(floor, floor + height, 150)
    source_z = np.interp(zs, field["knots"], field["source"])
    young_z = np.interp(zs, field["knots"], field["destination"])
    adult_tree, young_tree = field["adult_tree"], field["young_tree"]
    ratio = field["stage_ratio"]
    # Conservative regional scales avoid reacting to ray hits on an arm or a
    # cavity. These are artistic bounds, not clinical growth coefficients.
    relative = (zs - floor) / height
    head = smooth((relative - .84) / .09)
    sx = ratio ** .8 * (1-head) + ratio ** .28 * head
    xs = np.linspace(-height*.16, height*.16, 65)
    reference = tree(studio, studio_triangles)
    profiles = []
    for front in (True, False):
        grid = np.full((len(zs), len(xs)), ratio)
        for iz, z in enumerate(zs):
            center_depth = ray_y(young_tree, 0, young_z[iz], front)
            studio_radius = radius_x(reference, z)
            for ix, x in enumerate(xs):
                original = ray_y(reference, x, z, front)
                target = None
                if field.get("stage") == "Enfant":
                    if center_depth and studio_radius and studio_radius > .02:
                        target = center_depth * np.sqrt(max(.08, 1 - (x/(studio_radius*1.08))**2))
                else:
                    target = ray_y(young_tree, x*sx[iz], young_z[iz], front)
                if original and target and original > .015:
                    grid[iz, ix] = np.clip(target / original, .18, 1.5)
        profiles.append(blur(grid, 3))
    field.update(xs=xs, zs=zs, sx=sx, front=profiles[0], back=profiles[1])


def deform(points, field):
    x, y, z = points.T
    sx = np.interp(z, field["zs"], field["sx"])
    a = bilinear(field["front"], field["xs"], field["zs"], x, z)
    b = bilinear(field["back"], field["xs"], field["zs"], x, z)
    central = 1 - smooth((np.abs(x) / field["height"] - .105) / .055)
    sy = np.where(y < 0, a, b) * central + field["stage_ratio"] * (1-central)
    assert np.all(sx > 0) and np.all(sy > 0)
    normalized = (z-field["floor"]) / field["height"]
    torso = smooth((normalized-.40)/.10) * (1-smooth((normalized-.77)/.07))
    head = smooth((normalized-.84)/.09)
    safe_scale = field["stage_ratio"] ** .8 * (1-head) + field["stage_ratio"] ** .28 * head
    sy = sy*torso + safe_scale*(1-torso)
    y_new = y*sy
    if field.get("stage") == "Senior":
        y_new += np.interp(z, field["knots"], field["y_shift"])
    return np.column_stack((x*sx, y_new, monotone(z, field["knots"], field["values"])))


def main():
    asset, cache_path, output = [Path(value).resolve() for value in sys.argv[sys.argv.index("--") + 1:]]
    cache = np.load(cache_path, allow_pickle=False)
    with bpy.data.libraries.load(str(asset), link=False) as (_, target):
        target.collections = ["Realistic Human Base"]
    collection = target.collections[0]
    body = next(obj for obj in collection.objects if obj.get("human_modeling_body"))
    eyes = list(body.children)
    body.data.calc_loop_triangles()
    triangles = np.array([tri.vertices[:] for tri in body.data.loop_triangles])
    edges = np.array([edge.vertices[:] for edge in body.data.edges])
    body.data.shape_keys["human_modeling_age"] = 2.
    stages = (("Enfant", 0), ("Adolescent", 1), ("Senior", 3))
    results, reports = {}, []
    for sex in (0, 1):
        name = "Morphologie" if sex else "Basis"
        original = endpoint(body, sex)
        eye_z = np.mean(np.concatenate([coordinates(eye.data.shape_keys.key_blocks[name]) for eye in eyes])[:, 2])
        for stage, index in stages:
            field = make_field(original, eye_z, cache[f"points_{sex}_2"], cache[f"points_{sex}_{index}"],
                               cache[f"triangles_{sex}_2"], cache[f"triangles_{sex}_{index}"],
                               cache[f"joints_{sex}_2"], cache[f"joints_{sex}_{index}"])
            field["stage"] = stage
            prepare_profiles(field, original, triangles)
            for obj in (body, *eyes):
                points = endpoint(obj, sex)
                results[sex, stage, obj.name] = deform(points, field) - points
            reports.append({"sex": sex, "stage": stage, "z_anchors": field["knots"].tolist(),
                            "z_values": field["values"].tolist(), "scale_x_range": [float(field["sx"].min()), float(field["sx"].max())]})
            print("GROWTH_FIELD", sex, stage, flush=True)
    # Prepubertal development should not inherit the full adult sex difference.
    # These artistic blending coefficients still require biological calibration.
    for stage, strength in (("Enfant", .1), ("Adolescent", .65)):
        for obj in (body, *eyes):
            original_f = endpoint(obj, 0)
            original_m = endpoint(obj, 1)
            female = original_f + results[0, stage, obj.name]
            male = original_m + results[1, stage, obj.name]
            common = (female + male) / 2
            results[0, stage, obj.name] = common + (female-common)*strength - original_f
            results[1, stage, obj.name] = common + (male-common)*strength - original_m
    if "nominal_ages" in cache and int(cache["nominal_ages"][0]) == 5:
        reference = json.loads(cache_path.with_name("who-60-months.json").read_text(encoding="utf-8"))
        for sex, label in ((0, "F"), (1, "M")):
            points = endpoint(body, sex) + results[sex, "Enfant", body.name]
            points = soften_juvenile_torso(points, edges)
            results[sex, "Enfant", body.name] = points-endpoint(body, sex)
            scale = reference[label]["height"] / 100 / np.ptp(points[:, 2])
            floor = float(points[:, 2].min())
            corrected = {}
            for obj in (body, *eyes):
                original = endpoint(obj, sex)
                current = (original+results[sex, "Enfant", obj.name]) * scale
                current[:, 2] -= floor*scale
                corrected[obj.name] = current
            eye_z = float(np.concatenate([corrected[eye.name] for eye in eyes])[:, 2].mean())
            for obj in (body, *eyes):
                corrected[obj.name] = juvenile_face(corrected[obj.name], eye_z)
            circumference, level = head_section(corrected[body.name], triangles, eye_z)
            head_scale = reference[label]["head_circumference"] / 100 / circumference
            for obj in (body, *eyes):
                current = corrected[obj.name]
                weight = smooth((current[:, 2]-(eye_z-.09))/.065)
                current[:, :2] *= (1+(head_scale-1)*weight)[:, None]
                results[sex, "Enfant", obj.name] = current-endpoint(obj, sex)
            actual, level = head_section(corrected[body.name], triangles, eye_z)
            assert abs(actual-reference[label]["head_circumference"]/100) < 1e-5
            reports.append({"sex": label, "stage": "Enfant", "age_target_years": 5,
                            "height_m": float(np.ptp(corrected[body.name][:, 2])), "head_section_m": actual,
                            "head_section_z": level, "scope": "Horizontal head-section surrogate, not a validated clinical tape measurement",
                            "reference": reference})
    atlas_file = Path(__file__).resolve().parents[1] / "validation/reperes-07/reperes-adultes-travail.json"
    atlas = json.loads(atlas_file.read_text(encoding="utf-8"))["points"]
    if "nominal_ages" in cache and int(cache["nominal_ages"][1]) == 15:
        reference = json.loads(cache_path.with_name("who-180-months.json").read_text(encoding="utf-8"))
        for sex, label in ((0, "F"), (1, "M")):
            points = endpoint(body, sex)+results[sex, "Adolescent", body.name]
            floor = float(points[:, 2].min())
            eye_z = float(np.mean([np.mean((endpoint(eye, sex)+results[sex, "Adolescent", eye.name])[:, 2]) for eye in eyes]))
            neck = eye_z-.11
            growth = reference[label]["height"]/100-np.ptp(points[:, 2])
            for obj in (body, *eyes):
                original = endpoint(obj, sex)
                current = original+results[sex, "Adolescent", obj.name]
                current[:, 2] += growth*smooth((current[:, 2]-floor)/(neck-floor))
                results[sex, "Adolescent", obj.name] = current-original
            actual = float(np.ptp((endpoint(body, sex)+results[sex, "Adolescent", body.name])[:, 2]))
            assert abs(actual-reference[label]["height"]/100) < 1e-6
            reports.append({"sex": label, "stage": "Adolescent", "age_target_years": 15,
                            "height_m": actual, "reference": reference,
                            "scope": "Stature adjusted below the head. Regional growth proportions remain artistic."})
    for sex in (0, 1):
        original = endpoint(body, sex)
        points = original+results[sex, "Senior", body.name]
        centers = [np.mean(endpoint(eye, sex)+results[sex, "Senior", eye.name], axis=0) for eye in eyes]
        mouth = (points[atlas["ch_l"]["vertex"]]+points[atlas["ch_r"]["vertex"]])/2
        results[sex, "Senior", body.name] = aged_face(points, centers, mouth)-original
    reports.append({"stage": "Senior", "age_target_years": 75,
                    "qualitative_reference": "https://doi.org/10.1038/s41598-022-26376-8",
                    "scope": "Artistic regional cues informed by published trends; no fitted population amplitudes or fine skin wrinkles"})
    for obj in (body, *eyes):
        base = coordinates(obj.data.shape_keys.key_blocks["Basis"])
        for stage, _ in stages:
            delta = results[0, stage, obj.name]
            add_driver(write_key(obj, stage, base + delta), body, stage, False)
            key = write_key(obj, stage + " · morphologie", base + results[1, stage, obj.name] - delta)
            key.slider_min = -1
            add_driver(key, body, stage, True)
    if "nominal_ages" in cache:
        body["human_modeling_age_targets"] = cache["nominal_ages"].tolist()
    body["age_source"] = "Experimental growth field; WHO stature targets at 5/15 when available; regional anatomy remains unvalidated"
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.data.libraries.write(str(output), {collection, *(obj.data for obj in (body, *eyes))}, fake_user=True, compress=True)
    output.with_suffix(".json").write_text(json.dumps(reports, indent=2), encoding="utf-8")
    print("EXPERIMENTAL_GROWTH_FIELD_READY", flush=True)


if __name__ == "__main__":
    main()
