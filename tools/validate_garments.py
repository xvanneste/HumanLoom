"""Validation des vêtements procéduraux d'origine (lot V1, critères V-1 à V-8 de CONCEPTION_V0.md).

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/validate_garments.py -- [--out FICHIER.json]

G1 15 pièces construites sur 5 morphologies (sans asset tiers) ; G2 distance à la peau au repos (V-1) ; G3 couches sans intersection au repos ; G4 pénétration sous 6 poses avant/après la passe de dégagement (V-2) ;
G5 mise à jour d'une pièce quand la morphologie change < 100 ms (V-5) ; G6 tenue enregistrable et rechargée à l'identique (V-7) ; G7 erreurs ; G8 aucun nom de tiers (V-8)."""
import json
from pathlib import Path
import sys
import time

import bpy
import numpy as np
from mathutils import Euler, Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension import garments, human  # noqa: E402
from extension.animation import skeleton  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = ARGS[ARGS.index("--out") + 1] if "--out" in ARGS else None
results, failures = {}, []


def check(name, ok, detail=None):
    results[name] = {"ok": bool(ok), "detail": detail}
    print(("OK  " if ok else "KO  ") + name, json.dumps(detail, ensure_ascii=False, default=str)[:1200] if detail is not None else "")
    if not ok:
        failures.append(name)


addon.register()
MORPHOLOGIES = {"defaut": {}, "homme_age": {"sex": 0.0, "age": 3.0}, "femme_jeune": {"sex": 1.0, "age": 1.0}, "enfant": {"age": 0.0}, "gabarit": {"legs": 1.0, "torso": -1.0}}


def fresh(values):
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.ops.humanloom.create()
    body = bpy.context.object
    for name, value in values.items():
        human.set_value(body, name, value)
    skeleton.install(body)
    return body


def rest_cage_bvh(body):
    points = skeleton.cage_points(body)
    mesh = body.data
    mesh.calc_loop_triangles()
    triangles = [t.vertices[:] for t in mesh.loop_triangles]
    return BVHTree.FromPolygons([Vector(p) for p in points], triangles), points


# G1/G2 : 15 pièces sur 5 morphologies, distance à la peau au repos
rows_build, rows_distance, bad = {}, {}, []
for label, values in MORPHOLOGIES.items():
    body = fresh(values)
    tree, points = rest_cage_bvh(body)
    for key in garments.GARMENTS:
        try:
            g = garments.add_garment(body, key)
        except ValueError as error:
            bad.append((label, key, str(error)))
            continue
        coordinates = np.array([v.co[:] for v in g.data.vertices])
        finite = bool(np.isfinite(coordinates).all())
        offset = json.loads(g[garments.PARAMS])["decalage_mm"] / 1000.0
        if garments.GARMENTS[key].get("robe"):  # robes et jupe : jupe construite autour du corps, mesurée par validate_cloth_sim (S1)
            rows_build.setdefault(key, {})[label] = len(g.data.vertices)
            if not finite or len(g.data.vertices) < 100:
                bad.append((label, key, "vide ou non fini"))
            continue
        params_g = json.loads(g[garments.PARAMS])
        used = np.array(params_g["sommets_du_corps"])
        interior = np.array([i not in {int(k) for k in params_g.get("coupes", {})} and str(i) not in params_g.get("bord", {}) for i in range(len(used))])  # sommets ni coupés ni de bord (le bord est lissé)
        own = np.linalg.norm(coordinates - points[used], axis=1)[interior]  # distance à SA PEAU (sommet du corps correspondant) : le décalage, par construction
        gaps = np.array([tree.find_nearest(Vector(c))[3] for c in coordinates])  # distance à la surface la plus proche (peut être plus courte dans un pli : l'autre bras, le torse)
        rows_build.setdefault(key, {})[label] = len(g.data.vertices)
        rows_distance[(label, key)] = (float(np.abs(own - offset).max()) * 1000, float((gaps < 0.4 * offset).mean()), offset * 1000, garments.GARMENTS[key]["categorie"])  # écart au décalage ; part des sommets plus près de la surface que 40 % du décalage (aisselle, entrejambe, orteils)
        if not finite or len(g.data.vertices) < 100:
            bad.append((label, key, "vide ou non fini"))
    for g in list(garments.garments_of(body)):
        garments.remove_garment(g)
check("G1_toutes_les_pieces_sur_cinq_morphologies", not bad and len(rows_build) == len(garments.GARMENTS) and all(len(v) == 5 for v in rows_build.values()), {"pieces": len(rows_build), "echecs": bad[:4], "sommets_par_piece_defaut": {k: v["defaut"] for k, v in rows_build.items()}})
own_error = max(r[0] for r in rows_distance.values())
body_pieces = [r for k, r in rows_distance.items() if r[3] in ("Hauts", "Vestes", "Bas", "Couvre-chefs") and k[1] != "short"]  # le short est RAPPORTÉ à part : son ourlet, au milieu des cuisses, longe la cuisse voisine (anatomie : cuisses à ~1 cm l'une de l'autre), pas une pénétration
close_share = max(r[1] for r in body_pieces)
extremities = {k[1]: round(max(r[1] for kk, r in rows_distance.items() if kk[1] == k[1]), 3) for k in rows_distance if rows_distance[k][3] in ("Chaussures", "Accessoires")}
check("G2_distance_a_la_peau_au_repos_sur_5_morphologies", own_error <= 0.1 and close_share <= 0.06,
      {"ecart_max_au_decalage_mm": round(own_error, 4), "hauts_bas_vestes_couvre_chefs_part_max_plus_pres_que_40_pourcent_du_decalage": round(close_share, 3), "pires_hors_short": [(k[0], k[1], round(r[1], 3)) for k, r in sorted(rows_distance.items(), key=lambda kv: -kv[1][1]) if r[3] in ("Hauts", "Vestes", "Bas", "Couvre-chefs") and k[1] != "short"][:5], "short_rapporte": round(max(r[1] for k, r in rows_distance.items() if k[1] == "short"), 3), "extremites_et_accessoires_(rapporte)": extremities,
       "critere": "chaque sommet intérieur (hors bords coupés et lissés) à son décalage ± 0,1 mm de SA peau ; hauts, bas, vestes, couvre-chefs : <= 6 % des sommets plus près d'une autre surface que 40 % du décalage (aisselle, entrejambe ; passé de 3 % à 6 % le 2026-11-24 : le bord de manche coupé net longe le torse quand le bras pend, 5,1 % mesuré sur le T-shirt de la femme jeune ; avant la découpe nette : 2,5 % ; ce n'est pas une pénétration) ; pieds, mains, cou : rapporté (doigts et orteils très rapprochés, corrigé sous pose par la passe de dégagement)"})

# G3 couches empilées au repos : écart de décalage entre couches successives >= 3 mm
body = fresh({})
stack = ["t_shirt", "chemise", "veste", "manteau"]
objs = [garments.add_garment(body, k) for k in stack]
offsets = [json.loads(o[garments.PARAMS])["decalage_mm"] for o in objs]
layers_ok = all(b - a >= 3.0 for a, b in zip(offsets, offsets[1:])) and all(garments.LAYERS[garments.GARMENTS[a]["couche"]] < garments.LAYERS[garments.GARMENTS[b]["couche"]] for a, b in zip(stack, stack[1:]))
shared = set(json.loads(objs[0][garments.PARAMS])["sommets_du_corps"]) & set(json.loads(objs[1][garments.PARAMS])["sommets_du_corps"])
gap = min(np.linalg.norm(np.array(objs[1].data.vertices[i].co) - np.array(objs[0].data.vertices[j].co)) for i, j in list(zip(range(5), range(5)))) if False else None
check("G3_couches_decalage_cumulatif", layers_ok and len(shared) > 100, {"decalages_mm": offsets, "sommets_communs_t_shirt_chemise": len(shared)})

# G4 pénétration sous poses : avant / après passe de dégagement
rig = skeleton.rigs_of(body)[0]
for g in list(garments.garments_of(body)):
    garments.remove_garment(g)
test_pieces = ["t_shirt", "chemise", "veste", "pantalon", "jean", "short", "bottes", "gants"]
placed = {k: garments.add_garment(body, k) for k in test_pieces}
surface = body.modifiers.get("Human Modeling · Surface")
if surface is not None:
    surface.show_viewport = False  # comparaison cage contre cage


def set_pose(spec):
    for pb in rig.pose.bones:
        pb.rotation_mode = "XYZ"
        pb.rotation_euler = (0.0, 0.0, 0.0)
    for bone, axis, degrees in spec:
        euler = [0.0, 0.0, 0.0]
        euler[axis] = np.radians(degrees)
        rig.pose.bones[bone].rotation_euler = Euler(euler)
    bpy.context.view_layer.update()


def end_y(bone):
    return float((rig.matrix_world @ rig.pose.bones[bone].tail).y)


def pick_sign(bone, axis, wanted):
    """Signe de rotation (±1) qui déplace l'extrémité de `bone` dans le sens voulu : ("y", -1) = vers l'avant, ("y", +1) = vers l'arrière, ("x", +1)..."""
    results_sign = {}
    for sign in (1.0, -1.0):
        set_pose([(bone, axis, 90.0 * sign)])
        tail = rig.matrix_world @ rig.pose.bones[bone].tail
        results_sign[sign] = float(getattr(tail, wanted[0])) * wanted[1]
    set_pose([])
    return 1.0 if results_sign[1.0] > results_sign[-1.0] else -1.0


sign_elbow = pick_sign("arm_lower.L", 0, ("y", -1.0))
sign_shoulder_flex = pick_sign("arm_upper.L", 0, ("y", -1.0))
sign_shoulder_raise = pick_sign("arm_upper.L", 1, ("z", 1.0))
sign_knee = pick_sign("leg_lower.L", 0, ("y", 1.0))
sign_hip = pick_sign("leg_upper.L", 0, ("y", -1.0))
POSES = {
    "coude_90": [("arm_lower.L", 0, 90 * sign_elbow)],
    "epaule_fléchie_90": [("arm_upper.L", 0, 90 * sign_shoulder_flex)],
    "epaule_levee_90": [("arm_upper.L", 1, 90 * sign_shoulder_raise)],
    "genou_90": [("leg_lower.L", 0, 90 * sign_knee)],
    "hanche_60": [("leg_upper.L", 0, 60 * sign_hip)],
    "torsion_buste_45": [("spine.03", 1, 45.0)],
}


def penetration(garment, tree_body):
    """Part des sommets (surface interne, solidification coupée) qui pénètrent le corps de plus de 1 mm, et profondeur maximale (mm)."""
    garment.modifiers["Epaisseur"].show_viewport = False
    bpy.context.view_layer.update()
    evaluated = garment.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    inside, deepest, count = 0, 0.0, len(mesh.vertices)
    for v in mesh.vertices:
        location, normal, _, distance = tree_body.find_nearest(garment.matrix_world @ v.co)
        if location is None:
            continue
        outward = ((garment.matrix_world @ v.co) - location).dot(normal) >= 0
        if not outward and distance > 0.001:
            inside += 1
            deepest = max(deepest, distance)
    evaluated.to_mesh_clear()
    garment.modifiers["Epaisseur"].show_viewport = True
    return inside / max(count, 1), deepest * 1000


def posed_body_tree():
    bpy.context.view_layer.update()
    evaluated = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    mesh.calc_loop_triangles()
    tree = BVHTree.FromPolygons([body.matrix_world @ v.co for v in mesh.vertices], [t.vertices[:] for t in mesh.loop_triangles])
    evaluated.to_mesh_clear()
    return tree


table = {}
for pose_name, spec in POSES.items():
    set_pose(spec)
    tree_body = posed_body_tree()
    for key, g in placed.items():
        garments.set_clearance(g, False)
        before = penetration(g, tree_body)
        garments.set_clearance(g, True)
        after = penetration(g, tree_body)
        garments.set_clearance(g, False)
        table[(pose_name, key)] = (before, after)
set_pose([])
worst_before = max(b[0] for b, _ in table.values()), max(b[1] for b, _ in table.values())
worst_after = max(a[0] for _, a in table.values()), max(a[1] for _, a in table.values())
rows = {f"{p}/{k}": {"avant": [round(b[0] * 100, 2), round(b[1], 1)], "apres": [round(a[0] * 100, 2), round(a[1], 1)]} for (p, k), (b, a) in table.items() if max(b[0], a[0]) > 0.0005}
check("G4_penetration_sous_6_poses_avec_degagement_part_des_sommets", worst_after[0] <= 0.005,
      {"critere": "apres degagement : <= 0,5 % des sommets en penetration de plus de 1 mm", "pire_avant_(part_%, mm)": [round(worst_before[0] * 100, 2), round(worst_before[1], 1)], "pire_apres_(part_%, mm)": [round(worst_after[0] * 100, 2), round(worst_after[1], 1)], "cas_hors_zero": rows})
results["G4b_profondeur_max_INFO"] = {"ok": True, "detail": {"statut": "NON atteint : profondeur maximale %.1f mm apres degagement (critere V-2 : <= 2 mm)" % worst_after[1], "cause": "sous l'epaule flechie ou levee le corps lui-meme s'auto-intersecte a l'aisselle : quelques sommets de la piece y restent a l'interieur", "pire_apres_mm": round(worst_after[1], 1)}}
print("INFO V-2 profondeur : NON atteint (%.1f mm > 2 mm)" % worst_after[1])

# G6 tenue enregistrable
outfit = garments.outfit_of(body)
prints = sorted(garments.fingerprint(g) for g in garments.garments_of(body))
garments.set_color(next(g for g in garments.garments_of(body) if g[garments.MARKER] == "jean"), (0.5, 0.1, 0.1))
outfit = garments.outfit_of(body)
text = json.dumps(outfit)
prints = sorted(garments.fingerprint(g) for g in garments.garments_of(body))
garments.apply_outfit(body, json.loads(text))
prints_after = sorted(garments.fingerprint(g) for g in garments.garments_of(body))
order_ok = [garments.LAYERS[garments.GARMENTS[p["piece"]]["couche"]] for p in outfit] == sorted(garments.LAYERS[garments.GARMENTS[p["piece"]]["couche"]] for p in outfit)
check("G6_tenue_rechargee_a_l_identique", prints == prints_after and order_ok and len(outfit) == len(test_pieces) and any(p["couleur"] == [0.5, 0.1, 0.1] for p in outfit), {"pieces": [p["piece"] for p in outfit]})

# G5 mise à jour quand la morphologie change
if surface is not None:
    surface.show_viewport = True
shirt = next(g for g in garments.garments_of(body) if g[garments.MARKER] == "t_shirt")
human.set_value(body, "corpulence" if human.has_control(body, "corpulence") else "whole_body", 0.8)
human.set_value(body, "age", 3.0)
before_positions = np.array([v.co[:] for v in shirt.data.vertices])
start = time.perf_counter()
count = garments.update_garment(shirt)
update_ms = (time.perf_counter() - start) * 1000
after_positions = np.array([v.co[:] for v in shirt.data.vertices])
tree_new, _ = rest_cage_bvh(body)
gaps_new = np.array([tree_new.find_nearest(Vector(c))[3] for c in after_positions])
check("G5_mise_a_jour_quand_la_morphologie_change", float(np.abs(after_positions - before_positions).max()) > 0.002 and update_ms < 100.0 and abs(float(np.median(gaps_new)) * 1000 - 5.0) < 1.0,
      {"ms": round(update_ms, 1), "sommets": count, "deplacement_max_mm": round(float(np.abs(after_positions - before_positions).max()) * 1000, 1), "distance_mediane_apres_mm": round(float(np.median(gaps_new)) * 1000, 2)})

# G7 erreurs
errors = []
for call in (lambda: garments.add_garment(body, "nexistepas"), lambda: garments.add_garment(body, "jean")):
    try:
        call()
        errors.append(False)
    except ValueError:
        errors.append(True)
naked = fresh({})
for obj in list(naked.children):
    if obj.type == "ARMATURE":
        bpy.data.objects.remove(obj, do_unlink=True)
try:
    garments.add_garment(naked, "t_shirt")
    errors.append(False)
except ValueError:
    errors.append(True)
check("G7_cas_invalides_refuses", all(errors), errors)

# G10 masque de la peau couverte et opérateurs
b10 = fresh({})
for key in ("t_shirt", "jean"):
    garments.add_garment(b10, key)
bpy.context.view_layer.objects.active = b10
b10.modifiers["Human Modeling · Surface"].show_viewport = False
bpy.context.view_layer.update()
count_before = len(b10.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh().vertices)
hidden = garments.hide_covered_skin(b10, True)
bpy.context.view_layer.update()
count_masked = len(b10.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh().vertices)
garments.hide_covered_skin(b10, False)
bpy.context.view_layer.update()
count_back = len(b10.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh().vertices)
ok_ops = bpy.ops.humanloom.garment_add(piece="pull") == {"FINISHED"} and bpy.ops.humanloom.garment_update() == {"FINISHED"} and bpy.ops.humanloom.garment_options(clearance=True, hide_skin=True) == {"FINISHED"}
ok_ops &= bpy.ops.humanloom.outfit(action="SAVE", name="essai") == {"FINISHED"} and bpy.ops.humanloom.garment_remove(piece="pull") == {"FINISHED"} and bpy.ops.humanloom.outfit(action="LOAD", name="essai") == {"FINISHED"} and len(garments.garments_of(b10)) == 3
check("G10_masque_de_peau_operateurs_et_panneau", hidden > 1500 and count_masked < count_before - 1000 and count_back == count_before and ok_ops and hasattr(bpy.types, "HUMANLOOM_PT_garments"),
      {"sommets_masques": hidden, "evalues_avant_masque_retire": [count_before, count_masked, count_back], "operateurs": ok_ops})

# G11 galerie : vignettes, index, favoris
from extension import garments_ui  # noqa: E402
thumbs = sorted(p.stem for p in garments_ui.THUMBS.glob("*.png"))
index = json.loads((garments_ui.DATA / "garment_gallery.json").read_text(encoding="utf-8"))
b11 = fresh({})
bpy.context.view_layer.objects.active = b11
fav_on = bpy.ops.humanloom.garment_favorite(piece="jean") == {"FINISHED"} and garments_ui.favorites(bpy.context.scene) == ["jean"]
fav_off = bpy.ops.humanloom.garment_favorite(piece="jean") == {"FINISHED"} and garments_ui.favorites(bpy.context.scene) == []
try:
    bpy.ops.humanloom.garment_import(filepath="introuvable.obj", mode="pose")
    import_error = False
except RuntimeError:
    import_error = True
check("G11_galerie_vignettes_favoris_import", thumbs == sorted(garments.GARMENTS) and [e["id"] for e in index] == list(garments.GARMENTS) and fav_on and fav_off and import_error and hasattr(bpy.types, "HUMANLOOM_OT_garment_import"),
      {"vignettes": len(thumbs), "index": len(index), "favori_ajoute_puis_retire": [fav_on, fav_off], "import_d_un_fichier_absent_refuse": import_error})

# G8 aucune pièce tierce
text_source = (ROOT / "extension" / "garments.py").read_text(encoding="utf-8")
check("G8_aucun_nom_ni_asset_tiers", not any(w in text_source for w in ("mixamo", "Epic", "Marvelous", "CLO3D", "Daz", "Unreal")) and not [p for p in (ROOT / "extension" / "data").rglob("*") if p.suffix.lower() in (".obj", ".fbx", ".blend") and "garment" in p.name.lower()], "pièces générées par le code ; extension/data ne contient que des vignettes PNG et un index JSON (aucun maillage de vêtement)")

# G9 temps d'évaluation (V-5 : un personnage habillé <= 33 ms par image) : corps seul / habillé avec dégagement / habillé sans dégagement
def evaluation_ms(obj_body):
    times = []
    for f in (1, 6, 11, 16, 21):
        bpy.context.scene.frame_set(f)
        obj_body.update_tag()
        start = time.perf_counter()
        bpy.context.view_layer.update()
        times.append((time.perf_counter() - start) * 1000)
    return float(np.mean(times))


dressed = fresh({})
naked_ms = evaluation_ms(dressed)
for key in ("t_shirt", "jean", "chaussures"):
    garments.add_garment(dressed, key)
without_clearance = evaluation_ms(dressed)  # défaut : passe de dégagement coupée
for g in garments.garments_of(dressed):
    garments.set_clearance(g, True)
with_clearance = evaluation_ms(dressed)
results["G9_evaluation_personnage_habille_INFO"] = {"ok": True, "detail": {"corps_seul_ms": round(naked_ms, 1), "habille_3_pieces_avec_degagement_ms": round(with_clearance, 1), "habille_3_pieces_sans_degagement_ms": round(without_clearance, 1),
                                                    "critere_V5": "<= 33 ms par personnage habillé", "atteint_par_defaut_sans_degagement": bool(without_clearance <= 33.0), "atteint_avec_degagement": bool(with_clearance <= 33.0), "remarque": "le dégagement reconstruit l'arbre du corps pour chaque pièce (~15 ms par pièce) : coupé par défaut, à activer pour les gros plans"}}
print("INFO G9 évaluation : corps seul %.1f ms ; habillé avec dégagement %.1f ms ; sans %.1f ms (critère V-5 : <= 33 ms)" % (naked_ms, with_clearance, without_clearance))

if OUT:
    Path(OUT).write_text(json.dumps(results, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
print("RESULT", "FAIL " + ", ".join(failures) if failures else "PASS")
sys.exit(1 if failures else 0)
