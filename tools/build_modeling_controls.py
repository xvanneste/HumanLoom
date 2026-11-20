"""Build bounded proportion deformations on both adult endpoint shapes."""

import sys
from pathlib import Path

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from muscle_fields import fields as muscle_fields
from expanded_fields import fields as expanded_fields

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "extension"))
from proportions import BASE_ID, CONTROLS, CURRENT_SCHEMA, bind_control, key_name, property_name


def coordinates(key):
    result = np.empty(len(key.data) * 3)
    key.data.foreach_get("co", result)
    return result.reshape((-1, 3))


def smooth(values, lower, upper):
    weight = np.clip((values - lower) / (upper - lower), 0, 1)
    return weight * weight * (3 - 2 * weight)


def bell(values, center, radius):
    return np.exp(-((values - center) / radius) ** 2)


def deformations(points, height, eye_z):
    x, y, z = points.T
    absolute_x = np.abs(x)
    side = np.sign(x)
    normalized_z = z / height
    central = 1 - smooth(absolute_x / height, .11, .17)
    front = smooth(-y, .065, .105)
    head = smooth(z, eye_z - .13, eye_z - .065)
    eye_region = (
        smooth(absolute_x, .004, .014)
        * (1 - smooth(absolute_x, .054, .078))
        * (1 - smooth(np.abs(z - eye_z), .016, .041))
        * front
    )
    mouth = bell(x, 0, .044) * bell(z, eye_z - .067, .018) * front
    nose = bell(x, 0, .024) * bell(z, eye_z - .028, .033) * smooth(-y, .12, .15)
    lower_face = bell(z, eye_z - .085, .035) * front
    shoulders = smooth(absolute_x / height, .045, .13) * smooth(normalized_z, .32, .52)
    shoulders *= 1 - smooth(normalized_z, .84, .89)
    waist = bell(normalized_z, .60, .065) * central
    hips = bell(normalized_z, .48, .065) * central
    depth = bell(normalized_z, .68, .13) * central
    neck = bell(z, eye_z - .17, .045) * central
    zeros = np.zeros(len(points))
    abdomen = bell(normalized_z, .60, .12) * central
    pelvis = bell(normalized_z, .47, .08) * central
    thighs = bell(normalized_z, .34, .12) * central
    leg_axis = side * height * .065
    cheeks = bell(absolute_x, .045, .026) * bell(z, eye_z - .040, .035) * front
    fat_x = x * (.13 * abdomen + .10 * pelvis) + (x - leg_axis) * .14 * thighs
    fat_x = side * np.maximum(side * fat_x, -.45 * absolute_x)
    fat_y = (y + .01) * (.20 * abdomen + .10 * pelvis + .12 * thighs) - .003 * cheeks
    return {
        **muscle_fields(points, height),
        **expanded_fields(points, height, eye_z),
        "corpulence": np.column_stack((fat_x, fat_y, zeros)),
        "shoulders": np.column_stack((side * .014 * shoulders, zeros, zeros)),
        "waist": np.column_stack((x * .12 * waist, (y + .01) * .09 * waist, zeros)),
        "hips": np.column_stack((x * .10 * hips, (y + .01) * .05 * hips, zeros)),
        "torso_depth": np.column_stack((zeros, (y + .01) * .10 * depth, zeros)),
        "neck": np.column_stack((x * .10 * neck, (y + .01) * .06 * neck, zeros)),
        "legs": np.column_stack((zeros, zeros, .06 * np.clip(z, 0, height * .48))),
        "torso": np.column_stack((zeros, zeros, .028 * smooth(normalized_z, .46, .83))),
        "head_width": np.column_stack((x * .07 * head, zeros, zeros)),
        "head_height": np.column_stack((zeros, zeros, (z - eye_z) * .08 * head)),
        "jaw": np.column_stack((x * .13 * lower_face, zeros, zeros)),
        "chin": np.column_stack((zeros, -.004 * bell(x, 0, .031) * bell(z, eye_z - .105, .023) * front, zeros)),
        "cheeks": np.column_stack((side * .003 * bell(absolute_x, .052, .023) * bell(z, eye_z - .031, .026) * front, zeros, zeros)),
        "nose_length": np.column_stack((zeros, -.005 * nose, zeros)),
        "nose_width": np.column_stack((x * .18 * nose, zeros, zeros)),
        "mouth": np.column_stack((x * .12 * mouth, zeros, zeros)),
        "lips": np.column_stack((zeros, -.0015 * mouth, zeros)),
        "eye_spacing": np.column_stack((side * .003 * eye_region, zeros, zeros)),
        "eye_height": np.column_stack((zeros, zeros, .0025 * eye_region)),
        "forehead": np.column_stack((zeros, zeros, .005 * smooth(z, eye_z + .022, eye_z + .075))),
    }


def main():
    asset = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
    with bpy.data.libraries.load(str(asset), link=False) as (_, target):
        target.collections = ["Realistic Human Base"]
    collection = target.collections[0]
    body = next(obj for obj in collection.objects if obj.get("human_modeling_body"))
    objects = [body, *body.children]
    owner_keys = body.data.shape_keys
    endpoints = {}
    for morph_name in ("Basis", "Morphologie"):
        body_points = coordinates(owner_keys.key_blocks[morph_name])
        height = np.ptp(body_points[:, 2])
        eye_points = np.concatenate([
            coordinates(eye.data.shape_keys.key_blocks[morph_name]) for eye in body.children
        ])
        eye_z = eye_points[:, 2].mean()
        endpoints[morph_name] = {}
        for obj in objects:
            points = coordinates(obj.data.shape_keys.key_blocks[morph_name])
            if obj is body:
                values = deformations(points, height, eye_z)
            else:
                # Move eyeballs as rigid parts to retain their shape.
                center = points.mean(axis=0, keepdims=True)
                fields = deformations(center, height, eye_z)
                allowed = {"legs", "torso", "head_width", "head_height", "eye_spacing", "eye_height", "facial_asymmetry"}
                values = {
                    name: np.broadcast_to(delta if name in allowed else np.zeros_like(delta), points.shape).copy()
                    for name, delta in fields.items()
                }
            endpoints[morph_name][obj.name] = values

    for identifier, label in CONTROLS:
        prop = property_name(identifier)
        owner_keys[prop] = 0.0
        owner_keys.id_properties_ui(prop).update(
            min=-1.0, max=1.0, soft_min=-1.0, soft_max=1.0,
            default=0.0, description=label,
        )
        for obj in objects:
            basis = coordinates(obj.data.shape_keys.key_blocks["Basis"])
            poles = (("gain", 1.0), ("perte", -.65)) if identifier == "corpulence" else ((None, 1.0),)
            for pole, factor in poles:
                delta = endpoints["Basis"][obj.name][identifier] * factor
                correction = endpoints["Morphologie"][obj.name][identifier] * factor - delta
                if not np.any(delta) and not np.any(correction) and not (identifier == "skin_relief" and obj is body):
                    continue
                for corrective, displacement in ((False, delta), (True, correction)):
                    name = key_name(identifier, corrective, pole)
                    key = obj.data.shape_keys.key_blocks.get(name)
                    if key is None:
                        key = obj.shape_key_add(name=name)
                    key.data.foreach_set("co", (basis + displacement).reshape(-1))
                    key.slider_min = 0 if pole else -1
                    key.slider_max = 1
                    key.value = 0
                    bind_control(key, owner_keys, identifier, corrective, pole)
    body.data["human_modeling_schema"] = CURRENT_SCHEMA
    body.data["human_modeling_base"] = BASE_ID
    datablocks = {collection}
    datablocks.update(obj.data for obj in objects)
    bpy.data.libraries.write(str(asset), datablocks, fake_user=True, compress=True)
    print("MODELING_CONTROLS_READY", len(CONTROLS), flush=True)


if __name__ == "__main__":
    main()
