"""Animations dérivées sur des clips RÉELS de la bibliothèque locale (lot L5). Test IGNORÉ si la bibliothèque est absente.

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/validate_animation_derived_library.py -- [--library DOSSIER | HL_ANIMATION_LIBRARY] [--out FICHIER.json]

Trois dérivations à partir de clips re-ciblés (lecture seule, une action à la fois) : marche + bras droit tenu (pose de « bras levés »), course + bras gauche tenu, attente + haut du corps d'un clip de geste (jouée, étirée).
Mesures : jambes identiques à la base, os du groupe fidèles à la superposition, raccord de boucle avant/après (rapporté au pas médian), étiquette « dérivée »."""
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = ARGS[ARGS.index("--out") + 1] if "--out" in ARGS else None
library_arg = ARGS[ARGS.index("--library") + 1] if "--library" in ARGS else os.environ.get("HL_ANIMATION_LIBRARY")
blends = sorted(Path(library_arg).glob("*.blend")) if library_arg and Path(library_arg).is_dir() else []
if not blends:
    print("RESULT IGNORÉ : aucune bibliothèque (--library DOSSIER ou variable HL_ANIMATION_LIBRARY)")
    sys.exit(0)

import bpy  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension.animation import derive, mapping, retarget, retarget_bpy, skeleton  # noqa: E402

results, failures = {}, []


def check(name, ok, detail=None):
    results[name] = {"ok": bool(ok), "detail": detail}
    print(("OK  " if ok else "KO  ") + name, json.dumps(detail, ensure_ascii=False, default=str)[:900] if detail is not None else "")
    if not ok:
        failures.append(name)


addon.register()
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
bpy.ops.humanloom.create()
body = bpy.context.object
rig_object = skeleton.install(body)
target = retarget.rig_from_armature(rig_object)
target_map = mapping.from_armature(rig_object)
library = blends[0]
with bpy.data.libraries.load(str(library), link=False) as (names, _):
    armature_names, action_names = list(names.armatures), list(names.actions)
best = None
for name in armature_names:
    with bpy.data.libraries.load(str(library), link=False) as (_, wanted):
        wanted.armatures = [name]
    data = wanted.armatures[0]
    if len(data.bones) < 80:
        bpy.data.armatures.remove(data)
        continue
    pairs, report = mapping.auto_map(target_map, mapping.from_armature(data))
    score = (report.coverage, -len(report.low_confidence))
    if best is None or score > best[0]:
        best = (score, name, {t: p.source for t, p in pairs.items()})
    bpy.data.armatures.remove(data)
with bpy.data.libraries.load(str(library), link=False) as (_, wanted):
    wanted.armatures = [best[1]]
source = retarget.rig_from_armature(wanted.armatures[0])
links = best[2]


def converted(keywords):
    """Action re-ciblée (nos os) pour la première action de la bibliothèque dont le nom contient un des mots (sans pied R/L dans le nom)."""
    name = next((a for key in keywords for a in action_names if key in a and "Rfoot" not in a and "Lfoot" not in a), None)
    if name is None:
        return None
    with bpy.data.libraries.load(str(library), link=False) as (_, wanted):
        wanted.actions = [name]
    action = wanted.actions[0]
    motion, first = retarget_bpy.read_action(action, source)
    bpy.data.actions.remove(action)
    result = retarget.retarget(source, target, links, motion, retarget.Options(ik_limbs=("leg",), root_motion=retarget.IN_PLACE))
    result.report["noms_cibles"] = list(target.names)
    return retarget_bpy.write_action(rig_object, result, "re-ciblée " + name[-40:], first_frame=1)


walk, run, idle = converted(("Walk_Loop_RR_offset", "Walk_Loop")), converted(("Run_Loop_RR_offset", "Run_Loop")), converted(("Stand_Idle_Loop",))
reach, gesture = converted(("ragdoll_reach_up_right",)), converted(("gesture_come_on_in",))
check("D0_clips_de_la_bibliotheque_trouves", all(a is not None for a in (walk, run, idle, reach, gesture)), {"marche": walk and walk.name, "course": run and run.name, "attente": idle and idle.name, "bras_leves": reach and reach.name, "geste": gesture and gesture.name})
rows = {}
for label, base_action, overlay_action, groups, mode in (("marche_bras_droit_tenu", walk, reach, ["bras.R"], "figee"), ("course_bras_gauche_tenu", run, reach, ["bras.L"], "figee"), ("attente_geste_haut_du_corps", idle, gesture, ["haut_du_corps"], "etiree")):
    derived = derive.derive_action(rig_object, base_action, overlay_action, groups, mode, hold_frame=int(overlay_action.frame_range[1] * 0.5), loop=True, blend=8, name=label + " (dérivée)")
    back, _ = retarget_bpy.read_action(derived, target)
    base_back, _ = retarget_bpy.read_action(base_action, target)
    over_back, _ = retarget_bpy.read_action(overlay_action, target)
    names_ = list(target.names)
    legs = derive.bone_group(names_, "jambes")
    group_index = sorted({i for g in groups for i in derive.bone_group(names_, g)})
    legs_diff = float(derive.angle_between(back.quat[8:, legs], base_back.quat[8:back.quat.shape[0] + 0, legs][:back.quat.shape[0] - 8]).max())
    if mode == "figee":
        pose = over_back.quat[min(int(overlay_action.frame_range[1] * 0.5), over_back.quat.shape[0] - 1)]
        hold_diff = float(derive.angle_between(back.quat[:, group_index], pose[group_index][None]).max())
    else:
        hold_diff = float(derive.angle_between(derive.resample(over_back.quat, base_back.quat.shape[0])[8:back.quat.shape[0], group_index], back.quat[8:, group_index]).max())
    info = json.loads(derived["hl_derived"])
    rows[label] = {"images": int(back.quat.shape[0]), "jambes_ecart_max_deg": round(legs_diff, 3), "groupe_ecart_max_deg": round(hold_diff, 2), "raccord_avant": info["raccord_avant"], "raccord_apres": info["raccord_apres"], "etiquette": derived.get("hl_label")}
ok = all(r["jambes_ecart_max_deg"] < 0.5 and r["groupe_ecart_max_deg"] < 2.0 and r["etiquette"] == "dérivée" and r["raccord_apres"] <= max(1.5, r["raccord_avant"]) for r in rows.values())
check("D1_derivations_sur_clips_reels", ok and len(rows) == 3, rows)
if OUT:
    Path(OUT).write_text(json.dumps(results, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
print("RESULT", "FAIL " + ", ".join(failures) if failures else "PASS")
sys.exit(1 if failures else 0)
