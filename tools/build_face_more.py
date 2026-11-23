"""Commandes SUPPLÉMENTAIRES du visage (recalage des expressions sur FACS / guides d'émotions) : couches ajoutées APRÈS les commandes pilotes (`build_face_pilot.py`).

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/build_face_pilot.py -- <human_nodes_entree.blend> <human_nodes_sortie.blend> <human_sockets_sortie.json> [--report r.json]

Chaque commande est une entrée flottante 0 à 1 du groupe et une couche de sommets (attribut `b_f<n>`) calculée sur la cage du corps PAR DÉFAUT par une règle géométrique de ce projet (aucun visage tiers).
Les amplitudes viennent, quand une source a été LUE, de `extension/data/face_reference.json` (Baude et al. 2015 : excursions de marqueurs 2D de 10 adultes, fiabilité faible pour le bas du visage) ;
sinon elles sont PROVISOIRES (« non vérifié »). Chaque amplitude est réduite automatiquement tant qu'une face de la cage se retourne ; l'amplitude retenue et celle visée sont écrites dans le rapport.
Les déplacements sont en mm absolus d'un adulte (pas de mise à l'échelle par la taille de la tête : limite connue)."""
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


def cmd_brow_up():
    d = np.zeros((count, 3))
    for sx in (1.0, -1.0):
        d[:, 2] += brow_zone(sx)
    return d


def cmd_brow_down():
    d = np.zeros((count, 3))
    for sx in (1.0, -1.0):
        w = brow_zone(sx)
        d[:, 2] -= w
        d[:, 0] -= sx * 0.5 * w * smooth((0.030 - np.abs(P[:, 0])) / 0.025)  # le froncement rapproche aussi l'intérieur des sourcils (0,5 de l'amplitude)
    return d


def cmd_brow_inner_up():
    d = np.zeros((count, 3))
    for sx in (1.0, -1.0):
        d[:, 2] += brow_zone(sx, inner_only=True)
    return d


def cmd_smile(sx):
    c = P[corner_ids[sx]]
    w = gauss(c, 0.032, front)
    cheek = gauss(c + np.array([sx * 0.012, 0.0, 0.030]), 0.032, front)
    direction = np.array([sx * 0.40, 0.10, 0.91])
    direction /= np.linalg.norm(direction)
    return w[:, None] * direction[None, :] + 0.35 * cheek[:, None] * np.array([0.0, 0.0, 1.0])[None, :]


def cmd_cheek_puff():
    d = np.zeros((count, 3))
    for sx in (1.0, -1.0):
        w = gauss(np.array([sx * 0.045, slit_y + 0.025, slit_z + 0.010]), 0.030)
        d += w[:, None] * np.array([sx * 0.99, -0.15, 0.0])[None, :]
    return d


def cmd_lip_pucker():
    d = np.zeros((count, 3))
    for sx in (1.0, -1.0):
        w = gauss(P[corner_ids[sx]], 0.032, front)
        d[:, 0] -= sx * w
    lips = gauss(np.array([0.0, slit_y, slit_z]), 0.040, front)
    d[:, 1] -= 0.5 * lips  # les lèvres avancent (moitié de l'amplitude)
    return d


def cmd_nose_wrinkle():
    d = np.zeros((count, 3))
    for sx in (1.0, -1.0):
        w = gauss(nose_tip + np.array([sx * 0.016, 0.010, 0.012]), 0.016)
        d[:, 2] += w
        d[:, 0] -= sx * 0.4 * w
    return d


def cmd_mouth_down():
    d = np.zeros((count, 3))
    for sx in (1.0, -1.0):
        w = gauss(P[corner_ids[sx]], 0.030, front)
        d[:, 2] -= w
        d[:, 1] += 0.3 * w
    return d


def cmd_blink(sx):
    e = eyes[sx]
    dx, dz = P[:, 0] - e[0], P[:, 2] - e[2]
    u = np.sqrt((dx / 0.016) ** 2 + (dz / 0.011) ** 2)
    w = np.where(u < 1.0, 1.0, 1 - smooth((u - 1.0) / 1.6)) * (P[:, 1] < e[1] - 0.008)
    d = np.zeros((count, 3))
    d[:, 2] = -dz * w  # les deux paupières s'écrasent sur la ligne du centre de l'oeil ; l'amplitude (0 à 1) est appliquée en fin de chaîne
    return d, True


# nom: (fonction, amplitude visée en mm, source, unité de la fonction : 'mm' pour des directions unitaires, 'absolu' pour des déplacements déjà en mètres)
def cmd_eye_wide():
    d = np.zeros((count, 3))
    for sx in (1.0, -1.0):
        e = eyes[sx]
        d[:, 2] += gauss(e + np.array([0.0, 0.0, 0.011]), 0.012, P[:, 1] < e[1] - 0.008)  # paupière supérieure relevée (AU5)
    return d


def cmd_eye_squint():
    d = np.zeros((count, 3))
    for sx in (1.0, -1.0):
        e = eyes[sx]
        mask = P[:, 1] < e[1] - 0.008
        d[:, 2] += gauss(e + np.array([0.0, 0.0, -0.011]), 0.011, mask)  # paupière inférieure remontée / tendue (AU7, pattes d'oie du sourire)
        d[:, 2] -= 0.4 * gauss(e + np.array([0.0, 0.0, 0.011]), 0.011, mask)  # paupière supérieure légèrement abaissée
        d[:, 0] -= sx * 0.3 * gauss(e + np.array([sx * 0.016, 0.0, -0.004]), 0.012, mask)  # coin externe resserré
    return d


def cmd_brow_together():
    d = np.zeros((count, 3))
    for sx in (1.0, -1.0):
        d[:, 0] -= sx * brow_zone(sx) * smooth((0.050 - np.abs(P[:, 0])) / 0.030)  # sourcils rapprochés de la ligne médiane (AU4, composante horizontale)
    return d


def cmd_upper_lip_raise():
    d = np.zeros((count, 3))
    d[:, 2] += gauss(np.array([0.0, slit_y, slit_z + 0.004]), 0.011, front & (P[:, 2] > slit_z - 0.004))  # lèvre supérieure relevée (AU10)
    return d


def cmd_lip_stretch():
    d = np.zeros((count, 3))
    for sx in (1.0, -1.0):
        w = gauss(P[corner_ids[sx]], 0.030, front)
        d[:, 0] += sx * w  # coins étirés horizontalement vers l'extérieur (AU20)
        d[:, 2] -= 0.15 * w
    return d


def cmd_lips_press():
    d = np.zeros((count, 3))
    zone = gauss(np.array([0.0, slit_y, slit_z]), 0.016, front)
    d[:, 2] += np.where(P[:, 2] > slit_z, -1.0, 1.0) * zone  # les deux lèvres se serrent l'une contre l'autre (AU24)
    for sx in (1.0, -1.0):
        d[:, 0] -= sx * 0.5 * gauss(P[corner_ids[sx]], 0.020, front)
    return d


def cmd_chin_raise():
    d = np.zeros((count, 3))
    centre = P[skeleton.JAW_CHIN] + np.array([0.0, 0.0, 0.014])
    d[:, 2] += gauss(centre, 0.022, front)  # menton et lèvre inférieure poussés vers le haut (AU17)
    return d


COMMANDS = {
    "eye_wide": (cmd_eye_wide, 5.0, "artistique : aucune donnée lue (non vérifié) ; AU5 (FACS, Ekman & Friesen 1978 : numérotation seulement)"),
    "eye_squint": (cmd_eye_squint, 4.5, "artistique : aucune donnée lue (non vérifié) ; AU6/AU7"),
    "brow_together": (cmd_brow_together, 8.0, "artistique : aucune donnée lue (non vérifié) ; AU4 (composante horizontale)"),
    "upper_lip_raise": (cmd_upper_lip_raise, 6.0, "artistique : aucune donnée lue (non vérifié) ; AU10"),
    "lip_stretch": (cmd_lip_stretch, 8.0, "artistique : aucune donnée lue (non vérifié) ; AU20"),
    "lips_press": (cmd_lips_press, 2.0, "artistique : aucune donnée lue (non vérifié) ; AU24"),
    "chin_raise": (cmd_chin_raise, 2.5, "artistique : aucune donnée lue (non vérifié) ; AU17"),
}


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
        peak0 = float(np.linalg.norm(delta, axis=1).max())
        delta = smooth_field(delta, BLINK_SMOOTHING)
        delta *= peak0 / float(np.linalg.norm(delta, axis=1).max())  # le lissage répartit le déplacement ; on garde l'amplitude de fermeture complète
        amplitude = None
        scale = 1.0
    else:
        unit = smooth_field(result, SMOOTH_ITERATIONS)
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
assert "b_f1" in existing and "b_f12" not in existing, existing
base_index = len(existing)  # b_f0 (mouth_open) + pilotes
group_in = next(n for n in group.nodes if n.bl_idname == "NodeGroupInput")
set_position = next(n for n in group.nodes if n.bl_idname == "GeometryNodeSetPosition")
offset_link = next(l for l in group.links if l.to_node == set_position and l.to_socket.identifier == set_position.inputs["Offset"].identifier)
total = offset_link.from_socket
group.links.remove(offset_link)
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
    group.links.new(group_in.outputs[name], scale_node.inputs[3])
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
group["hl_face_more"] = 1
group.use_fake_user = True
mesh.use_fake_user = True
OUT.parent.mkdir(parents=True, exist_ok=True)
bpy.data.libraries.write(str(OUT), {group, mesh}, compress=True)
SOCKETS_OUT.write_text(json.dumps(sockets, indent=1, ensure_ascii=False), encoding="utf-8")
if REPORT:
    REPORT.write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
print("FACE_PILOT_OK", len(layers), "commandes", OUT.stat().st_size, "octets")
