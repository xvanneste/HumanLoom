"""Planche de contrôle du rig corps (lot A2) : os superposés au fil de fer de la cage, de face et de profil, sur 3 morphologies.

  blender --background --factory-startup --offline-mode --python tools/render_rig_board.py -- DOSSIER_DE_SORTIE

Sortie : `rig_<morphologie>_face.png`, `rig_<morphologie>_profil.png`, `rig_<morphologie>_mains.png` (agrandissement des mains). Projection orthographique tracée en numpy
(aucun moteur de rendu) ; gris = arêtes de la cage, couleur = os (rouge : côté gauche +x, bleu : côté droit, noir : axe).
"""
from pathlib import Path
import sys

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension import human  # noqa: E402
from extension.animation import skeleton  # noqa: E402

OUT = Path(sys.argv[sys.argv.index("--") + 1])
OUT.mkdir(parents=True, exist_ok=True)
MORPHOLOGIES = {"neutre": {}, "homme_age": {"sex": 0.0, "age": 3.0}, "femme_jeune": {"sex": 1.0, "age": 1.0}}
SIZE = 1100

addon.register()


def line(image, p, q, color, width=1):
    n = int(max(abs(q[0] - p[0]), abs(q[1] - p[1]))) + 1
    xs, ys = np.linspace(p[0], q[0], n), np.linspace(p[1], q[1], n)
    for dx in range(-(width // 2), width // 2 + 1):
        for dy in range(-(width // 2), width // 2 + 1):
            x, y = (xs + dx).astype(int), (ys + dy).astype(int)
            ok = (x >= 0) & (x < SIZE) & (y >= 0) & (y < SIZE)
            image[y[ok], x[ok], :3] = color


def render(points, edges, bones, axes, center, extent, path):
    image = np.ones((SIZE, SIZE, 4), np.float32)
    ax, ay = axes

    def project(p):
        return ((p[ax] - center[0]) / extent * SIZE + SIZE / 2, (p[ay] - center[1]) / extent * SIZE + SIZE / 2)

    projected = np.array([project(p) for p in points])
    for a, b in edges:
        line(image, projected[a], projected[b], (0.8, 0.8, 0.8))
    for name, head, tail in bones:
        color = (0.85, 0.1, 0.1) if name.endswith(".L") else (0.1, 0.2, 0.9) if name.endswith(".R") else (0.0, 0.0, 0.0)
        p, q = project(head), project(tail)
        line(image, p, q, color, 2)
        line(image, (p[0] - 2, p[1]), (p[0] + 2, p[1]), (0, 0.6, 0), 3)
    picture = bpy.data.images.new(str(path), SIZE, SIZE, alpha=True)
    picture.pixels = image.ravel().tolist()
    picture.filepath_raw = str(path)
    picture.file_format = "PNG"
    picture.save()
    bpy.data.images.remove(picture)


for label, values in MORPHOLOGIES.items():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.ops.humanloom.create()
    body = bpy.context.object
    for name, value in values.items():
        human.set_value(body, name, value)
    skeleton.install(body)
    points = skeleton.cage_points(body)
    mesh = body.data
    edges = np.array([e.vertices[:] for e in mesh.edges])
    rig = skeleton.rigs_of(body)[0]
    bones = [(b.name, np.array(b.head_local[:]), np.array(b.tail_local[:])) for b in rig.data.bones]
    height = points[:, 2].max() - points[:, 2].min()
    center_z = (points[:, 2].max() + points[:, 2].min()) / 2
    render(points, edges, bones, (0, 2), (0.0, center_z), height * 1.1, OUT / f"rig_{label}_face.png")
    render(points, edges, bones, (1, 2), (float(points[:, 1].mean()), center_z), height * 1.1, OUT / f"rig_{label}_profil.png")
    hand_center = np.array([c for n, c in ((b[0], (b[1] + b[2]) / 2) for b in bones) if n == "hand.L"][0])
    render(points, edges, bones, (0, 2), (hand_center[0], hand_center[2]), height * 0.22, OUT / f"rig_{label}_mains.png")
    render(points, edges, bones, (1, 2), (hand_center[1], hand_center[2]), height * 0.22, OUT / f"rig_{label}_mains_profil.png")
    print("PLANCHE", label, "os", len(bones), "stature", round(float(height), 3))
