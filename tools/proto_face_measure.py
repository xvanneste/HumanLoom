"""PROTOTYPE JETABLE de mesure (D-30) : tête de Rain ↔ tête de HumanLoom. Aucun code de production, aucune donnée de Rain dans le dépôt.

Mesure, sur des chiffres, ce qu'il faut pour choisir entre le portage de Rain (A), des clés ARKit (B) ou un hybride (C) :
  T1 topologie autour des yeux et de la bouche (densité d'arêtes, ouverture de la bouche, polygones non quadrangulaires) ;
  T2 correspondance de têtes : 8 repères AUTOMATIQUES (approximatifs : extrema), thin-plate spline, résidu et validation croisée ;
  T3 os de Rain recalés : combien tombent hors de la peau de HumanLoom ;
  T4 transfert des poids (projection sur la face la plus proche, interpolée) : influences, élagage à 8 et 4, distance de projection ;
  T5 clé de forme sur « HL Human Base » avant les nœuds : addition, effet de la morphologie, temps d'évaluation (critère 33 ms).
Pré-requis : sortie de `proto_face_extract_rain.py` (--rain-npz). Exécution :
  blender --background --factory-startup --offline-mode --python tools/proto_face_measure.py -- --rain-npz X.npz --out Y.json
"""
import json
from pathlib import Path
import statistics
import sys
import time

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
ARGS = sys.argv[sys.argv.index("--") + 1:]
RAIN = np.load(ARGS[ARGS.index("--rain-npz") + 1], allow_pickle=False)
OUT = ARGS[ARGS.index("--out") + 1]
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension import human  # noqa: E402

report = {}


def say(key, value):
    report[key] = value
    print("MESURE", key, json.dumps(value, ensure_ascii=False)[:700])


# --- HumanLoom : cage évaluée (nœuds seulement), yeux ----------------------------------------------------------------------------
addon.register()
bpy.ops.humanloom.create()
body = bpy.context.object
for modifier in body.modifiers:
    modifier.show_viewport = modifier.name == "HL Human"


def evaluate(obj):
    human.touch(obj)
    bpy.context.view_layer.update()
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    buffer = np.empty(len(mesh.vertices) * 3, np.float32)
    mesh.vertices.foreach_get("co", buffer)
    points = buffer.reshape(-1, 3).astype(np.float64)
    evaluated.to_mesh_clear()
    return points


hl = evaluate(body)
hl_mesh = body.data
hl_mesh.calc_loop_triangles()
hl_triangles = np.array([t.vertices[:] for t in hl_mesh.loop_triangles], dtype=np.int64)
hl_edges = np.array([e.vertices[:] for e in hl_mesh.edges], dtype=np.int64)
hl_polygon_sizes = np.array([len(p.vertices) for p in hl_mesh.polygons], dtype=np.int64)
hl_edge_faces = np.zeros(len(hl_mesh.edges), dtype=np.int64)
lookup = {tuple(sorted(e.vertices)): i for i, e in enumerate(hl_mesh.edges)}
for polygon in hl_mesh.polygons:
    ring = list(polygon.vertices)
    for a, b in zip(ring, ring[1:] + ring[:1]):
        hl_edge_faces[lookup[tuple(sorted((a, b)))]] += 1
hl_eyes = [np.mean([(o.matrix_world @ v.co)[:] for v in o.data.vertices], axis=0) for o in (body.humanloom.eye_left, body.humanloom.eye_right)]

rain = RAIN["points"]
rain_eye_points = RAIN["eye_points"]


# --- repères automatiques (approximatifs) -------------------------------------------------------------------------------------------
def landmarks(points, eye_a, eye_b, top_drop):
    """8 repères par extrema : sommet, pointe du nez, menton, oreilles (x extrêmes), arrière, deux yeux. `top_drop` : hauteur minimale d'une tête sous le sommet."""
    zmax = points[:, 2].max()
    zone = points[points[:, 2] > zmax - top_drop]
    nose = zone[np.argmin(zone[:, 1])]
    face = zone[(zone[:, 1] < nose[1] + 0.05) & (np.abs(zone[:, 0]) < 0.01) & (zone[:, 2] < nose[2])]
    chin = face[np.argmin(face[:, 2])]
    head = zone[zone[:, 2] > chin[2] - 0.01]
    ear_zone = head[(head[:, 1] > nose[1] + 0.06) & (head[:, 2] > chin[2] + 0.3 * (zmax - chin[2])) & (head[:, 2] < zmax - 0.3 * (zmax - chin[2]))]
    left, right = ear_zone[np.argmax(ear_zone[:, 0])], ear_zone[np.argmin(ear_zone[:, 0])]
    back = head[np.argmax(head[:, 1])]
    eye_left, eye_right = (eye_a, eye_b) if eye_a[0] > eye_b[0] else (eye_b, eye_a)
    names = ["top", "nose", "chin", "ear_+x", "ear_-x", "back", "eye_+x", "eye_-x"]
    return names, np.array([points[np.argmax(points[:, 2])], nose, chin, left, right, back, eye_left, eye_right]), head


rain_eye_a = rain_eye_points[rain_eye_points[:, 0] > 0].mean(0)
rain_eye_b = rain_eye_points[rain_eye_points[:, 0] <= 0].mean(0)
names, lm_rain, rain_head = landmarks(rain, rain_eye_a, rain_eye_b, 0.40)
_, lm_hl, hl_head = landmarks(hl, hl_eyes[0], hl_eyes[1], 0.40)
say("reperes_auto_rain_m", {n: lm_rain[i].round(4).tolist() for i, n in enumerate(names)})
say("reperes_auto_humanloom_m", {n: lm_hl[i].round(4).tolist() for i, n in enumerate(names)})


def ratios(lm):
    d = lambda a, b: float(np.linalg.norm(lm[a] - lm[b]))
    n = {k: i for i, k in enumerate(names)}
    return {"hauteur_menton_sommet": d(n["chin"], n["top"]), "nez_menton": d(n["nose"], n["chin"]), "largeur_oreilles": d(n["ear_+x"], n["ear_-x"]),
            "ecart_yeux": d(n["eye_+x"], n["eye_-x"]), "profondeur_nez_arriere": d(n["nose"], n["back"]), "nez_sommet": d(n["nose"], n["top"])}


r_rain, r_hl = ratios(lm_rain), ratios(lm_hl)
say("T2_proportions_rain_m", {k: round(v, 4) for k, v in r_rain.items()})
say("T2_proportions_humanloom_m", {k: round(v, 4) for k, v in r_hl.items()})
say("T2_rapport_humanloom_sur_rain", {k: round(r_hl[k] / r_rain[k], 3) for k in r_rain})
say("T2_rapports_adimensionnes", {"nez_menton/hauteur": [round(r_rain["nez_menton"] / r_rain["hauteur_menton_sommet"], 3), round(r_hl["nez_menton"] / r_hl["hauteur_menton_sommet"], 3)],
                                  "ecart_yeux/largeur_oreilles": [round(r_rain["ecart_yeux"] / r_rain["largeur_oreilles"], 3), round(r_hl["ecart_yeux"] / r_hl["largeur_oreilles"], 3)]})


# --- thin-plate spline 3D (noyau |r|) avec partie affine -------------------------------------------------------------------------------
class ThinPlate:
    def __init__(self, source, target, regularization=0.0):
        n = len(source)
        kernel = np.linalg.norm(source[:, None] - source[None], axis=2) + regularization * np.eye(n)
        affine = np.hstack([np.ones((n, 1)), source])
        system = np.zeros((n + 4, n + 4))
        system[:n, :n], system[:n, n:], system[n:, :n] = kernel, affine, affine.T
        right = np.zeros((n + 4, 3))
        right[:n] = target
        self.source, self.solution = source, np.linalg.solve(system, right)

    def __call__(self, points):
        kernel = np.linalg.norm(points[:, None] - self.source[None], axis=2)
        n = len(self.source)
        return kernel @ self.solution[:n] + np.hstack([np.ones((len(points), 1)), points]) @ self.solution[n:]


warp = ThinPlate(lm_rain, lm_hl)
say("T2_residu_aux_reperes_mm", round(float(np.abs(warp(lm_rain) - lm_hl).max()) * 1000, 6))
errors = []
for i in range(len(lm_rain)):
    keep = [j for j in range(len(lm_rain)) if j != i]
    model = ThinPlate(lm_rain[keep], lm_hl[keep])
    errors.append(float(np.linalg.norm(model(lm_rain[i:i + 1])[0] - lm_hl[i])) * 1000)
say("T2_validation_croisee_mm", {"par_repere": dict(zip(names, np.round(errors, 1))), "moyenne": round(statistics.mean(errors), 1), "max": round(max(errors), 1)})

# Chamfer avant/après (tête de Rain au-dessus du menton) contre la surface de HumanLoom.
hl_tree = BVHTree.FromPolygons([Vector(p) for p in hl], [tuple(t) for t in hl_triangles])
chin_rain = lm_rain[2][2]
rain_face = rain[rain[:, 2] > chin_rain]


def distance_to_hl(points):
    result = np.empty(len(points))
    for i, p in enumerate(points):
        nearest = hl_tree.find_nearest(Vector(p))
        result[i] = nearest[3] if nearest[0] is not None else np.inf
    return result


def summary(values):
    return {"moyenne_mm": round(float(values.mean()) * 1000, 2), "p95_mm": round(float(np.percentile(values, 95)) * 1000, 2), "max_mm": round(float(values.max()) * 1000, 2)}


scale = r_hl["hauteur_menton_sommet"] / r_rain["hauteur_menton_sommet"]
similarity = (rain_face - lm_rain.mean(0)) * scale + lm_hl.mean(0)
say("T2_chamfer_rain_vers_humanloom_similitude", summary(distance_to_hl(similarity)))
warped_face = warp(rain_face)
say("T2_chamfer_rain_vers_humanloom_apres_TPS", summary(distance_to_hl(warped_face)))
say("T2_sommets_rain_au_dessus_du_menton", int(len(rain_face)))

# --- T1 topologie autour des yeux et de la bouche ----------------------------------------------------------------------------------------
def region_stats(points, edges, polygon_sizes, edge_faces, center, radius):
    mask = np.linalg.norm(points[edges[:, 0]] - center, axis=1) < radius
    lengths = np.linalg.norm(points[edges[mask, 0]] - points[edges[mask, 1]], axis=1)
    vertices = int((np.linalg.norm(points - center, axis=1) < radius).sum())
    return {"sommets": vertices, "arete_moyenne_mm": round(float(lengths.mean()) * 1000, 2) if len(lengths) else None, "aretes_de_bord": int((edge_faces[mask] == 1).sum())}


def mouth_center(lm):
    n = {k: i for i, k in enumerate(names)}
    nose, chin = lm[n["nose"]], lm[n["chin"]]
    return nose + 0.45 * (chin - nose)  # milieu approximatif entre le nez et le menton (estimation, pas un repère anatomique)


def skin_point(tree, point):
    """Point de la peau devant un centre d'œil (tir vers l'avant, -y) ; le centre lui-même est dans le globe, derrière la peau."""
    hit = tree.ray_cast(Vector(point), Vector((0, -1, 0)), 0.2)
    if hit[0] is not None:
        return np.array(hit[0])
    nearest = tree.find_nearest(Vector(point))  # paupière ouverte (trou du maillage) : point de la peau le plus proche
    return np.array(nearest[0]) if nearest[0] is not None else np.asarray(point)


rain_warped_for_tree = rain
rain_tree_raw = BVHTree.FromPolygons([Vector(p) for p in rain], [tuple(t) for t in RAIN["triangles"]])
for label, points, edges, sizes, faces_per_edge, lm, eye_pair, scale_factor, tree in (
        ("rain", rain, RAIN["edges"], RAIN["polygon_sizes"], RAIN["edge_faces"], lm_rain, (rain_eye_a, rain_eye_b), 1.0, rain_tree_raw),
        ("humanloom", hl, hl_edges, hl_polygon_sizes, hl_edge_faces, lm_hl, (hl_eyes[0], hl_eyes[1]), scale, hl_tree)):
    radius_eye, radius_mouth = 0.025 * scale_factor, 0.035 * scale_factor
    say(f"T1_{label}_oeil", region_stats(points, edges, sizes, faces_per_edge, skin_point(tree, eye_pair[0]), radius_eye))
    say(f"T1_{label}_bouche_estimee", region_stats(points, edges, sizes, faces_per_edge, mouth_center(lm), radius_mouth))
    head_vertices = (points[:, 2] > lm[2][2])
    in_head = head_vertices[edges[:, 0]] & head_vertices[edges[:, 1]]
    say(f"T1_{label}_tete", {"aretes": int(in_head.sum()), "aretes_de_bord_tete": int((faces_per_edge[in_head] == 1).sum()), "polygones_non_quad": int((sizes != 4).sum()), "polygones": int(len(sizes))})
# Rayon d'étude exprimé en échelle du visage : 2,5 cm autour de l'œil et 3,5 cm autour de la bouche pour Rain, mis à l'échelle de la hauteur menton-sommet pour HumanLoom.

# --- T3 os recalés dans la peau ----------------------------------------------------------------------------------------------------------
bone_names = [str(n) for n in RAIN["bone_names"]]
bone_head = warp(RAIN["bone_head"])
inside, outside_distances = [], []
for name, p in zip(bone_names, bone_head):
    nearest = hl_tree.find_nearest(Vector(p))
    if nearest[0] is None:
        continue
    normal_side = (Vector(p) - nearest[0]).dot(nearest[1])
    inside.append(normal_side < 0)
    if normal_side >= 0:
        outside_distances.append((nearest[3], name))
signed = []
for name, p in zip(bone_names, bone_head):
    nearest = hl_tree.find_nearest(Vector(p))
    if nearest[0] is not None:
        sign = 1.0 if (Vector(p) - nearest[0]).dot(nearest[1]) >= 0 else -1.0
        signed.append(sign * nearest[3])
signed = np.array(signed)
keep = np.array([not ("Eye" in n or "Teeth" in n or "Tongue" in n or "Gum" in n) for n in bone_names])[:len(signed)]
say("T3_distance_signee_os_a_la_peau_mm", {"hors_yeux_dents": {"mediane": round(float(np.median(signed[keep])) * 1000, 1), "p10": round(float(np.percentile(signed[keep], 10)) * 1000, 1), "p90": round(float(np.percentile(signed[keep], 90)) * 1000, 1),
    "plus_de_5mm_dehors": int((signed[keep] > 0.005).sum()), "plus_de_10mm_dehors": int((signed[keep] > 0.010).sum()), "plus_de_10mm_dedans": int((signed[keep] < -0.010).sum())}, "convention": "positif = hors de la peau"})
inside = np.array(inside)
outside_distances.sort(reverse=True)
is_eye_or_teeth = np.array([("Eye" in n or "Teeth" in n or "Tongue" in n or "Gum" in n) for n in bone_names])
say("T3_os_de_visage_rain", int(len(bone_names)))
say("T3_os_dans_la_peau", {"dans": int(inside.sum()), "hors_peau": int((~inside).sum()), "hors_peau_hors_yeux_dents": int(((~inside) & ~is_eye_or_teeth).sum()),
                           "distance_max_hors_peau_mm": round(outside_distances[0][0] * 1000, 1) if outside_distances else 0,
                           "plus_eloignes": [(n, round(d * 1000, 1)) for d, n in outside_distances[:6]]})

# --- T4 transfert des poids ---------------------------------------------------------------------------------------------------------------
rain_warped_all = warp(rain)
rain_tree = BVHTree.FromPolygons([Vector(p) for p in rain_warped_all], [tuple(t) for t in RAIN["triangles"]])
n_rain = len(rain)
group_count = len(RAIN["group_names"])
weights = [dict() for _ in range(n_rain)]
NOT_BONES = {"CorrectiveSmooth", "Lattice_Head", "Mix_Heads", "NeckSeam", "Side.L", "Side.R", "mask_modifier"}  # groupes-masques de modificateurs (mesuré : ne sont pas des os)
group_list = [str(n) for n in RAIN["group_names"]]
for v, g, w in zip(RAIN["vi"], RAIN["gi"], RAIN["wt"]):
    if group_list[int(g)] not in NOT_BONES:
        weights[int(v)][int(g)] = float(w)
head_mask = hl[:, 2] > lm_hl[2][2] - 0.005
head_ids = np.nonzero(head_mask)[0]
triangle_array = RAIN["triangles"]
influence_counts, projection_distances, transferred = [], [], {}
for vid in head_ids:
    point = Vector(hl[vid])
    nearest = rain_tree.find_nearest(point)
    if nearest[0] is None:
        continue
    tri = triangle_array[nearest[2]]
    a, b, c = (rain_warped_all[t] for t in tri)
    p = np.array(nearest[0])
    v0, v1, v2 = b - a, c - a, p - a
    d00, d01, d11, d20, d21 = v0 @ v0, v0 @ v1, v1 @ v1, v2 @ v0, v2 @ v1
    denom = d00 * d11 - d01 * d01
    bary = np.array([1.0, 0.0, 0.0]) if abs(denom) < 1e-18 else np.array([1 - (d11 * d20 - d01 * d21) / denom - (d00 * d21 - d01 * d20) / denom, (d11 * d20 - d01 * d21) / denom, (d00 * d21 - d01 * d20) / denom])
    mix = {}
    for weight, t in zip(bary, tri):
        for g, w in weights[int(t)].items():
            mix[g] = mix.get(g, 0.0) + weight * w
    total = sum(mix.values())
    mix = {g: w / total for g, w in mix.items()} if total > 0 else {}
    transferred[int(vid)] = mix
    influence_counts.append(len(mix))
    projection_distances.append(nearest[3])
influence_counts = np.array(influence_counts)
projection_distances = np.array(projection_distances)
say("T4_sommets_humanloom_de_la_tete", int(len(head_ids)))
say("T4_distance_de_projection", summary(projection_distances) | {"au_dela_de_5_mm": int((projection_distances > 0.005).sum())})
say("T4_influences_par_sommet_apres_transfert", {"max": int(influence_counts.max()), "moyenne": round(float(influence_counts.mean()), 2), "plus_de_8": int((influence_counts > 8).sum()), "plus_de_4": int((influence_counts > 4).sum())})


def prune(mix, limit):
    kept = dict(sorted(mix.items(), key=lambda kv: -kv[1])[:limit])
    total = sum(kept.values())
    return {g: w / total for g, w in kept.items()}


for limit in (8, 4):
    changes = []
    for mix in transferred.values():
        small = prune(mix, limit)
        changes.append(sum(abs(mix.get(g, 0.0) - small.get(g, 0.0)) for g in set(mix) | set(small)))
    changes = np.array(changes)
    say(f"T4_changement_des_poids_si_{limit}_influences", {"moyenne_L1": round(float(changes.mean()), 4), "p95_L1": round(float(np.percentile(changes, 95)), 4), "max_L1": round(float(changes.max()), 4), "sommets_modifies": int((changes > 1e-6).sum())})
group_names = [str(n) for n in RAIN["group_names"]]


def dominant(center, radius, pattern):
    mass, hit = {}, 0.0
    for vid, mix in transferred.items():
        if np.linalg.norm(hl[vid] - center) < radius:
            for g, w in mix.items():
                mass[g] = mass.get(g, 0.0) + w
    total = sum(mass.values()) or 1.0
    top = sorted(mass.items(), key=lambda kv: -kv[1])[:5]
    share = sum(w for g, w in mass.items() if any(k in group_names[g] for k in pattern)) / total
    return {"part_des_groupes_attendus": round(share, 3), "groupes_dominants": [(group_names[g], round(w / total, 3)) for g, w in top]}


say("T4_semantique_bouche_humanloom", dominant(skin_point(hl_tree, mouth_center(lm_hl)), 0.02, ("Lip", "Mouth", "Jaw", "Chin", "LaughLine")))
say("T4_semantique_oeil_humanloom", dominant(skin_point(hl_tree, hl_eyes[0]), 0.02, ("Eye", "eye", "Brow")))
used = {g for mix in transferred.values() for g in mix}
say("T4_groupes_utilises_sur_la_tete_humanloom", {"utilises": len(used), "groupes_rain": int(group_count)})

# --- T5 clé de forme sur « HL Human Base » avant les nœuds -----------------------------------------------------------------------------------
mesh_name = body.data.name
body.shape_key_add(name="Basis", from_mix=False)
key = body.shape_key_add(name="proto_bouche", from_mix=False)
mouth = mouth_center(lm_hl)
base_positions = np.array([v.co[:] for v in body.data.vertices])
shift = np.zeros_like(base_positions)
near = np.linalg.norm(base_positions - mouth, axis=1) < 0.03
shift[near, 2] = -0.005
for i, v in enumerate(key.data):
    v.co = Vector(base_positions[i] + shift[i])
timings = {}
results = {}
for age in (1.0, 3.0):
    human.set_value(body, "age", age)
    key.value = 0.0
    neutral = evaluate(body)
    key.value = 1.0
    shifted = evaluate(body)
    moved = np.linalg.norm(shifted - neutral, axis=1)
    results[age] = {"sommets_deplaces": int((moved > 1e-6).sum()), "deplacement_max_mm": round(float(moved.max()) * 1000, 3), "attendu_mm": 5.0}
for label, value in (("sans_cle", 0.0), ("avec_cle", 1.0)):
    key.value = value
    samples = []
    for _ in range(20):
        human.set_value(body, "age", 1.0 + 0.01 * _)  # force une réévaluation à chaque tour
        start = time.perf_counter()
        evaluate(body)
        samples.append((time.perf_counter() - start) * 1000)
    timings[label] = {"mediane_ms": round(statistics.median(samples), 1), "max_ms": round(max(samples), 1)}
say("T5_cle_de_forme_avant_les_noeuds", {"maillage_d_entree": mesh_name, "par_age": results, "temps_evaluation": timings, "critere_ms": 33})

Path(OUT).write_text(json.dumps(report, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
print("PROTO_OK")
