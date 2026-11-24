"""Diagnostic des articulations (coude, épaule, genou, hanche, poignet, cou) : mesures chiffrées de la déformation du corps posé, sur 3 morphologies. Pas d'opinion : des nombres.

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/diagnose_joints.py -- DOSSIER_DE_SORTIE [--tag avant] [--preserve 1] [--morphs defaut,femme_jeune,homme_age] [--timing 1]

Mesures à chaque angle (région = sommets au repos à moins de R du pivot) :
 - dV_local (cm³) : somme signée des volumes tétraédriques (pivot, triangle) des triangles de la région, posé − repos. Invariante par rotation rigide autour du pivot : seule la déformation (perte/gain de volume) sort.
   Région ouverte : l'effet du bord n'est pas nul ; comparer des angles et des options entre eux, pas à une valeur absolue. Aussi le volume total du corps (cm³, fermé aux orifices près) posé − repos : dV_corps.
 - section : tranche de sommets (au repos) à une distance s du pivot le long de l'os enfant ; rapport d'axes sqrt(λ2/λ1) (analyse en composantes principales des sommets posés) et rapport d'aire sqrt(λ1·λ2) posé/repos.
   Un rapport d'aire qui s'effondre = « papier de bonbon » ; un rapport d'axes qui baisse = aplatissement.
 - retournées : triangles de la région dont la normale posée s'écarte de plus de 90° de la normale de repos tournée par la rotation RIGIDE de leur os dominant (un triangle qui tourne avec son os n'est pas retourné).
 - torsion (essais de roulis) : rayon moyen posé/repos par tranche le long du membre ; le minimum des tranches = pincement.
Référence de ce qu'on attend d'un membre réel : conservation approximative du volume lors d'un mouvement articulaire — NON VÉRIFIÉ (aucune source lue) ; les valeurs servent à comparer AVANT / APRÈS sur NOTRE modèle.
`--timing 1` : temps d'évaluation par image du corps posé (ms)."""
import json
import math
from pathlib import Path
import sys
import time

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension import human  # noqa: E402
from extension.animation import skeleton  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:]
OUT = Path(ARGS[0])
OUT.mkdir(parents=True, exist_ok=True)
TAG = ARGS[ARGS.index("--tag") + 1] if "--tag" in ARGS else "etat"
PRESERVE = "--preserve" in ARGS and ARGS[ARGS.index("--preserve") + 1] == "1"
TIMING = "--timing" in ARGS and ARGS[ARGS.index("--timing") + 1] == "1"
ALL = {"defaut": {}, "femme_jeune": {"sex": 1.0, "age": 1.0}, "homme_age": {"sex": 0.0, "age": 3.0}}
MORPHS = {k: ALL[k] for k in (ARGS[ARGS.index("--morphs") + 1].split(",") if "--morphs" in ARGS else ALL)}
SIDE = "L"
CSMOOTH = ARGS[ARGS.index("--csmooth") + 1] if "--csmooth" in ARGS else None  # "facteur,iterations" : modificateur Corrective Smooth après l'armature (essai)
WEIGHT_SMOOTH = ARGS[ARGS.index("--wsmooth") + 1] if "--wsmooth" in ARGS else None  # "iterations,facteur" : lissage des poids (essai, voir weight_fix)
EXTRA = ("HL Corrective", "HL Rig DQS")
addon.register()
if "--dqsextra" in ARGS:  # essai : bases d'os supplémentaires en quaternions duals (ex. arm_upper,arm_upper_twist,clavicle)
    _extra = tuple(ARGS[ARGS.index("--dqsextra") + 1].split(","))
    _orig = skeleton.in_dqs_zone
    skeleton.in_dqs_zone = lambda name: _orig(name) or name.split(".")[0] in _extra
if "--wsmooth" in ARGS:  # "iterations,facteur,rayon" : lissage des poids de l'épaule
    _v = ARGS[ARGS.index("--wsmooth") + 1].split(",")
    skeleton.SHOULDER_SMOOTH = (int(_v[0]), float(_v[1]), float(_v[2]))
if "--notwist" in ARGS:
    skeleton.attach_twist = lambda armature: None
if "--noredist" in ARGS:
    skeleton.redistribute_distal = lambda n, i, w, p, t: (i, w)


def evaluate_cage(body):
    saved = [(m, m.show_viewport) for m in body.modifiers]
    for m in body.modifiers:
        m.show_viewport = m.name in (human.MODIFIER_NAME, skeleton.MODIFIER_NAME) + EXTRA
    human.touch(body)
    bpy.context.view_layer.update()
    evaluated = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    points = np.array([v.co[:] for v in mesh.vertices])
    evaluated.to_mesh_clear()
    for m, state in saved:
        m.show_viewport = state
    return points


def volume(points, triangles, origin=None):
    p = points - (origin if origin is not None else 0.0)
    return float(np.einsum("ij,ij->i", p[triangles[:, 0]], np.cross(p[triangles[:, 1]], p[triangles[:, 2]])).sum() / 6.0)


def set_pose(rig, values):
    for bone in rig.pose.bones:
        bone.rotation_mode = "XYZ"
        bone.rotation_euler = (0.0, 0.0, 0.0)
    for name, euler in values.items():
        rig.pose.bones[name].rotation_euler = euler
    bpy.context.view_layer.update()


def head_pos(rig, name):
    return np.array((rig.matrix_world @ rig.pose.bones[name].head)[:])


def tail_pos(rig, name):
    return np.array((rig.matrix_world @ rig.pose.bones[name].tail)[:])


def pick_sign(rig, name, axis, metric):
    """Sens de rotation (±1) de `name` autour de `axis` pour lequel `metric()` (une valeur à MINIMISER) baisse le plus."""
    best = {}
    for sign in (1.0, -1.0):
        e = [0.0, 0.0, 0.0]
        e[axis] = sign * math.radians(40)
        set_pose(rig, {name: tuple(e)})
        best[sign] = metric()
    set_pose(rig, {})
    return 1.0 if best[1.0] <= best[-1.0] else -1.0


def rot(axis, degrees):
    e = [0.0, 0.0, 0.0]
    e[axis] = math.radians(degrees)
    return tuple(e)


def build_joints(rig):
    """Définition des articulations : os pivot, os enfant (axe), rayon de région, distances de tranche, essais et angles. Les signes sont mesurés sur CE corps."""
    s = SIDE
    shoulder_head = lambda: head_pos(rig, f"arm_upper.{s}")  # noqa: E731
    sign_elbow = pick_sign(rig, f"arm_lower.{s}", 0, lambda: float(np.linalg.norm(tail_pos(rig, f"arm_lower.{s}") - shoulder_head())))
    sign_shoulder = pick_sign(rig, f"arm_upper.{s}", 2, lambda: -float(tail_pos(rig, f"arm_upper.{s}")[2]))
    clav = {}
    for axis in (0, 2):
        for sign in (1.0, -1.0):
            e = [0.0, 0.0, 0.0]
            e[axis] = sign * math.radians(20)
            set_pose(rig, {f"clavicle.{s}": tuple(e)})
            clav[(axis, sign)] = float(head_pos(rig, f"arm_upper.{s}")[2])
    set_pose(rig, {})
    clav_axis, clav_sign = max(clav, key=clav.get)  # rotation de la clavicule qui monte l'épaule
    sign_knee = pick_sign(rig, f"leg_lower.{s}", 0, lambda: float(np.linalg.norm(tail_pos(rig, f"leg_lower.{s}") - head_pos(rig, f"leg_upper.{s}"))))
    sign_hip = pick_sign(rig, f"leg_upper.{s}", 0, lambda: float(head_pos(rig, f"leg_lower.{s}")[1]))  # genou vers l'avant (−y)
    sign_wrist = pick_sign(rig, f"hand.{s}", 0, lambda: float(tail_pos(rig, f"hand.{s}")[1]))  # flexion palmaire : vers l'avant (−y)
    return {
        "coude": {"pivot": f"arm_lower.{s}", "axe_os": f"arm_lower.{s}", "R": 0.12, "tranches": (0.0, 0.04), "angles": [0, 45, 90, 120, 150], "pose": lambda a: {f"arm_lower.{s}": rot(0, sign_elbow * a)}},
        "epaule_levee": {"pivot": f"arm_upper.{s}", "axe_os": f"arm_upper.{s}", "R": 0.14, "tranches": (0.05,), "angles": [0, 45, 90, 135, 180], "pose": lambda a: {f"arm_upper.{s}": rot(2, sign_shoulder * a)}},
        "epaule_rythme": {"pivot": f"arm_upper.{s}", "axe_os": f"arm_upper.{s}", "R": 0.14, "tranches": (0.05,), "angles": [0, 45, 90, 135, 180],
                          "pose": lambda a: {f"arm_upper.{s}": rot(2, sign_shoulder * a * 2 / 3), f"clavicle.{s}": rot(clav_axis, clav_sign * a / 3)}},  # rythme scapulo-huméral 2:1 (règle courante de rig : 2/3 gléno-huméral, 1/3 clavicule/omoplate) : NON VÉRIFIÉ ici
        "epaule_rotation": {"pivot": f"arm_upper.{s}", "axe_os": f"arm_upper.{s}", "R": 0.14, "tranches": (0.05,), "angles": [-60, 0, 60], "pose": lambda a: {f"arm_upper.{s}": rot(1, a)}},
        "genou": {"pivot": f"leg_lower.{s}", "axe_os": f"leg_lower.{s}", "R": 0.14, "tranches": (0.0, 0.05), "angles": [0, 45, 90, 135], "pose": lambda a: {f"leg_lower.{s}": rot(0, sign_knee * a)}},
        "hanche": {"pivot": f"leg_upper.{s}", "axe_os": f"leg_upper.{s}", "R": 0.16, "tranches": (0.06,), "angles": [0, 45, 90], "pose": lambda a: {f"leg_upper.{s}": rot(0, sign_hip * a)}},
        "poignet": {"pivot": f"hand.{s}", "axe_os": f"hand.{s}", "R": 0.07, "tranches": (0.0,), "angles": [-45, 0, 45], "pose": lambda a: {f"hand.{s}": rot(0, sign_wrist * a)}},
        "cou_flexion": {"pivot": "neck.01", "axe_os": "neck.02", "R": 0.10, "tranches": (0.0,), "angles": [0, 30, 45, 70], "pose": lambda a: {"neck.01": rot(0, a / 3), "neck.02": rot(0, a / 3), "head": rot(0, a / 3)}},
    }


# essais de torsion : (nom, pose, os dont l'axe sert de référence, rayon max, tranches le long du membre)
def build_twists(rig):
    s = SIDE
    return {
        "torsion_avant_bras_90": {"pose": {f"hand.{s}": rot(1, 90)}, "membre": f"arm_lower.{s}", "R": 0.08},
        "torsion_bras_90": {"pose": {f"arm_upper.{s}": rot(1, 90)}, "membre": f"arm_upper.{s}", "R": 0.10},
        "torsion_cuisse_60": {"pose": {f"leg_upper.{s}": rot(1, 60)}, "membre": f"leg_upper.{s}", "R": 0.12},
        "torsion_jambe_60": {"pose": {f"foot.{s}": rot(1, 60)}, "membre": f"leg_lower.{s}", "R": 0.09},
    }


def run_morph(label, values):
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.ops.humanloom.create()
    body = bpy.context.object
    for name, value in values.items():
        human.set_value(body, name, value)
    rig = skeleton.install(body)
    if PRESERVE:
        body.modifiers[skeleton.MODIFIER_NAME].use_deform_preserve_volume = True
    if "--maskmode" in ARGS:  # essai : tout en quaternions duals (all) ou tout en linéaire (none)
        mode = ARGS[ARGS.index("--maskmode") + 1]
        everything = list(range(len(body.data.vertices)))
        body.vertex_groups[skeleton.GROUP_DQS].add(everything, 1.0 if mode == "all" else 0.0, "REPLACE")
        body.vertex_groups[skeleton.GROUP_LBS].add(everything, 0.0 if mode == "all" else 1.0, "REPLACE")
    if CSMOOTH:
        factor, iterations = CSMOOTH.split(",")
        modifier = body.modifiers.new("HL Corrective", "CORRECTIVE_SMOOTH")
        modifier.factor, modifier.iterations, modifier.rest_source, modifier.smooth_type = float(factor), int(iterations), "ORCO", "SIMPLE"
        modifier.use_only_smooth = False
        body.modifiers.move(len(body.modifiers) - 1, list(body.modifiers).index(body.modifiers[skeleton.MODIFIER_NAME]) + 1)
    for bone in rig.pose.bones:
        bone.rotation_mode = "XYZ"
    mesh = body.data
    mesh.calc_loop_triangles()
    triangles = np.array([t.vertices[:] for t in mesh.loop_triangles])
    set_pose(rig, {})
    rest = evaluate_cage(body)

    def normals_of(points):
        n = np.cross(points[triangles[:, 1]] - points[triangles[:, 0]], points[triangles[:, 2]] - points[triangles[:, 0]])
        return n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-18)

    rest_n = normals_of(rest)
    rest_area = np.linalg.norm(np.cross(rest[triangles[:, 1]] - rest[triangles[:, 0]], rest[triangles[:, 2]] - rest[triangles[:, 0]]), axis=1) / 2
    groups = {g.index: g.name for g in body.vertex_groups}
    dominant = []
    for v in mesh.vertices:
        candidates = [g for g in v.groups if groups[g.group] not in (skeleton.GROUP_LBS, skeleton.GROUP_DQS)]  # les masques de modificateurs ne sont pas des os
        best = max(candidates, key=lambda g: g.weight) if candidates else None
        dominant.append(groups[best.group] if best else "")
    vertex_bone = np.array(dominant)
    tri_bone = vertex_bone[triangles[:, 0]]
    rest_matrices = {b.name: np.array(b.matrix_local.to_3x3()) for b in rig.data.bones}
    total_rest = volume(rest, triangles)
    results = {}

    def bone_rotations():
        return {b.name: np.array(b.matrix.to_3x3()) @ np.linalg.inv(rest_matrices[b.name]) for b in rig.pose.bones}

    for joint, spec in build_joints(rig).items():
        pivot = np.array(rig.data.bones[spec["pivot"]].head_local)
        axis_bone = rig.data.bones[spec["axe_os"]]
        axis_head, axis_tail = np.array(axis_bone.head_local), np.array(axis_bone.tail_local)
        u = (axis_tail - axis_head) / np.linalg.norm(axis_tail - axis_head)
        region = np.linalg.norm(rest - pivot, axis=1) < spec["R"]
        tri_in = region[triangles].all(1)
        rest_local = volume_region = None
        v_rest_local = float(np.einsum("ij,ij->i", (rest[triangles[tri_in, 0]] - pivot), np.cross(rest[triangles[tri_in, 1]] - pivot, rest[triangles[tri_in, 2]] - pivot)).sum() / 6.0)
        sections = {}
        for distance in spec["tranches"]:
            t = (rest - axis_head) @ u
            radial = np.linalg.norm((rest - axis_head) - np.outer(t, u), axis=1)
            offset = (pivot - axis_head) @ u
            sel = np.where((np.abs(t - offset - distance) < 0.01) & (radial < 0.11))[0]
            sections[distance] = sel

        def section_numbers(points, sel):
            c = points[sel] - points[sel].mean(0)
            eig = np.sort(np.linalg.eigvalsh(c.T @ c / len(sel)))[::-1]
            return math.sqrt(max(eig[1], 1e-18) / max(eig[0], 1e-18)), math.sqrt(max(eig[0] * eig[1], 1e-18))

        rest_sections = {d: section_numbers(rest, sel) for d, sel in sections.items() if len(sel) >= 8}
        rows = {}
        for angle in spec["angles"]:
            set_pose(rig, spec["pose"](angle))
            points = evaluate_cage(body)
            rotations = bone_rotations()
            local = float(np.einsum("ij,ij->i", (points[triangles[tri_in, 0]] - pivot), np.cross(points[triangles[tri_in, 1]] - pivot, points[triangles[tri_in, 2]] - pivot)).sum() / 6.0) - v_rest_local
            n = normals_of(points)
            expected = np.array([rotations.get(b, np.eye(3)) @ rest_n[i] for i, b in enumerate(tri_bone)]) if False else None
            flips = 0
            idx = np.where(tri_in & (rest_area > 1e-10))[0]
            for i in idx:
                predicted = rotations.get(tri_bone[i], np.eye(3)) @ rest_n[i]
                if float(n[i] @ predicted) < 0.0:
                    flips += 1
            row = {"dV_local_cm3": round(local * 1e6, 2), "dV_corps_cm3": round((volume(points, triangles) - total_rest) * 1e6, 1), "retournees": flips}
            for d, sel in sections.items():
                if d in rest_sections:
                    ratio, area = section_numbers(points, sel)
                    row[f"section_{d:.2f}"] = {"rapport_axes": round(ratio, 3), "rapport_axes_repos": round(rest_sections[d][0], 3), "aire_sur_repos": round(area / rest_sections[d][1], 3)}
            rows[str(angle)] = row
        results[joint] = rows
        set_pose(rig, {})
        print("ARTICULATION", TAG, label, joint, json.dumps(rows, ensure_ascii=False), flush=True)

    # torsions : rayon moyen posé/repos par tranche le long du membre
    for name, spec in build_twists(rig).items():
        bone = rig.data.bones[spec["membre"]]
        head, tail = np.array(bone.head_local), np.array(bone.tail_local)
        length = float(np.linalg.norm(tail - head))
        u = (tail - head) / length
        t = (rest - head) @ u / length
        radial = np.linalg.norm((rest - head) - np.outer((rest - head) @ u, u), axis=1)
        bins = [np.where((t >= lo) & (t < lo + 0.1) & (radial < spec["R"]))[0] for lo in np.arange(0.0, 1.0, 0.1)]
        set_pose(rig, spec["pose"])
        points = evaluate_cage(body)
        ratios = []
        for sel in bins:
            if len(sel) < 6:
                ratios.append(None)
                continue
            r0 = float(np.linalg.norm((rest[sel] - head) - np.outer((rest[sel] - head) @ u, u), axis=1).mean())
            r1 = float(np.linalg.norm((points[sel] - head) - np.outer((points[sel] - head) @ u, u), axis=1).mean())
            ratios.append(round(r1 / r0, 3))
        valid = [r for r in ratios if r is not None]
        flips_zone = 0
        rotations = bone_rotations()
        n = normals_of(points)
        in_limb = np.isin(np.arange(len(rest)), np.concatenate([b for b in bins if len(b)]))
        for i in np.where(in_limb[triangles].all(1) & (rest_area > 1e-10))[0]:
            if float(n[i] @ (rotations.get(tri_bone[i], np.eye(3)) @ rest_n[i])) < 0.0:
                flips_zone += 1
        results[name] = {"rayon_pose_sur_repos_par_tranche": ratios, "pincement_min": min(valid), "retournees": flips_zone}
        set_pose(rig, {})
        print("TORSION", TAG, label, name, json.dumps(results[name], ensure_ascii=False), flush=True)

    if TIMING:
        set_pose(rig, {f"arm_lower.{SIDE}": rot(0, 90), f"leg_lower.{SIDE}": rot(0, 90)})
        evaluate_cage(body)
        start = time.perf_counter()
        for k in range(10):
            rig.pose.bones[f"arm_lower.{SIDE}"].rotation_euler = rot(0, 90 + k)
            evaluate_cage(body)
        results["temps_evaluation_ms"] = round((time.perf_counter() - start) * 100.0, 1)
        print("TEMPS", TAG, label, results["temps_evaluation_ms"], flush=True)
        set_pose(rig, {})
    return results


allrows = {label: run_morph(label, values) for label, values in MORPHS.items()}
(OUT / f"articulations_{TAG}.json").write_text(json.dumps(allrows, indent=1, ensure_ascii=False), encoding="utf-8")
