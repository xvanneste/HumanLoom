"""Validation du moteur de foule natif (lots C1 et C2) : tirage à graine, diversité (pas de clones), garde-fous, comportements, trajectoires, évitement, décalage de phase, foule figée (réouverture),
régénération ciblée, zones (trottoirs, passage), variantes extensibles, niveaux de détail.

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/validate_crowd.py -- [--out FICHIER.json]

Les animations de comportement sont des clips synthétiques (bouchon) : aucune bibliothèque requise."""
import json
from pathlib import Path
import sys
import tempfile

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension import crowd, human  # noqa: E402
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
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)

# C1 tirage déterministe
spec = crowd.default_spec(40, 7)
a, b = crowd.sample_members(spec), crowd.sample_members(spec)
c = crowd.sample_members(crowd.default_spec(40, 8))
check("C1_tirage_deterministe_a_graine", a == b and a != c and all(m["params"] != n["params"] for m, n in zip(a, c)), {"identiques_meme_graine": a == b, "differents_autre_graine": a != c})

# C2 diversité
big = crowd.default_spec(150, 21)
members = crowd.sample_members(big)
report = crowd.diversity_report(members)
check("C2_diversite_pas_de_clones", len(members) == 150 and report["distance_min"] >= big["min_distance"] and report["couverture_age"] >= 0.8 * (3 - 1) / 3 and report["couverture_sexe"] >= 0.8
      and len({json.dumps(m["params"], sort_keys=True) for m in members}) == 150, report)

# C3 garde-fous
extreme = crowd.default_spec(60, 3)
extreme["ranges"] = {k: ([-1.0, 1.0] if k not in ("sex", "age") else ([0.0, 1.0] if k == "sex" else [0.0, 3.0])) for k in extreme["ranges"]}
extremes = crowd.sample_members(extreme)
within = all(crowd._limits(k)[0] - 1e-9 <= v <= crowd._limits(k)[1] + 1e-9 for m in extremes for k, v in m["params"].items())
plausible = all(abs(m["params"]["adiposity"]) + abs(m["params"]["muscles"]) <= 1.4 + 1e-9 for m in extremes)
check("C3_garde_fous_anatomiques", within and plausible, {"dans_les_bornes": within, "adiposite_muscles_bornes": plausible, "pire_somme": round(max(abs(m["params"]["adiposity"]) + abs(m["params"]["muscles"]) for m in extremes), 3)})

# C6 évitement (simulation seule, sans objets) : deux flux opposés
flow = crowd.default_spec(12, 1)
flow["frames"] = 240
flow["area"] = [-8.0, -4.0, 8.0, 4.0]
agents = []
for i in range(12):  # 6 contre 6 dans un couloir de 3 m (2 personnes par mètre de largeur : dense)
    left = i % 2 == 0
    y = -1.5 + 3.0 * (i // 2) / 5.0
    agents.append({"id": i, "behavior": "walk", "start": [-6.0 if left else 6.0, y], "path": [[6.0 if left else -6.0, y]], "speed": 1.4, "lateral": 0.0, "delay_s": 0.0})


def min_distance(positions):
    n = positions.shape[1]
    d = np.linalg.norm(positions[:, :, None] - positions[:, None], axis=-1) + np.eye(n)[None] * 1e9
    return float(d.min())


with_avoid, _ = crowd.simulate(dict(flow, avoidance=True), agents)
without_avoid, _ = crowd.simulate(dict(flow, avoidance=False), agents)
check("C6_evitement_entre_flux_opposes", min_distance(with_avoid) >= 0.40 and min_distance(without_avoid) < 0.25 and np.isfinite(with_avoid).all(),
      {"distance_min_avec_m": round(min_distance(with_avoid), 3), "distance_min_sans_m": round(min_distance(without_avoid), 3)})

# C4/C5/C7/C10/C11 construction d'une foule complète (10 personnages, 6 comportements, zones, variantes)
applied = []
crowd.register_variant_applier("outfit", lambda body, value: applied.append((body.name, value)))
full = crowd.default_spec(10, 5)
full["frames"] = 300
full["behaviors"] = {"walk": 2.0, "run": 1.5, "wait": 1.5, "chat": 3.0, "jump": 1.0, "cross": 2.0}
full["zones"] = [{"kind": "sidewalk", "rect": [-10.0, 3.0, 10.0, 5.0]}, {"kind": "crossing", "rect": [-1.0, -3.0, 1.0, 3.0]}]
full["light_cycle_s"] = 4.0
full["variants"] = {"outfit": ["tenue_a", "tenue_b", "tenue_c"]}
summary = crowd.generate(bpy.context, full)
scene = bpy.context.scene
bodies = crowd.members_of(scene)
spec_loaded, members_loaded = crowd.load(scene)
collection = bpy.data.collections.get(crowd.COLLECTION)
rigs_ok = all(len(skeleton.rigs_of(b)) == 1 for b in bodies)
in_collection = all(b in collection.objects.values() and all(r in collection.objects.values() for r in skeleton.rigs_of(b)) for b in bodies)
expr_ok = all(abs(human.get_value(b, "smile_duchenne") - (1.0 if m["expression"] == "joie" else 0.0)) < 1e-6 for b, m in zip(bodies, members_loaded))
check("C4_construction_objets_rigs_expressions", len(bodies) == 10 and rigs_ok and in_collection and expr_ok and summary["personnages"] == 10 and len(applied) == 10 and {v for _, v in applied} <= {"tenue_a", "tenue_b", "tenue_c"},
      {"comportements": summary["comportements"], "variantes_appliquees": len(applied), "diversite_min": round(summary["diversite"]["distance_min"], 3)})

positions, yaws = crowd.simulate(spec_loaded, members_loaded)
fps = spec_loaded["fps"]
rows, ok5 = {}, True
for i, m in enumerate(members_loaded):
    travelled = float(np.linalg.norm(np.diff(positions[:, i], axis=0), axis=1).sum())
    rows.setdefault(m["behavior"], []).append(round(travelled, 2))
    if m["behavior"] in ("wait", "jump", "chat"):
        ok5 &= travelled < 1e-6
    if m["behavior"] in ("walk", "run"):
        ok5 &= travelled > 0.4 * m["speed"] * spec_loaded["frames"] / fps  # trajet continu (allers-retours) : au moins 40 % de la distance théorique malgré virages et évitement
chat_pairs = [(m, next(n for n in members_loaded if n["id"] == m["partner"])) for m in members_loaded if m["behavior"] == "chat" and m["id"] < m.get("partner", -1)]
pair_ok = all(abs(np.linalg.norm(np.array(m["start"]) - np.array(n["start"])) - 1.0) < 0.05 for m, n in chat_pairs)
for m, n in chat_pairs:
    i, j = m["id"], n["id"]
    to_partner = np.array(n["start"]) - np.array(m["start"])
    ok5 &= abs((np.arctan2(to_partner[1], to_partner[0]) - yaws[-1, [k for k, x in enumerate(members_loaded) if x["id"] == i][0]] + np.pi) % (2 * np.pi) - np.pi) < 0.05
check("C5_comportements_vitesses_discussions", ok5 and pair_ok and len(chat_pairs) >= 1, {"distance_parcourue_m_par_comportement": rows, "paires_de_discussion": len(chat_pairs)})

walkers = [(b, m) for b, m in zip(bodies, members_loaded) if m["behavior"] in ("walk", "run", "cross")]
starts = {round(m["strip_start"], 3) for _, m in walkers}
scales = [(m["speed"], skeleton.rigs_of(b)[0].animation_data.nla_tracks["Foule"].strips[0].scale) for b, m in walkers]
scales_ok = all(s[1] > 0 for s in scales) and (len({round(s[1], 3) for s in scales}) > 1)
check("C7_decalage_de_phase_et_echelle_de_vitesse", len(starts) >= max(2, int(0.7 * len(walkers))) and scales_ok and all(m["cycle_frames"] > 0 for _, m in walkers),
      {"departs_de_bande_distincts": len(starts), "marcheurs": len(walkers), "echelles": sorted({round(s[1], 2) for s in scales})})

sidewalk = full["zones"][0]["rect"]
crossing = full["zones"][1]["rect"]
rows10, ok10 = {}, True
for i, m in enumerate(members_loaded):
    if m["behavior"] == "cross":
        far = np.array(m["path"][0])
        ok10 &= crossing[0] - 1e-6 <= m["start"][0] <= crossing[2] + 1e-6 and crossing[1] - 1e-6 <= m["start"][1] <= crossing[3] + 1e-6
        ok10 &= m["delay_s"] >= 0.0 and np.linalg.norm(positions[0, i] - np.array(m["start"])) < 1e-6
        ok10 &= float(np.linalg.norm(positions[-1, i] - far)) < 0.6  # arrivé de l'autre côté
        rows10.setdefault("traversees", []).append(round(float(np.linalg.norm(positions[-1, i] - far)), 2))
    if m["behavior"] in ("walk", "run"):
        ok10 &= sidewalk[0] - 1e-6 <= m["start"][0] <= sidewalk[2] + 1e-6 and sidewalk[1] - 1e-6 <= m["start"][1] <= sidewalk[3] + 1e-6
check("C10_trottoirs_et_passage_pieton", ok10 and bool(rows10), rows10)

# C8 foule figée : enregistrement, réouverture, refus de regénérer sans demande, régénération ciblée
frame_check = 100
scene.frame_set(frame_check)
before = {b.name: tuple(round(x, 5) for x in b.matrix_world.translation) for b in bodies}
saved_json = scene[crowd.KEY]
refused = False
try:
    crowd.generate(bpy.context, full)
except ValueError:
    refused = True
path = Path(tempfile.mkdtemp(prefix="hl_crowd_")) / "foule.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(path))
bpy.ops.wm.open_mainfile(filepath=str(path))
addon.register() if not hasattr(bpy.types, "HUMANLOOM_PT_rig") else None
scene = bpy.context.scene
scene.frame_set(frame_check)
bodies2 = crowd.members_of(scene)
after = {b.name: tuple(round(x, 5) for x in b.matrix_world.translation) for b in bodies2}
check("C8_foule_figee_reouverture_identique", scene[crowd.KEY] == saved_json and before == after and len(bodies2) == 10 and refused, {"json_identique": scene[crowd.KEY] == saved_json, "positions_identiques": before == after, "regeneration_sans_demande_refusee": refused})

old_members = crowd.load(scene)[1]
old_positions = {b[crowd.OBJECT_KEY]: tuple(b.matrix_world.translation) for b in bodies2}
planned = crowd.regenerate_member(bpy.context, 3)
new_members = crowd.load(scene)[1]
changed = [m["id"] for m, n in zip(old_members, new_members) if m["params"] != n["params"]]
others_same = all(old_members[i] == new_members[i] for i in range(10) if i != 3)
check("C8b_regeneration_ciblee_d_un_personnage", changed == [3] and others_same and len(crowd.members_of(scene)) == 10 and planned["regenerated"] == 1, {"personnages_modifies": changed, "autres_identiques": others_same})
regen_spec = crowd.load(scene)[0]
all_summary = crowd.regenerate_all(bpy.context)
new_all = crowd.load(scene)[1]
check("C8c_regeneration_totale_sur_demande", crowd.load(scene)[0]["regeneration"] == regen_spec["regeneration"] + 1 and all_summary["personnages"] == 10 and [m["params"] for m in new_all] != [m["params"] for m in old_members] and len(crowd.members_of(scene)) == 10)

# C9 niveaux de détail (le niveau 2 garde les triangles de la cage mais retire les nœuds géométriques : gain en temps d'évaluation, mesuré par tools/measure_crowd.py)
body = crowd.members_of(scene)[0]
stature_full = float(max(skeleton.cage_points(body)[:, 2]))
counts, flags = {}, {}
for level in crowd.LOD_LEVELS:
    crowd.apply_lod(body, level)
    counts[level] = crowd.triangle_count(body)
    flags[level] = {"noeuds": human.MODIFIER_NAME in [m.name for m in body.modifiers], "armature": any(m.type == "ARMATURE" for m in body.modifiers), "groupes": len(body.vertex_groups), "dents_cachees": all(p.hide_viewport for p in dental.parts_of(body))}
height_lod = float(max(v.co.z for v in body.data.vertices))
refused_back = False
try:
    crowd.apply_lod(body, 1)
except ValueError:
    refused_back = True
check("C9_niveaux_de_detail", counts[0] > counts[1] >= counts[2] > counts[3] and not flags[2]["noeuds"] and flags[2]["armature"] and flags[2]["groupes"] >= 60 and flags[1]["dents_cachees"] and abs(height_lod - stature_full) < 0.02 and refused_back,
      {"triangles": counts, "etat": flags, "stature_cage_m": round(stature_full, 3), "stature_lod2_m": round(height_lod, 3)})
camera_data = bpy.data.cameras.new("cam")
camera = bpy.data.objects.new("cam", camera_data)
scene.collection.objects.link(camera)
scene.camera = camera
camera.location = (0.0, 0.0, 1.6)
levels = crowd.auto_lod(scene)
check("C9b_lod_automatique_selon_la_distance", set(levels) == set(range(10)) and all(0 <= v <= 3 for v in levels.values()) and all(levels[i] >= 0 for i in levels), {"niveaux": levels})

# C12 opérateurs et panneau : une foule figée refuse « Générer » (poll), « Régénérer ce personnage » agit sur le personnage actif
bpy.context.view_layer.objects.active = crowd.members_of(scene)[2]
ok_poll = not bpy.ops.humanloom.crowd_generate.poll()
ok_member = bpy.ops.humanloom.crowd_regenerate_member() == {"FINISHED"} and len(crowd.members_of(scene)) == 10
ok_clear = bpy.ops.humanloom.crowd_clear() == {"FINISHED"} and crowd.load(scene) is None and not crowd.members_of(scene)
ok_generate = bpy.ops.humanloom.crowd_generate(count=2, seed=4, frames=48) == {"FINISHED"} and len(crowd.members_of(scene)) == 2
check("C12_operateurs_et_panneau", ok_poll and ok_member and ok_clear and ok_generate and hasattr(bpy.types, "HUMANLOOM_PT_crowd"), {"generer_refuse_si_foule": ok_poll, "regenerer_personnage": ok_member, "effacer": ok_clear, "generer_2": ok_generate})

if OUT:
    Path(OUT).write_text(json.dumps(results, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
print("RESULT", "FAIL " + ", ".join(failures) if failures else "PASS")
sys.exit(1 if failures else 0)
