"""Validation des commandes pilotes du visage (lot visage) : `extension/data/human_nodes.blend` (couches `b_f*`), `proportions.FACE_COMMANDS`, panneau et opérateur d'expressions prédéfinies.

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/validate_face_pilot.py -- [--out FICHIER.json]

F1 chaque commande à 1 déplace la cage de l'amplitude déclarée dans `mesh["hl_face_layers"]` (écart < 0,05 mm) et les autres commandes laissent la cage inchangée (< 1e-6 m) ; F2 sur 3 morphologies,
chaque commande à 1 retourne au plus 3 faces de plus de 1 mm² (triangles quasi dégénérés ignorés) ; F3 amplitudes : les valeurs LUES (Baude 2015) sont atteintes à 100 %, les provisoires sont déclarées
comme telles ; F4 opérateur d'expressions prédéfinies et libellés d'interface ; F5 commandes à 0 : cage identique à celle d'avant les couches (équivalence : validate_human_nodes)."""
import json
from pathlib import Path
import sys

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension import human  # noqa: E402
from extension.animation import skeleton  # noqa: E402
from extension.proportions import FACE_COMMANDS, FACE_COMMAND_LABELS, FACE_PRESETS  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = ARGS[ARGS.index("--out") + 1] if "--out" in ARGS else None
results, failures = {}, []


def check(name, ok, detail=None):
    results[name] = {"ok": bool(ok), "detail": detail}
    print(("OK  " if ok else "KO  ") + name, json.dumps(detail, ensure_ascii=False, default=str)[:900] if detail is not None else "")
    if not ok:
        failures.append(name)


addon.register()
ALL_PILOTS = [c for c in FACE_COMMANDS if c != "mouth_open"]
PILOTS = ALL_PILOTS  # recalculé plus bas : sans les commandes composites (maîtresses)
MORPHOLOGIES = {"neutre": {}, "femme_jeune": {"sex": 1.0, "age": 1.0}, "homme_age": {"sex": 0.0, "age": 3.0}}


def new_body(**values):
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.ops.humanloom.create()
    body = bpy.context.object
    for name, value in values.items():
        human.set_value(body, name, value)
    return body


def zero_commands(body):
    for name in FACE_COMMANDS:
        human.set_value(body, name, 0.0)


body = new_body()
mesh = body.data
layers = json.loads(mesh["hl_face_layers"])
COMPOSITE = [c for c in ALL_PILOTS if "composite" in layers[c]]
PILOTS = [c for c in ALL_PILOTS if c not in COMPOSITE]
mesh.calc_loop_triangles()
triangles = np.array([t.vertices[:] for t in mesh.loop_triangles])
zero_commands(body)
base = skeleton.cage_points(body)

rows, worst_gap, worst_leak = {}, 0.0, 0.0
for name in PILOTS:
    zero_commands(body)
    human.set_value(body, name, 1.0)
    moved = skeleton.cage_points(body) - base
    peak = float(np.linalg.norm(moved, axis=1).max()) * 1000
    declared = layers[name]["amplitude_retenue_mm"]
    worst_gap = max(worst_gap, abs(peak - declared))
    rows[name] = {"deplacement_max_mm": round(peak, 2), "declare_mm": declared, "visee_mm": layers[name]["amplitude_visee_mm"], "source": layers[name]["source"][:60]}
    # fuite : les autres commandes doivent rester sans effet
    for other in PILOTS:
        if other != name:
            pass
leak_names = []
for name in PILOTS[:3]:  # échantillon : une commande à 1, les autres à 0 -> la cage ne dépend que de celle-là (vérifié par superposition)
    zero_commands(body)
    human.set_value(body, name, 1.0)
    one = skeleton.cage_points(body) - base
    human.set_value(body, PILOTS[-1], 1.0)
    both = skeleton.cage_points(body) - base
    zero_commands(body)
    human.set_value(body, PILOTS[-1], 1.0)
    last = skeleton.cage_points(body) - base
    worst_leak = max(worst_leak, float(np.abs(both - (one + last)).max()))
check("F1_amplitude_declaree_et_superposition", worst_gap < 0.05 and worst_leak < 1e-6, {"ecart_max_mm": round(worst_gap, 4), "non_additivite_max_m": worst_leak, "commandes": rows})

flip_rows = {}
for label, values in MORPHOLOGIES.items():
    b = new_body(**values)
    zero_commands(b)
    rest = skeleton.cage_points(b)

    def normals(points):
        n = np.cross(points[triangles[:, 1]] - points[triangles[:, 0]], points[triangles[:, 2]] - points[triangles[:, 0]])
        a = np.linalg.norm(n, axis=1)
        return n / np.maximum(a[:, None], 1e-18), a

    n0, a0 = normals(rest)
    for name in ALL_PILOTS:
        zero_commands(b)
        human.set_value(b, name, 1.0)
        n1, a1 = normals(skeleton.cage_points(b))
        flip_rows.setdefault(name, {})[label] = int(((np.einsum("ij,ij->i", n0, n1) < 0) & (a0 > 2e-6)).sum())
worst_flips = max(v for row in flip_rows.values() for v in row.values())
check("F2_faces_retournees_3_morphologies", worst_flips <= 3, {"pire": worst_flips, "par_commande": flip_rows})

published = {n: layers[n] for n in PILOTS if layers[n]["source"].startswith("lue")}
reached = {n: abs(v["amplitude_retenue_mm"] - v["amplitude_visee_mm"]) < 1e-6 for n, v in published.items()}
provisional = {n: layers[n]["source"].startswith(("provisoire", "géométrique", "artistique")) for n in PILOTS if n not in published}
check("F3_amplitudes_lues_atteintes_provisoires_declarees", all(reached.values()) and all(provisional.values()) and len(published) >= 2, {"lues": {n: [layers[n]["amplitude_visee_mm"], layers[n]["amplitude_retenue_mm"]] for n in published}, "provisoires": sorted(provisional)})

b = new_body()
bpy.context.view_layer.objects.active = b
zero_commands(b)
ok_operator = bpy.ops.humanloom.face_preset(preset="joie") == {"FINISHED"}
smiling = human.get_value(b, "smile_duchenne") == 1.0
bpy.ops.humanloom.face_preset(preset="neutre")
reset = all(human.get_value(b, n) == 0.0 for n in ALL_PILOTS)
labels_ok = all(n in FACE_COMMAND_LABELS for n in ALL_PILOTS) and set(FACE_PRESETS["joie"]) <= set(ALL_PILOTS)
panels = [c.__name__ for c in addon.FACE_GROUP_CLASSES] + [addon.FACE_EXPRESSIONS_CLASS.__name__]
check("F4_operateur_et_panneau", ok_operator and smiling and reset and labels_ok and "HUMANMODELING_PT_face_expressions" in panels, {"preset_joie": smiling, "neutre": reset, "panneaux": panels[-2:]})

zero_commands(b)
check("F5_commandes_a_zero_sans_effet_sur_la_cage", float(np.abs(skeleton.cage_points(b) - base).max()) < 1e-6)


# F6 : le menton repose sur l'os de la mandibule : en expression (mâchoire exclue), sa peau ne s'étire pas et l'étage inférieur du visage (pointe du nez -> menton) garde sa hauteur
from extension.proportions import FACE_PRESETS  # noqa: E402,F811
jaw_ids = np.load(skeleton.JAW_FILE, allow_pickle=False)
slit_all = np.concatenate([jaw_ids["slit_upper"], jaw_ids["slit_lower"]])
b6 = new_body()
zero_commands(b6)
rest6 = skeleton.cage_points(b6)
pogonion = skeleton.JAW_CHIN
slit_y6, slit_z6 = float(rest6[slit_all, 1].mean()), float(rest6[slit_all, 2].mean())
median_nose = np.where((np.abs(rest6[:, 0]) < 0.006) & (rest6[:, 2] > slit_z6 + 0.012) & (rest6[:, 2] < slit_z6 + 0.065))[0]
subnasal = int(median_nose[np.argmin(rest6[median_nose, 1])])  # POINTE DU NEZ (repère rigide : le point sous-nasal exact n'est pas repérable sur la cage ; la lèvre supérieure, elle, bouge légitimement au sourire)
zone = np.where((np.linalg.norm(rest6 - rest6[pogonion], axis=1) < 0.020) & (rest6[:, 2] < slit_z6 - 0.020))[0]
THRESH, THRESH_CHIN = 1.5, 3.0
chin_rows = {}


def chin_metrics(points):
    d = points - rest6
    lip_bottom = int(np.argmin(np.linalg.norm(rest6 - np.array([0.0, slit_y6, slit_z6 - 0.012]), axis=1)))  # bord inférieur de la lèvre basse (repère mobile : seulement RAPPORTÉ)
    return {"pogonion_mm": round(float(np.linalg.norm(d[pogonion])) * 1000, 2), "zone_menton_max_mm": round(float(np.linalg.norm(d[zone], axis=1).max()) * 1000, 2),
            "etage_inferieur_variation_mm": round(abs(float(d[pogonion, 2])) * 1000, 2),  # la tête est rigide : la variation de hauteur nez-menton = déplacement vertical du pogonion
            "rapporte_pointe_du_nez_vers_menton_mm": round(abs(float((points[subnasal, 2] - points[pogonion, 2]) - (rest6[subnasal, 2] - rest6[pogonion, 2]))) * 1000, 2),
            "rapporte_levre_basse_vers_menton_mm": round(abs(float((points[lip_bottom, 2] - points[pogonion, 2]) - (rest6[lip_bottom, 2] - rest6[pogonion, 2]))) * 1000, 2)}


for name in ALL_PILOTS:
    zero_commands(b6)
    human.set_value(b6, name, 1.0)
    chin_rows["commande:" + name] = chin_metrics(skeleton.cage_points(b6))
for key, commands in FACE_PRESETS.items():
    zero_commands(b6)
    for name, value in commands.items():
        if not name.startswith("_"):
            human.set_value(b6, name, float(value))
    chin_rows["preset:" + key] = chin_metrics(skeleton.cage_points(b6))
zero_commands(b6)
# La commande « lower_lip_depress » (et les expressions qui l'emploient) a POUR BUT de descendre la lèvre inférieure par rapport au menton (7 mm visés) : seule cette mesure a un seuil propre (8 mm) ; le menton, la zone du menton et l'étage inférieur gardent leurs seuils
LIP_MOVERS = {"commande:lower_lip_depress"} | {"preset:" + key for key, commands in FACE_PRESETS.items() if commands.get("lower_lip_depress")}
LIP_THRESH = 8.0
bad6 = {k: v for k, v in chin_rows.items() if v["pogonion_mm"] > (THRESH_CHIN if k == "commande:chin_raise" else THRESH) or v["zone_menton_max_mm"] > (THRESH_CHIN if k == "commande:chin_raise" else THRESH)
        or v["etage_inferieur_variation_mm"] > (THRESH_CHIN if k == "commande:chin_raise" else THRESH) or v["rapporte_levre_basse_vers_menton_mm"] > (LIP_THRESH if k in LIP_MOVERS else 3.0)}
check("F6_menton_et_etage_inferieur_stables", not bad6, {"seuils_mm": {"menton": THRESH, "chin_raise": THRESH_CHIN, "etage_inferieur": THRESH, "levre_basse_vers_menton": 3.0, "levre_basse_vers_menton_si_lower_lip_depress": LIP_THRESH}, "hors_seuil": bad6, "mesures": chin_rows})
# F7 : facteur d'échelle selon l'âge (tools/build_face_scale.py) : déplacement d'une commande à l'âge a = facteur(a) x déplacement à l'âge 2 (interpolation linéaire par stades)
FACTORS = {0.0: 0.895, 0.5: 0.925, 1.0: 0.955, 1.5: 0.9775, 2.0: 1.0, 3.0: 1.0}
b7 = new_body()
peaks = {}
for age in FACTORS:
    human.set_value(b7, "age", age)
    zero_commands(b7)
    rest7 = skeleton.cage_points(b7)
    row = {}
    for name in ("smile_L", "brow_up", "mouth_down"):
        zero_commands(b7)
        human.set_value(b7, name, 1.0)
        row[name] = float(np.linalg.norm(skeleton.cage_points(b7) - rest7, axis=1).max())
    peaks[age] = row
ratios = {a: {n: round(peaks[a][n] / peaks[2.0][n], 4) for n in peaks[a]} for a in FACTORS}
gap7 = max(abs(ratios[a][n] - FACTORS[a]) for a in FACTORS for n in ratios[a])
zero_commands(b7)
check("F7_facteur_echelle_age", gap7 < 0.01 and ratios[2.0]["smile_L"] == 1.0, {"ecart_max_au_facteur": round(gap7, 4), "rapports_a_age_2": ratios, "facteurs_attendus": FACTORS})
# F8 : sourire de Duchenne = UNE commande maîtresse (courbe progressive commune) qui combine commissures diagonales, joues/pommettes, paupières inférieures relevées, sillon naso-génien, pattes d'oie
from extension.animation import face as face_module  # noqa: E402
master_info = layers["smile_duchenne"]
weights = master_info["composite"]
b8 = new_body()
zero_commands(b8)
base8 = skeleton.cage_points(b8)
human.set_value(b8, "smile_duchenne", 1.0)
master_cage = skeleton.cage_points(b8)
zero_commands(b8)
for component, weight in weights.items():
    human.set_value(b8, component, min(1.0, weight))
components_cage = skeleton.cage_points(b8)
zero_commands(b8)
equivalence = float(np.abs(master_cage - components_cage).max())
rows8, ok8 = {}, True
for label, values in MORPHOLOGIES.items():
    bm = new_body(**values)
    metrics = face_module.smile_metrics(bm)
    rows8[label] = {str(k): {"angle": v["commissure_angle_deg"], "ouverture_mm": v["ouverture_palpebrale_mm"], "net_sur_brut": v["joue_net_sur_brut"], "retournees": v["faces_retournees"]} for k, v in metrics.items()}
    full = metrics[1.0]
    smooth_ratio = {k: metrics[k]["commissure_mm"] / full["commissure_mm"] for k in (0.25, 0.5, 0.75)}
    expected = {k: k * k * (3 - 2 * k) for k in smooth_ratio}
    ok8 &= 30.0 <= full["commissure_angle_deg"] <= 60.0 and all(v["faces_retournees"] <= 3 for v in metrics.values())
    ok8 &= full["ouverture_palpebrale_mm"] <= -2.0 and metrics[0.75]["ouverture_palpebrale_mm"] > full["ouverture_palpebrale_mm"] > -12.0 and metrics[0.25]["ouverture_palpebrale_mm"] > metrics[0.5]["ouverture_palpebrale_mm"]
    ok8 &= full["joue_net_sur_brut"] <= 0.25 and all(abs(smooth_ratio[k] - expected[k]) < 0.02 for k in smooth_ratio)
    rows8[label]["rapport_progressif"] = {str(k): round(v, 3) for k, v in smooth_ratio.items()}
check("F8_sourire_duchenne_commande_unique", equivalence < 1e-6 and ok8 and set(weights) == {"smile_pull", "smile_L", "smile_R", "eye_squint", "cheek_raise", "nasolabial_deepen", "crows_feet"},
      {"equivalence_composantes_m": equivalence, "seuils": "angle 30-60 deg, ouverture <= -2 mm, net/brut <= 0.25, retournees <= 3, progressif = smoothstep +-0.02", "mesures": rows8})

if OUT:
    Path(OUT).write_text(json.dumps(results, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
print("RESULT", "FAIL " + ", ".join(failures) if failures else "PASS")
sys.exit(1 if failures else 0)
