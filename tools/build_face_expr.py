"""Détails d'expression manquants (revue contre DESCRIPTIONS_EXPRESSIONS.md) : plis et gestes ajoutés APRÈS les commandes du sourire, sur la cage PAR DÉFAUT du corps (règles géométriques de ce projet).

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/build_face_expr.py -- <human_nodes_entree.blend> <human_nodes_sortie.blend> <human_sockets_sortie.json> [--report r.json]

Nouvelles couches :
  forehead_wrinkles    rides horizontales du front (AU1/AU2 : surprise, peur, tristesse) ;
  glabella_wrinkles    deux rides verticales entre les sourcils (AU4 : colère, tristesse, peur) ;
  nose_bridge_wrinkles plis obliques sur la racine et le dos du nez (AU9 : dégoût) ;
  nostril_flare        narines qui se dilatent (colère, peur) ;
  dimpler_L, dimpler_R durcissement/fossette du coin de la bouche d'un seul côté (AU14, mépris).
Amplitudes PROVISOIRES (non vérifié) ; AU : noms et muscles lus sur la page Wikipédia « Facial Action Coding System » (source secondaire). Chaque amplitude est réduite tant qu'une face se retourne ; échelle d'âge appliquée comme aux autres commandes."""
import json
import math
from pathlib import Path
import sys

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
ARGS = sys.argv[sys.argv.index("--") + 1:]
SOURCE, OUT, SOCKETS_OUT = Path(ARGS[0]).resolve(), Path(ARGS[1]).resolve(), Path(ARGS[2]).resolve()
REPORT = Path(ARGS[ARGS.index("--report") + 1]).resolve() if "--report" in ARGS else None

import extension as addon  # noqa: E402
from extension.animation import skeleton  # noqa: E402

addon.register()
bpy.ops.humanloom.create()
body = bpy.context.object
rig = skeleton.install(body)
mesh_body = body.data
mesh_body.calc_loop_triangles()
triangles = np.array([t.vertices[:] for t in mesh_body.loop_triangles])
edges = np.array([e.vertices[:] for e in mesh_body.edges])
P = skeleton.cage_points(body)
count = len(P)
jaw = np.load(skeleton.JAW_FILE, allow_pickle=False)
slit_ids = np.concatenate([jaw["slit_upper"], jaw["slit_lower"]])
corner_ids = {1.0: int(slit_ids[np.argmax(P[slit_ids, 0])]), -1.0: int(slit_ids[np.argmin(P[slit_ids, 0])])}
slit_y, slit_z = float(P[slit_ids, 1].mean()), float(P[slit_ids, 2].mean())
eyes = {sx: np.mean([np.array((e.matrix_world @ v.co)[:]) for v in e.data.vertices], axis=0) for sx, e in zip((1.0, -1.0), sorted(skeleton.eyes_of(body), key=lambda e: -np.mean([(e.matrix_world @ v.co).x for v in e.data.vertices])))}
nose_zone = np.where((np.abs(P[:, 0]) < 0.006) & (P[:, 2] > slit_z + 0.012) & (P[:, 2] < slit_z + 0.065))[0]
nose_tip = P[nose_zone[np.argmin(P[nose_zone, 1])]]
front = P[:, 1] < slit_y + 0.004  # peau devant le plan de la fente (pas l'intérieur de la bouche)


def smooth(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


def gauss(centre, radius, mask=None):
    w = np.exp(-(np.linalg.norm(P - np.asarray(centre), axis=1) / radius) ** 2)
    return w * (mask if mask is not None else 1.0)


MM = 1e-3
# Région « os » : la peau du menton et de la mandibule ne s'étire pas quand la bouche bouge ; tout champ (sauf `chin_raise`) est annulé sous le sillon labio-mentonnier (fondu sur 8 mm, sillon à 12 mm sous la fente)
GROOVE_Z = slit_z - 0.012
CHIN_MASK = 1.0 - smooth((GROOVE_Z - P[:, 2]) / 0.008)
BAUDE = "Baude M., Hutin E., Gracies J.M., BioMed Res Int 2015, doi:10.1155/2015/812961 (PMC4486482), Tableau 1 : excursion moyenne de marqueurs 2D (cm), 10 adultes sains de 39 ± 12 ans, fiabilité faible pour le bas du visage"


def brow_zone(sx, inner_only=False):
    e = eyes[sx]
    dz = P[:, 2] - e[2]
    dx = np.abs(P[:, 0] - e[0])
    w = smooth((dz - 0.013) / 0.014) * (1 - smooth((dz - 0.030) / 0.060)) * (1 - smooth((dx - 0.020) / 0.015)) * (P[:, 1] < e[1] - 0.008)
    if inner_only:
        w = w * (1 - smooth((np.abs(P[:, 0]) - 0.026) / 0.010)) * smooth((np.abs(P[:, 0]) - 0.002) / 0.006)
    return w


_cross = np.cross(P[triangles[:, 1]] - P[triangles[:, 0]], P[triangles[:, 2]] - P[triangles[:, 0]])
_tri_area = np.linalg.norm(_cross, axis=1) / 2.0
_vertex_n, _vertex_a = np.zeros_like(P), np.zeros(count)
for _k in range(3):
    np.add.at(_vertex_n, triangles[:, _k], _cross / 2.0 / 3.0)
    np.add.at(_vertex_a, triangles[:, _k], _tri_area / 3.0)
_vertex_n /= np.maximum(np.linalg.norm(_vertex_n, axis=1), 1e-18)[:, None]


def volume_compensate(d, centre, r_in, r_out, mask):
    """Conservation approximative du volume mou : le flux net du déplacement (Σ (d·n) A) sur le disque `r_in` est repris, de signe opposé, par une couronne [r_in, r_out] (la peau qui monte à la pommette vient de la couronne)."""
    dist = np.linalg.norm(P - centre, axis=1)
    inside = (dist < r_in) & mask
    flux = float((np.einsum("ij,ij->i", d, _vertex_n) * _vertex_a)[inside].sum())
    ring = smooth((dist - r_in) / 0.006) * (1 - smooth((dist - r_out) / 0.010)) * mask
    area = float((ring * _vertex_a).sum())
    return d - (flux / max(area, 1e-12)) * (ring[:, None] * _vertex_n)


def ridges_along_z(centres_z, width, x_limit, x_fade):
    """Plis horizontaux : profil gaussien en z autour de chaque hauteur, fondu en x."""
    profile = sum(np.exp(-((P[:, 2] - z) / width) ** 2) for z in centres_z)
    return profile * (1 - smooth((np.abs(P[:, 0]) - x_limit) / x_fade))


def cmd_forehead_wrinkles():
    e = 0.5 * (eyes[1.0] + eyes[-1.0])
    mask = (P[:, 1] < -0.02) & (P[:, 2] > e[2] + 0.030) & (P[:, 2] < e[2] + 0.090)
    w = ridges_along_z([e[2] + 0.042, e[2] + 0.057, e[2] + 0.072], 0.0032, 0.030, 0.020) * mask
    return w[:, None] * _vertex_n  # relief vers l'extérieur le long de la normale (plis en relief ; entre eux la peau reste au repos)


def cmd_glabella_wrinkles():
    d = np.zeros((count, 3))
    e = 0.5 * (eyes[1.0] + eyes[-1.0])
    for sx in (1.0, -1.0):
        x = sx * 0.0065
        w = np.exp(-((P[:, 0] - x) / 0.0022) ** 2) * smooth((P[:, 2] - (e[2] + 0.012)) / 0.006) * (1 - smooth((P[:, 2] - (e[2] + 0.038)) / 0.008)) * (P[:, 1] < -0.02)
        d += w[:, None] * _vertex_n  # deux rides verticales entre les sourcils
    return d


def cmd_nose_bridge_wrinkles():
    d = np.zeros((count, 3))
    e = 0.5 * (eyes[1.0] + eyes[-1.0])
    for sx in (1.0, -1.0):
        for k in (0.0, 0.006):
            a_ = np.array([sx * (0.004 + k), e[2] - 0.002])
            b_ = np.array([sx * (0.014 + k), e[2] - 0.022])
            ab = b_ - a_
            xz = np.stack([P[:, 0], P[:, 2]], axis=1)
            t = np.clip(((xz - a_) @ ab) / float(ab @ ab), 0.0, 1.0)
            dist = np.linalg.norm(xz - (a_ + t[:, None] * ab[None, :]), axis=1)
            w = np.exp(-(dist / 0.0022) ** 2) * (P[:, 1] < -0.10) * (P[:, 2] < e[2] + 0.004)
            d += w[:, None] * _vertex_n  # plis obliques de chaque côté de la racine du nez
    return d


def cmd_nostril_flare():
    d = np.zeros((count, 3))
    for sx in (1.0, -1.0):
        w = gauss(nose_tip + np.array([sx * 0.016, 0.010, 0.010]), 0.012)
        d[:, 0] += sx * w  # les ailes du nez s'écartent
        d[:, 2] -= 0.25 * w
    return d


def cmd_dimpler(sx):
    d = np.zeros((count, 3))
    c = P[corner_ids[sx]]
    corner = gauss(c, 0.014, front) * (np.sign(P[:, 0]) == sx)
    d[:, 0] -= sx * 0.7 * corner  # le coin de la bouche se resserre vers le centre (buccinateur)
    d[:, 1] += 0.35 * corner
    dimple = gauss(c + np.array([sx * 0.008, 0.0, 0.0]), 0.006, front) * (np.sign(P[:, 0]) == sx)
    d[:, 1] += 0.9 * dimple  # fossette : creux de la peau juste en dehors du coin
    return d


COMMANDS = {
    "forehead_wrinkles": (cmd_forehead_wrinkles, 0.9, "artistique : aucune donnée lue (non vérifié) ; AU1/AU2 (rides du front)"),
    "glabella_wrinkles": (cmd_glabella_wrinkles, 0.9, "artistique : aucune donnée lue (non vérifié) ; AU4 (rides de la glabelle)"),
    "nose_bridge_wrinkles": (cmd_nose_bridge_wrinkles, 0.9, "artistique : aucune donnée lue (non vérifié) ; AU9 (plis du nez)"),
    "nostril_flare": (cmd_nostril_flare, 2.0, "artistique : aucune donnée lue (non vérifié) ; dilatation des narines"),
    "dimpler_L": (lambda: cmd_dimpler(1.0), 2.5, "artistique : aucune donnée lue (non vérifié) ; AU14 (côté +x)"),
    "dimpler_R": (lambda: cmd_dimpler(-1.0), 2.5, "artistique : aucune donnée lue (non vérifié) ; AU14 (côté -x)"),
}
UNSMOOTHED = ("forehead_wrinkles", "glabella_wrinkles", "nose_bridge_wrinkles")  # les plis ne sont pas lissés sur le graphe (ils s'effaceraient), seulement légèrement


def geometry(points):
    n = np.cross(points[triangles[:, 1]] - points[triangles[:, 0]], points[triangles[:, 2]] - points[triangles[:, 0]])
    a = np.linalg.norm(n, axis=1)
    return n / np.maximum(a[:, None], 1e-18), a


n0, a0 = geometry(P)
rest_lengths = np.linalg.norm(P[edges[:, 0]] - P[edges[:, 1]], axis=1)


def flips(delta):
    n1, a1 = geometry(P + delta)
    return int(((np.einsum("ij,ij->i", n0, n1) < 0) & (a0 > 2e-6)).sum())  # les triangles quasi dégénérés (< 1 mm²) basculent au moindre déplacement : ignorés


neighbors = [set() for _ in range(count)]
for a_, b_ in edges:
    neighbors[a_].add(b_)
    neighbors[b_].add(a_)
src_ = np.concatenate([edges[:, 0], edges[:, 1]])
dst_ = np.concatenate([edges[:, 1], edges[:, 0]])
degree_ = np.bincount(src_, minlength=count).astype(float)
SMOOTH_ITERATIONS = int(ARGS[ARGS.index("--smooth") + 1]) if "--smooth" in ARGS else 12
BLINK_SMOOTHING = int(ARGS[ARGS.index("--blink-smooth") + 1]) if "--blink-smooth" in ARGS else 4


def smooth_field(field, iterations):
    """Diffuse le champ de déplacement sur le graphe du maillage : les sommets voisins bougent de façon cohérente (moins de faces retournées pour la même amplitude)."""
    field = field.copy()
    for _ in range(iterations):
        total = np.zeros_like(field)
        np.add.at(total, src_, field[dst_])
        field = 0.5 * field + 0.5 * total / np.maximum(degree_, 1)[:, None]
    return field


layers, report = {}, {}
for name, (function, target_mm, source) in COMMANDS.items():
    result = function()
    if isinstance(result, tuple):  # déplacements déjà en mètres (fermeture des paupières)
        delta, full = result
        if name == "crows_feet":
            delta = delta * (target_mm * MM / float(np.linalg.norm(delta, axis=1).max()))
        peak0 = float(np.linalg.norm(delta, axis=1).max())
        delta = smooth_field(delta, BLINK_SMOOTHING)
        delta *= peak0 / float(np.linalg.norm(delta, axis=1).max())  # le lissage répartit le déplacement ; on garde l'amplitude de fermeture complète
        amplitude = None
        scale = 1.0
    else:
        unit = smooth_field(result, 2 if name in UNSMOOTHED else SMOOTH_ITERATIONS)
        if name != "chin_raise":
            unit = unit * CHIN_MASK[:, None]
        peak = float(np.linalg.norm(unit, axis=1).max())
        scale = target_mm * MM / peak
        delta = unit * scale
        full = False
    retained = 1.0
    count_flips = flips(delta)
    if count_flips:  # diagnostic : où se retournent les faces à l'amplitude visée
        n1_, a1_ = geometry(P + delta)
        bad = np.where((np.einsum("ij,ij->i", n0, n1_) < 0) & (a0 > 2e-6))[0]
        print("  RETOURNEES", name, count_flips, [((P[triangles[t]].mean(0) * 1000).round(0).tolist(), round(float(a0[t]) * 5e5, 1)) for t in bad[:6]])
    while count_flips > 0 and retained > 0.2:
        retained *= 0.9
        count_flips = flips(delta * retained)
    delta = delta * retained
    layers[name] = delta.astype(np.float32)
    moved = np.linalg.norm(delta, axis=1)
    n1, a1 = geometry(P + delta)
    report[name] = {"amplitude_visee_mm": target_mm, "amplitude_retenue_mm": round(float(moved.max()) * 1000, 2), "facteur_de_reduction": round(retained, 3), "retournees": flips(delta), "sommets": int((moved > 1e-6).sum()),
                    "aire_min_relative": round(float(np.min(a1[a0 > 1e-10] / a0[a0 > 1e-10])), 3), "etirement_max": round(float((np.linalg.norm((P + delta)[edges[:, 0]] - (P + delta)[edges[:, 1]], axis=1) / np.maximum(rest_lengths, 1e-9)).max()), 2), "source": source}
    print("PILOTE", name, json.dumps({k: v for k, v in report[name].items() if k != "source"}, ensure_ascii=False))

# --- édition d'une copie du groupe ---------------------------------------------------------------------------------------------------------------
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
for datablock in list(bpy.data.meshes) + list(bpy.data.node_groups):
    if datablock.name.startswith("HL Human"):
        (bpy.data.meshes if isinstance(datablock, bpy.types.Mesh) else bpy.data.node_groups).remove(datablock)
with bpy.data.libraries.load(str(SOURCE), link=False) as (_, blocks):
    blocks.node_groups = ["HL Human"]
    blocks.meshes = ["HL Human Base"]
group, mesh = blocks.node_groups[0], blocks.meshes[0]
assert group.name == "HL Human" and mesh.name == "HL Human Base"
existing = sorted(k for k in mesh.attributes.keys() if k.startswith("b_f"))
assert "b_f23" in existing and "b_f24" not in existing, existing
base_index = len(existing)  # b_f0 (mouth_open) + pilotes
group_in = next(n for n in group.nodes if n.bl_idname == "NodeGroupInput")
set_position = next(n for n in group.nodes if n.bl_idname == "GeometryNodeSetPosition")
offset_link = next(l for l in group.links if l.to_node == set_position and l.to_socket.identifier == set_position.inputs["Offset"].identifier)
total = offset_link.from_socket
group.links.remove(offset_link)
reference_scale = next(n for n in group.nodes if n.bl_idname == "ShaderNodeVectorMath" and n.operation == "SCALE" and n.inputs[0].is_linked
                       and n.inputs[0].links[0].from_node.bl_idname == "GeometryNodeInputNamedAttribute" and n.inputs[0].links[0].from_node.inputs["Name"].default_value == "b_f1")
age_factor = reference_scale.inputs[3].links[0].from_node.inputs[1].links[0].from_socket  # facteur d'échelle selon l'âge (build_face_scale.py)
sockets = json.loads((ROOT / "extension" / "data" / "human_sockets.json").read_text(encoding="utf-8"))
face_info = json.loads(mesh["hl_face_layers"]) if "hl_face_layers" in mesh else {}
for n, (name, layer) in enumerate(layers.items(), start=base_index):
    item = group.interface.new_socket(name, in_out="INPUT", socket_type="NodeSocketFloat")
    item.default_value, item.min_value, item.max_value = 0.0, 0.0, 1.0
    attribute = mesh.attributes.new(f"b_f{n}", "FLOAT_VECTOR", "POINT")
    attribute.data.foreach_set("vector", layer.ravel())
    named = group.nodes.new("GeometryNodeInputNamedAttribute")
    named.data_type = "FLOAT_VECTOR"
    named.inputs["Name"].default_value = f"b_f{n}"
    scale_node = group.nodes.new("ShaderNodeVectorMath")
    scale_node.operation = "SCALE"
    group.links.new(named.outputs["Attribute"], scale_node.inputs[0])
    product = group.nodes.new("ShaderNodeMath")
    product.operation = "MULTIPLY"
    group.links.new(group_in.outputs[name], product.inputs[0])
    group.links.new(age_factor, product.inputs[1])
    group.links.new(product.outputs[0], scale_node.inputs[3])
    add = group.nodes.new("ShaderNodeVectorMath")
    add.operation = "ADD"
    group.links.new(total, add.inputs[0])
    group.links.new(scale_node.outputs[0], add.inputs[1])
    total = add.outputs[0]
    identifier = next(i.identifier for i in group.interface.items_tree if i.item_type == "SOCKET" and i.in_out == "INPUT" and i.name == name)
    sockets[name] = [identifier, 0.0, 0.0, 1.0]
    face_info[name] = {"couche": f"b_f{n}", "source": report[name]["source"], "amplitude_retenue_mm": report[name]["amplitude_retenue_mm"], "amplitude_visee_mm": report[name]["amplitude_visee_mm"]}
group.links.new(total, set_position.inputs["Offset"])


mesh["hl_face_layers"] = json.dumps(face_info, ensure_ascii=False)
group["hl_face_more"] = 2
group.use_fake_user = True
mesh.use_fake_user = True
OUT.parent.mkdir(parents=True, exist_ok=True)
bpy.data.libraries.write(str(OUT), {group, mesh}, compress=True)
SOCKETS_OUT.write_text(json.dumps(sockets, indent=1, ensure_ascii=False), encoding="utf-8")
if REPORT:
    REPORT.write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
print("FACE_PILOT_OK", len(layers), "commandes", OUT.stat().st_size, "octets")
