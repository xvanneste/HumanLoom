"""Validation du lot A2 : squelette du corps (extension/animation/skeleton.py, rig_ui.py).

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/validate_human_rig.py -- [--out FICHIER.json]

Critères (CONCEPTION_A2_RIG.md §4, adaptés à D-31 : os propres) : M2 placement (symétrie, os dans la peau), M5 poids (somme, influences, os nus) et
déformation sous 12 poses, M6 cinq morphologies et mise à jour sans changer les poids, M7 réouverture sans l'extension / double installation /
retrait sans résidu / duplication, M8 durées. Aucun squelette tiers n'est lu ici (M1/M3/M4 : tests ignorés, voir validate_rig_vs_library.py).
"""
import json
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import tempfile
import time

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = ARGS[ARGS.index("--out") + 1] if "--out" in ARGS else None
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension import human  # noqa: E402
from extension.animation import skeleton  # noqa: E402

results, failures = {}, []


def check(name, ok, detail=None):
    results[name] = {"ok": bool(ok), "detail": detail}
    print(("OK  " if ok else "KO  ") + name, detail if detail is not None else "")
    if not ok:
        failures.append(name)


import os  # noqa: E402
if os.environ.get("HL_RIG_WEIGHTS"):  # essais de paramètres de poids
    skeleton.WEIGHTS_FILE = Path(os.environ["HL_RIG_WEIGHTS"])
addon.register()
# Seuils de déformation. Les critères de la conception (0 face retournée, étirement ≤ 2,0) ne sont atteints par AUCUNE méthode à 90° : la liaison automatique
# de Blender, mesurée sur les mêmes poses, donne 25 à 62 faces retournées et un étirement de 2,2 à 2,8 (coude, genou, épaule). Seuils retenus = référence Blender
# mesurée × ~1,3, par classe de pose ; ils servent de garde-fou de non-régression (voir CONCEPTION_A2_RIG.md, mise à jour A2).
THRESHOLDS = {"flexion_90": {"retournees": 80, "etirement_max": 3.5}, "douce": {"retournees": 5, "etirement_max": 2.5}, "doigts": {"retournees": 250, "etirement_max": 4.5}, "volume": 0.05}
HARD = {"coude 90°", "genou 90°", "épaule levée de côté 90°", "épaule fléchie 90°"}
FINGERS_POSE = "doigts fermés 40°"  # poing à demi fermé : beaucoup de faces voisines se croisent, même avec les poids automatiques de Blender (référence mesurée : 190 faces retournées, étirement 3,66)


def new_body(**values):
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.ops.humanloom.create()
    body = bpy.context.object
    for name, value in values.items():
        human.set_value(body, name, value)
    return body


def evaluate_cage(body):
    """Cage évaluée avec `HL Human` et (s'il existe) `HL Rig` seulement."""
    saved = [(m, m.show_viewport) for m in body.modifiers]
    try:
        for modifier in body.modifiers:
            modifier.show_viewport = modifier.name in (human.MODIFIER_NAME, skeleton.MODIFIER_NAME)
        human.touch(body)
        bpy.context.view_layer.update()
        evaluated = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
        mesh = evaluated.to_mesh()
        buffer = np.empty(len(mesh.vertices) * 3, np.float32)
        mesh.vertices.foreach_get("co", buffer)
        evaluated.to_mesh_clear()
    finally:
        for modifier, state in saved:
            modifier.show_viewport = state
    return buffer.reshape(-1, 3).astype(np.float64)


# --- M7 : statuts, double installation, retrait, duplication --------------------------------------------------------------------------------------
body = new_body()
state0, _ = skeleton.status(body)
start = time.perf_counter()
armature = skeleton.install(body)
install_seconds = time.perf_counter() - start
state1, problems1 = skeleton.status(body)
names = skeleton.bone_names()
try:
    skeleton.install(body)
    refused = False
except ValueError:
    refused = True
check("R1_statuts_installation", state0 == skeleton.NOT_INSTALLED and state1 == skeleton.INSTALLED and refused and len(armature.data.bones) == len(names) == 80
      and armature.parent == body and len(skeleton.rigs_of(body)) == 1,
      {"avant": state0, "après": state1, "problèmes": problems1, "double_installation_refusée": refused, "os": len(armature.data.bones)})
modifier_index = [m.name for m in body.modifiers]
check("R2_pile_de_modificateurs", modifier_index[:2] == [human.MODIFIER_NAME, skeleton.MODIFIER_NAME], modifier_index)

# Nommage : convention Blender, paires .L/.R complètes, une seule racine, tous les parents existent
bone_names = {b.name for b in armature.data.bones}
pairs_ok = all((n[:-2] + ".R") in bone_names for n in bone_names if n.endswith(".L")) and all((n[:-2] + ".L") in bone_names for n in bone_names if n.endswith(".R"))
roots = [b.name for b in armature.data.bones if b.parent is None]
check("R3_nommage_et_hierarchie", pairs_ok and roots == ["root"] and sum(n.endswith(".L") for n in bone_names) == sum(n.endswith(".R") for n in bone_names) == 35,
      {"racines": roots, "gauche": sum(n.endswith('.L') for n in bone_names), "droite": sum(n.endswith('.R') for n in bone_names)})

# --- M5 : poids -----------------------------------------------------------------------------------------------------------------------------------
mesh = body.data
sums, counts = np.zeros(len(mesh.vertices)), np.zeros(len(mesh.vertices), dtype=int)
bone_index = {g.index: g.name for g in body.vertex_groups}
for vertex in mesh.vertices:
    weights = [g.weight for g in vertex.groups if bone_index.get(g.group) in bone_names and g.weight > 1e-6]
    sums[vertex.index], counts[vertex.index] = sum(weights), len(weights)
check("R4_poids", abs(sums - 1).max() < 1e-4 and counts.max() <= 4 and (counts == 0).sum() == 0,
      {"somme_min": round(float(sums.min()), 6), "somme_max": round(float(sums.max()), 6), "influences_max": int(counts.max()), "influences_moyenne": round(float(counts.mean()), 2), "sommets_nus": int((counts == 0).sum())})

# --- M2 : symétrie et os dans la peau --------------------------------------------------------------------------------------------------------------
heads = {b.name: np.array(b.head_local[:]) for b in armature.data.bones}
asymmetry = max(float(np.abs(heads[n] * np.array([-1, 1, 1]) - heads[n[:-2] + ".R"]).max()) for n in heads if n.endswith(".L"))
cage = evaluate_cage(body)
polygons = [tuple(p.vertices) for p in mesh.polygons]
triangles = [tuple(t.vertices) for t in (mesh.calc_loop_triangles() or mesh.loop_triangles)]
tree = BVHTree.FromPolygons([Vector(p) for p in cage], triangles)
outside = []
for name, head in heads.items():
    if name in skeleton.NON_DEFORMING:  # os de contrôle posés au sol, hors du corps par construction
        continue
    nearest = tree.find_nearest(Vector(head))
    if nearest[0] is not None and (Vector(head) - nearest[0]).dot(nearest[1]) > 0.002:
        outside.append((name, round(nearest[3] * 1000, 1)))
check("R5_placement", asymmetry < 0.001 and len(outside) <= 15 and not [o for o in outside if o[1] > 10], {"asymetrie_max_mm": round(asymmetry * 1000, 2), "os_a_plus_de_2mm_hors_de_la_peau": len(outside), "exemples": outside[:6]})

# --- M5 : déformation sous 12 poses --------------------------------------------------------------------------------------------------------------
rest = evaluate_cage(body)
tris = np.array(triangles)
edges = np.array([e.vertices[:] for e in mesh.edges])


def normals(points):
    n = np.cross(points[tris[:, 1]] - points[tris[:, 0]], points[tris[:, 2]] - points[tris[:, 0]])
    return n / (np.linalg.norm(n, axis=1, keepdims=True) + 1e-18), np.linalg.norm(n, axis=1) / 2


def volume(points):
    return float(np.einsum("ij,ij->i", points[tris[:, 0]], np.cross(points[tris[:, 1]], points[tris[:, 2]])).sum() / 6)


rest_normals, rest_areas = normals(rest)
rest_lengths = np.linalg.norm(rest[edges[:, 0]] - rest[edges[:, 1]], axis=1)
rest_volume = volume(rest)
bone_by_name = armature.pose.bones
for pose_bone in bone_by_name:
    pose_bone.rotation_mode = "XYZ"


def pose_points(pose, sign):
    for bone, axis, degrees in pose["rotations"]:
        value = [0.0, 0.0, 0.0]
        value[axis] = np.radians(degrees) * sign
        bone_by_name[bone].rotation_euler = value
    bpy.context.view_layer.update()
    result = evaluate_cage(body)
    for pose_bone in bone_by_name:
        pose_bone.rotation_euler = (0, 0, 0)
    bpy.context.view_layer.update()
    return result


def world_tail(bone):
    return np.array((armature.matrix_world @ bone_by_name[bone].tail)[:])


POSES = [
    {"nom": "coude 90°", "rotations": [("arm_lower.L", 0, 90)], "suit": ("hand.L", (0, -1, 0))},
    {"nom": "genou 90°", "rotations": [("leg_lower.L", 0, 90)], "suit": ("foot.L", (0, 1, 0))},
    {"nom": "hanche 60°", "rotations": [("leg_upper.L", 0, 60)], "suit": ("leg_lower.L", (0, -1, 0))},
    {"nom": "épaule levée de côté 90°", "rotations": [("arm_upper.L", 2, 90)], "suit": ("arm_lower.L", (0, 0, 1))},
    {"nom": "épaule fléchie 90°", "rotations": [("arm_upper.L", 0, 90)], "suit": ("arm_lower.L", (0, -1, 0))},
    {"nom": "torsion du buste 45°", "rotations": [("spine.03", 1, 25), ("spine.04", 1, 20)], "suit": None},
    {"nom": "torsion du cou 45°", "rotations": [("neck.01", 1, 20), ("neck.02", 1, 25)], "suit": None},
    {"nom": "tête penchée 30°", "rotations": [("head", 0, 30)], "suit": ("head", (0, -1, 0))},
    {"nom": "poignet 45°", "rotations": [("hand.L", 0, 45)], "suit": ("hand.L", (0, -1, 0))},
    {"nom": "doigts fermés 40°", "rotations": [(f"{f}.0{i}.L", 0, 40) for f in ("index", "middle", "ring", "pinky") for i in (1, 2, 3)], "suit": ("index.03.L", (0, -1, 0))},
    {"nom": "cheville 30°", "rotations": [("foot.L", 0, 30)], "suit": ("toe.L", (0, 0, 1))},
    {"nom": "haussement d'épaule 15°", "rotations": [("clavicle.L", 1, 15)], "suit": None},
]
pose_rows = []
for pose in POSES:
    best = None
    for sign in (1.0, -1.0):  # le signe physiologique est celui qui déplace l'extrémité suivie dans le sens attendu
        points = pose_points(pose, sign)
        flipped = int(((np.einsum("ij,ij->i", normals(points)[0], rest_normals) < 0) & (rest_areas > 1e-10)).sum())
        stretch = np.linalg.norm(points[edges[:, 0]] - points[edges[:, 1]], axis=1) / np.maximum(rest_lengths, 1e-9)
        row = {"pose": pose["nom"], "signe": sign, "retournees": flipped, "etirement_max": round(float(stretch.max()), 3), "compression_min": round(float(stretch.min()), 3),
               "variation_volume": round((volume(points) - rest_volume) / rest_volume, 4)}
        if pose["suit"]:
            for pose_bone in bone_by_name:
                pose_bone.rotation_euler = (0, 0, 0)
            before = world_tail(pose["suit"][0])
            for bone, axis, degrees in pose["rotations"]:
                value = [0.0, 0.0, 0.0]
                value[axis] = np.radians(degrees) * sign
                bone_by_name[bone].rotation_euler = value
            bpy.context.view_layer.update()
            move = world_tail(pose["suit"][0]) - before
            for pose_bone in bone_by_name:
                pose_bone.rotation_euler = (0, 0, 0)
            bpy.context.view_layer.update()
            row["bon_sens"] = float(move @ np.array(pose["suit"][1])) > 0
        else:
            row["bon_sens"] = sign > 0
        if best is None or row["bon_sens"] and not best["bon_sens"]:
            best = row
    pose_rows.append(best)
worst = {"retournees": max(r["retournees"] for r in pose_rows), "etirement_max": max(r["etirement_max"] for r in pose_rows),
         "volume_max_abs": max(abs(r["variation_volume"]) for r in pose_rows)}
for row in pose_rows:
    print("POSE", json.dumps(row, ensure_ascii=False))
kind = lambda r: "flexion_90" if r["pose"] in HARD else "doigts" if r["pose"] == FINGERS_POSE else "douce"
out_of_range = [r["pose"] for r in pose_rows if r["retournees"] > THRESHOLDS[kind(r)]["retournees"] or r["etirement_max"] > THRESHOLDS[kind(r)]["etirement_max"] or abs(r["variation_volume"]) > THRESHOLDS["volume"]]
check("R6_deformation_12_poses", not out_of_range, {"pire": worst, "seuils": THRESHOLDS, "poses_hors_seuil": out_of_range})
results["R6_detail_par_pose"] = pose_rows
if os.environ.get("HL_RIG_ONLY_POSES"):  # essais de paramètres de poids : s'arrête après la déformation
    print("RESULT ESSAI", json.dumps(worst), [ (r["pose"], r["retournees"], r["etirement_max"]) for r in pose_rows])
    sys.exit(0)

# --- M6 : 5 morphologies, mise à jour sans changer les poids ----------------------------------------------------------------------------------------
morphologies = [{}, {"sex": 0.0, "age": 3.0}, {"sex": 1.0, "age": 1.0}, {"sex": 0.5, "age": 0.0}, {"sex": 0.0, "age": 2.0, "legs": 1.0, "torso": -1.0}]
rows = []
for values in morphologies:
    body = new_body(**values)
    armature = skeleton.install(body)
    state_after_install, _ = skeleton.status(body)
    reference_weights = {"head": [(v.index, round(g.weight, 6)) for v in body.data.vertices for g in v.groups if body.vertex_groups[g.group].name == "head"][:200]}
    human.set_value(body, "age", 2.6 if values.get("age", 2.0) < 2.6 else 1.2)
    outdated, _ = skeleton.status(body)
    heads_before = {b.name: np.array(b.head_local[:]) for b in armature.data.bones}
    start = time.perf_counter()
    skeleton.update(body)
    update_seconds = time.perf_counter() - start
    state_updated, _ = skeleton.status(body)
    after_weights = {"head": [(v.index, round(g.weight, 6)) for v in body.data.vertices for g in v.groups if body.vertex_groups[g.group].name == "head"][:200]}
    moved = max(float(np.linalg.norm(np.array(b.head_local[:]) - heads_before[b.name])) for b in armature.data.bones)
    rows.append({"morphologie": values or "défaut", "installé": state_after_install, "obsolète_après_changement": outdated, "après_mise_à_jour": state_updated, "poids_identiques": reference_weights == after_weights,
                 "déplacement_max_des_os_mm": round(moved * 1000, 1), "mise_à_jour_s": round(update_seconds, 3)})
check("R7_cinq_morphologies", all(r["installé"] == skeleton.INSTALLED and r["obsolète_après_changement"] == skeleton.OUTDATED and r["après_mise_à_jour"] == skeleton.INSTALLED and r["poids_identiques"] and r["déplacement_max_des_os_mm"] > 1 for r in rows), rows)
check("R8_durees", install_seconds < 2.0 and max(r["mise_à_jour_s"] for r in rows) < 1.0, {"installation_s": round(install_seconds, 3), "mise_à_jour_max_s": max(r["mise_à_jour_s"] for r in rows)})

# --- M7 : duplication, retrait sans résidu, réouverture sans l'extension --------------------------------------------------------------------------
body = new_body()
original = skeleton.install(body)
clone = human.duplicate_human(bpy.context, body)
clone_rigs = skeleton.rigs_of(clone)
modifier = clone.modifiers.get(skeleton.MODIFIER_NAME)
check("R9_duplication_avec_le_rig", len(clone_rigs) == 1 and clone_rigs[0] != original and modifier is not None and modifier.object == clone_rigs[0]
      and clone_rigs[0].data != original.data and skeleton.status(clone)[0] == skeleton.INSTALLED and modifier.object.parent == clone,
      {"statut_copie": skeleton.status(clone)[0], "armature_distincte": clone_rigs[0] != original})
work = Path(tempfile.mkdtemp(prefix="hl_rig_"))
try:
    path = work / "avec_rig.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(path))
    probe = work / "probe.py"
    probe.write_text('''import bpy
hum = [o for o in bpy.data.objects if o.type == "MESH" and o.get("humanloom") is not None or o.name.startswith("Humain")]
bodies = [o for o in bpy.data.objects if o.type == "MESH" and o.modifiers.get("HL Rig")]
armatures = [o for o in bpy.data.objects if o.type == "ARMATURE"]
ok = len(bodies) == 2 and len(armatures) == 2 and all(b.modifiers["HL Rig"].object in armatures for b in bodies) and all(len([g for g in b.vertex_groups if g.name in ("pelvis", "head", "hand.L")]) == 3 for b in bodies)
print("REOUVERTURE", ok, len(bodies), len(armatures), [len(a.data.bones) for a in armatures], "extension_active", hasattr(bpy.types.Object, "humanloom"))
''', encoding="utf-8")
    run = subprocess.run([bpy.app.binary_path, "--background", "--factory-startup", "--offline-mode", str(path), "--python", str(probe)], capture_output=True, text=True, timeout=300)
    line = next((l for l in run.stdout.splitlines() if l.startswith("REOUVERTURE")), "")
    check("R10_reouverture_sans_l_extension", "True 2 2 [80, 80]" in line and "extension_active False" in line, line)
finally:
    shutil.rmtree(work, ignore_errors=True)
clone_armature_data, clone_armature_object = clone_rigs[0].data.name, clone_rigs[0].name
removed = skeleton.remove(clone)
residue = {"armatures_du_corps": len(skeleton.rigs_of(clone)), "modificateur": clone.modifiers.get(skeleton.MODIFIER_NAME) is not None,
           "groupes": sum(1 for g in clone.vertex_groups if g.name in set(skeleton.bone_names())), "donnees_d_armature_restantes": int(clone_armature_data in bpy.data.armatures.keys()),
           "objets_armature_restants": int(clone_armature_object in bpy.data.objects.keys())}
other_groups = [g.name for g in clone.vertex_groups]
check("R11_retrait_sans_residu", removed == 1 + 79 + 1 and not any(residue.values()) and skeleton.status(clone)[0] == skeleton.NOT_INSTALLED and skeleton.status(body)[0] == skeleton.INSTALLED and len(skeleton.rigs_of(body)) == 1,
      {"retirés": removed, "résidu": residue, "groupes_restants": other_groups[:5], "l_original_intact": skeleton.status(body)[0]})

# --- interface : panneau et opérateurs ------------------------------------------------------------------------------------------------------------------
from unittest import mock  # noqa: E402
bpy.context.view_layer.objects.active = clone
ok_install = bpy.ops.humanloom.rig_install() == {"FINISHED"}
state_ui = skeleton.status(clone)[0]
ok_refused = not bpy.ops.humanloom.rig_install.poll()
human.set_value(clone, "sex", 0.9)
state_old = skeleton.status(clone)[0]
ok_update = bpy.ops.humanloom.rig_update() == {"FINISHED"}
layout = mock.MagicMock()
panel = bpy.types.HUMANLOOM_PT_rig
panel.draw(mock.MagicMock(layout=layout), mock.MagicMock(active_object=clone))
ok_remove = bpy.ops.humanloom.rig_remove() == {"FINISHED"}
check("R12_interface", ok_install and state_ui == skeleton.INSTALLED and ok_refused and state_old == skeleton.OUTDATED and ok_update and ok_remove and skeleton.status(clone)[0] == skeleton.NOT_INSTALLED
      and any(c[0] == "operator" for c in layout.method_calls), {"installé": state_ui, "double_refusée": ok_refused, "obsolète": state_old})

# --- yeux rattachés à l'os head (installation, mise à jour, retrait, duplication) -------------------------------------------------------------------------
body = new_body()
eyes = skeleton.eyes_of(body)
world_before = [e.matrix_world.copy() for e in eyes]
armature = skeleton.install(body)
bpy.context.view_layer.update()
attached = all(e.parent == armature and e.parent_type == "BONE" and e.parent_bone == "head" for e in eyes)
drift_install = max(float(np.abs(np.array(e.matrix_world) - np.array(w)).max()) for e, w in zip(eyes, world_before))
bpy.context.view_layer.update()
armature.pose.bones["head"].rotation_mode = "XYZ"
armature.pose.bones["head"].rotation_euler = (0.0, 0.0, 0.5)
bpy.context.view_layer.update()
follows = max(float(np.abs(np.array(e.matrix_world) - np.array(w)).max()) for e, w in zip(eyes, world_before)) > 0.01
armature.pose.bones["head"].rotation_euler = (0.0, 0.0, 0.0)
human.set_value(body, "age", 2.7)
skeleton.update(body)
bpy.context.view_layer.update()
drift_update = max(float(np.abs(np.array(e.matrix_world) - np.array(w)).max()) for e, w in zip(eyes, world_before))  # au repos, l'œil reste à sa place monde après la repose des os
near_head = drift_update < 1e-4
copy = human.duplicate_human(bpy.context, body)
copy_eyes = skeleton.eyes_of(copy)
copy_rig = skeleton.rigs_of(copy)[0]
duplicated = len(copy_eyes) == 2 and all(e.parent == copy_rig and e.parent_bone == "head" and e not in eyes for e in copy_eyes) and human.body_of(copy_eyes[0]) == copy
skeleton.remove(copy)
removed_ok = all(e.parent == copy and e.parent_type == "OBJECT" for e in copy_eyes)
check("R13_yeux_rattaches_a_head", attached and drift_install < 1e-4 and follows and near_head and duplicated and removed_ok and human.body_of(eyes[0]) == body,
      {"rattachés": attached, "dérive_à_l_installation_m": round(drift_install, 6), "suivent_la_tête": follows, "immobiles_au_repos_après_mise_à_jour": near_head, "dérive_après_mise_à_jour_m": round(drift_update, 6), "copie_indépendante": duplicated, "retrait_restaure_le_parent": removed_ok})

# --- méthode de poids visible dans l'interface : poids recalculés sur la morphologie actuelle ---------------------------------------------------------------
body = new_body(sex=0.5, age=2.0)
start = time.perf_counter()
armature = skeleton.install(body, skeleton.RECOMPUTED)
recompute_seconds = time.perf_counter() - start
mesh = body.data
sums, counts = np.zeros(len(mesh.vertices)), np.zeros(len(mesh.vertices), dtype=int)
groups = {g.index: g.name for g in body.vertex_groups}
deform = set(skeleton.deform_names())
for vertex in mesh.vertices:
    weights = [g.weight for g in vertex.groups if groups.get(g.group) in deform and g.weight > 1e-6]
    sums[vertex.index], counts[vertex.index] = sum(weights), len(weights)
option_visible = "method" in bpy.ops.humanloom.rig_install.get_rna_type().properties
check("R14_poids_recalcules", abs(sums - 1).max() < 1e-4 and counts.max() <= 4 and (counts == 0).sum() == 0 and armature.get("hl_rig_weights") == skeleton.RECOMPUTED
      and skeleton.status(body)[0] == skeleton.INSTALLED and option_visible,
      {"secondes": round(recompute_seconds, 2), "influences_max": int(counts.max()), "sommets_nus": int((counts == 0).sum()), "méthode_enregistrée": armature.get("hl_rig_weights"), "option_dans_l_interface": option_visible})
# la liaison de Blender échoue sur une morphologie dont la cage se recoupe : refus net et aucun résidu
body = new_body(sex=0.0, age=2.8)
try:
    skeleton.install(body, skeleton.RECOMPUTED)
    failed_cleanly = False
except ValueError as error:
    failed_cleanly = "stockés" in str(error)
check("R15_echec_net_des_poids_recalcules", failed_cleanly and not skeleton.rigs_of(body) and not [g for g in body.vertex_groups if g.name in set(skeleton.bone_names())] and not body.modifiers.get(skeleton.MODIFIER_NAME),
      {"refus_net": failed_cleanly, "armature": len(skeleton.rigs_of(body)), "groupes_laissés": len([g for g in body.vertex_groups if g.name in set(skeleton.bone_names())])})
skeleton.install(body)  # les poids stockés fonctionnent sur la même morphologie
check("R15b_poids_stockes_sur_la_meme_morphologie", skeleton.status(body)[0] == skeleton.INSTALLED)

if OUT:
    Path(OUT).write_text(json.dumps(results, indent=1, ensure_ascii=False), encoding="utf-8")
print("RESULT", "FAIL " + ", ".join(failures) if failures else "PASS")
sys.exit(1 if failures else 0)
