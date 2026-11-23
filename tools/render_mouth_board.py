"""Planche de la bouche (lot F0) : coupe médiane de la cage, mâchoire fermée puis ouverte, sur 3 morphologies, et mesures de la déformation.

  blender --background --factory-startup --offline-mode --python tools/render_mouth_board.py -- DOSSIER_DE_SORTIE [--angle 20]

Sortie : `bouche_<morphologie>.png` (gauche : fermée, droite : ouverte ; noir = ligne médiane, gris = arêtes à moins de 40 mm du plan médian, rouge = sommets de la fente) et une ligne
`MESURE` par morphologie : ouverture de la fente (mm), descente du menton (mm), triangles retournés, étirement d'arête maximal. Projection orthographique en numpy (aucun moteur de rendu)."""
from pathlib import Path
import math
import sys

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension import human  # noqa: E402
from extension.animation import dental, skeleton  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:]
OUT = Path(ARGS[0])
OUT.mkdir(parents=True, exist_ok=True)
ANGLE = float(ARGS[ARGS.index("--angle") + 1]) if "--angle" in ARGS else 20.0
MORPHOLOGIES = {"neutre": {}, "homme_age": {"sex": 0.0, "age": 3.0}, "femme_jeune": {"sex": 1.0, "age": 1.0}}
W, H = 700, 700
addon.register()


def evaluated_points(body):
    saved = [(m, m.show_viewport) for m in body.modifiers]
    for m in body.modifiers:
        m.show_viewport = m.name in (human.MODIFIER_NAME, skeleton.MODIFIER_NAME)
    human.touch(body)
    bpy.context.view_layer.update()
    mesh = body.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh()
    buffer = np.empty(len(mesh.vertices) * 3, np.float32)
    mesh.vertices.foreach_get("co", buffer)
    body.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh_clear()
    for m, state in saved:
        m.show_viewport = state
    return buffer.reshape(-1, 3).astype(np.float64)


COLORS = {"HL Dents hautes": (0.1, 0.3, 0.9), "HL Dents basses": (0.95, 0.5, 0.0), "HL Langue": (0.8, 0.1, 0.6)}


def part_geometry(body):
    """{nom: (points monde, arêtes)} des dents, gencives et langue à la pose courante."""
    bpy.context.view_layer.update()
    out = {}
    for obj in dental.parts_of(body):
        matrix = obj.matrix_world
        points = np.array([(matrix @ v.co)[:] for v in obj.data.vertices])
        out[obj.name] = (points, np.array([e.vertices[:] for e in obj.data.edges]))
    return out


def draw_parts(image, offset, parts, center, extent, axes):
    ax, ay = axes
    for name, (points, edges) in parts.items():
        color = COLORS[name]
        pr = np.stack([offset + (points[:, ax] - center[0]) / extent * (W // 2) + W // 4, (points[:, ay] - center[1]) / extent * H + H / 2], 1)
        for a, b in edges:
            n = int(max(abs(pr[b] - pr[a]))) + 1
            xs = np.linspace(pr[a][0], pr[b][0], n).astype(int)
            ys = np.linspace(pr[a][1], pr[b][1], n).astype(int)
            ok = (xs >= offset) & (xs < offset + W // 2) & (ys >= 0) & (ys < H)
            image[ys[ok], xs[ok]] = color


def draw(image, offset, P, edges, center, extent, slit):
    def project(p):
        return (offset + (p[1] - center[0]) / extent * (W // 2) + W // 4, (p[2] - center[1]) / extent * H + H / 2)

    def line(p, q, color, width=1):
        n = int(max(abs(q[0] - p[0]), abs(q[1] - p[1]))) + 1
        for t in np.linspace(0, 1, n):
            x, y = int(p[0] + (q[0] - p[0]) * t), int(p[1] + (q[1] - p[1]) * t)
            if offset <= x < offset + W // 2 and 0 <= y < H:
                image[max(0, y - width // 2):y + width // 2 + 1, max(0, x - width // 2):x + width // 2 + 1] = color

    pr = [project(p) for p in P]
    for a, b in edges:
        if min(abs(P[a, 0]), abs(P[b, 0])) < 0.04:
            median = abs(P[a, 0]) < 0.0015 and abs(P[b, 0]) < 0.0015
            line(pr[a], pr[b], (0, 0, 0) if median else (0.8, 0.8, 0.8), 2 if median else 1)
    for v in slit:
        x, y = pr[v]
        if offset <= x < offset + W // 2 and 0 <= y < H:
            image[int(y) - 2:int(y) + 3, int(x) - 2:int(x) + 3] = (0.9, 0.1, 0.1)


for label, values in MORPHOLOGIES.items():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.ops.humanloom.create()
    body = bpy.context.object
    for name, value in values.items():
        human.set_value(body, name, value)
    rig = skeleton.install(body)
    mesh = body.data
    edges = np.array([e.vertices[:] for e in mesh.edges])
    closed = evaluated_points(body)
    pose = rig.pose.bones[skeleton.JAW]
    pose.rotation_mode = "XYZ"
    best = None
    for sign in (1.0, -1.0):
        pose.rotation_euler = (sign * math.radians(ANGLE), 0, 0)
        trial = evaluated_points(body)
        drop = closed[skeleton.JAW_CHIN, 2] - trial[skeleton.JAW_CHIN, 2]
        if best is None or drop > best[0]:
            best = (drop, sign, trial)
    drop, sign, opened = best
    pose.rotation_euler = (sign * math.radians(ANGLE), 0, 0)
    triangles = np.array([p.vertices[:] for p in mesh.polygons if len(p.vertices) == 3] + [p.vertices[:3] for p in mesh.polygons if len(p.vertices) == 4])

    def normals(P):
        return np.cross(P[triangles[:, 1]] - P[triangles[:, 0]], P[triangles[:, 2]] - P[triangles[:, 0]])

    flipped = int(((normals(closed) * normals(opened)).sum(1) < 0).sum())
    lengths = lambda P: np.linalg.norm(P[edges[:, 0]] - P[edges[:, 1]], axis=1)
    long_edges = lengths(closed) >= 0.003  # les arêtes minuscules du pli de la fente ne comptent pas (rapport sans signification)
    stretch = float(np.max(lengths(opened)[long_edges] / lengths(closed)[long_edges]))
    a, b = skeleton.JAW_SLIT
    gap_closed, gap_open = float(np.linalg.norm(closed[a] - closed[b])) * 1000, float(np.linalg.norm(opened[a] - opened[b])) * 1000
    print("MESURE", label, json_dump := f"angle {ANGLE:.0f}° menton descend de {drop * 1000:.1f} mm, fente {gap_closed:.1f} -> {gap_open:.1f} mm, triangles retournés {flipped}, étirement max d'une arête de plus de 3 mm au repos x{stretch:.2f}")
    image = np.ones((H, W, 3), np.float32)
    centre = (float(closed[:, 1][closed[:, 2] > closed[:, 2].max() - 0.25].mean()), float(closed[:, 2].max() - 0.16))
    slit = [a, b]
    draw(image, 0, closed, edges, centre, 0.22, slit)
    draw(image, W // 2, opened, edges, centre, 0.22, slit)
    pose.rotation_euler = (0, 0, 0)
    draw_parts(image, 0, part_geometry(body), centre, 0.22, (1, 2))
    pose.rotation_euler = (sign * math.radians(ANGLE), 0, 0)
    parts_open = part_geometry(body)
    draw_parts(image, W // 2, parts_open, centre, 0.22, (1, 2))
    picture = bpy.data.images.new(f"b_{label}", W, H, alpha=False)
    picture.pixels = np.concatenate([image, np.ones((H, W, 1), np.float32)], 2).ravel().tolist()
    picture.filepath_raw = str(OUT / f"bouche_{label}.png")
    picture.file_format = "PNG"
    picture.save()
    bpy.data.images.remove(picture)
    # vue de dessus (x, y) des dents et de la langue, bouche fermée (gauche) et ouverte (droite)
    top_image = np.ones((H, W, 3), np.float32)
    pose.rotation_euler = (0, 0, 0)
    closed_parts = part_geometry(body)
    all_points = np.vstack([p for p, _ in closed_parts.values()])
    middle = (float(all_points[:, 1].mean()), float(all_points[:, 0].mean()))
    top_closed = {n: (np.stack([v[:, 1], v[:, 0], v[:, 2]], 1), e) for n, (v, e) in closed_parts.items()}
    top_open = {n: (np.stack([v[:, 1], v[:, 0], v[:, 2]], 1), e) for n, (v, e) in parts_open.items()}
    draw_parts(top_image, 0, top_closed, middle, 0.14, (0, 1))
    draw_parts(top_image, W // 2, top_open, middle, 0.14, (0, 1))
    picture = bpy.data.images.new(f"d_{label}", W, H, alpha=False)
    picture.pixels = np.concatenate([top_image, np.ones((H, W, 1), np.float32)], 2).ravel().tolist()
    picture.filepath_raw = str(OUT / f"bouche_{label}_dessus.png")
    picture.file_format = "PNG"
    picture.save()
    bpy.data.images.remove(picture)
