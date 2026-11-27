"""Recette locale Blender 5.2 des espaces et du parentage des accessoires."""
import json
from pathlib import Path
import sys
import traceback

import bpy
import numpy as np
from mathutils import Euler, Matrix, Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import extension
from extension import accessories as A, human
from extension.animation import skeleton

KEYS = ('telephone', 'sac_a_dos', 'lunettes', 'sac_a_main', 'sac_de_courses',
        'parapluie_ferme', 'parapluie_ouvert')
BONES = dict(zip(KEYS, ('hand.R', 'spine.03', 'head', 'hand.R', 'hand.L', 'hand.R', 'hand.R')))
SIMPLE = KEYS[:3]
ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
import tempfile
OUT = Path(ARGS[0]) if ARGS else Path(tempfile.mkdtemp(prefix='hl_accessory_transforms_')) / 'accessory_transforms.json'
RESULTS = {}


def update():
    bpy.context.view_layer.update()


def fresh(label, age=None, use_operator=False):
    if use_operator:
        bpy.ops.humanloom.create(age=2.0 if age is None else age)
        body = bpy.context.object
    else:
        body = human.create_human(bpy.context)
        if age is not None:
            human.set_value(body, 'age', age)
    body.name = label
    body.modifiers['Human Modeling · Surface'].show_viewport = False
    return body, skeleton.install(body, correctives=False)


def set_object_transform(body, location=(2, -0.7, 2), rotation=(0.31, -0.27, 0.54), scale=(1.18, 0.83, 1.34)):
    body.location = location
    body.rotation_euler = Euler(rotation)
    body.scale = scale
    update()


def evaluated(obj):
    return obj.evaluated_get(bpy.context.evaluated_depsgraph_get())


def mesh_world(obj):
    obj = evaluated(obj)
    return np.array([list(obj.matrix_world @ v.co) for v in obj.data.vertices])


def apply_transform(points, matrix):
    matrix = np.asarray(matrix)
    return points @ matrix[:3, :3].T + matrix[:3, 3]


def max_error(a, b):
    return float(np.max(np.linalg.norm(a - b, axis=1)))


def add(body, keys=SIMPLE):
    result = {key: A.add_accessory(body, key) for key in keys}
    update()
    return result


def grasp_and_pose(rig):
    for name, angles in {'arm_upper.R': (-0.34, 0.24, -0.41), 'arm_lower.R': (0.35, -0.21, 0.18),
                         'head': (0.09, 0.12, -0.14), 'spine.03': (0.11, 0.06, -0.08)}.items():
        bone = rig.pose.bones[name]
        bone.rotation_mode = 'XYZ'
        bone.rotation_euler = angles
    update()


def check_parents(rig, accessories):
    assert all(obj.parent == rig and obj.parent_type == 'BONE' and obj.parent_bone == BONES[key]
               for key, obj in accessories.items())


def palm_world(rig):
    rig = evaluated(rig)
    hand = rig.pose.bones['hand.R']
    return rig.matrix_world @ hand.head.lerp(hand.tail, 0.5)


def face_screen_world(phone):
    phone = evaluated(phone)
    screen = max((p for p in phone.data.polygons if p.material_index == 1), key=lambda p: p.center.z)
    points = [phone.matrix_world @ phone.data.vertices[i].co for i in screen.vertices]
    normal = (points[1] - points[0]).cross(points[2] - points[0]).normalized()
    centre = sum(points, Vector((0, 0, 0))) / len(points)
    return centre, normal


def compare_affine():
    reference, rig_reference = fresh('Affinage référence')
    base = add(reference, KEYS)
    vertices = {key: mesh_world(obj) for key, obj in base.items()}
    check_parents(rig_reference, base)
    outcomes = {}
    cases = {
        'translation_X_2_m': ((2, 0, 0), (0, 0, 0), (1, 1, 1)),
        'translation_Z_2_m': ((0, 0, 2), (0, 0, 0), (1, 1, 1)),
        'rotation_et_echelle_uniforme': ((0, 0, 0), (0.31, -0.27, 0.54), (1.16,) * 3),
        'affine_non_uniforme': ((2, -0.7, 2), (0.31, -0.27, 0.54), (1.18, 0.83, 1.34)),
    }
    for label, parameters in cases.items():
        for timing in ('avant', 'apres'):
            body, rig = fresh(f'{label} {timing}')
            if timing == 'apres':
                set_object_transform(body, *parameters)
            items = add(body, KEYS)
            if timing == 'avant':
                set_object_transform(body, *parameters)
            check_parents(rig, items)
            errors = {key: max_error(mesh_world(obj), apply_transform(vertices[key], body.matrix_world))
                      for key, obj in items.items()}
            assert max(errors.values()) < 0.0001, (label, timing, errors)
            assert (items['telephone'].matrix_world.translation - palm_world(rig)).length < 0.0001
            outcomes[f'{label}_{timing}'] = {k: round(v * 1000, 4) for k, v in errors.items()}
    assert len(A.accessories_of(reference)) == len(KEYS)
    assert all(np.array_equal(mesh_world(obj), vertices[key]) for key, obj in base.items())
    return {'ecart_max_par_maillage_mm': outcomes, 'personnage_temoin_stable': True}


def compare_pose_and_parent():
    outcomes = {}
    for relative in (False, True):
        old_body, old_rig = fresh(f'Pose avant ajout {relative}')
        new_body, new_rig = fresh(f'Pose après ajout {relative}')
        for rig in (old_rig, new_rig):
            for name in ('hand.R', 'spine.03', 'head'):
                rig.data.bones[name].use_relative_parent = relative
        for body in (old_body, new_body):
            set_object_transform(body)
        existing = add(old_body)
        old_geometry = {key: mesh_world(obj) for key, obj in existing.items()}
        for rig in (old_rig, new_rig):
            grasp_and_pose(rig)
        new = add(new_body)
        check_parents(new_rig, new)
        differences = {key: max_error(mesh_world(obj), mesh_world(existing[key])) for key, obj in new.items()}
        motion = {key: max_error(mesh_world(obj), old_geometry[key]) for key, obj in existing.items()}
        assert max(differences.values()) < 0.0001, (relative, differences)
        assert min(motion.values()) > 0.015, (relative, motion)
        outcomes[str(relative)] = {'ordre_m': differences, 'mouvement_m': motion}
    return outcomes


def apply_body(body):
    bpy.ops.object.select_all(action='DESELECT')
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True, isolate_users=True)
    update()


def surface_gap(body, obj):
    points = mesh_world(body)
    body_data = evaluated(body).data
    mesh_tree = BVHTree.FromPolygons([Vector(v) for v in points], [p.vertices[:] for p in body_data.polygons])
    return min(mesh_tree.find_nearest(Vector(p))[3] for p in mesh_world(obj))


def baked_cases():
    results = {}
    rotation_only = ((2, 0, 2), (0.31, -0.27, 0.54), (1, 1, 1))
    scale_only = ((2, 0, 2), (0, 0, 0), (1.18, 0.83, 1.34))
    combined = ((2, 0, 2), (0.31, -0.27, 0.54), (1.18, 0.83, 1.34))
    for label, params in (('rotation', rotation_only), ('echelle', scale_only), ('combinees', combined)):
        for freeze_cage in (False, True):
            old_body, old_rig = fresh(f'{label} {freeze_cage} avant CTRL A')
            new_body, new_rig = fresh(f'{label} {freeze_cage} après CTRL A')
            for body in (old_body, new_body):
                if freeze_cage:
                    # Matérialise la cage, puis garde le modificateur natif désactivé sous un autre nom.
                    cage = skeleton.cage_points(body)
                    body.data.vertices.foreach_set('co', cage.astype(np.float32).ravel())
                    body.data.update()
                    native = body.modifiers[human.MODIFIER_NAME]
                    native.name = 'Cage enregistrée de la fixture'
                    native.show_viewport = False
                set_object_transform(body, *params)
            existing = add(old_body)
            pre_bake = {key: mesh_world(obj) for key, obj in existing.items()}
            body_before = mesh_world(old_body)
            for body in (old_body, new_body):
                apply_body(body)
            new = add(new_body)
            check_parents(new_rig, new)
            cabin_delta = max_error(mesh_world(old_body), body_before)
            existing_delta = {key: max_error(mesh_world(obj), pre_bake[key]) for key, obj in existing.items()}
            order_delta = {key: max_error(mesh_world(obj), mesh_world(existing[key])) for key, obj in new.items()}
            assert max(existing_delta.values()) < 0.0001, existing_delta
            assert order_delta['telephone'] < 0.003, order_delta
            assert (new['telephone'].matrix_world.translation - palm_world(new_rig)).length < 0.0001
            gaps = {key: surface_gap(new_body, new[key]) for key in ('sac_a_dos', 'lunettes')}
            if freeze_cage:
                assert cabin_delta < 0.0001 and max(order_delta.values()) < 0.0001, (label, cabin_delta, order_delta)
            assert all(gap < 0.045 for gap in gaps.values()), gaps
            results[f'{label}_{"cage_figee" if freeze_cage else "native"}'] = {
                'cage_delta_m': cabin_delta, 'accessoires_deja_attaches_delta_m': existing_delta,
                'ordre_ajout_delta_m': order_delta, 'ecarts_surface_accessoires_m': gaps,
            }
    return results


def ear_landmarks_world(body):
    """Mesure anatomique indépendante à partir des yeux et de la surface de la tête en scène."""
    eyes = [mesh_world(eye).mean(axis=0) for eye in skeleton.eyes_of(body)]
    centre = Vector(np.mean(eyes, axis=0))
    model = body.matrix_world
    across = (model.to_3x3() @ Vector((1, 0, 0))).normalized()
    upwards = (model.to_3x3() @ Vector((0, 0, 1))).normalized()
    back = (model.to_3x3() @ Vector((0, 1, 0))).normalized()
    centre += 0.065 * back
    ear_centre = centre - 0.024 * upwards
    head_group = body.vertex_groups['head'].index
    head_vertices = [v.index for v in evaluated(body).data.vertices
                     if any(g.group == head_group and g.weight > 0.8 for g in v.groups)]
    relative = mesh_world(body)[head_vertices] - np.array(ear_centre)
    # Limite latérale de la surface sur une bande à hauteur d'oreille.
    region = relative[(abs(relative @ np.array(upwards)) < 0.045) & (abs(relative @ np.array(back)) < 0.045)]
    ear = ear_centre + float((region @ np.array(across)).min()) * across
    return ear, centre


def compare_ear_and_persist():
    samples = {}
    targets = {}
    expected = {}
    for label, params, age in (
        ('A_oreille_origine', ((0, 0, 0), (0, 0, 0), (1, 1, 1)), None),
        ('B_oreille_X2', ((2, 0, 0), (0, 0, 0), (1, 1, 1)), None),
        ('C_oreille_affine', ((4, -0.4, 0.3), (0.08, -0.12, 0.25), (1.18, 0.83, 1.34)), None),
        ('D_enfant', ((6, 0, 0), (0.02, -0.12, 0.14), (1.12, 0.88, 1.20)), 0.0),
    ):
        body, rig = fresh(label, age, use_operator=True)
        set_object_transform(body, *params)
        items = add(body)
        phone = items['telephone']
        if age is None:
            report = A.pose_phone_ear(body)
            update()
            ear, centre = ear_landmarks_world(body)
            screen_centre, screen_normal = face_screen_world(phone)
            screen_distance = (screen_centre - ear).length
            screen_dot = screen_normal.dot((centre - screen_centre).normalized())
            assert (phone.matrix_world.translation - palm_world(rig)).length < 0.0001
            assert screen_distance < 0.1 and screen_dot > 0.6, (label, screen_distance, screen_dot, report)
            assert report['ecart_mm'] < 22 and report['angle_normale_deg'] < 60, (label, report)
            samples[label] = {'ecart_ecran_surface_oreille_mm': 1000 * screen_distance,
                              'cosinus_normale_ecran_vers_tete': screen_dot, 'solveur': report}
            if 'A_oreille_origine' in targets:
                expected_phone = apply_transform(targets['A_oreille_origine'], body.matrix_world)
                assert max_error(mesh_world(phone), expected_phone) < 0.001, (label, report)
            targets[label] = mesh_world(phone)
        else:
            samples[label] = {'sac_proche_du_dos_m': surface_gap(body, items['sac_a_dos']),
                              'lunettes_proches_du_visage_m': surface_gap(body, items['lunettes'])}
            assert max(samples[label].values()) < 0.06, samples[label]
        expected[label] = {key: (obj.name, mesh_world(obj)) for key, obj in items.items()}
    if len(ARGS) > 1:
        bpy.context.preferences.filepaths.save_version = 0
        bpy.ops.wm.save_as_mainfile(filepath=ARGS[1])
        bpy.ops.wm.open_mainfile(filepath=ARGS[1], load_ui=False, use_scripts=False)
        update()
        for body_name, items in expected.items():
            body = bpy.data.objects[body_name]
            rig = skeleton.rigs_of(body)[0]
            recovered = {obj[A.MARKER]: obj for obj in A.accessories_of(body)}
            check_parents(rig, recovered)
            for key, (name, points) in items.items():
                assert recovered[key].name == name and max_error(mesh_world(recovered[key]), points) < 0.0001, (body_name, key)
        samples['reouverture'] = len(expected)
    return samples


def run(name, probe):
    try:
        for obj in list(bpy.data.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        RESULTS[name] = {'ok': True, 'result': probe()}
    except Exception:
        RESULTS[name] = {'ok': False, 'traceback': traceback.format_exc()}
    OUT.write_text(json.dumps(RESULTS, indent=2), encoding='utf-8')
    print(name, json.dumps(RESULTS[name]), flush=True)


extension.register()
probes = {
    'affine': compare_affine,
    'pose_et_parent': compare_pose_and_parent,
    'transformations_appliquees': baked_cases,
    'oreille_personnages_persistance': compare_ear_and_persist,
}
for name in ARGS[2:] or probes:
    run(name, probes[name])
raise SystemExit(0 if all(row['ok'] for row in RESULTS.values()) else 1)
