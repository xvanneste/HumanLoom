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

# A3 suit l'os : la position du téléphone DANS LE REPÈRE DE LA MAIN ne change pas quand le bras tourne (il est décalé de la paume : seul le repère de la main compte)
phone = placed["telephone"]


def in_hand_frame():
    bpy.context.view_layer.update()
    origin, hx, hy, hz = A._hand_frame(rig, "R")
    return (world_points(phone).mean(axis=0) - origin) @ np.stack([hx, hy, hz], axis=1), origin


local_before, hand_before = in_hand_frame()
rig.pose.bones["arm_upper.R"].rotation_mode = "XYZ"
rig.pose.bones["arm_upper.R"].rotation_euler = Euler((0.0, 0.0, np.radians(-60.0)))
local_after, hand_after = in_hand_frame()
rig.pose.bones["arm_upper.R"].rotation_euler = (0.0, 0.0, 0.0)
bpy.context.view_layer.update()
check("A3_l_accessoire_suit_l_os", float(np.linalg.norm(hand_after - hand_before)) > 0.2 and float(np.linalg.norm(local_after - local_before)) < 0.003,
      {"deplacement_main_m": round(float(np.linalg.norm(hand_after - hand_before)), 3), "ecart_repere_main_m": round(float(np.linalg.norm(local_after - local_before)), 5)})

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

# A10 téléphone : vraie forme avec écran (2 matériaux), pose « à l'oreille » mesurée, retrait propre
bodyp, rigp = fresh()
phone = A.add_accessory(bodyp, "telephone")
two_materials = len(phone.data.materials) == 2 and {p.material_index for p in phone.data.polygons} == {0, 1}
report = A.pose_phone_ear(bodyp, "R")
bpy.context.view_layer.update()
pts = world_points(phone)
target, head_centre = A.ear_target(bodyp, "R")
screen_idx = max((p for p in phone.data.polygons if p.material_index == 1), key=lambda p: p.center[2])  # face avant de la plaque d'écran
screen_normal = np.array((phone.matrix_world.to_3x3() @ screen_idx.normal)[:])
to_head = head_centre - pts.mean(axis=0)
to_head /= np.linalg.norm(to_head)
screen_angle = float(np.degrees(np.arccos(np.clip(screen_normal / np.linalg.norm(screen_normal) @ to_head, -1, 1))))
check("A10_telephone_ecran_et_oreille", two_materials and report["ecart_mm"] <= 15.0 and report["angle_normale_deg"] <= 45.0 and screen_angle <= 60.0,
      {"deux_materiaux": two_materials, "ecart_mm": report["ecart_mm"], "angle_normale_deg": report["angle_normale_deg"], "ecran_vers_tete_deg": round(screen_angle, 1), "limites": "écart ≤ 15 mm, normale paume ≤ 45°, écran ≤ 60° de la tête (recherche aléatoire, posture de modélisation non issue de données publiées)"})
A.remove_accessory(phone)
A.reset_hand(bodyp, "R")

# A11 parapluie tenu : tige verticale dans le poing (mesures sur le maillage monde)
bodyu, rigu = fresh()
rows = {}
for key in ("parapluie_ferme", "parapluie_ouvert"):
    umbrella = A.add_accessory(bodyu, key)
    bpy.context.view_layer.update()
    up = world_points(umbrella)
    extent = up.max(axis=0) - up.min(axis=0)
    rows[key] = {"etendue_m": extent.round(3).tolist()}
    if key == "parapluie_ferme":
        rows[key]["vertical"] = bool(extent[2] > 0.8 and extent[0] < 0.10 and extent[1] < 0.10)
    else:
        rows[key]["vertical"] = bool(extent[2] > 0.8 and abs(extent[0] - extent[1]) < 0.05)
    A.remove_accessory(umbrella)
hand_rest = np.array([float(a) for a in rigu.pose.bones["arm_lower.R"].rotation_euler])
check("A11_parapluie_tenu_vertical", all(r["vertical"] for r in rows.values()) and float(np.abs(hand_rest).max()) < 1e-6, {**rows, "bras_remis_a_zero": float(np.abs(hand_rest).max()) < 1e-6})

# A12 matériaux PROPRES à chaque accessoire (GRM-002) : le même accessoire, de deux couleurs, sur deux personnages ne se recolore pas mutuellement ; le retrait libère son matériau
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
bpy.ops.humanloom.create()
body_a = bpy.context.object
rig_a = skeleton.install(body_a)
bpy.ops.humanloom.create()
body_b = bpy.context.object
rig_b = skeleton.install(body_b)
red, blue = (0.8, 0.1, 0.1), (0.1, 0.1, 0.8)
bag_a = A.add_accessory(body_a, "sac_a_dos", red)
bag_b = A.add_accessory(body_b, "sac_a_dos", blue)
mat_a, mat_b = bag_a.material_slots[0].material, bag_b.material_slots[0].material
base_a = tuple(round(v, 3) for v in mat_a.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value[:3])
base_b = tuple(round(v, 3) for v in mat_b.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value[:3])
name_b = mat_b.name
A.remove_accessory(bag_b)
check("A12_materiaux_propres_a_chaque_accessoire", mat_a is not mat_b and base_a == tuple(round(v, 3) for v in red) and base_b == tuple(round(v, 3) for v in blue) and bpy.data.materials.get(name_b) is not mat_b and mat_a.name in bpy.data.materials,
      {"couleur_a": base_a, "couleur_b": base_b, "materiau_b_libere": bpy.data.materials.get(name_b) is not mat_b})

# A13 pose de l'utilisateur conservée (GRM-010) : ajouter puis retirer un accessoire tenu en main (préhension + coude/poignet du parapluie) restitue EXACTEMENT les modes de rotation et les valeurs d'avant
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
bpy.ops.humanloom.create()
body_p = bpy.context.object
rig_p = skeleton.install(body_p)
tracked = ["index.01.R", "index.02.R", "thumb.01.R", "hand.R", "arm_lower.R", "arm_upper.R"]
rig_p.pose.bones["index.01.R"].rotation_mode = "QUATERNION"
rig_p.pose.bones["index.01.R"].rotation_quaternion = (0.9659, 0.2588, 0.0, 0.0)
rig_p.pose.bones["index.02.R"].rotation_mode = "ZXY"
rig_p.pose.bones["index.02.R"].rotation_euler = (0.2, 0.1, -0.05)
rig_p.pose.bones["thumb.01.R"].rotation_mode = "AXIS_ANGLE"
rig_p.pose.bones["thumb.01.R"].rotation_axis_angle = (0.3, 0.0, 1.0, 0.0)
rig_p.pose.bones["hand.R"].rotation_mode = "XYZ"
rig_p.pose.bones["hand.R"].rotation_euler = (0.1, 0.2, 0.3)
rig_p.pose.bones["arm_lower.R"].rotation_mode = "QUATERNION"
rig_p.pose.bones["arm_lower.R"].rotation_quaternion = (0.9, 0.0, 0.0, 0.4359)
rig_p.pose.bones["arm_upper.R"].location = (0.0, 0.0, 0.0)
bpy.context.view_layer.update()


def pose_snapshot():
    return {n: (rig_p.pose.bones[n].rotation_mode, tuple(round(v, 6) for v in rig_p.pose.bones[n].rotation_quaternion), tuple(round(v, 6) for v in rig_p.pose.bones[n].rotation_euler), tuple(round(v, 6) for v in rig_p.pose.bones[n].rotation_axis_angle)) for n in tracked}


before_pose = pose_snapshot()
umbrella_p = A.add_accessory(body_p, "parapluie_ferme")
changed_pose = pose_snapshot() != before_pose
A.remove_accessory(umbrella_p)
after_pose = pose_snapshot()
check("A13_pose_de_l_utilisateur_conservee", changed_pose and after_pose == before_pose and A.POSE_BACKUP not in rig_p, {"la_pose_change_pendant_l_accessoire": changed_pose, "identique_apres_retrait": after_pose == before_pose, "differences": {n: (before_pose[n], after_pose[n]) for n in tracked if before_pose[n] != after_pose[n]}})

# A8 aucun nom de tiers
text = (ROOT / "extension" / "accessories.py").read_text(encoding="utf-8")
check("A8_aucun_asset_tiers", not any(w in text for w in ("mixamo", "Epic", "Marvelous", "CLO3D", "Daz", "Unreal", "import_scene", "obj_import")), "formes générées par le code")

if OUT:
    Path(OUT).write_text(json.dumps(results, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
print("RESULT", "FAIL " + ", ".join(failures) if failures else "PASS")
sys.exit(1 if failures else 0)
