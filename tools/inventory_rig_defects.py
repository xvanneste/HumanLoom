"""Inventaire mesuré des défauts articulaires du rig (référence AVANT correctifs de pose) : épaule (3 plans + rotations), clavicule, coude, avant-bras, poignet, hanche (flexion, abduction, rotation), genou, cheville,
cou, tronc (flexion, torsion, inclinaison), sur plusieurs morphologies. LECTURE SEULE sur l'extension (aucune modification de `extension/`).

  blender --background --factory-startup --offline-mode --python-exit-code 0 --python tools/inventory_rig_defects.py -- DOSSIER_DE_SORTIE [--tag base] [--morphs defaut,femme_jeune,homme_age,gabarit,inverse]

Critères chiffrés (CONCEPTION_RIG_CORRECTIFS.md §1) évalués pour chaque famille de poses et chaque angle, sur le pire des deux sens de rotation physiologiquement plausibles :
 - aire de section (tranche perpendiculaire à l'os enfant, rapport aire posée / aire de repos, valeurs hors du sommet) : ≥ 0,85 et ≤ 1,10 (pas d'effondrement, pas de bosse > +10 %) ;
 - aire de surface de la région (somme des aires des triangles de la région, posé / repos) dans [0,85 ; 1,10] (généralisation pour les régions sans tranche : tronc, cou, clavicule) ;
 - pincement (poses de roulis) : rayon moyen posé / repos par tranche, minimum ≥ 0,9 ;
 - faces retournées dans la région (normale posée à plus de 90° de la normale de repos tournée par la rotation RIGIDE de l'os dominant) : ≤ 2 ;
 - arêtes étirées : rapport maximal d'une arête de la région < 3 (R6 : 3,5 pour les flexions à 90°).
Les sens (± d'un axe) sont ESSAYÉS tous les deux ; seuls les angles physiologiquement plausibles sont gardés (liste par famille). Aucune amplitude publiée n'a été lue : les amplitudes sont des choix de test, pas des normes."""
import json
import math
from pathlib import Path
import sys

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
TAG = ARGS[ARGS.index("--tag") + 1] if "--tag" in ARGS else "base"
ALL = {"defaut": {}, "femme_jeune": {"sex": 1.0, "age": 1.0}, "homme_age": {"sex": 0.0, "age": 3.0}, "gabarit": {"legs": 1.0, "torso": -1.0}, "inverse": {"legs": -1.0, "torso": 1.0}}
MORPHS = {k: ALL[k] for k in (ARGS[ARGS.index("--morphs") + 1].split(",") if "--morphs" in ARGS else ["defaut", "femme_jeune", "homme_age"])}
THRESHOLDS = {"aire_min": 0.85, "aire_max": 1.10, "pincement_min": 0.90, "retournees_max": 2, "etirement_max": 3.0}
S = "L"
addon.register()


def evaluate(body):
    saved = [(m, m.show_viewport) for m in body.modifiers]
    for m in body.modifiers:
        m.show_viewport = m.name in (human.MODIFIER_NAME, skeleton.MODIFIER_NAME, getattr(skeleton, "DQS_MODIFIER", ""))
    human.touch(body)
    bpy.context.view_layer.update()
    ev = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = ev.to_mesh()
    points = np.array([v.co[:] for v in mesh.vertices])
    ev.to_mesh_clear()
    for m, state in saved:
        m.show_viewport = state
    return points


def rot(axis, degrees):
    e = [0.0, 0.0, 0.0]
    e[axis] = math.radians(degrees)
    return tuple(e)


def euler(x=0.0, y=0.0, z=0.0):
    return (math.radians(x), math.radians(y), math.radians(z))


def run_morph(label, values):
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.ops.humanloom.create()
    body = bpy.context.object
    for name, value in values.items():
        human.set_value(body, name, value)
    rig = skeleton.install(body)
    for bone in rig.pose.bones:
        bone.rotation_mode = "XYZ"
    mesh = body.data
    mesh.calc_loop_triangles()
    tris = np.array([t.vertices[:] for t in mesh.loop_triangles])
    edges = np.array([e.vertices[:] for e in mesh.edges])
    groups = {g.index: g.name for g in body.vertex_groups}
    masks = {skeleton.GROUP_LBS, skeleton.GROUP_DQS} if hasattr(skeleton, "GROUP_LBS") else set()
    dominant = []
    for v in mesh.vertices:
        c = [g for g in v.groups if groups[g.group] not in masks]
        dominant.append(groups[max(c, key=lambda g: g.weight).group] if c else "")
    tri_bone = np.array(dominant)[tris[:, 0]]
    rest_local = {b.name: np.array(b.matrix_local.to_3x3()) for b in rig.data.bones}

    def pose(values_):
        for b in rig.pose.bones:
            b.rotation_euler = (0.0, 0.0, 0.0)
        for name, e in values_.items():
            rig.pose.bones[name].rotation_euler = e
        bpy.context.view_layer.update()

    pose({})
    rest = evaluate(body)

    def normals(p):
        n = np.cross(p[tris[:, 1]] - p[tris[:, 0]], p[tris[:, 2]] - p[tris[:, 0]])
        a = np.linalg.norm(n, axis=1)
        return n / np.maximum(a[:, None], 1e-18), a / 2

    rest_n, rest_a = normals(rest)
    rest_len = np.linalg.norm(rest[edges[:, 0]] - rest[edges[:, 1]], axis=1)

    def head(name):
        return np.array(rig.data.bones[name].head_local)

    def world_head(name):
        return np.array((rig.matrix_world @ rig.pose.bones[name].head)[:])

    def world_tail(name):
        return np.array((rig.matrix_world @ rig.pose.bones[name].tail)[:])

    def section(points, axis_bone, pivot_bone, distance):
        b = rig.data.bones[axis_bone]
        h, t = np.array(b.head_local), np.array(b.tail_local)
        u = (t - h) / np.linalg.norm(t - h)
        s = (rest - h) @ u
        offset = (head(pivot_bone) - h) @ u
        radial = np.linalg.norm((rest - h) - np.outer(s, u), axis=1)
        sel = np.where((np.abs(s - offset - distance) < 0.01) & (radial < 0.11))[0]
        return sel

    def area_of(points, sel):
        c = points[sel] - points[sel].mean(0)
        eig = np.sort(np.linalg.eigvalsh(c.T @ c / len(sel)))[::-1]
        return math.sqrt(max(eig[0] * eig[1], 1e-18))

    # familles : (nom, os pivot, os de l'axe de section, distance de section, rayon de région, liste (angle, pose) par sens)
    def hinge_sign(bone, axis, metric):
        scores = {}
        for sign in (1.0, -1.0):
            e = [0.0, 0.0, 0.0]
            e[axis] = math.radians(40 * sign)
            pose({bone: tuple(e)})
            scores[sign] = metric()
        pose({})
        return 1.0 if scores[1.0] <= scores[-1.0] else -1.0

    f = {}
    # épaule : sagittal (flexion vers l'avant), frontal (abduction), intermédiaire (plan de l'omoplate, 45°)
    sg = hinge_sign(f"arm_upper.{S}", 0, lambda: float(world_tail(f"arm_upper.{S}")[1]))  # le coude va vers l'avant (−y) : minimise y
    fr = hinge_sign(f"arm_upper.{S}", 2, lambda: -float(world_tail(f"arm_upper.{S}")[2]))  # le coude monte
    sh = dict(pivot=f"arm_upper.{S}", axis=f"arm_upper.{S}", dist=0.05, R=0.14)
    f["epaule_sagittal"] = dict(sh, angles=[0, 45, 90, 135, 180], pose=lambda a: {f"arm_upper.{S}": rot(0, sg * a)})
    f["epaule_frontal"] = dict(sh, angles=[0, 45, 90, 135, 180], pose=lambda a: {f"arm_upper.{S}": rot(2, fr * a)})
    f["epaule_intermediaire"] = dict(sh, angles=[0, 45, 90, 135, 180], pose=lambda a: {f"arm_upper.{S}": euler(sg * a * 0.7071, 0, fr * a * 0.7071)})
    f["epaule_extension"] = dict(sh, angles=[0, 30, 60], pose=lambda a: {f"arm_upper.{S}": rot(0, -sg * a)})
    f["epaule_rotation_neutre"] = dict(sh, angles=[-60, -30, 0, 30, 60, 90], pose=lambda a: {f"arm_upper.{S}": rot(1, a)}, roll=True)
    f["epaule_rotation_levee90"] = dict(sh, angles=[-60, 0, 60], pose=lambda a: {f"arm_upper.{S}": euler(0, a, fr * 90)})
    # clavicule
    clav = dict(pivot=f"clavicle.{S}", axis=f"clavicle.{S}", dist=0.04, R=0.13)
    f["clavicule_x"] = dict(clav, angles=[-15, 0, 15, 30], pose=lambda a: {f"clavicle.{S}": rot(0, a)})
    f["clavicule_z"] = dict(clav, angles=[-15, 0, 15, 30], pose=lambda a: {f"clavicle.{S}": rot(2, a)})
    # coude, avant-bras, poignet
    ce = hinge_sign(f"arm_lower.{S}", 0, lambda: float(np.linalg.norm(world_tail(f"arm_lower.{S}") - world_head(f"arm_upper.{S}"))))
    f["coude_flexion"] = dict(pivot=f"arm_lower.{S}", axis=f"arm_lower.{S}", dist=0.0, R=0.12, angles=[0, 45, 90, 120, 150], pose=lambda a: {f"arm_lower.{S}": rot(0, ce * a)})
    f["avant_bras_torsion"] = dict(pivot=f"arm_lower.{S}", axis=f"arm_lower.{S}", dist=0.12, R=0.12, angles=[-90, -45, 0, 45, 90], pose=lambda a: {f"hand.{S}": rot(1, a)}, roll=True, limb=f"arm_lower.{S}")
    wsign = hinge_sign(f"hand.{S}", 0, lambda: float(world_tail(f"hand.{S}")[1]))
    f["poignet_flexion"] = dict(pivot=f"hand.{S}", axis=f"hand.{S}", dist=0.0, R=0.07, angles=[-60, -30, 0, 30, 60], pose=lambda a: {f"hand.{S}": rot(0, wsign * a)})
    f["poignet_deviation"] = dict(pivot=f"hand.{S}", axis=f"hand.{S}", dist=0.0, R=0.07, angles=[-20, 0, 20, 30], pose=lambda a: {f"hand.{S}": rot(2, a)})
    # hanche
    hs = hinge_sign(f"leg_upper.{S}", 0, lambda: float(world_head(f"leg_lower.{S}")[1]))
    ha = hinge_sign(f"leg_upper.{S}", 2, lambda: -abs(float(world_head(f"leg_lower.{S}")[0])) + 0.0 * 1)  # le genou s'écarte
    hip = dict(pivot=f"leg_upper.{S}", axis=f"leg_upper.{S}", dist=0.06, R=0.16)
    f["hanche_flexion"] = dict(hip, angles=[0, 45, 90, 120], pose=lambda a: {f"leg_upper.{S}": rot(0, hs * a)})
    f["hanche_extension"] = dict(hip, angles=[0, 15, 30], pose=lambda a: {f"leg_upper.{S}": rot(0, -hs * a)})
    f["hanche_abduction"] = dict(hip, angles=[0, 20, 45], pose=lambda a: {f"leg_upper.{S}": rot(2, ha * a)})
    f["hanche_rotation"] = dict(hip, angles=[-45, -20, 0, 20, 45], pose=lambda a: {f"leg_upper.{S}": rot(1, a)}, roll=True, limb=f"leg_upper.{S}")
    f["hanche_flexion_abduction"] = dict(hip, angles=[0, 45, 90], pose=lambda a: {f"leg_upper.{S}": euler(hs * a, 0, ha * a / 3)})
    # genou, cheville
    ks = hinge_sign(f"leg_lower.{S}", 0, lambda: float(np.linalg.norm(world_tail(f"leg_lower.{S}") - world_head(f"leg_upper.{S}"))))
    f["genou_flexion"] = dict(pivot=f"leg_lower.{S}", axis=f"leg_lower.{S}", dist=0.0, R=0.14, angles=[0, 45, 90, 135], pose=lambda a: {f"leg_lower.{S}": rot(0, ks * a)})
    f["cheville"] = dict(pivot=f"foot.{S}", axis=f"leg_lower.{S}", dist=0.30, R=0.10, angles=[-30, -15, 0, 15, 30], pose=lambda a: {f"foot.{S}": rot(0, a)})
    # cou, tronc
    neck = dict(pivot="neck.01", axis="neck.02", dist=0.0, R=0.10)
    f["cou_flexion"] = dict(neck, angles=[-30, 0, 30, 45, 70], pose=lambda a: {"neck.01": rot(0, a / 3), "neck.02": rot(0, a / 3), "head": rot(0, a / 3)})
    f["cou_rotation"] = dict(neck, angles=[-60, -30, 0, 30, 60], pose=lambda a: {"neck.01": rot(1, a / 3), "neck.02": rot(1, 2 * a / 3)})
    f["cou_inclinaison"] = dict(neck, angles=[-30, 0, 30], pose=lambda a: {"neck.01": rot(2, a / 3), "neck.02": rot(2, a / 3), "head": rot(2, a / 3)})
    trunk = dict(pivot="spine.03", axis="spine.03", dist=0.0, R=0.22)
    f["tronc_flexion"] = dict(trunk, angles=[-20, 0, 20, 45], pose=lambda a: {"spine.02": rot(0, a / 3), "spine.03": rot(0, a / 3), "spine.04": rot(0, a / 3)})
    f["tronc_torsion"] = dict(trunk, angles=[-45, -20, 0, 20, 45], pose=lambda a: {"spine.02": rot(1, a / 3), "spine.03": rot(1, a / 3), "spine.04": rot(1, a / 3)})
    f["tronc_inclinaison"] = dict(trunk, angles=[-30, -15, 0, 15, 30], pose=lambda a: {"spine.02": rot(2, a / 3), "spine.03": rot(2, a / 3), "spine.04": rot(2, a / 3)})

    results = {}
    for name, spec in f.items():
        pivot = head(spec["pivot"])
        region = np.linalg.norm(rest - pivot, axis=1) < spec["R"]
        tri_in = region[tris].all(1) & (rest_a > 1e-10)
        edge_in = region[edges].all(1)
        sel = section(rest, spec["axis"], spec["pivot"], spec["dist"])
        rest_section = area_of(rest, sel) if len(sel) >= 8 else None
        rest_surface = float(rest_a[tri_in].sum())
        rows = {}
        limb_bins = None
        if spec.get("roll"):
            lb = rig.data.bones[spec.get("limb", spec["axis"])]
            lh, lt = np.array(lb.head_local), np.array(lb.tail_local)
            length = float(np.linalg.norm(lt - lh))
            lu = (lt - lh) / length
            t = (rest - lh) @ lu / length
            rad = np.linalg.norm((rest - lh) - np.outer((rest - lh) @ lu, lu), axis=1)
            limb_bins = [np.where((t >= lo) & (t < lo + 0.1) & (rad < 0.11))[0] for lo in np.arange(0.0, 1.0, 0.1)]
        for angle in spec["angles"]:
            pose(spec["pose"](angle))
            pts = evaluate(body)
            n, a = normals(pts)
            rotations = {b.name: np.array(b.matrix.to_3x3()) @ np.linalg.inv(rest_local[b.name]) for b in rig.pose.bones}
            flips = 0
            for i in np.where(tri_in)[0]:
                if float(n[i] @ (rotations.get(tri_bone[i], np.eye(3)) @ rest_n[i])) < 0.0:
                    flips += 1
            stretch = float((np.linalg.norm(pts[edges[edge_in][:, 0]] - pts[edges[edge_in][:, 1]], axis=1) / np.maximum(rest_len[edge_in], 1e-9)).max())
            row = {"retournees": flips, "etirement_max": round(stretch, 2), "aire_surface": round(float(a[tri_in].sum()) / rest_surface, 3)}
            if rest_section is not None:
                row["aire_section"] = round(area_of(pts, sel) / rest_section, 3)
            if limb_bins is not None:
                ratios = []
                for b in limb_bins:
                    if len(b) >= 6:
                        r0 = np.linalg.norm((rest[b] - lh) - np.outer((rest[b] - lh) @ lu, lu), axis=1).mean()
                        r1 = np.linalg.norm((pts[b] - lh) - np.outer((pts[b] - lh) @ lu, lu), axis=1).mean()
                        ratios.append(r1 / r0)
                row["pincement_min"] = round(float(min(ratios)), 3)
            rows[str(angle)] = row
        pose({})
        results[name] = rows
    # verdicts
    verdict = {}
    for name, rows in results.items():
        bad = []
        for angle, r in rows.items():
            fails = []
            if r["retournees"] > THRESHOLDS["retournees_max"]:
                fails.append("retournees")
            if r["etirement_max"] >= THRESHOLDS["etirement_max"]:
                fails.append("etirement")
            for key in ("aire_section", "aire_surface"):
                if key in r and not (THRESHOLDS["aire_min"] <= r[key] <= THRESHOLDS["aire_max"]):
                    fails.append(key)
            if "pincement_min" in r and r["pincement_min"] < THRESHOLDS["pincement_min"]:
                fails.append("pincement")
            if fails:
                bad.append({"angle": angle, "criteres": fails})
        verdict[name] = bad
    print("INVENTAIRE", TAG, label, json.dumps({"hors_critere": {k: [b["angle"] + ":" + "+".join(b["criteres"]) for b in v] for k, v in verdict.items() if v}}, ensure_ascii=False), flush=True)
    return {"mesures": results, "hors_critere": verdict}


data = {label: run_morph(label, values) for label, values in MORPHS.items()}
data["seuils"] = THRESHOLDS
(OUT / f"inventaire_{TAG}.json").write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
print("FINI")
