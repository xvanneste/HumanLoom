"""Validation des vêtements en quaternions duals : les vêtements suivent la peau du corps (deux modificateurs Armature à masques complémentaires, comme le corps) et ne sont plus traversés par le corps au coude et au genou plié.

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/validate_garment_dqs.py -- [--out FICHIER.json]

D1 structure : t-shirt, jean, veste, robe, pièce importée en mode « pose » ont les deux modificateurs et des groupes complémentaires ; D2 non-traversée : veste (manches longues) et jean, coude et genou à 90/110/135° ; profondeur de pénétration du corps dans le vêtement
(sommets du vêtement à l'intérieur du corps de plus de 1 mm, enveloppe de peau seule : sans Solidify ni Shrinkwrap), montage d'origine (un seul Armature linéaire) comparé au montage à deux modificateurs ; D3 retrait propre."""
import json
import math
from pathlib import Path
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Quaternion
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = ARGS[ARGS.index("--out") + 1] if "--out" in ARGS else None
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension import garments, human  # noqa: E402
from extension.animation import correctives, skeleton  # noqa: E402

results, failures = {}, []


def check(name, ok, detail=None):
    results[name] = {"ok": bool(ok), "detail": detail}
    print(("OK  " if ok else "KO  ") + name, json.dumps(detail, ensure_ascii=False, default=str) if detail is not None else "")
    if not ok:
        failures.append(name)


addon.register()
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
bpy.ops.humanloom.create()
body = bpy.context.object
rig = skeleton.install(body, correctives=False)
body.modifiers["Human Modeling · Surface"].show_viewport = False
data = np.load(correctives.DATA, allow_pickle=False)
signs = {"coude": float(data["coude_L_sign"]), "genou": float(data["genou_L_sign"])}
shirt = garments.add_garment(body, "t_shirt")
jean = garments.add_garment(body, "jean")
jacket = garments.add_garment(body, "veste")  # manches longues : le coude plié
pieces = {"t_shirt": shirt, "jean": jean, "veste": jacket}

# D1 structure
dress = garments.add_garment(body, "robe_courte")
rows = {}
for key, piece in [(k, p) for k, p in pieces.items()] + ([("robe_courte", dress)]):
    names = [m.name for m in piece.modifiers if m.type == "ARMATURE"]
    lbs, dqs = piece.vertex_groups.get(skeleton.GROUP_LBS), piece.vertex_groups.get(skeleton.GROUP_DQS)
    count = len(piece.data.vertices)
    inside = np.zeros(count, int)
    for v in piece.data.vertices:
        for g in v.groups:
            if lbs is not None and g.group == lbs.index and g.weight > 0.5:
                inside[v.index] += 1
            if dqs is not None and g.group == dqs.index and g.weight > 0.5:
                inside[v.index] += 10
    rows[key] = {"modificateurs": names, "complementaires": bool(lbs is not None and dqs is not None and set(np.unique(inside)) <= {1, 10}), "sommets_dqs": int((inside == 10).sum()), "sommets": count}
check("D1_deux_modificateurs_et_masques_complementaires", all(r["modificateurs"] == ["Armature", "Armature DQS"] and r["complementaires"] and r["sommets_dqs"] > 0 for r in rows.values()), rows)


def reset():
    for b in rig.pose.bones:
        b.rotation_mode = "QUATERNION"
        b.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
        b.location = (0.0, 0.0, 0.0)


def skin_only(piece):
    """Enveloppe de peau seule : seuls les modificateurs Armature restent actifs."""
    saved = [(m, m.show_viewport) for m in piece.modifiers]
    for m in piece.modifiers:
        m.show_viewport = m.type == "ARMATURE"
    return saved


def evaluated(obj):
    bpy.context.view_layer.update()
    ev = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = ev.to_mesh()
    buf = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", buf)
    ev.to_mesh_clear()
    return buf.reshape(-1, 3)


def body_tree():
    saved = [(m, m.show_viewport) for m in body.modifiers]
    for m in body.modifiers:
        m.show_viewport = m.name in (human.MODIFIER_NAME, skeleton.MODIFIER_NAME, skeleton.DQS_MODIFIER)
    bpy.context.view_layer.update()
    ev = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = ev.to_mesh()
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.transform(body.matrix_world)
    tree = BVHTree.FromBMesh(bm)
    ev.to_mesh_clear()
    bm.free()
    for m, state in saved:
        m.show_viewport = state
    return tree


def penetration(piece, tree, pivot, radius):
    points = evaluated(piece)
    world = np.array([(piece.matrix_world @ __import__("mathutils").Vector(p))[:] for p in points]) if False else points
    depth = []
    for p in world:
        if np.linalg.norm(p - pivot) > radius:
            continue
        location, normal, _index, _dist = tree.find_nearest(p.tolist())
        if location is None:
            continue
        signed = float((p - np.array(location)) @ np.array(normal))
        depth.append(-signed)
    depth = np.array(depth)
    return {"sommets_zone": int(len(depth)), "au_dela_de_1mm": int((depth > 0.001).sum()), "profondeur_max_mm": round(float(depth.max()) * 1000, 2) if len(depth) else 0.0, "profondeur_moyenne_au_dela_mm": round(float(depth[depth > 0.001].mean()) * 1000, 2) if (depth > 0.001).any() else 0.0}


def linear_only(piece, state):
    """state True : montage d'origine (un seul Armature linéaire sans masque) ; False : deux modificateurs."""
    arm = piece.modifiers["Armature"]
    dual = piece.modifiers.get("Armature DQS")
    arm.vertex_group = "" if state else skeleton.GROUP_LBS
    if dual is not None:
        dual.show_viewport = not state


report = {}
worst_ratio = []
for joint, piece_key, bone, radius in (("coude", "veste", "arm_lower.L", 0.18), ("genou", "jean", "leg_lower.L", 0.22)):
    piece = pieces[piece_key]
    saved = skin_only(piece)
    for angle in (90, 110, 135):
        reset()
        rig.pose.bones[bone].rotation_quaternion = Quaternion((1.0, 0.0, 0.0), math.radians(signs[joint] * angle))
        bpy.context.view_layer.update()
        pivot = np.array((rig.matrix_world @ rig.pose.bones[bone].head)[:])
        tree = body_tree()
        out = {}
        for label, state in (("origine_lineaire", True), ("deux_modificateurs", False)):
            linear_only(piece, state)
            out[label] = penetration(piece, tree, pivot, radius)
        report[f"{joint}_{angle}"] = out
    for m, state in saved:
        m.show_viewport = state
    linear_only(piece, False)
reset()
ok = all(v["deux_modificateurs"]["profondeur_max_mm"] <= v["origine_lineaire"]["profondeur_max_mm"] + 0.5 and v["deux_modificateurs"]["au_dela_de_1mm"] <= v["origine_lineaire"]["au_dela_de_1mm"] for v in report.values())
check("D2_non_traversee_coude_et_genou", ok, report)

# D3 retrait propre : retirer le vêtement ne laisse aucun groupe ni objet
before = len(bpy.data.objects)
garments.remove_garment(shirt)
check("D3_retrait_propre", len(bpy.data.objects) == before - 1, {"objets": [before, len(bpy.data.objects)]})

if OUT:
    Path(OUT).write_text(json.dumps(results, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
print("RESULT", "FAIL " + ", ".join(failures) if failures else "PASS")
sys.exit(1 if failures else 0)
