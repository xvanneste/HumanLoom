"""Validation du lot A3 (cœur) : retargeting analytique sur des squelettes SYNTHÉTIQUES, en circuit fermé (CONCEPTION_A3.md : Q1, Q6, Q7, Q8, cache).

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/validate_animation_retarget.py -- [--out FICHIER.json]

Circuit fermé : le squelette source est NOTRE rig dont chaque repère de repos est tourné au hasard (0 à 40°) ; l'animation source est construite pour avoir la même pose
monde qu'une animation cible connue ; le retargeting doit la retrouver. Aucun squelette tiers n'est lu.
"""
import json
from pathlib import Path
import shutil
import sys
import tempfile

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = ARGS[ARGS.index("--out") + 1] if "--out" in ARGS else None
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension.animation import retarget, retarget_bpy, skeleton  # noqa: E402

results, failures = {}, []


def check(name, ok, detail=None):
    results[name] = {"ok": bool(ok), "detail": detail}
    print(("OK  " if ok else "KO  ") + name, detail if detail is not None else "")
    if not ok:
        failures.append(name)


addon.register()
bpy.ops.humanloom.create()
body = bpy.context.object
rig_object = skeleton.install(body)
target = retarget.rig_from_armature(rig_object)
rng = np.random.default_rng(3)
FRAMES = 40


def random_rotation(max_degrees):
    axis = rng.normal(size=3)
    axis /= np.linalg.norm(axis)
    angle = np.radians(rng.uniform(0, max_degrees))
    k = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    return np.eye(3) + np.sin(angle) * k + (1 - np.cos(angle)) * k @ k


def angle_between(q1, q2):
    return np.degrees(2 * np.arccos(np.clip(np.abs((q1 * q2).sum(-1)), 0, 1)))


# squelette source : repères de repos tournés ; animation cible connue
source_rest = target.rest.copy()
for i in range(len(target.names)):
    source_rest[i][:3, :3] = target.rest[i][:3, :3] @ random_rotation(40)
source = retarget.Rig(list(target.names), list(target.parents), source_rest)
count = len(target.names)
phase = rng.uniform(0, 6.28, (count, 3))
frames = np.arange(FRAMES)[:, None, None] / FRAMES
angles = np.radians(25) * np.sin(2 * np.pi * frames * (1 + np.arange(3))[None, None, :] + phase[None])  # (F, N, 3)
quat_a = np.zeros((FRAMES, count, 4))
for f in range(FRAMES):
    for i in range(count):
        v = angles[f, i]
        angle = np.linalg.norm(v) + 1e-12
        quat_a[f, i] = np.concatenate([[np.cos(angle / 2)], np.sin(angle / 2) * v / angle])
quat_a[:, target.index["root"]] = [1, 0, 0, 0]
loc_a = np.zeros((FRAMES, count, 3))
pelvis = target.index["pelvis"]
t = np.arange(FRAMES) / FRAMES
loc_a[:, pelvis] = np.stack([1.5 * t, 0.1 * np.sin(6.28 * t), 0.05 * np.sin(12.56 * t)], -1)  # avance de 1,5 m en x, oscillation verticale
world_a = retarget.forward_kinematics(target, loc_a, quat_a)
rotations_s = np.einsum("fnij,njk->fnik", world_a[:, :, :3, :3], np.einsum("nji,njk->nik", target.rest[:, :3, :3], source_rest[:, :3, :3]))
positions = np.full((FRAMES, count, 3), np.nan)
positions[:, pelvis] = world_a[:, pelvis, :3, 3]
loc_s, quat_s, _ = retarget.world_to_basis(source, rotations_s, positions)
motion = retarget.Motion(loc_s, quat_s, 30.0)
mapping = {n: n for n in target.names}
check("Q0_repos_source_different", float(np.median([np.degrees(np.arccos(np.clip((np.trace(source_rest[i][:3, :3].T @ target.rest[i][:3, :3]) - 1) / 2, -1, 1))) for i in range(count)])) > 10,
      "repères source tournés de plus de 10° en médiane")

for mode in (retarget.ABSOLUTE, retarget.DELTA, retarget.ABSOLUTE_IK):
    result = retarget.retarget(source, target, mapping, motion, retarget.Options(pose_mode=mode, root_motion=retarget.KEEP))
    error = angle_between(result.quat, quat_a)
    positions_back = retarget.joint_positions(target, result.loc, result.quat)
    position_error = np.linalg.norm(positions_back - world_a[:, :, :3, 3], axis=-1)
    check(f"Q1_circuit_ferme_{mode}", np.median(error) <= 0.1 and error.max() <= 0.5 and position_error.max() <= 0.001,
          {"orientation_mediane_deg": round(float(np.median(error)), 6), "orientation_max_deg": round(float(error.max()), 6), "position_max_mm": round(float(position_error.max()) * 1000, 6)})

# Q1b : clavicule limitée — seule la clavicule change (orientation monde de tous les autres os conservée) ; son angle par rapport au repos est réduit du facteur demandé
full = retarget.retarget(source, target, mapping, motion, retarget.Options(pose_mode=retarget.ABSOLUTE, root_motion=retarget.KEEP))
half = retarget.retarget(source, target, mapping, motion, retarget.Options(pose_mode=retarget.ABSOLUTE, root_motion=retarget.KEEP, clavicle_scale=0.5))
world_full, world_half = retarget.forward_kinematics(target, full.loc, full.quat), retarget.forward_kinematics(target, half.loc, half.quat)
ci = {target.index["clavicle.L"], target.index["clavicle.R"]}
others = [i for i in range(count) if i not in ci]
rot_diff = np.abs(world_full[:, others, :3, :3] - world_half[:, others, :3, :3]).max()


def angle_to_rest(world, i):
    delta = np.einsum("fij,jk->fik", world[:, i, :3, :3], target.rest[i][:3, :3].T)
    return np.degrees(np.arccos(np.clip((np.trace(delta, axis1=-2, axis2=-1) - 1) / 2, -1, 1)))


ratio = np.median([np.median(angle_to_rest(world_half, i) / np.maximum(angle_to_rest(world_full, i), 1e-6)) for i in ci])
check("Q1b_clavicule_limitee", rot_diff < 1e-5 and abs(float(ratio) - 0.5) < 0.02 and retarget.Options().clavicle_scale == 1.0,
      {"ecart_orientation_monde_autres_os": float(rot_diff), "rapport_angle_clavicule": round(float(ratio), 4), "defaut": retarget.Options().clavicle_scale})

# Q7 : gestionnaire de root motion
by_mode = {}
for mode in (retarget.IN_PLACE, retarget.KEEP, retarget.EXTRACT):
    outcome = retarget.retarget(source, target, mapping, motion, retarget.Options(root_motion=mode))
    by_mode[mode] = (outcome, retarget.joint_positions(target, outcome.loc, outcome.quat)[:, pelvis])
keep, extract, in_place = by_mode[retarget.KEEP][1], by_mode[retarget.EXTRACT][1], by_mode[retarget.IN_PLACE][1]
root = target.index["root"]
extracted_root = retarget.joint_positions(target, by_mode[retarget.EXTRACT][0].loc, by_mode[retarget.EXTRACT][0].quat)[:, root]
kept_root = retarget.joint_positions(target, by_mode[retarget.KEEP][0].loc, by_mode[retarget.KEEP][0].quat)[:, root]
travel = keep - keep[0]
check("Q7_root_motion", np.abs(keep - extract).max() < 1e-4 and np.abs(in_place[:, :2] - in_place[0, :2]).max() < 1e-6 and np.abs(in_place[:, 2] - keep[:, 2]).max() < 1e-6
      and np.abs(kept_root - kept_root[0]).max() < 1e-9 and np.abs((extracted_root - extracted_root[0])[:, :2] - travel[:, :2]).max() < 1e-4 and np.abs((extracted_root - extracted_root[0])[:, 2]).max() < 1e-6,
      {"conserver_vs_extraire_max_m": float(np.abs(keep - extract).max()), "sur_place_derive_horizontale_m": float(np.abs(in_place[:, :2] - in_place[0, :2]).max()),
       "root_deplacement_monde_x_m": round(float((extracted_root - extracted_root[0])[-1, 0]), 4), "bassin_deplacement_monde_x_m": round(float(travel[-1, 0]), 4)})

# Q8 : rapport ; os sans source (torsions et un os de colonne retirés) = base identité
partial = {t: s for t, s in mapping.items() if "twist" not in t and t != "spine.02"}
outcome = retarget.retarget(source, target, partial, motion, retarget.Options())
missing = outcome.report["os_cibles_sans_source"]
identity = [float(np.abs(outcome.quat[:, target.index[n]] @ np.array([1.0, 0, 0, 0])).min()) for n in missing if "twist" in n]
check("Q8_rapport_et_os_sans_source", set(outcome.report) >= {"noms_cibles", "mode_pose", "root_motion", "os_cibles_sans_source", "os_sources_non_utilises", "echelle_translation", "deplacement_horizontal_m"}
      and "spine.02" in missing and sum("twist" in n for n in missing) == 16 and min(identity) > 0.9999 and len(outcome.report["os_sources_non_utilises"]) == len(missing),
      {"cibles_sans_source": len(missing), "echelle": round(outcome.report["echelle_translation"], 4), "deplacement_m": round(outcome.report["deplacement_horizontal_m"], 3)})
check("Q8b_quaternions_continus", float(np.min((outcome.quat[1:] * outcome.quat[:-1]).sum(-1))) >= 0)

# cache : empreinte déterministe et sensible aux options ; aller-retour disque
work = Path(tempfile.mkdtemp(prefix="hl_retarget_"))
try:
    key_a = retarget.signature(source, mapping, retarget.Options(), "action-1")
    check("C1_empreinte_de_cache", key_a == retarget.signature(source, mapping, retarget.Options(), "action-1") and key_a != retarget.signature(source, mapping, retarget.Options(pose_mode=retarget.DELTA), "action-1")
          and key_a != retarget.signature(source, mapping, retarget.Options(), "action-2") and key_a != retarget.signature(source, {**mapping, "head": "neck.01"}, retarget.Options(), "action-1"), key_a)
    result = retarget.retarget(source, target, mapping, motion)
    retarget_bpy.cache_save(work, key_a, result)
    loaded = retarget_bpy.cache_load(work, key_a)
    check("C2_cache_aller_retour", loaded is not None and np.abs(loaded.quat - result.quat).max() < 1e-6 and np.abs(loaded.loc - result.loc).max() < 1e-6 and retarget_bpy.cache_load(work, "inexistant") is None)

    # écriture/lecture d'action et aperçu non destructif (Q6)
    action = retarget_bpy.write_action(rig_object, result, "test@HumanLoom", first_frame=1)
    back, start = retarget_bpy.read_action(action, target)
    quat_error = angle_between(back.quat, result.quat)
    check("A1_ecriture_lecture_d_action", back.frames == FRAMES and start == 1 and quat_error.max() < 0.01 and np.abs(back.loc[:, pelvis] - result.loc[:, pelvis]).max() < 1e-5 and rig_object.animation_data.action is None
          if rig_object.animation_data else back.frames == FRAMES and start == 1 and quat_error.max() < 0.01,
          {"images": back.frames, "orientation_max_deg": round(float(quat_error.max()), 5)})
    for pose_bone in rig_object.pose.bones:
        pose_bone.rotation_mode = "QUATERNION"
    rig_object.pose.bones["hand.L"].rotation_quaternion = (0.9, 0.1, 0.2, 0.3)
    rig_object.pose.bones["pelvis"].location = (0.0, 0.05, 0.0)
    bpy.context.scene.frame_set(7)
    before = {b.name: (tuple(b.location), tuple(b.rotation_quaternion)) for b in rig_object.pose.bones}
    had_animation = rig_object.animation_data is not None and rig_object.animation_data.action is not None
    preview = retarget_bpy.Preview()
    preview.start(rig_object, action)
    bpy.context.scene.frame_set(20)
    previewed = rig_object.animation_data.action == action
    bpy.context.view_layer.update()
    moved = any(tuple(b.rotation_quaternion) != before[b.name][1] for b in rig_object.pose.bones)
    preview.stop()
    after = {b.name: (tuple(b.location), tuple(b.rotation_quaternion)) for b in rig_object.pose.bones}
    check("Q6_apercu_non_destructif", previewed and moved and before == after and bpy.context.scene.frame_current == 7 and (rig_object.animation_data is None or rig_object.animation_data.action is None) and not had_animation,
          {"aperçu_actif": previewed, "pose_modifiée_pendant": moved, "pose_restaurée": before == after, "image": bpy.context.scene.frame_current})
    # aperçu sur un rig qui a déjà une action : restaurée à l'identique
    other = bpy.data.actions.new("autre")
    retarget_bpy.replace_action(rig_object, other)
    preview.start(rig_object, action)
    preview.stop()
    check("Q6b_action_precedente_restauree", rig_object.animation_data.action == other)
    strip = retarget_bpy.add_to_nla(rig_object, action, "nla-test")
    check("N1_ajout_au_nla", len(rig_object.animation_data.nla_tracks) == 1 and strip.action == action and strip.name == action.name, [t.name for t in rig_object.animation_data.nla_tracks])
    retarget_bpy.replace_action(rig_object, action)
    check("N2_remplacement", rig_object.animation_data.action == action)
finally:
    shutil.rmtree(work, ignore_errors=True)

if OUT:
    Path(OUT).write_text(json.dumps(results, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
print("RESULT", "FAIL " + ", ".join(failures) if failures else "PASS")
sys.exit(1 if failures else 0)
