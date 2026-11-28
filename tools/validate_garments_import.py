"""Validation de l'import de vêtements de l'utilisateur (lot V2, critère V-6) : ajustement automatique, rapport chiffré, échec signalé jamais masqué.

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/validate_garments_import.py -- [--out FICHIER.json]

La pièce « de l'utilisateur » est fabriquée ici (une chemise procédurale exportée en OBJ puis modifiée) : aucun fichier tiers. I1 import en mode « pose » (poids transférés, Armature, suit une pose) ; I2 mode « morphologie »
(Surface Deform : suit un changement de morphologie) ; I3 ajustement automatique : une pièce un peu trop petite est repoussée hors de la peau ; I4 échecs signalés (trop petite, trop éloignée, format, fichier absent) sans résidu."""
import json
from pathlib import Path
import sys
import tempfile

import bpy
import numpy as np
from mathutils import Euler

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
    print(("OK  " if ok else "KO  ") + name, json.dumps(detail, ensure_ascii=False, default=str)[:900] if detail is not None else "")
    if not ok:
        failures.append(name)


addon.register()
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
bpy.ops.humanloom.create()
body = bpy.context.object
rig = skeleton.install(body)
body.modifiers["Human Modeling · Surface"].show_viewport = False
work = Path(tempfile.mkdtemp(prefix="hl_import_"))


def export_variant(name, scale=1.0, shift=(0.0, 0.0, 0.0)):
    """Chemise procédurale -> OBJ, avec échelle autour de l'axe du corps et décalage (la pièce « de l'utilisateur »)."""
    source = garments.add_garment(body, "chemise")
    from extension.animation import correctives
    correctives.detach_garment(source)  # pièce « étrangère » exportée : on édite ses sommets directement (avec des clés de forme, la clé de base prévaudrait)
    for v in source.data.vertices:
        v.co = (v.co.x * scale + shift[0], v.co.y * scale + shift[1], v.co.z + shift[2])
    for modifier in list(source.modifiers):
        source.modifiers.remove(modifier)
    source.parent = None
    for other in bpy.context.view_layer.objects:
        other.select_set(False)
    source.select_set(True)
    bpy.context.view_layer.objects.active = source
    path = work / (name + ".obj")
    bpy.ops.wm.obj_export(filepath=str(path), export_selected_objects=True)
    mesh = source.data
    bpy.data.objects.remove(source, do_unlink=True)
    bpy.data.meshes.remove(mesh)
    return path


def leftovers():
    return [o.name for o in bpy.data.objects if o.get(garments.IMPORT_MARKER)]


path_ok = export_variant("chemise_utilisateur", 1.0)
reference = garments.add_garment(body, "chemise")  # même pièce procédurale, pour comparer la pose
imports = garments.import_garment(body, path_ok, "pose")
user, report = imports[0]
groups = len(user.vertex_groups)
sample = [sum(g.weight for g in v.groups) for v in user.data.vertices[:200]] if groups else [0.0]
check("I1a_import_pose_poids_et_armature", report["statut"] == "ok" and groups > 20 and float(np.mean(sample)) > 0.9 and any(m.type == "ARMATURE" for m in user.modifiers) and user.parent == body and user[garments.IMPORT_MARKER],
      {"rapport": report, "groupes_de_sommets": groups, "somme_des_poids_moyenne_200_premiers": round(float(np.mean(sample)), 3)})


armature_names = [m.name for m in user.modifiers if m.type == "ARMATURE"]
lbs_group, dqs_group = user.vertex_groups.get(skeleton.GROUP_LBS), user.vertex_groups.get(skeleton.GROUP_DQS)
check("I1c_importee_en_deux_modificateurs_armature", armature_names == ["Armature", "Armature DQS"] and lbs_group is not None and dqs_group is not None, {"modificateurs": armature_names, "groupes_masque": [g is not None for g in (lbs_group, dqs_group)]})


def set_pose():
    for pb in rig.pose.bones:
        pb.rotation_mode = "XYZ"
        pb.rotation_euler = (0.0, 0.0, 0.0)
    rig.pose.bones["arm_upper.L"].rotation_euler = Euler((0.0, 0.0, np.radians(-70.0)))
    rig.pose.bones["spine.03"].rotation_euler = Euler((0.0, np.radians(30.0), 0.0))
    bpy.context.view_layer.update()


def evaluated_points(obj):
    if "Epaisseur" in obj.modifiers:
        obj.modifiers["Epaisseur"].show_viewport = False
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    points = np.array([(obj.matrix_world @ v.co)[:] for v in mesh.vertices])
    evaluated.to_mesh_clear()
    return points


set_pose()
posed_user = evaluated_points(user)
posed_reference = evaluated_points(reference)
rest_user = np.array([(user.matrix_world @ v.co)[:] for v in user.data.vertices])
moved = float(np.linalg.norm(posed_user - rest_user, axis=1).max())
gap = float(np.linalg.norm(posed_user - posed_reference, axis=1).mean()) if len(posed_user) == len(posed_reference) else float("nan")
check("I1b_la_piece_importee_suit_la_pose", moved > 0.05 and (gap < 0.02 or np.isnan(gap)), {"deplacement_max_m": round(moved, 3), "ecart_moyen_a_la_piece_procedurale_m": round(gap, 4), "memes_sommets": len(posed_user) == len(posed_reference)})
for pb in rig.pose.bones:
    pb.rotation_euler = (0.0, 0.0, 0.0)
bpy.context.view_layer.update()

# I2 mode morphologie : Surface Deform lié au corps
morph_imports = garments.import_garment(body, path_ok, "morphologie")
follow, follow_report = morph_imports[0]


def positions(obj):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    out = np.array([(obj.matrix_world @ v.co)[:] for v in mesh.vertices])
    evaluated.to_mesh_clear()
    return out


before = positions(follow)
human.set_value(body, "whole_body", 0.8)
human.set_value(body, "shoulders", 0.8)
bpy.context.view_layer.update()
after = positions(follow)
shift = float(np.linalg.norm(after - before, axis=1).max())
cage = skeleton.cage_points(body)
nearest = np.array([np.min(np.linalg.norm(cage[::7] - p, axis=1)) for p in after[::40]])
check("I2_mode_morphologie_surface_deform_suit_le_corps", follow_report["statut"] == "ok" and shift > 0.01 and any(m.type == "SURFACE_DEFORM" for m in follow.modifiers) and not any(m.type == "ARMATURE" for m in follow.modifiers) and float(np.median(nearest)) < 0.05,
      {"deplacement_max_m": round(shift, 3), "distance_mediane_a_la_peau_m": round(float(np.median(nearest)), 4)})
human.set_value(body, "whole_body", 0.0)
human.set_value(body, "shoulders", 0.0)

# I3 ajustement automatique d'une pièce un peu trop petite
garments.remove_garment(reference)
for obj, _ in imports + morph_imports:
    bpy.data.objects.remove(obj, do_unlink=True)
path_small = export_variant("chemise_serree", 0.965)
small, small_report = garments.import_garment(body, path_small, "pose")[0]
check("I3_ajustement_automatique_repousse_les_sommets_interieurs", small_report["statut"] == "ok" and small_report["part_a_l_interieur_avant"] > 0.0 and small_report["sommets_repousses"] > 0, small_report)
after_report = garments.fit_report(body, small, apply=False)
check("I3b_apres_ajustement_plus_aucun_sommet_a_l_interieur", after_report["part_a_l_interieur_avant"] == 0.0, after_report)
bpy.data.objects.remove(small, do_unlink=True)

# I4 échecs signalés, sans résidu
errors = {}
path_tiny = export_variant("chemise_minuscule", 0.55)
path_far = export_variant("chemise_loin", 1.0, shift=(1.2, 0.0, 0.0))
for label, call in (("trop_petite", lambda: garments.import_garment(body, path_tiny, "pose")), ("trop_eloignee", lambda: garments.import_garment(body, path_far, "pose")),
                    ("format", lambda: garments.import_garment(body, work / "x.stl", "pose")), ("fichier_absent", lambda: garments.import_garment(body, work / "absent.obj", "pose")),
                    ("mode", lambda: garments.import_garment(body, path_ok, "autre"))):
    try:
        call()
        errors[label] = "PAS D'ERREUR"
    except ValueError as error:
        errors[label] = str(error)[:90]
check("I4_echecs_signales_sans_residu", all(v != "PAS D'ERREUR" for v in errors.values()) and errors["trop_petite"].startswith("échec") and errors["trop_eloignee"].startswith("échec") and not leftovers(), {"erreurs": errors, "residus": leftovers()})

# I5 opérateur d'import du panneau
bpy.context.view_layer.objects.active = body
before_count = len(leftovers())
ok_operator = bpy.ops.humanloom.garment_import(filepath=str(path_ok), mode="pose") == {"FINISHED"} and len(leftovers()) == before_count + 1
check("I5_operateur_d_import", ok_operator, {"importes": len(leftovers())})

# I6 import transactionnel (GRM-003) : un fichier à deux pièces dont la seconde échoue n'en laisse AUCUNE (ni objet, ni maillage, ni matériau créé par l'import)
def export_pair(name):
    objects = []
    for shift in (0.0, 1.2):
        source = garments.add_garment(body, "chemise")
        from extension.animation import correctives
        correctives.detach_garment(source)
        for v in source.data.vertices:
            v.co = (v.co.x + shift, v.co.y, v.co.z)
        for modifier in list(source.modifiers):
            source.modifiers.remove(modifier)
        source.parent = None
        objects.append(source)
    for other in bpy.context.view_layer.objects:
        other.select_set(False)
    for source in objects:
        source.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    path = work / (name + ".obj")
    bpy.ops.wm.obj_export(filepath=str(path), export_selected_objects=True)
    for source in objects:
        mesh = source.data
        bpy.data.objects.remove(source, do_unlink=True)
        bpy.data.meshes.remove(mesh)
    return path


pair = export_pair("deux_pieces_dont_une_loin")
objects_before, meshes_before, materials_before = {o.name for o in bpy.data.objects}, {m.name for m in bpy.data.meshes}, {m.name for m in bpy.data.materials}
try:
    garments.import_garment(body, pair, "pose")
    pair_error = "PAS D'ERREUR"
except ValueError as error:
    pair_error = str(error)[:60]
residue = {"objets": sorted({o.name for o in bpy.data.objects} - objects_before), "maillages": sorted({m.name for m in bpy.data.meshes} - meshes_before), "materiaux": sorted({m.name for m in bpy.data.materials} - materials_before)}
check("I6_import_transactionnel_aucun_residu", pair_error.startswith("échec") and not any(residue.values()), {"erreur": pair_error, "residus": residue})

# I7 tenue et pièce importée (GRM-001) : enregistrer / recharger une tenue avec une pièce importée ne lève plus KeyError et ne détruit pas la pièce importée
bpy.context.view_layer.objects.active = body
imported = [o for o in garments.garments_of(body) if o.get(garments.IMPORT_MARKER)]
if not imported:
    garments.import_garment(body, path_ok, "pose")
    imported = [o for o in garments.garments_of(body) if o.get(garments.IMPORT_MARKER)]
procedural_before = sorted(g[garments.MARKER] for g in garments.garments_of(body) if not g.get(garments.IMPORT_MARKER))
try:
    saved_outfit = garments.outfit_of(body)
    outfit_error = None
except KeyError as error:
    saved_outfit, outfit_error = [], repr(error)
garments.apply_outfit(body, saved_outfit)
imported_after = [o for o in garments.garments_of(body) if o.get(garments.IMPORT_MARKER)]
check("I7_tenue_avec_piece_importee", outfit_error is None and len(imported) >= 1 and len(imported_after) == len(imported) and all(p["piece"] in garments.GARMENTS for p in saved_outfit) and sorted(p["piece"] for p in saved_outfit) == procedural_before,
      {"erreur": outfit_error, "importees_avant": len(imported), "importees_apres": len(imported_after), "pieces_enregistrees": [p["piece"] for p in saved_outfit]})

if OUT:
    Path(OUT).write_text(json.dumps(results, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
print("RESULT", "FAIL " + ", ".join(failures) if failures else "PASS")
sys.exit(1 if failures else 0)
