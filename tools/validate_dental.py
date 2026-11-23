"""Validation du lot F0-f : dents, gencives et langue (extension/animation/dental.py).

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/validate_dental.py -- [--out FICHIER.json]

D1 objets, parents (head / jaw), matériaux ; D2 dimensions publiées (Alsahli 2025) retrouvées dans la géométrie, écart mesuré ; D3 provenance : tout ce qui n'est pas publié vient du bloc
« provisoires » et porte « non vérifié » ; D4 la dentition et la langue sont dans la cavité (hors de la masse du corps), bouche fermée et ouverte, sur 3 morphologies ; D5 suivi de la mâchoire ;
D6 âge (lactéale / adulte / usure du senior) ; D7 mise à jour ; D8 retrait sans résidu ; D9 duplication indépendante. Aucun critère n'est assoupli : les écarts sont écrits dans le détail."""
import json
import math
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension import human  # noqa: E402
from extension.animation import dental, skeleton  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = ARGS[ARGS.index("--out") + 1] if "--out" in ARGS else None
results, failures = {}, []


def check(name, ok, detail=None):
    results[name] = {"ok": bool(ok), "detail": detail}
    print(("OK  " if ok else "KO  ") + name, json.dumps(detail, ensure_ascii=False, default=str)[:900] if detail is not None else "")
    if not ok:
        failures.append(name)


addon.register()
REFERENCE = dental.load_reference()


def new_body(**values):
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.ops.humanloom.create()
    body = bpy.context.object
    for name, value in values.items():
        human.set_value(body, name, value)
    return body


def evaluated_cage(body):
    saved = [(m, m.show_viewport) for m in body.modifiers]
    for m in body.modifiers:
        m.show_viewport = m.name in (human.MODIFIER_NAME, skeleton.MODIFIER_NAME)
    human.touch(body)
    bpy.context.view_layer.update()
    evaluated = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    points = np.array([v.co[:] for v in mesh.vertices], np.float64)
    polygons = [tuple(p.vertices) for p in mesh.polygons]
    evaluated.to_mesh_clear()
    for m, state in saved:
        m.show_viewport = state
    return points, polygons


def world_points(obj):
    bpy.context.view_layer.update()
    return np.array([(obj.matrix_world @ v.co)[:] for v in obj.data.vertices])


def inside_solid(points, tree):
    return dental.collision_flags(points, tree)


MORPHOLOGIES = {"neutre": {}, "femme_jeune": {"sex": 1.0, "age": 1.0}, "homme_age": {"sex": 0.0, "age": 3.0}}

# D1 / D2 / D3
body = new_body()
rig = skeleton.install(body)
parts = {o.name: o for o in dental.parts_of(body)}
check("D1_objets_et_parents", set(parts) == {"HL Dents hautes", "HL Dents basses", "HL Langue"}
      and all(o.parent == rig and o.parent_type == "BONE" for o in parts.values())
      and parts["HL Dents hautes"].parent_bone == "head" and parts["HL Dents basses"].parent_bone == skeleton.JAW and parts["HL Langue"].parent_bone == skeleton.JAW
      and all(len(o.data.vertices) > 100 and len(o.data.materials) >= 1 for o in parts.values()),
      {n: {"parent_bone": o.parent_bone, "sommets": len(o.data.vertices), "matériaux": [m.name for m in o.data.materials]} for n, o in parts.items()})

published = REFERENCE["valeurs"]["dents_maxillaires_anterieures_adultes"]
rows = {}
worst = 0.0
for label, values in (("homme", {"sex": 0.0, "age": 2.0}), ("femme", {"sex": 1.0, "age": 2.0})):
    body_s = new_body(**values)
    skeleton.install(body_s)
    upper = next(o for o in dental.parts_of(body_s) if o.name == "HL Dents hautes")
    teeth = json.loads(upper["hl_dental_teeth"])
    points = world_points(upper)
    k = upper["hl_dental_arch_k"]
    positions = dental.arch_positions([t["largeur"] * 1e-3 for t in teeth], k)
    per_tooth = 164
    table = published["hommes" if label == "homme" else "femmes"]
    for index, tooth in enumerate(teeth[:3]):  # incisive centrale, latérale, canine (côté +x)
        vertices = points[index * per_tooth: index * per_tooth + per_tooth - 2]
        tangent = np.array([positions[index][2][0], positions[index][2][1]])
        width = float((vertices[:, :2] @ tangent).max() - (vertices[:, :2] @ tangent).min()) * 1000
        height = float(vertices[:, 2].max() - vertices[:, 2].min()) * 1000
        ref = table[tooth["nom"]]
        rows[f"{label}_{tooth['nom']}"] = {"largeur_mesuree": round(width, 3), "largeur_publiee": ref["largeur_moyenne"], "longueur_mesuree": round(height, 3), "longueur_publiee": ref["longueur_moyenne"]}
        worst = max(worst, abs(width - ref["largeur_moyenne"]), abs(height - ref["longueur_moyenne"]))
check("D2_dimensions_publiees_Alsahli_2025", worst < 0.05, {"ecart_max_mm": round(worst, 4), "lignes": rows})

prov = REFERENCE["provisoires"]
body = new_body()
skeleton.install(body)
teeth = json.loads(next(o for o in dental.parts_of(body) if o.name == "HL Dents hautes")["hl_dental_teeth"])
unpublished_ok = all(t["source"] == "provisoire" for t in teeth if t["nom"] not in published["hommes"]) and all(t["source"].startswith("publié") for t in teeth if t["nom"] in published["hommes"])
statuses = prov["statut"].startswith("non vérifié") and published["source"].startswith("Alsahli")
all_null_marked = all(v.get("statut", "").startswith("non vérifié") for v in REFERENCE["valeurs"].values() if v.get("valeur", 1) is None)
check("D3_provenance_publie_ou_provisoire_signale", unpublished_ok and statuses and all_null_marked, {"provisoires": [t["nom"] for t in teeth if t["source"] == "provisoire"], "publiees": [t["nom"] for t in teeth if t["source"] != "provisoire"]})

# D4 dans la cavité, 3 morphologies, bouche fermée puis ouverte (20°)
fit = {}
for label, values in MORPHOLOGIES.items():
    body = new_body(**values)
    rig = skeleton.install(body)
    pose = rig.pose.bones[skeleton.JAW]
    pose.rotation_mode = "XYZ"
    state = {}
    for pose_name, angle in (("fermee", 0.0), ("ouverte_20", None)):
        if angle is None:
            best = None
            for sign in (1.0, -1.0):
                pose.rotation_euler = (sign * math.radians(20), 0, 0)
                points, polygons = evaluated_cage(body)
                drop = -points[skeleton.JAW_CHIN, 2]
                if best is None or drop > best[0]:
                    best = (drop, sign)
            pose.rotation_euler = (best[1] * math.radians(20), 0, 0)
        else:
            pose.rotation_euler = (0, 0, 0)
        points, polygons = evaluated_cage(body)
        tree = BVHTree.FromPolygons([tuple(map(float, p)) for p in points], polygons)
        for part in dental.parts_of(body):
            flags = inside_solid(world_points(part), tree)
            state[f"{pose_name}/{part.name}"] = {"sommets": len(flags), "dans_la_masse": int(flags.sum()), "pourcent": round(float(flags.mean()) * 100, 2)}
    fit[label] = state
worst_percent = max(v["pourcent"] for s in fit.values() for v in s.values())
check("D4_dans_la_cavite", worst_percent <= 5.0, {"pire_pourcent": worst_percent, "mesures": fit})

# D5 suivi de la mâchoire
body = new_body()
rig = skeleton.install(body)
pose = rig.pose.bones[skeleton.JAW]
pose.rotation_mode = "XYZ"
before = {o.name: world_points(o).mean(0) for o in dental.parts_of(body)}
pose.rotation_euler = (math.radians(20), 0, 0)
after = {o.name: world_points(o).mean(0) for o in dental.parts_of(body)}
moves = {n: round(float(np.linalg.norm(after[n] - before[n])) * 1000, 2) for n in before}
pose.rotation_euler = (math.radians(-20), 0, 0)
after2 = {o.name: world_points(o).mean(0) for o in dental.parts_of(body)}
moves2 = {n: round(float(np.linalg.norm(after2[n] - before[n])) * 1000, 2) for n in before}
check("D5_machoire_entraine_dents_basses_et_langue", moves["HL Dents hautes"] < 0.01 and moves["HL Dents basses"] > 10 and moves["HL Langue"] > 10 and moves2["HL Dents hautes"] < 0.01, {"+20": moves, "-20": moves2})
pose.rotation_euler = (0, 0, 0)

# D6 âge
counts = {}
for label, values in (("enfant", {"age": 0.0}), ("adulte", {"age": 2.0}), ("senior", {"age": 3.0})):
    body = new_body(**values)
    skeleton.install(body)
    upper = next(o for o in dental.parts_of(body) if o.name == "HL Dents hautes")
    teeth = json.loads(upper["hl_dental_teeth"])
    counts[label] = {"dents_par_cote": len(teeth), "lacteale": bool(upper["hl_dental_primary"]), "centrale": {"largeur": round(teeth[0]["largeur"], 3), "hauteur": round(teeth[0]["hauteur"], 3), "usure": round(teeth[0]["usure"], 3)}}
check("D6_adaptation_a_l_age", counts["enfant"]["dents_par_cote"] == 5 and counts["enfant"]["lacteale"] and counts["adulte"]["dents_par_cote"] == 7 and not counts["adulte"]["lacteale"]
      and counts["enfant"]["centrale"]["largeur"] < counts["adulte"]["centrale"]["largeur"] and counts["senior"]["centrale"]["usure"] == prov["usure_senior_mm"]["perte_de_hauteur_incisives_canines"]
      and counts["senior"]["centrale"]["hauteur"] < counts["adulte"]["centrale"]["hauteur"], counts)

# D7 mise à jour
body = new_body()
rig = skeleton.install(body)
names_before = sorted(o.name for o in dental.parts_of(body))
tongue_before = world_points(next(o for o in dental.parts_of(body) if o.name == "HL Langue")).mean(0)
human.set_value(body, "age", 3.0)
human.set_value(body, "sex", 0.0)
state_outdated = skeleton.status(body)[0]
skeleton.update(body, dental=True)
parts_after = dental.parts_of(body)
tongue_after = world_points(next(o for o in parts_after if o.name == "HL Langue")).mean(0)
check("D7_mise_a_jour", state_outdated == skeleton.OUTDATED and sorted(o.name for o in parts_after) == names_before and len(parts_after) == 3 and float(np.linalg.norm(tongue_after - tongue_before)) > 1e-3
      and all(o.parent == rig for o in parts_after) and skeleton.status(body)[0] == skeleton.INSTALLED, {"deplacement_langue_mm": round(float(np.linalg.norm(tongue_after - tongue_before)) * 1000, 2), "objets": len(parts_after)})

# D9 duplication (avant le retrait)
clone = human.duplicate_human(bpy.context, body)
clone_rig = skeleton.rigs_of(clone)
clone_parts = dental.parts_of(clone)
originals = dental.parts_of(body)
check("D9_duplication_independante", len(clone_rig) == 1 and len(clone_parts) == 3 and all(c.parent == clone_rig[0] for c in clone_parts) and len(originals) == 3
      and all(c.data is not o.data for c in clone_parts for o in originals), {"copies": [c.name for c in clone_parts], "armature_de_la_copie": clone_rig[0].name if clone_rig else None})

# D8 retrait sans résidu
bpy.data.orphans_purge(do_recursive=True)  # les corps des essais précédents ont laissé des maillages orphelins : on ne mesure que le retrait de CE test
removed = skeleton.remove(clone)
mesh_names_left = [m.name for m in bpy.data.meshes if m.name.startswith(("HL Dents", "HL Langue")) and m.users == 0]
check("D8_retrait_sans_residu", not dental.parts_of(clone) and len(dental.parts_of(body)) == 3 and not mesh_names_left, {"retires": removed, "maillages_orphelins": mesh_names_left})
skeleton.remove(body)
check("D8b_retrait_du_dernier", not [o for o in bpy.data.objects if o.get(dental.MARKER)] and not [m for m in bpy.data.meshes if m.name.startswith(("HL Dents", "HL Langue")) and m.users == 0])

if OUT:
    Path(OUT).write_text(json.dumps(results, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
print("RESULT", "FAIL " + ", ".join(failures) if failures else "PASS")
sys.exit(1 if failures else 0)
