"""Validation du lot L5 (animations dérivées) : calques par groupes d'os, boucles sans raccord, étiquetage « dérivée », pont Blender. Sans bibliothèque (clips synthétiques sur NOTRE rig).

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/validate_animation_derived.py -- [--out FICHIER.json]

L1 quaternions et groupes d'os ; L2 calque « figé » : les os du groupe tiennent la pose de la superposition, tous les autres suivent la base ; L3 calque « étiré » ; L4 boucle : le raccord (saut fin→début rapporté au
pas médian) passe d'un clip non bouclé (>> 3) à <= 1,5 ; L5 pont Blender : action écrite, étiquetée, relue ; L6 refus des cas invalides."""
import json
from pathlib import Path
import sys

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension.animation import derive, retarget, retarget_bpy, skeleton  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = ARGS[ARGS.index("--out") + 1] if "--out" in ARGS else None
results, failures = {}, []


def check(name, ok, detail=None):
    results[name] = {"ok": bool(ok), "detail": detail}
    print(("OK  " if ok else "KO  ") + name, json.dumps(detail, ensure_ascii=False, default=str)[:800] if detail is not None else "")
    if not ok:
        failures.append(name)


addon.register()
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
bpy.ops.humanloom.create()
body = bpy.context.object
rig_object = skeleton.install(body)
rig = retarget.rig_from_armature(rig_object)
names = list(rig.names)
count = len(names)
rng = np.random.default_rng(5)


def clip(frames, amplitude, loopable=False, seed=0):
    """Clip synthétique : sinusoïdes de rotation sur tous les os ; `loopable` : périodique exactement sur `frames` images."""
    generator = np.random.default_rng(seed)
    phase = generator.uniform(0, 6.28, (count, 3))
    t = np.arange(frames)[:, None, None] / (frames if loopable else frames * 1.37)
    angles = np.radians(amplitude) * np.sin(2 * np.pi * t * (1 + np.arange(3))[None, None, :] + phase[None])
    quat = np.zeros((frames, count, 4))
    a = np.linalg.norm(angles, axis=-1) + 1e-12
    quat[..., 0] = np.cos(a / 2)
    quat[..., 1:] = np.sin(a / 2)[..., None] * angles / a[..., None]
    loc = np.zeros((frames, count, 3))
    return quat, loc


# L1
q0, q1 = clip(2, 40, seed=1)[0][0], clip(2, 40, seed=2)[0][0]
mid = derive.slerp(q0, q1, 0.5)
exact = np.allclose(derive.slerp(q0, q1, 0.0), q0 / np.linalg.norm(q0, axis=-1, keepdims=True)) and np.allclose(derive.slerp(q0, q1, 1.0), q1 / np.linalg.norm(q1, axis=-1, keepdims=True))
half = np.allclose(derive.angle_between(q0, mid) + derive.angle_between(mid, q1), derive.angle_between(q0, q1), atol=1e-4) and np.allclose(derive.angle_between(q0, mid), derive.angle_between(mid, q1), atol=1e-4)
groups = {g: derive.bone_group(names, g) for g in derive.GROUPS}
disjoint = not (set(groups["bras.R"]) & set(groups["bras.L"])) and not (set(groups["haut_du_corps"]) & set(groups["jambes"]))
check("L1_quaternions_et_groupes_d_os", exact and half and disjoint and all(len(v) > 0 for v in groups.values()) and all(names[i].endswith(".R") for i in groups["bras.R"]) and "pelvis" not in {names[i] for i in groups["haut_du_corps"]},
      {g: len(v) for g, v in groups.items()})

# L2 calque figé
base_q, base_l = clip(48, 25, loopable=True, seed=3)
over_q, _ = clip(30, 35, seed=4)
base = {"names": names, "quat": base_q, "loc": base_l}
quat, loc = derive.layer(base, {"quat": over_q}, ["bras.R"], mode="figee", hold_frame=7)
arm = groups["bras.R"]
others = [i for i in range(count) if i not in arm]
check("L2_calque_fige_bras_tenu_le_reste_suit_la_base", np.allclose(quat[:, arm], over_q[7][arm][None]) and np.array_equal(quat[:, others], base_q[:, others]) and np.array_equal(loc, base_l),
      {"os_du_groupe": len(arm), "os_de_la_base": len(others)})

# L3 calque étiré
quat2, _ = derive.layer(base, {"quat": over_q}, ["haut_du_corps"], mode="etiree")
upper = groups["haut_du_corps"]
check("L3_calque_etire_sur_la_duree_de_la_base", np.allclose(quat2[0, upper], over_q[0][upper]) and np.allclose(quat2[-1, upper], over_q[-1][upper]) and quat2.shape == base_q.shape and np.array_equal(quat2[:, groups["jambes"]], base_q[:, groups["jambes"]]),
      {"images": quat2.shape[0], "superposition_images": over_q.shape[0]})

# L4 boucle sans raccord
open_q, open_l = clip(60, 30, loopable=False, seed=6)
seam_before, jump_before = derive.loop_seam(open_q)
loop_q, loop_l = derive.make_loop(open_q, open_l, blend=10)
seam_after, jump_after = derive.loop_seam(loop_q)
perfect_q, _ = clip(60, 30, loopable=True, seed=6)
seam_perfect = derive.loop_seam(perfect_q)[0]
check("L4_boucle_sans_raccord", seam_before > 3.0 and seam_after <= 1.5 and loop_q.shape[0] == 50 and np.allclose(loop_q[10:], open_q[10:50]) and jump_after < jump_before,
      {"raccord_avant": round(seam_before, 2), "raccord_apres": round(seam_after, 2), "saut_degres_avant_apres": [round(jump_before, 1), round(jump_after, 1)], "images": loop_q.shape[0]})

# L5 pont Blender
moving = {"pelvis", "root"}


def write(name, quat_):
    return retarget_bpy.write_action(rig_object, retarget.Result(quat_, np.zeros((quat_.shape[0], count, 3)), {"noms_cibles": names}), name)


action_base = write("essai_base", clip(48, 25, loopable=False, seed=7)[0])
action_over = write("essai_superposition", clip(30, 35, seed=8)[0])
derived = derive.derive_action(rig_object, action_base, action_over, ["bras.R"], mode="figee", hold_frame=5, loop=True, blend=8)
info = json.loads(derived["hl_derived"])
read_back, _ = retarget_bpy.read_action(derived, rig)
base_back, _ = retarget_bpy.read_action(action_base, rig)
over_back, _ = retarget_bpy.read_action(action_over, rig)
legs = groups["jambes"]
arm_index = groups["bras.R"]
frames_out = read_back.quat.shape[0]
same_legs = np.allclose(derive.angle_between(read_back.quat[8:, legs], base_back.quat[8:frames_out, legs]), 0.0, atol=0.01)
arm_ok = np.allclose(derive.angle_between(read_back.quat[:, arm_index], over_back.quat[5][arm_index][None]), 0.0, atol=0.5)  # bras tenu : la pose figée, partout, y compris pendant le fondu (les deux images fondues portent la même pose)
check("L5_pont_blender_action_etiquetee_et_relue", derived.get("hl_label") == "dérivée" and "dérivée" in derived.name and info["base"] == "essai_base" and info["superposition"] == "essai_superposition" and info["groupes"] == ["bras.R"]
      and info["boucle"] and info["raccord_apres"] <= info["raccord_avant"] and frames_out == 48 - 8 and same_legs and arm_ok and derived in derive.derived_actions() and action_base not in derive.derived_actions(),
      {"info": info, "images": frames_out, "jambes_comme_la_base": same_legs, "bras_tenu": arm_ok})

# L6 refus des cas invalides
refused = []
for kwargs in ({"groups": ["nexistepas"], "mode": "figee"}, {"groups": ["bras.R"], "mode": "inconnu"}):
    try:
        derive.layer(base, {"quat": over_q}, **kwargs)
        refused.append(False)
    except ValueError:
        refused.append(True)
check("L6_cas_invalides_refuses", all(refused), refused)

# L7 opérateur et panneau
bpy.context.view_layer.objects.active = body
wm = bpy.context.window_manager
wm.hl_derive_base, wm.hl_derive_overlay, wm.hl_derive_group, wm.hl_derive_mode, wm.hl_derive_hold = "essai_base", "essai_superposition", "bras.L", "figee", 3
before = len(rig_object.animation_data.nla_tracks)
ok_op = bpy.ops.humanloom.derive_animation() == {"FINISHED"} and len(rig_object.animation_data.nla_tracks) == before + 1 and len(derive.derived_actions()) == 2
wm.hl_derive_overlay = "essai_base"
try:
    bpy.ops.humanloom.derive_animation()
    refused_same = False
except RuntimeError:
    refused_same = True
check("L7_operateur_et_panneau", ok_op and refused_same and hasattr(bpy.types, "HUMANLOOM_PT_derive"), {"piste_nla_ajoutee": ok_op, "memes_actions_refusees": refused_same})

if OUT:
    Path(OUT).write_text(json.dumps(results, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
print("RESULT", "FAIL " + ", ".join(failures) if failures else "PASS")
sys.exit(1 if failures else 0)
