"""Validation du visage complet (lot L1) : galerie/mélange de poses, visèmes, correspondance ARKit, formes cuites, clips faciaux en NLA indépendants du corps.

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/validate_face_poses.py -- [--out FICHIER.json]

P1 galerie (index, favoris, poses utilisateur) ; P2 application et mélange de poses ; P3 visèmes : 15 poses, source déclarée « non vérifié », ouverture croissante a > e > i ;
P4 ARKit : 52 coefficients, couverture numérique, aucun coefficient hors liste, conversion en pose ; P5 formes cuites : une forme par commande + coefficients couverts, déplacements et restauration ;
P6 clips NLA : le clip facial et un mouvement de corps coexistent et s'éteignent indépendamment."""
import json
from pathlib import Path
import sys

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension import human  # noqa: E402
from extension.animation import dental, face, skeleton  # noqa: E402
from extension.proportions import FACE_COMMANDS  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = ARGS[ARGS.index("--out") + 1] if "--out" in ARGS else None
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
rig = skeleton.install(body)
scene = bpy.context.scene

# P1
rows = face.gallery(scene)
face.save_pose(scene, "ma_pose", {"smile_L": 0.5})
face.toggle_favorite(scene, "expression:joie")
rows2 = face.gallery(scene)
check("P1_galerie_index_favoris_utilisateur", len(rows) >= 8 + 15 and "utilisateur:ma_pose" in [r["id"] for r in rows2] and rows2[0]["id"] == "expression:joie" and rows2[0]["favori"]
      and not face.toggle_favorite(scene, "expression:joie") and all(r["source"] for r in rows2), {"nombre": len(rows), "categories": sorted({r["categorie"] for r in rows2})})

# P2
a, b = face.builtin_poses()["expression:joie"]["pose"], face.builtin_poses()["expression:surprise"]["pose"]
mix = face.mix_poses(a, b, 0.25)
face.apply_pose(body, mix)
got = face.read_pose(body)
check("P2_application_et_melange", abs(got["smile_duchenne"] - 0.75 * a["smile_duchenne"]) < 1e-3 and abs(got["brow_up"] - 0.25 * b["brow_up"]) < 1e-3 and abs(got["_jaw"] - 0.25 * b["_jaw"]) < 0.05
      and face.mix_poses(a, b, 0.0)["smile_duchenne"] == a["smile_duchenne"] and face.mix_poses(a, b, 1.0)["brow_up"] == b["brow_up"], {"lu": got})
face.apply_pose(body, {})
check("P2b_neutre_remet_a_zero", face.read_pose(body) == {}, face.read_pose(body))
# P2c le regard fait partie de la pose lue (ANI-010) : lecture, mélange et restauration exacts
face.apply_pose(body, {"_gaze": [20.0, 10.0], "smile_L": 0.5})
read_with_gaze = face.read_pose(body)
saved_gaze = dict(read_with_gaze)
face.apply_pose(body, {})
face.apply_pose(body, {"_gaze": [0.0, 0.0]})
after_reset = face.read_pose(body)
face.apply_pose(body, saved_gaze)
restored = face.read_pose(body)
check("P2c_regard_dans_la_pose_lue", abs(read_with_gaze.get("_gaze", [0, 0])[0] - 20.0) < 0.05 and abs(read_with_gaze.get("_gaze", [0, 0])[1] - 10.0) < 0.05 and "_gaze" not in after_reset and restored == saved_gaze,
      {"lu": read_with_gaze.get("_gaze"), "apres_remise_a_zero": after_reset.get("_gaze"), "restaure": restored.get("_gaze")})
face.apply_pose(body, {"_gaze": [0.0, 0.0]})
face.apply_pose(body, {})


# P3
visemes = {k: v for k, v in face.builtin_poses().items() if v["categorie"] == "visème"}
opens = {k: visemes["visème:" + k]["pose"].get("_jaw", 0.0) for k in face.VISEMES}
check("P3_visemes", len(visemes) == 15 and all("non vérifié" in v["source"] for v in visemes.values()) and opens["aa"] > opens["e"] > opens["ih"] and opens["sil"] == 0
      and all(set(p["pose"]) - {"_jaw", "_tongue", "_gaze"} <= set(FACE_COMMANDS) and set(p["pose"].get("_tongue", {})) <= set(dental.TONGUE_SHAPES) for p in visemes.values()), {"ouvertures_deg": opens})
for key in face.VISEMES:
    face.apply_pose(body, face.VISEMES[key][1])
face.apply_pose(body, {})

# P4
report = face.arkit_report()
pose = face.arkit_to_pose({"jawOpen": 0.5, "mouthSmileLeft": 1.0, "tongueOut": 0.5, "eyeLookUpLeft": 1.0, "eyeLookUpRight": 1.0, "browInnerUp": 0.4})
try:
    face.arkit_to_pose({"inventé": 1.0})
    rejected = False
except ValueError:
    rejected = True
check("P4_arkit_couverture", report["total"] == 52 and sum(report["par_categorie"].values()) == 52 and 0.3 < report["couverture_ponderee"] <= 1.0 and rejected
      and abs(pose["_jaw"] - 15.0) < 1e-6 and pose["smile_L"] == 1.0 and abs(pose["_tongue"]["langue_sortie"] - 0.5) < 1e-6 and abs(pose["_gaze"][1] - 35.0) < 1e-6 and abs(pose["brow_inner_up"] - 0.4) < 1e-6
      and all(c in FACE_COMMANDS or c.startswith("_") for ent in face.ARKIT.values() for c, _ in ent[1]),
      {"par_categorie": report["par_categorie"], "couverture_ponderee": report["couverture_ponderee"], "non_couverts": report["non_couverts"]})
face.apply_pose(body, pose)
check("P4b_arkit_applique", face.read_pose(body).get("smile_L") == 1.0 and "_tongue" in face.read_pose(body))

# P4c mâchoire latérale et propulsion (jawLeft / jawRight / jawForward) : translations de l'os `jaw`, mesurées sur la pointe du menton (sommet JAW_CHIN) de la cage posée
face.apply_pose(body, {})
skeleton_points = lambda: skeleton.cage_points(body)  # cage de repos (sans pose) : repère de comparaison
bpy.context.view_layer.update()


def chin_world():
    saved = [(m, m.show_viewport) for m in body.modifiers]
    for m in body.modifiers:
        m.show_viewport = m.name in ("HL Human", "HL Rig", "HL Rig DQS")
    bpy.context.view_layer.update()
    ev = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = ev.to_mesh()
    point = np.array(me.vertices[skeleton.JAW_CHIN].co[:])
    ev.to_mesh_clear()
    for m, state in saved:
        m.show_viewport = state
    return point


rest_chin = chin_world()
rows_jaw = {}
for label, coefficients in (("gauche", {"jawLeft": 1.0}), ("droite", {"jawRight": 1.0}), ("avant", {"jawForward": 1.0}), ("gauche_et_droite_se_compensent", {"jawLeft": 1.0, "jawRight": 1.0}), ("demi_gauche", {"jawLeft": 0.5})):
    face.apply_pose(body, face.arkit_to_pose(coefficients))
    moved = (chin_world() - rest_chin) * 1000.0
    rows_jaw[label] = {"dx_mm": round(float(moved[0]), 2), "dy_mm": round(float(moved[1]), 2), "dz_mm": round(float(moved[2]), 2), "lue": {k: v for k, v in face.read_pose(body).items() if k.startswith("_jaw_")}}
face.apply_pose(body, {})
back = (chin_world() - rest_chin) * 1000.0
# le menton suit l'os à ~85 % (poids de peau de la pointe du menton < 1 : 6,41 mm pour 7,5 mm d'os, 7,18 pour 8,4) : critère = entre 80 et 100 % de l'excursion de l'os, dans le bon sens
side_ok = 0.8 * skeleton.JAW_SIDE_MM <= rows_jaw["gauche"]["dx_mm"] <= skeleton.JAW_SIDE_MM and -skeleton.JAW_SIDE_MM <= rows_jaw["droite"]["dx_mm"] <= -0.8 * skeleton.JAW_SIDE_MM
forward_ok = -skeleton.JAW_FORWARD_MM <= rows_jaw["avant"]["dy_mm"] <= -0.8 * skeleton.JAW_FORWARD_MM
check("P4c_machoire_lateral_et_propulsion", side_ok and forward_ok and abs(rows_jaw["gauche_et_droite_se_compensent"]["dx_mm"]) < 0.5 and 0.35 * skeleton.JAW_SIDE_MM <= rows_jaw["demi_gauche"]["dx_mm"] <= 0.55 * skeleton.JAW_SIDE_MM and float(np.abs(back).max()) < 0.01
      and abs(rows_jaw["gauche"]["lue"].get("_jaw_side", 0.0) - skeleton.JAW_SIDE_MM) < 0.01, rows_jaw)

face.apply_pose(body, {})

# P5
before = {n: human.get_value(body, n) for n in FACE_COMMANDS if human.has_control(body, n)}
export, bake = face.bake_shapes(body)
keys = export.data.shape_keys.key_blocks
shapes_ok = all(n in keys for n in FACE_COMMANDS if n not in bake["ignorees_pilotees"])
moves_ok = all(v > 0.1 for v in bake["formes"].values())
after = {n: human.get_value(body, n) for n in FACE_COMMANDS if human.has_control(body, n)}
check("P5_formes_cuites", shapes_ok and moves_ok and bake["arkit_cuits"] >= 20 and before == after and len(export.data.vertices) == bake["sommets"] and len(export.vertex_groups) >= 1
      and not any(m.type == "ARMATURE" and not m.show_viewport for m in body.modifiers),
      {"formes": len(bake["formes"]), "arkit_cuits": bake["arkit_cuits"], "pilotees_ignorees": bake["ignorees_pilotees"], "groupes": len(export.vertex_groups), "groupes_source": len(body.vertex_groups), "sommets_source": len(body.data.vertices),
       "deplacements_mm_min_max": [min(bake["formes"].values()), max(bake["formes"].values())]})

# P6
spine = rig.pose.bones["spine"] if "spine" in rig.pose.bones else rig.pose.bones[1]
rig.animation_data_create()
spine.rotation_mode = "XYZ"
spine.rotation_euler = (0.0, 0.0, 0.0)
spine.keyframe_insert("rotation_euler", frame=1)
spine.rotation_euler = (0.4, 0.0, 0.0)
spine.keyframe_insert("rotation_euler", frame=25)
body_action = rig.animation_data.action
strips = face.build_clip(body, "parole", [(1, {}), (12, {"smile_L": 1.0, "smile_R": 1.0, "_jaw": 15.0, "_tongue": {"langue_sortie": 1.0}, "_gaze": [20.0, 5.0]}), (25, {})], start=1)
check("P6a_clip_cree_et_actions_du_corps_intactes", len(strips) == 3 and rig.animation_data.action == body_action and len(face.clip_strips(body)) == 3, {"bandes": [s.name for s in strips]})


def sample(frame):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    tongue = next(o for o in dental.parts_of(body) if o.name == "HL Langue")
    return {"smile": human.get_value(body, "smile_L"), "jaw": abs(float(np.degrees(rig.pose.bones[skeleton.JAW].rotation_euler[0]))), "spine": float(rig.pose.bones[spine.name].rotation_euler[0]),
            "langue": tongue.data.shape_keys.key_blocks["langue_sortie"].value, "mouth_open": human.get_value(body, "mouth_open")}


s1, s12, s25 = sample(1), sample(12), sample(25)
face_ok = s12["smile"] > 0.95 and abs(s12["jaw"] - 15) < 0.5 and s12["langue"] > 0.95 and s1["smile"] < 0.01 and s25["smile"] < 0.01 and s12["mouth_open"] > 0.3
body_ok = abs(s1["spine"]) < 1e-6 and abs(s25["spine"] - 0.4) < 1e-4
face.set_clips_enabled(body, False)
m12 = sample(12)
off_ok = m12["smile"] < 0.01 and abs(m12["jaw"]) < 0.5 and abs(m12["spine"] - float(np.interp(12, [1, 25], [0, 0.4]))) < 0.02
face.set_clips_enabled(body, True)
rig.animation_data.action = None
spine.rotation_euler = (0.0, 0.0, 0.0)
n12 = sample(12)
no_body_ok = n12["smile"] > 0.95 and abs(n12["spine"]) < 1e-6
rig.animation_data.action = body_action
check("P6b_clip_et_corps_independants", face_ok and body_ok and off_ok and no_body_ok, {"image1": s1, "image12": s12, "image25": s25, "visage_coupe": m12, "sans_action_corps": n12})
removed = face.remove_clips(body)
r12 = sample(12)
check("P6c_retrait_du_clip", removed >= 2 and not face.clip_strips(body) and r12["smile"] < 0.01 and abs(r12["spine"] - float(np.interp(12, [1, 25], [0, 0.4]))) < 0.02, {"pistes_retirees": removed, "image12": r12, "bandes_restantes": len(face.clip_strips(body))})

# P7 : dents du bas visibles au sourire large et au rire, sur 3 morphologies (mesure relative, voir face.teeth_visible_fraction)
rows7, ok7 = {}, True
for label, values in {"neutre": {}, "femme_jeune": {"sex": 1.0, "age": 1.0}, "homme_age": {"sex": 0.0, "age": 3.0}}.items():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.ops.humanloom.create()
    b7 = bpy.context.object
    for name, value in values.items():
        human.set_value(b7, name, value)
    skeleton.install(b7)
    row = {}
    for pid in ("expression:neutre", "expression:joie", "expression:sourire_large", "expression:rire"):
        face.apply_pose(b7, face.builtin_poses()[pid]["pose"])
        row[pid] = round(face.teeth_visible_fraction(b7, "lower") * 100, 1)
    rows7[label] = row
    ok7 &= row["expression:rire"] >= 15.0 and row["expression:sourire_large"] >= 5.0 and row["expression:neutre"] <= 3.0
check("P7_dents_basses_visibles_au_sourire_large_et_au_rire", ok7, {"pourcent_sommets_visibles": rows7, "seuils": "rire >= 15, sourire_large >= 5, neutre <= 3"})

# P8 : opérateurs et panneau de la galerie
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
bpy.ops.humanloom.create()
b8 = bpy.context.object
bpy.context.view_layer.objects.active = b8
skeleton.install(b8)
wm = bpy.context.window_manager
ok_apply = bpy.ops.humanloom.face_pose_apply(pose_id="expression:rire") == {"FINISHED"} and human.get_value(b8, "smile_duchenne") == 1.0
try:
    bpy.ops.humanloom.face_pose_apply(pose_id="nexiste:pas")
    ok_unknown = False
except RuntimeError:
    ok_unknown = True
ok_fav = bpy.ops.humanloom.face_pose_favorite(pose_id="expression:peur") == {"FINISHED"} and "expression:peur" in face.favorites(bpy.context.scene)
bpy.ops.humanloom.face_pose_apply(pose_id="expression:neutre")
wm.hl_face_mix_a, wm.hl_face_mix_b, wm.hl_face_mix_factor = "expression:neutre", "expression:joie", 0.5
ok_mix = bpy.ops.humanloom.face_pose_mix() == {"FINISHED"} and abs(human.get_value(b8, "smile_duchenne") - 0.5) < 1e-3
ok_clip = bpy.ops.humanloom.face_clip(start=1, length=10, name="essai") == {"FINISHED"} and len(face.clip_strips(b8)) >= 2
bpy.context.scene.frame_set(11)
ok_clip_end = human.get_value(b8, "smile_duchenne") > 0.95
ok_remove = bpy.ops.humanloom.face_clip_remove() == {"FINISHED"} and not face.clip_strips(b8)
ok_bake = bpy.ops.humanloom.face_bake_shapes(arkit=True) == {"FINISHED"}
ok_report = bpy.ops.humanloom.face_arkit_report() == {"FINISHED"}
from extension.animation import face_ui  # noqa: E402
icons = [face_ui._icon(r["id"]) for r in face.gallery(bpy.context.scene) if r["categorie"] != "utilisateur"]
thumbs = Path(face_ui.THUMBS)
check("P8_operateurs_et_panneau_galerie", all([ok_apply, ok_unknown, ok_fav, ok_mix, ok_clip, ok_clip_end, ok_remove, ok_bake, ok_report]) and len(icons) == len(face.builtin_poses()) and hasattr(bpy.types, "HUMANLOOM_PT_face_gallery")
      and len(list(thumbs.glob("*.png"))) == len(face_ui._gallery_index()) == len(face.builtin_poses()),
      {"apply": ok_apply, "inconnue": ok_unknown, "favori": ok_fav, "melange": ok_mix, "clip": ok_clip, "clip_fin": ok_clip_end, "retrait": ok_remove, "cuisson": ok_bake, "rapport": ok_report, "vignettes": len(icons)})

if OUT:
    Path(OUT).write_text(json.dumps(results, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
print("RESULT", "FAIL " + ", ".join(failures) if failures else "PASS")
sys.exit(1 if failures else 0)
