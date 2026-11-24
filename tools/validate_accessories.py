"""Validation des accessoires, points d'attache et poses de préhension (lot V3).

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/validate_accessories.py -- [--out FICHIER.json]

A1 sept accessoires procéduraux sans asset tiers ; A2 points d'attache (mains, dos, visage) : positions mesurées sur le corps, aucune pénétration au repos pour le sac à dos et les lunettes ; A3 l'accessoire suit l'os
(rotation du bras) ; A4 préhension : fermeture mesurée des doigts, retour à la main ouverte, contact des bouts de doigts avec la poignée ; A5 parapluie ouvert / fermé ; A6 échelle selon la stature ; A7 erreurs ; A8 panneau."""
import json
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Euler, Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension import accessories as A, human  # noqa: E402
from extension.animation import skeleton  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = ARGS[ARGS.index("--out") + 1] if "--out" in ARGS else None
results, failures = {}, []


def check(name, ok, detail=None):
    results[name] = {"ok": bool(ok), "detail": detail}
    print(("OK  " if ok else "KO  ") + name, json.dumps(detail, ensure_ascii=False, default=str)[:900] if detail is not None else "")
    if not ok:
        failures.append(name)


addon.register()


def fresh(values=None):
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.ops.humanloom.create()
    body = bpy.context.object
    for name, value in (values or {}).items():
        human.set_value(body, name, value)
    rig = skeleton.install(body)
    body.modifiers["Human Modeling · Surface"].show_viewport = False
    return body, rig


def world_points(obj):
    bpy.context.view_layer.update()
    return np.array([(obj.matrix_world @ v.co)[:] for v in obj.data.vertices])


body, rig = fresh()
cage = skeleton.cage_points(body)
mesh = body.data
mesh.calc_loop_triangles()
tree = BVHTree.FromPolygons([Vector(p) for p in cage], [t.vertices[:] for t in mesh.loop_triangles])
placed = {}
for key in A.ACCESSORIES:
    placed[key] = A.add_accessory(body, key)
rows = {k: {"sommets": len(o.data.vertices), "os": o.parent_bone, "attache": json.loads(o[A.PARAMS])["socket"]} for k, o in placed.items()}
finite = all(np.isfinite(world_points(o)).all() for o in placed.values())
check("A1_sept_accessoires_proceduraux", len(placed) == 7 and finite and all(r["sommets"] >= 8 for r in rows.values()) and all(o.parent == rig and o.parent_type == "BONE" for o in placed.values()), rows)

# A2 points d'attache : positions et non-pénétration
palm = {}
for side in "LR":
    origin, x, y, z = A._hand_frame(rig, side)
    hand_head = np.array((rig.matrix_world @ rig.pose.bones["hand." + side].head)[:])
    palm[side] = float(np.linalg.norm(origin - hand_head))
back = placed["sac_a_dos"]
back_points = world_points(back)
inside = 0
for p in back_points:
    location, normal, _, distance = tree.find_nearest(Vector(p))
    if location is not None and (Vector(p) - location).dot(normal) < 0:
        inside += 1
glasses_points = world_points(placed["lunettes"])
glasses_min = min(tree.find_nearest(Vector(p))[3] for p in glasses_points)
glasses_inside = sum(1 for p in glasses_points if (lambda r: r[0] is not None and (Vector(p) - r[0]).dot(r[1]) < 0)(tree.find_nearest(Vector(p))))
back_gap = min(tree.find_nearest(Vector(p))[3] for p in back_points)
eyes = np.mean([skeleton._eye_centre(body, e) for e in skeleton.eyes_of(body)], axis=0)
glasses_centre = glasses_points.mean(axis=0)
check("A2_points_d_attache_sans_penetration", all(d < 0.06 for d in palm.values()) and inside == 0 and glasses_inside == 0 and 0.0 < back_gap < 0.03 and 0.002 < glasses_min < 0.03 and np.linalg.norm(glasses_centre[[0, 2]] - eyes[[0, 2]]) < 0.02,
      {"paume_a_la_tete_de_main_m": {k: round(v, 3) for k, v in palm.items()}, "sac_a_dos_sommets_a_l_interieur": inside, "sac_a_dos_distance_min_au_dos_m": round(float(back_gap), 4), "lunettes_a_l_interieur": glasses_inside,
       "lunettes_distance_min_au_visage_m": round(float(glasses_min), 4), "lunettes_centre_a_l_axe_des_yeux_m": round(float(np.linalg.norm(glasses_centre[[0, 2]] - eyes[[0, 2]])), 4)})

# A3 suit l'os
phone = placed["telephone"]
before = world_points(phone).mean(axis=0)
hand_before = A._hand_frame(rig, "R")[0]
rig.pose.bones["arm_upper.R"].rotation_mode = "XYZ"
rig.pose.bones["arm_upper.R"].rotation_euler = Euler((0.0, 0.0, np.radians(-60.0)))
bpy.context.view_layer.update()
after = world_points(phone).mean(axis=0)
hand_after = A._hand_frame(rig, "R")[0]
moved_phone, moved_hand = after - before, hand_after - hand_before
rig.pose.bones["arm_upper.R"].rotation_euler = (0.0, 0.0, 0.0)
bpy.context.view_layer.update()
check("A3_l_accessoire_suit_l_os", float(np.linalg.norm(moved_hand)) > 0.2 and float(np.linalg.norm(moved_phone - moved_hand)) < 0.02, {"deplacement_main_m": round(float(np.linalg.norm(moved_hand)), 3), "ecart_telephone_main_m": round(float(np.linalg.norm(moved_phone - moved_hand)), 4)})

# A4 préhension
A.release_grasp(body, "R")
open_tips = np.array(A.fingertip_distances(body, "R"))
A.apply_grasp(body, "R", "poignee")
closed_tips = np.array(A.fingertip_distances(body, "R"))
half = np.array((A.apply_grasp(body, "R", "poignee", 0.5), A.fingertip_distances(body, "R"))[1])
A.release_grasp(body, "R")
reopened = np.array(A.fingertip_distances(body, "R"))
bag = placed["sac_a_main"]
A.apply_grasp(body, "R", "poignee")
origin, hx, hy, hz = A._hand_frame(rig, "R")
bag_points = world_points(bag)
handle_axis_point = origin + np.stack([hx, hy, hz], axis=1) @ A._grip(body, "R")[0]  # centre de la poignée (monde)
A.apply_grasp(body, "R", "poignee")
tips = np.array([np.array((rig.matrix_world @ rig.pose.bones[f"{f}.03.R"].tail)[:]) for f in A.FINGERS])
tip_to_handle = np.linalg.norm(tips - handle_axis_point, axis=1)
A.release_grasp(body, "R")
check("A4_prehension_fermeture_retour_et_contact", float(np.mean(closed_tips / open_tips)) < 0.7 and np.all(closed_tips < half) and np.all(half < open_tips) and np.allclose(reopened, open_tips, atol=1e-6) and float(tip_to_handle.max()) < 0.07,
      {"bouts_de_doigts_a_la_paume_ouverte_m": np.round(open_tips, 3).tolist(), "fermee": np.round(closed_tips, 3).tolist(), "rapport_moyen": round(float(np.mean(closed_tips / open_tips)), 2),
       "bouts_de_doigts_a_la_poignee_m": np.round(tip_to_handle, 3).tolist(), "criterion": "rapport < 0,7 ; progression monotone ; retour exact ; bouts de doigts à moins de 7 cm de la poignée"})

# A5 parapluie ouvert / fermé
closed, opened = world_points(placed["parapluie_ferme"]), world_points(placed["parapluie_ouvert"])
width_closed = float(max(np.ptp(closed[:, 0]), np.ptp(closed[:, 1])))
width_open = float(max(np.ptp(opened[:, 0]), np.ptp(opened[:, 1])))
check("A5_parapluie_ouvert_plus_large_que_ferme", width_open > 3 * width_closed and width_open > 0.7, {"largeur_fermee_m": round(width_closed, 3), "largeur_ouverte_m": round(width_open, 3)})

# retrait : la préhension est relâchée quand le dernier objet tenu est retiré
for key in ("sac_a_main", "telephone", "parapluie_ferme", "parapluie_ouvert"):
    A.remove_accessory(placed[key])
released = np.array(A.fingertip_distances(body, "R"))
check("A5b_retrait_relache_la_main", np.allclose(released, open_tips, atol=1e-6) and len([o for o in A.accessories_of(body)]) == 3, {"restants": [o[A.MARKER] for o in A.accessories_of(body)]})

# A6 échelle selon la stature
child, child_rig = fresh({"age": 0.0})
bag_child = A.add_accessory(child, "sac_de_courses")
child_height = float(np.ptp(world_points(bag_child)[:, 2]))
adult, adult_rig = fresh()
bag_adult = A.add_accessory(adult, "sac_de_courses")
adult_height = float(np.ptp(world_points(bag_adult)[:, 2]))
check("A6_dimensions_selon_la_stature", child_height < adult_height, {"hauteur_sac_adulte_m": round(adult_height, 3), "hauteur_sac_enfant_m": round(child_height, 3)})

# A7 erreurs
errors = []
for call in (lambda: A.add_accessory(adult, "nexistepas"), lambda: A.add_accessory(adult, "sac_de_courses")):
    try:
        call()
        errors.append(False)
    except ValueError:
        errors.append(True)
for obj in list(adult.children):
    if obj.type == "ARMATURE":
        bpy.data.objects.remove(obj, do_unlink=True)
try:
    A.add_accessory(adult, "lunettes")
    errors.append(False)
except ValueError:
    errors.append(True)
try:
    A.apply_grasp(adult, "R", "inconnue")
    errors.append(False)
except (ValueError, IndexError):
    errors.append(True)
check("A7_cas_invalides_refuses", all(errors), errors)

# A9 panneau et opérateurs
body9, rig9 = fresh()
bpy.context.view_layer.objects.active = body9
ok_ops = bpy.ops.humanloom.accessory_add(piece="sac_a_main") == {"FINISHED"} and len(A.accessories_of(body9)) == 1
closed_tip = np.array(A.fingertip_distances(body9, "R"))
ok_ops &= bpy.ops.humanloom.grasp(side="R", pose="ouvrir") == {"FINISHED"} and float(np.mean(np.array(A.fingertip_distances(body9, "R")) / closed_tip)) > 1.2
ok_ops &= bpy.ops.humanloom.grasp(side="R", pose="poignee", amount=1.0) == {"FINISHED"}
ok_ops &= bpy.ops.humanloom.accessory_remove(piece="sac_a_main") == {"FINISHED"} and not A.accessories_of(body9)
check("A9_operateurs_et_panneau", ok_ops and hasattr(bpy.types, "HUMANLOOM_PT_accessories"), {"operateurs": ok_ops})

# A8 aucun nom de tiers
text = (ROOT / "extension" / "accessories.py").read_text(encoding="utf-8")
check("A8_aucun_asset_tiers", not any(w in text for w in ("mixamo", "Epic", "Marvelous", "CLO3D", "Daz", "Unreal", "import_scene", "obj_import")), "formes générées par le code")

if OUT:
    Path(OUT).write_text(json.dumps(results, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
print("RESULT", "FAIL " + ", ".join(failures) if failures else "PASS")
sys.exit(1 if failures else 0)
