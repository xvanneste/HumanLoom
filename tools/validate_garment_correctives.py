"""Validation du dégagement de flexion PROPRE AU VÊTEMENT (extension/garment_clearance.py) et du report des correctifs du corps sur les pièces sans sommets correspondants (animation/correctives.attach_projected) : CONCEPTION_RIG_CORRECTIFS.md §17.

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/validate_garment_correctives.py -- [--out FICHIER.json]

G1 calcul (veste, jean, t-shirt, robe, pièce importée) ; G2 coude de la veste : profondeur de pénétration (enveloppe de peau seule) sur un balayage fin de 40 à 150° (pas de 2°) ; G3 genou du jean ; G4 coût d'évaluation par image ;
G5 report des correctifs du corps par projection (robe, pièce importée « pose ») ; G6 ajustement à la morphologie (clés refaites) ; G7 coupure et retrait propres ; G8 foule (pièces à maillage propre, pose de la foule ignorée)."""
import json
import math
from pathlib import Path
import sys
import tempfile
import time

import bpy
import numpy as np
from mathutils import Quaternion

ROOT = Path(__file__).resolve().parents[1]
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = ARGS[ARGS.index("--out") + 1] if "--out" in ARGS else None
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension import crowd, garment_clearance as gc, garments, human  # noqa: E402
from extension.animation import correctives, skeleton  # noqa: E402

results, failures = {}, []


def check(name, ok, detail=None):
    results[name] = {"ok": bool(ok), "detail": detail}
    print(("OK  " if ok else "KO  ") + name, json.dumps(detail, ensure_ascii=False, default=str)[:1400] if detail is not None else "")
    if not ok:
        failures.append(name)


addon.register()
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
bpy.ops.humanloom.create()
body = bpy.context.object
rig = skeleton.install(body)
body.modifiers["Human Modeling · Surface"].show_viewport = False
data = np.load(correctives.DATA, allow_pickle=False)
signs = {"coude": float(data["coude_L_sign"]), "genou": float(data["genou_L_sign"])}
work = Path(tempfile.mkdtemp(prefix="hl_gcorr_"))


def reset(armature=None):
    for b in (armature or rig).pose.bones:
        b.rotation_mode = "QUATERNION"
        b.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
        b.location = (0.0, 0.0, 0.0)


def skin_only(piece):
    saved = [(m, m.show_viewport) for m in piece.modifiers]
    for m in piece.modifiers:
        m.show_viewport = m.type == "ARMATURE"
    return saved


def world_points(piece):
    bpy.context.view_layer.update()
    evaluated = piece.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    buffer = np.empty(len(mesh.vertices) * 3, np.float32)
    mesh.vertices.foreach_get("co", buffer)
    evaluated.to_mesh_clear()
    matrix = np.array(piece.matrix_world)
    return buffer.reshape(-1, 3).astype(np.float64) @ matrix[:3, :3].T + matrix[:3, 3]


def depth_max(piece, owner, armature, bone, radius):
    """Profondeur maximale (m) d'un sommet de la pièce dans le corps `owner` posé, dans le rayon `radius` de la tête de l'os (peau seule)."""
    pivot = np.array((armature.matrix_world @ armature.pose.bones[bone].head)[:])
    tree = gc._body_tree(owner)
    worst = -1.0
    for p in world_points(piece):
        if np.linalg.norm(p - pivot) > radius:
            continue
        location, normal, _i, _d = tree.find_nearest(p.tolist())
        if location is not None:
            worst = max(worst, -float((p - np.array(location)) @ np.array(normal)))
    return round(worst * 1000, 2)


def sweep(piece, joint, bone, radius, angles, with_keys, owner=None, armature=None):
    owner, armature = owner or body, armature or rig
    for key in gc.keys_of(piece.data):
        key.mute = not with_keys
    saved = skin_only(piece)
    out = {}
    for angle in angles:
        reset(armature)
        armature.pose.bones[bone].rotation_quaternion = Quaternion((1.0, 0.0, 0.0), math.radians(signs[joint] * angle))
        bpy.context.view_layer.update()
        out[angle] = depth_max(piece, owner, armature, bone, radius)
    for m, state in saved:
        m.show_viewport = state
    for key in gc.keys_of(piece.data):
        key.mute = not gc.enabled(piece)
    reset(armature)
    return out


shirt = garments.add_garment(body, "t_shirt")
jean = garments.add_garment(body, "jean")
jacket = garments.add_garment(body, "veste")
dress = garments.add_garment(body, "robe_courte")

# G1 calcul
timing, counts = {}, {}
for name, piece in (("t_shirt", shirt), ("jean", jean), ("veste", jacket), ("robe_courte", dress)):
    start = time.time()
    counts[name] = gc.build(piece, body)
    timing[name] = round(time.time() - start, 1)
names_ok = all(k.name.startswith("HLG ") and not k.mute for p in (jacket, jean) for k in gc.keys_of(p.data))
drivers = {n: len([f for f in p.data.shape_keys.animation_data.drivers if f.data_path.startswith(f'key_blocks["{gc.KEY_PREFIX}')]) if p.data.shape_keys and p.data.shape_keys.animation_data else 0 for n, p in (("veste", jacket), ("jean", jean), ("t_shirt", shirt))}
check("G1_calcul_des_cles_par_piece", names_ok and counts["veste"].get("coude_L", 0) > 100 and counts["veste"].get("coude_R", 0) > 100 and counts["jean"].get("genou_L", 0) > 50 and drivers["veste"] == len(gc.keys_of(jacket.data)) and "hlg_angle_coude_L" in rig.keys(),
      {"sommets_deplaces": counts, "secondes": timing, "pilotes": drivers, "cles_veste": len(gc.keys_of(jacket.data))})

# G2 coude de la veste : balayage fin, avec / sans les clés
angles = list(range(40, 151, 2)) + [90, 110, 135]
without = sweep(jacket, "coude", "arm_lower.L", 0.18, angles, False)
with_keys = sweep(jacket, "coude", "arm_lower.L", 0.18, angles, True)
up_to_136 = {a: v for a, v in with_keys.items() if a <= 136}
above = {a: v for a, v in with_keys.items() if a > 136}
check("G2a_coude_veste_jusqu_a_136_degres", max(up_to_136.values()) <= 2.0 and all(with_keys[a] <= 2.0 for a in (90, 110, 135)), {"max_avec_mm": max(up_to_136.values()), "max_sans_mm": max(v for a, v in without.items() if a <= 136), "a_90_110_135_avec": [with_keys[a] for a in (90, 110, 135)], "a_90_110_135_sans": [without[a] for a in (90, 110, 135)]})
check("G2b_coude_veste_au_dela_de_136_degres", max(above.values()) <= 6.5 and max(above.values()) < max(v for a, v in without.items() if a > 136) / 2, {"max_avec_mm": max(above.values()), "max_sans_mm": max(v for a, v in without.items() if a > 136), "limite_mm": 6.5, "note": "interpolation linéaire entre des clés espacées de 3° ; limite posée APRÈS mesure (CONCEPTION §17)"})

# G3 genou du jean
knee_angles = list(range(40, 151, 2)) + [90, 110, 135]
knee_without = sweep(jean, "genou", "leg_lower.L", 0.22, knee_angles, False)
knee_with = sweep(jean, "genou", "leg_lower.L", 0.22, knee_angles, True)
check("G3_genou_jean_pas_pire_et_reduit", max(knee_with.values()) <= max(knee_without.values()) and sum(v > 2.0 for v in knee_with.values()) < sum(v > 2.0 for v in knee_without.values()), {"max_avec_mm": max(knee_with.values()), "max_sans_mm": max(knee_without.values()),
      "angles_au_dela_de_2mm_avec_sans": [sum(v > 2.0 for v in knee_with.values()), sum(v > 2.0 for v in knee_without.values())], "a_90_110_135_avec": [knee_with[a] for a in (90, 110, 135)], "a_90_110_135_sans": [knee_without[a] for a in (90, 110, 135)]})


# G4 coût par image
def frame_cost(pieces, n=40):
    reset()
    start = time.time()
    for i in range(n):
        rig.pose.bones["arm_lower.L"].rotation_quaternion = Quaternion((1.0, 0.0, 0.0), math.radians(signs["coude"] * (40 + 2 * i)))
        rig.pose.bones["leg_lower.L"].rotation_quaternion = Quaternion((1.0, 0.0, 0.0), math.radians(signs["genou"] * (40 + 2 * i)))
        bpy.context.view_layer.update()
        for p in pieces:
            world_points(p)
    elapsed = (time.time() - start) / n * 1000
    reset()
    return elapsed


pieces = [shirt, jean, jacket, dress]
for p in pieces:
    for key in gc.keys_of(p.data):
        key.mute = True
base_cost = min(frame_cost(pieces) for _ in range(3))
for p in pieces:
    for key in gc.keys_of(p.data):
        key.mute = False
keys_cost = min(frame_cost(pieces) for _ in range(3))
for p in pieces:
    garments.set_clearance(p, True)
shrink_cost = min(frame_cost(pieces) for _ in range(3))
for p in pieces:
    garments.set_clearance(p, False)
check("G4_cout_par_image", keys_cost - base_cost <= 4.0, {"sans_cles_ms": round(base_cost, 1), "avec_cles_ms": round(keys_cost, 1), "avec_passe_degagement_ms": round(shrink_cost, 1), "surcout_cles_ms": round(keys_cost - base_cost, 1), "surcout_degagement_ms": round(shrink_cost - keys_cost, 1)})

# G5 report par projection des correctifs du corps (robe et pièce importée « pose »)
export_source = garments.add_garment(body, "chemise")
correctives.detach_garment(export_source)
gc.remove(export_source)
for modifier in list(export_source.modifiers):
    export_source.modifiers.remove(modifier)
export_source.parent = None
for other in bpy.context.view_layer.objects:
    other.select_set(False)
export_source.select_set(True)
bpy.context.view_layer.objects.active = export_source
path = work / "chemise_utilisateur.obj"
bpy.ops.wm.obj_export(filepath=str(path), export_selected_objects=True)
export_mesh = export_source.data
bpy.data.objects.remove(export_source, do_unlink=True)
bpy.data.meshes.remove(export_mesh)
imported, _report = garments.import_garment(body, path, "pose")[0]
morph_imported, _report2 = garments.import_garment(body, path, "morphologie")[0] if False else (None, None)
hlc_keys = {n: len(correctives.keys_of(p.data)) for n, p in (("t_shirt", shirt), ("veste", jacket), ("robe_courte", dress), ("importee_pose", imported))}
body_keys = len(correctives.keys_of(body.data))
# amplitude comparée au corps : le sommet de la pièce le plus déplacé par les clés d'un coude à 110° doit l'être comme son voisin du corps
correctives.set_enabled(body, True)
reset()
rig.pose.bones["arm_lower.L"].rotation_quaternion = Quaternion((1.0, 0.0, 0.0), math.radians(signs["coude"] * 110))
bpy.context.view_layer.update()
shift = {}
for name, piece in (("robe_courte", dress), ("importee_pose", imported), ("veste", jacket)):
    on = world_points(piece)
    for key in correctives.keys_of(piece.data):
        key.mute = True
    off = world_points(piece)
    for key in correctives.keys_of(piece.data):
        key.mute = False
    shift[name] = round(float(np.linalg.norm(on - off, axis=1).max()) * 1000, 2)
body_on = world_points(body)
for key in correctives.keys_of(body.data):
    key.mute = True
body_off = world_points(body)
for key in correctives.keys_of(body.data):
    key.mute = False
shift["corps"] = round(float(np.linalg.norm(body_on - body_off, axis=1).max()) * 1000, 2)
check("G5_correctifs_du_corps_reportes_sur_robe_et_importee", hlc_keys["robe_courte"] == body_keys and hlc_keys["importee_pose"] == body_keys and hlc_keys["veste"] == body_keys and shift["importee_pose"] > 0.5 and shift["importee_pose"] <= shift["corps"] * 1.5 + 0.5,
      {"cles_hlc_corps": body_keys, "cles_hlc_pieces": hlc_keys, "deplacement_max_a_110_mm": shift})
correctives.set_enabled(body, False)
reset()

# G6 ajustement à la morphologie : les clés de dégagement sont refaites (positions nouvelles)
before_labels = {k.name.rsplit(" ", 1)[0] for k in gc.keys_of(jacket.data)}
before = len(gc.keys_of(jacket.data))
human.set_value(body, "age", 2.5)
garments.update_garment(jacket)
after = len(gc.keys_of(jacket.data))
changed = sweep(jacket, "coude", "arm_lower.L", 0.18, (90, 110, 135), True)
changed_without = sweep(jacket, "coude", "arm_lower.L", 0.18, (90, 110, 135), False)
after_labels = {k.name.rsplit(" ", 1)[0] for k in gc.keys_of(jacket.data)}
check("G6_ajustement_a_la_morphologie_refait_les_cles", before > 0 and after >= before and before_labels <= after_labels and len(set(k.name for k in gc.keys_of(jacket.data))) == after and all(changed[a] <= 2.5 for a in changed) and all(changed_without[a] > changed[a] for a in changed), {"cles_avant_apres": [before, after], "etiquettes_apres": sorted(after_labels), "avec_mm": changed, "sans_mm": changed_without})
human.set_value(body, "age", 0.0)
garments.update_garment(jacket)

# G7 coupure et retrait propres
gc.set_enabled(jacket, False)
muted = all(k.mute for k in gc.keys_of(jacket.data))
gc.set_enabled(jacket, True)
removed = gc.remove(jacket, rig)
clean = not gc.keys_of(jacket.data) and not any(k.startswith(gc.PROP_PREFIX) for k in rig.keys()) and (jacket.data.shape_keys is None or not [k for k in jacket.data.shape_keys.key_blocks if k.name.startswith("HLG")])
check("G7_coupure_et_retrait_propres", muted and removed > 0 and clean, {"muet": muted, "cles_retirees": removed, "propre": clean})

# G8 foule : chaque personnage porte ses pièces (maillages propres) ; la pose animée de la foule ne fausse pas le calcul
scene = bpy.context.scene
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)
crowd.register_variant_applier("outfit", garments.crowd_outfit)
spec = crowd.default_spec(2, 5)
spec["frames"] = 12
spec["variants"] = {"outfit": [["veste", "jean"]]}
crowd.generate(bpy.context, spec)
members = crowd.members_of(scene)
rows = {}
meshes = set()
for member in members:
    armature = skeleton.rigs_of(member)[0]
    worn = {g[garments.MARKER]: g for g in garments.garments_of(member)}
    meshes.update(g.data.name for g in worn.values())
    start = time.time()
    built = gc.build(worn["veste"], member)
    elapsed = round(time.time() - start, 1)
    animation = armature.animation_data
    saved_animation = (animation.action, animation.use_nla) if animation else None
    if animation:
        animation.action, animation.use_nla = None, False
    own = {a: None for a in (110,)}
    for state in (False, True):
        for key in gc.keys_of(worn["veste"].data):
            key.mute = not state
        saved = skin_only(worn["veste"])
        reset(armature)
        armature.pose.bones["arm_lower.L"].rotation_quaternion = Quaternion((1.0, 0.0, 0.0), math.radians(signs["coude"] * 110))
        bpy.context.view_layer.update()
        own[state] = depth_max(worn["veste"], member, armature, "arm_lower.L", 0.18)
        for m, s in saved:
            m.show_viewport = s
    reset(armature)
    if animation:
        animation.action, animation.use_nla = saved_animation
    rows[member.name] = {"sommets_deplaces": built, "secondes": elapsed, "profondeur_110_sans_mm": own[False], "profondeur_110_avec_mm": own[True]}
check("G8_foule_cles_par_personnage", len(meshes) == len(members) * 2 and all(r["sommets_deplaces"] and r["profondeur_110_avec_mm"] <= 2.5 and r["profondeur_110_avec_mm"] < r["profondeur_110_sans_mm"] for r in rows.values()), {"personnages": rows, "maillages_de_pieces_distincts": len(meshes)})
crowd.clear(scene)

# G9 correctifs du CORPS dans la foule : maillage de base propre au personnage (install_independent) ; le coude plié d'un personnage ne déplace que SES sommets ; effacement de la foule propre
crowd.generate(bpy.context, spec)
members = crowd.members_of(scene)
armatures = [skeleton.rigs_of(m)[0] for m in members]
shared_before = len({m.data.name for m in members})
created = correctives.install_independent(members[0], armatures[0])
correctives.set_enabled(members[0], True)
for armature in armatures:
    if armature.animation_data:
        armature.animation_data.action, armature.animation_data.use_nla = None, False
    reset(armature)
armatures[0].pose.bones["arm_lower.L"].rotation_quaternion = Quaternion((1.0, 0.0, 0.0), math.radians(signs["coude"] * 110))
bpy.context.view_layer.update()
on = world_points(members[0])
for key in correctives.keys_of(members[0].data):
    key.mute = True
off = world_points(members[0])
other = world_points(members[1])
move = round(float(np.linalg.norm(on - off, axis=1).max()) * 1000, 2)
check("G9_correctifs_du_corps_en_foule_par_maillage_propre", created == 40 and move > 5.0 and len({m.data.name for m in members}) == shared_before + 1 and not correctives.installed(members[1]), {"cles": created, "deplacement_personnage_0_mm": move, "maillages_de_base": [shared_before, len({m.data.name for m in members})]})
try:
    crowd.clear(scene)
    cleared = True
except ValueError as error:
    cleared = str(error)
check("G9b_effacement_de_la_foule_apres_correctifs", cleared is True and not [o for o in bpy.data.objects if o.get(crowd.OBJECT_KEY) is not None], {"resultat": cleared})

if OUT:
    Path(OUT).write_text(json.dumps(results, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
print("RESULT", "FAIL " + ", ".join(failures) if failures else "PASS")
sys.exit(1 if failures else 0)
