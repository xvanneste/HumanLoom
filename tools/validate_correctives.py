"""Validation des formes correctives des articulations à charnière (coude, genou) : installation/retrait, pilotes simples, lecture de l'angle, amélioration des critères HORS ENTRAÎNEMENT sur 5 morphologies (données livrées puis recalcul
sur la morphologie), visage inchangé, coût, foule.

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/validate_correctives.py -- [--out FICHIER.json] [--morphs defaut,...] [--data FICHIER.npz] [--debug 1] [--rebuild homme_age|none]

C1 installation (clés, propriétés, pilotes à expression simple) et retrait sans résidu ; C2 lecture de l'angle (±0,5°) ; C3 critères de rig_metrics (plis nouveaux, étirement, aire de section, zone proche) aux angles HORS entraînement avec les
données livrées : plis cumulés ≥ 2× moins sur l'ensemble des morphologies ET ≥ 3× moins sur le corps par défaut ; C4 visage inchangé (0,000 mm) ; C5 coût (ratio ≤ 1,30) ; C6 la foule n'installe pas de correctifs ; C7 recalcul sur une morphologie
(statut a_jour puis obsolète, plis cumulés ≥ 3× moins)."""
import json
import math
from pathlib import Path
import sys
import time

import bpy
import numpy as np
from mathutils import Quaternion

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import extension as addon  # noqa: E402
from extension import human  # noqa: E402
from extension.animation import correctives, skeleton  # noqa: E402
import rig_metrics as M  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = ARGS[ARGS.index("--out") + 1] if "--out" in ARGS else None
ALL = {"defaut": {}, "femme_jeune": {"sex": 1.0, "age": 1.0}, "homme_age": {"sex": 0.0, "age": 3.0}, "gabarit": {"legs": 1.0, "torso": -1.0}, "inverse": {"legs": -1.0, "torso": 1.0}}
MORPHS = {k: ALL[k] for k in (ARGS[ARGS.index("--morphs") + 1].split(",") if "--morphs" in ARGS else ALL)}
REBUILD = ARGS[ARGS.index("--rebuild") + 1] if "--rebuild" in ARGS else "homme_age"
TEST_ANGLES = {"coude": [22, 52, 97, 128, 142], "genou": [22, 52, 97, 120, 130]}
results, failures = {}, []


def check(name, ok, detail=None):
    results[name] = {"ok": bool(ok), "detail": detail}
    print(("OK  " if ok else "KO  ") + name, json.dumps(detail, ensure_ascii=False, default=str)[:700] if detail is not None else "")
    if not ok:
        failures.append(name)


addon.register()
if "--data" in ARGS:
    correctives.DATA = Path(ARGS[ARGS.index("--data") + 1])


def fresh(values=None, correctives_on=True):
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.ops.humanloom.create()
    body = bpy.context.object
    for name, value in (values or {}).items():
        human.set_value(body, name, value)
    rig = skeleton.install(body, correctives=correctives_on)
    body.modifiers["Human Modeling · Surface"].show_viewport = False
    return body, rig


def evaluate(body):
    return correctives._evaluate(body)


def set_flexion(rig, label, angle, sign):
    joint, side = label.split("_")
    bone = rig.pose.bones[f"{correctives.BONES[joint]}.{side}"]
    for b in rig.pose.bones:
        b.rotation_mode = "QUATERNION"
        b.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
    bone.rotation_quaternion = Quaternion((1.0, 0.0, 0.0), math.radians(sign * angle))
    bpy.context.view_layer.update()


def mute(body, state):
    for key in correctives.keys_of(body.data):
        key.mute = state
    bpy.context.view_layer.update()


def measure(body, rig, label_list, signs, debug_morph=None):
    """Critères aux angles de test, avec et sans correctifs (clés muettes) : retourne ({étiquette: {...}}, écart max du visage en mm)."""
    mesh = body.data
    mesh.calc_loop_triangles()
    tris = np.array([t.vertices[:] for t in mesh.loop_triangles])
    edges = np.array([e.vertices[:] for e in mesh.edges])
    groups = {g.index: g.name for g in body.vertex_groups}
    head = np.zeros(len(mesh.vertices), bool)
    dominant = []
    for v in mesh.vertices:
        head[v.index] = any(groups[g.group] in ("head", "jaw") and g.weight > 1e-3 for g in v.groups)
        c = [g for g in v.groups if groups[g.group] not in (skeleton.GROUP_LBS, skeleton.GROUP_DQS)]
        dominant.append(groups[max(c, key=lambda g: g.weight).group] if c else "")
    mute(body, False)
    for b in rig.pose.bones:
        b.rotation_mode = "QUATERNION"
        b.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
    bpy.context.view_layer.update()
    rest = evaluate(body)
    lookup = {b.name: i for i, b in enumerate(rig.pose.bones)}
    tri_bone = np.array(dominant)[tris[:, 0]]
    rest_local = {b.name: np.array(b.matrix_local.to_3x3()) for b in rig.data.bones}
    summary, face_worst = {}, 0.0
    for label in label_list:
        joint, side = label.split("_")
        bone = rig.data.bones[f"{correctives.BONES[joint]}.{side}"]
        pivot, tail = np.array(bone.head_local), np.array(bone.tail_local)
        axis = (tail - pivot) / np.linalg.norm(tail - pivot)
        region = M.Region(rest, tris, edges, pivot, 0.12 if joint == "coude" else 0.14, pivot, axis, 0.0)
        fails, plis, worst = {"sans": 0, "avec": 0}, {"sans": 0, "avec": 0}, {"sans": 0.0, "avec": 0.0}
        for angle in TEST_ANGLES[joint]:
            base_points = None
            for state, muted in (("sans", True), ("avec", False)):
                set_flexion(rig, label, angle, signs[label])
                mute(body, muted)
                points = evaluate(body)
                rot3 = np.array([np.array(b.matrix.to_3x3()) @ np.linalg.inv(rest_local[b.name]) for b in rig.pose.bones])
                tri_rot = np.array([rot3[lookup[n]] if n in lookup else np.eye(3) for n in tri_bone])
                row = region.measure(points, tri_rot)
                if debug_morph and side == "L":
                    print("   ", debug_morph, label, angle, state, row, flush=True)
                fails[state] += int(bool(M.failures(row)) or row["etirement_max"] >= M.THRESHOLDS["etirement_max"])
                plis[state] += row["plis"]
                worst[state] = max(worst[state], row["etirement_max"])
                if state == "sans":
                    base_points = points
                else:
                    face_worst = max(face_worst, float(np.linalg.norm(points - base_points, axis=1)[head].max()) * 1000)
        summary[label] = {"hors_critere": fails, "plis_cumules": plis, "etirement_max": worst}
    mute(body, False)
    return summary, face_worst


def signs_of(data):
    return {label: float(data[f"{label}_sign"]) for label in correctives.labels(data)}


def totals(summary):
    out = {"plis": {"sans": 0, "avec": 0}, "hors_critere": {"sans": 0, "avec": 0}}
    for r in summary.values():
        for s in ("sans", "avec"):
            out["plis"][s] += r["plis_cumules"][s]
            out["hors_critere"][s] += r["hors_critere"][s]
    return out


# C1 installation / retrait
body, rig = fresh()
data = dict(np.load(correctives.DATA, allow_pickle=False))
signs = signs_of(data)
keys = correctives.keys_of(body.data)
drivers = list(body.data.shape_keys.animation_data.drivers) + list(rig.animation_data.drivers)
simple = all(f.driver.is_simple_expression for f in drivers)
props = [k for k in rig.keys() if k.startswith(correctives.PROP_PREFIX)]
check("C1_installation", len(keys) > 30 and len(props) == len(correctives.labels(data)) and simple and correctives.status(body) == "generique",
      {"cles": len(keys), "proprietes": len(props), "pilotes": len(drivers), "expressions_simples": simple, "statut": correctives.status(body)})
skeleton.remove(body)
check("C1b_retrait_sans_residu", body.data.shape_keys is None and not correctives.keys_of(body.data), {"cles_restantes": 0 if body.data.shape_keys is None else len(body.data.shape_keys.key_blocks)})

# C2 lecture de l'angle
body, rig = fresh()
reads = {}
for label in correctives.labels(data):
    set_flexion(rig, label, 90.0, signs[label])
    reads[label] = round(float(rig[correctives.PROP_PREFIX + label]), 2)
check("C2_lecture_de_l_angle", all(abs(v - 90.0) < 0.5 for v in reads.values()), reads)

# C3 / C4 données livrées, morphologies
per_morph, face_worst = {}, 0.0
for morph, values in MORPHS.items():
    body, rig = fresh(values)
    summary, face = measure(body, rig, correctives.labels(data), signs, debug_morph=morph if "--debug" in ARGS else None)
    per_morph[morph] = summary
    face_worst = max(face_worst, face)
    print("MORPH", morph, json.dumps({k: (v["plis_cumules"]["sans"], v["plis_cumules"]["avec"]) for k, v in summary.items()}), flush=True)
merged = {f"{m}:{k}": v for m, s in per_morph.items() for k, v in s.items()}
t_all = totals(merged)
t_default = totals(per_morph["defaut"]) if "defaut" in per_morph else None
check("C3_criteres_hors_entrainement", t_all["plis"]["avec"] <= 0.5 * t_all["plis"]["sans"] and (t_default is None or t_default["plis"]["avec"] <= 0.3 * t_default["plis"]["sans"]),
      {"morphologies": list(per_morph), "tous": t_all, "defaut": t_default, "critere": "plis cumulés ≥ 2× moins sur l'ensemble (données du corps par défaut appliquées à toutes les morphologies) et ≥ 3× moins sur le corps par défaut ; « plis ≤ 2 » strict rapporté, non exigé"})
check("C4_visage_inchange", face_worst < 1e-6, {"ecart_max_visage_mm": face_worst})

# C5 coût d'évaluation
body, rig = fresh()
for b in rig.pose.bones:
    b.rotation_mode = "QUATERNION"


def timing(muted, frames=40):
    mute(body, muted)
    evaluate(body)
    start = time.perf_counter()
    for k in range(frames):
        for side in ("L", "R"):
            rig.pose.bones[f"arm_lower.{side}"].rotation_quaternion = Quaternion((1, 0, 0), math.radians(3 * k))
            rig.pose.bones[f"leg_lower.{side}"].rotation_quaternion = Quaternion((1, 0, 0), math.radians(-2 * k))
        bpy.context.view_layer.update()
        evaluate(body)
    return (time.perf_counter() - start) * 1000.0 / frames


without = min(timing(True), timing(True))
with_c = min(timing(False), timing(False))
check("C5_cout_d_evaluation", with_c <= 1.30 * without, {"sans_ms": round(without, 1), "avec_ms": round(with_c, 1), "ratio": round(with_c / without, 2)})

# C8 vêtements : les correctifs du corps suivent les pièces (sous-maillages du corps), y compris après mise à jour de la morphologie, et sont retirés avec le rig
from extension import garments  # noqa: E402
body, rig = fresh()
worn = [garments.add_garment(body, "veste"), garments.add_garment(body, "pantalon")]
body_keys = correctives.keys_of(body.data)
body_basis = np.array([v.co[:] for v in body.data.shape_keys.key_blocks[0].data])
same, counts = True, []
worst_delta = 0.0
for piece in worn:
    used = np.array(json.loads(piece[garments.PARAMS])["sommets_du_corps"])
    piece_keys = correctives.keys_of(piece.data)
    counts.append(len(piece_keys))
    basis = np.array([v.co[:] for v in piece.data.shape_keys.key_blocks[0].data])
    for key in body_keys:
        body_delta = (np.array([v.co[:] for v in key.data]) - body_basis)[used]
        piece_delta = np.array([v.co[:] for v in piece.data.shape_keys.key_blocks[key.name].data]) - basis
        worst_delta = max(worst_delta, float(np.abs(body_delta - piece_delta).max()))
set_flexion(rig, "coude_L", 120.0, signs["coude_L"])
values_equal = all(abs(piece.data.shape_keys.key_blocks[k.name].value - k.value) < 1e-6 for piece in worn for k in body_keys)
before_update = [correctives.garment_deltas(p) for p in worn]
for piece in worn:
    garments.update_garment(piece)
after_update = [correctives.garment_deltas(p) for p in worn]
kept = all(max(float(np.abs(before_update[i][k] - after_update[i][k]).max()) for k in before_update[i]) < 1e-6 for i in range(len(worn)))
basis_ok = all(float(np.abs(np.array([v.co[:] for v in p.data.shape_keys.key_blocks[0].data]) - np.array([v.co[:] for v in p.data.vertices])).max()) < 1e-7 for p in worn)
skeleton.remove(body)
clean = all(p.data.shape_keys is None for p in worn)
check("C8_vetements_suivent_les_correctifs", all(c == len(body_keys) for c in counts) and worst_delta < 1e-6 and values_equal and kept and basis_ok and clean,
      {"cles_par_piece": counts, "cles_corps": len(body_keys), "ecart_max_deplacement_m": worst_delta, "valeurs_pilotees_egales": values_equal, "deplacements_conserves_apres_mise_a_jour": kept, "base_synchronisee": basis_ok, "retrait_propre": clean})

# C9 défaut : correctifs COUPÉS (décision de l'utilisateur : coude et genou corrects sans correctifs) ; bascule corps + vêtements ; état conservé
body, rig = fresh()
piece = garments.add_garment(body, "pantalon")
all_keys = lambda: correctives.keys_of(body.data) + correctives.keys_of(piece.data)
default_off = bool(all_keys()) and all(k.mute for k in all_keys()) and not correctives.enabled(body)
changed_on = correctives.set_enabled(body, True)
on = all(not k.mute for k in all_keys()) and correctives.enabled(body)
changed_off = correctives.set_enabled(body, False)
off = all(k.mute for k in all_keys()) and not correctives.enabled(body)
correctives.set_enabled(body, True)
kept_prop = bool(rig.get(correctives.ENABLED_PROP))
skeleton.remove(body)
check("C9_defaut_coupe_et_bascule", default_off and on and off and changed_on == changed_off and changed_on > 60 and kept_prop,
      {"defaut_coupe": default_off, "active": on, "recoupe": off, "cles_modifiees": [changed_on, changed_off], "propriete_sur_le_rig": kept_prop})

# C6 la foule n'installe pas de correctifs
from extension import crowd  # noqa: E402
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
spec = crowd.default_spec(2, 3)
spec["frames"] = 10
crowd.generate(bpy.context, spec)
members = crowd.members_of(bpy.context.scene)
check("C6_foule_sans_correctifs", members and all(not correctives.keys_of(m.data) for m in members), {"personnages": len(members)})

# C7 recalcul sur la morphologie courante
if REBUILD and REBUILD != "none":
    body, rig = fresh(ALL[REBUILD])
    before = correctives.status(body)
    start = time.perf_counter()
    steps = correctives.rebuild_steps(body, rig)
    payload = None
    while True:
        try:
            next(steps)
        except StopIteration as stop:
            payload = stop.value
            break
    elapsed = time.perf_counter() - start
    status_now = correctives.status(body)
    new_signs = signs_of(payload)
    summary, face = measure(body, rig, correctives.labels(payload), new_signs)
    t_new = totals(summary)
    human.set_value(body, "legs", 0.8)
    status_after_change = correctives.status(body)
    check("C7_recalcul_sur_la_morphologie", before == "generique" and status_now == "a_jour" and status_after_change == "obsolete" and t_new["plis"]["avec"] <= t_new["plis"]["sans"] / 3.0 and face < 1e-6,
          {"morphologie": REBUILD, "duree_s": round(elapsed), "statuts": [before, status_now, status_after_change], "plis": t_new["plis"], "hors_critere": t_new["hors_critere"], "visage_mm": face})

if OUT:
    Path(OUT).write_text(json.dumps(results, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
print("RESULT", "FAIL " + ", ".join(failures) if failures else "PASS")
sys.exit(1 if failures else 0)
