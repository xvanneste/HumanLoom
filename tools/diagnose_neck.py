"""Diagnostic du cou (rig du corps) : poses, mesures de déformation et planche avec les poids en couleurs.

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/diagnose_neck.py -- DOSSIER_DE_SORTIE [--method stockes|recalcules] [--images 1] [--tag avant]

Poses (angles TOTAUX répartis sur les os du cou : 1/3 `neck.01`, 2/3 `neck.02` pour la rotation axiale ; flexion, extension et inclinaison : 1/3 `neck.01`, 1/3 `neck.02`, 1/3 `head`) :
rotation axiale 30 / 60 / 80°, flexion avant 30 / 45°, extension 30°, inclinaison latérale 30°. Pour chaque pose et chaque morphologie : triangles retournés, étirement maximal d'une arête,
compression minimale, variation de volume (même définition que `validate_human_rig` R6) ; `--images 1` : rendus Workbench (face, profil, trois-quarts, arrière) avec les poids en couleurs :
rouge = neck.01, vert = neck.02, bleu = head, cyan = jaw, jaune = clavicules et colonne, gris = autres. Les valeurs sont des mesures de NOTRE modèle ; aucune amplitude physiologique publiée n'est
comparée ici (aucune n'a été lue)."""
import json
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension import human  # noqa: E402
from extension.animation import skeleton  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:]
OUT = Path(ARGS[0])
OUT.mkdir(parents=True, exist_ok=True)
METHOD = ARGS[ARGS.index("--method") + 1] if "--method" in ARGS else skeleton.STORED
IMAGES = "--images" in ARGS and ARGS[ARGS.index("--images") + 1] == "1"
TAG = ARGS[ARGS.index("--tag") + 1] if "--tag" in ARGS else "etat"
MORPHOLOGIES = {"neutre": {}, "homme_age": {"sex": 0.0, "age": 3.0}, "femme_jeune": {"sex": 1.0, "age": 1.0}}
# (nom, [(os, axe, fraction)], angle total) ; axe 0 = X (flexion), 1 = Y (rotation axiale), 2 = Z
POSES = [
    ("axiale_30", [("neck.01", 1, 1 / 3), ("neck.02", 1, 2 / 3)], 30), ("axiale_60", [("neck.01", 1, 1 / 3), ("neck.02", 1, 2 / 3)], 60), ("axiale_80", [("neck.01", 1, 1 / 3), ("neck.02", 1, 2 / 3)], 80),
    ("flexion_30", [("neck.01", 0, 1 / 3), ("neck.02", 0, 1 / 3), ("head", 0, 1 / 3)], 30), ("flexion_45", [("neck.01", 0, 1 / 3), ("neck.02", 0, 1 / 3), ("head", 0, 1 / 3)], 45),
    ("extension_30", [("neck.01", 0, 1 / 3), ("neck.02", 0, 1 / 3), ("head", 0, 1 / 3)], -30),
    ("inclinaison_30", [("neck.01", 2, 1 / 3), ("neck.02", 2, 1 / 3), ("head", 2, 1 / 3)], 30),
    ("rotation_R6_45", [("neck.01", 1, 20 / 45), ("neck.02", 1, 25 / 45)], 45),
]
IMAGE_POSES = ("axiale_60", "flexion_45", "extension_30", "inclinaison_30")
addon.register()
if "--jaw-weights" in ARGS:  # poids de mâchoire de rechange (essais)
    skeleton.JAW_FILE = Path(ARGS[ARGS.index("--jaw-weights") + 1])
if "--weights" in ARGS:  # poids de rechange (essais) : fichier .npz au format de `human_rig_weights.npz`
    skeleton.WEIGHTS_FILE = Path(ARGS[ARGS.index("--weights") + 1])


def evaluate_cage(body):
    saved = [(m, m.show_viewport) for m in body.modifiers]
    for m in body.modifiers:
        m.show_viewport = m.name in (human.MODIFIER_NAME, skeleton.MODIFIER_NAME)
    human.touch(body)
    bpy.context.view_layer.update()
    evaluated = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    points = np.array([v.co[:] for v in mesh.vertices])
    evaluated.to_mesh_clear()
    for m, state in saved:
        m.show_viewport = state
    return points


def vertex_colors(body):
    colors = {"neck.01": (0.9, 0.1, 0.1), "neck.02": (0.1, 0.8, 0.1), "head": (0.1, 0.2, 0.95), skeleton.JAW: (0.0, 0.8, 0.8)}
    other = {"clavicle.L": (0.95, 0.85, 0.1), "clavicle.R": (0.95, 0.85, 0.1), "spine.05": (0.95, 0.85, 0.1), "spine.04": (0.95, 0.85, 0.1)}
    names = {g.index: g.name for g in body.vertex_groups}
    out = np.full((len(body.data.vertices), 4), (0.6, 0.6, 0.6, 1.0))
    for v in body.data.vertices:
        if not v.groups:
            continue
        rgb = np.zeros(3)
        total = 0.0
        for g in v.groups:
            c = colors.get(names[g.group]) or other.get(names[g.group]) or (0.6, 0.6, 0.6)
            rgb += np.array(c) * g.weight
            total += g.weight
        out[v.index, :3] = rgb / max(total, 1e-9)
    return out


def render(points, body, colors, path, direction, centre, scale):
    mesh = bpy.data.meshes.new("diag")
    mesh.from_pydata([tuple(p) for p in points], [], [tuple(p.vertices) for p in body.data.polygons])
    attribute = mesh.color_attributes.new("w", "FLOAT_COLOR", "POINT")
    attribute.data.foreach_set("color", colors.ravel())
    obj = bpy.data.objects.new("diag", mesh)
    bpy.context.scene.collection.objects.link(obj)
    for o in bpy.data.objects:
        if o not in (obj,) and o.type in ("MESH", "ARMATURE"):
            o.hide_render = True
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = scene.render.resolution_y = 600
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "VERTEX"
    scene.world.color = (1, 1, 1) if scene.world else None
    camera_data = bpy.data.cameras.new("cam")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = scale
    camera = bpy.data.objects.new("cam", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    d = Vector(direction).normalized()
    camera.location = Vector(centre) + d * 1.0
    camera.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(camera, do_unlink=True)
    bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.meshes.remove(mesh)


results = {}
for label, values in MORPHOLOGIES.items():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.ops.humanloom.create()
    body = bpy.context.object
    for name, value in values.items():
        human.set_value(body, name, value)
    try:
        rig = skeleton.install(body, METHOD)
    except ValueError as error:
        results[label] = {"erreur": str(error)}
        print("COU", label, "ÉCHEC DE LA LIAISON :", error)
        continue
    if "--dqs" in ARGS:  # liaison par quaternions duals (Blender : « Preserve Volume ») : essai contre l'effondrement en papier de bonbon
        body.modifiers[skeleton.MODIFIER_NAME].use_deform_preserve_volume = True
    for bone in rig.pose.bones:
        bone.rotation_mode = "XYZ"
    mesh = body.data
    mesh.calc_loop_triangles()
    triangles = np.array([t.vertices[:] for t in mesh.loop_triangles])
    edges = np.array([e.vertices[:] for e in mesh.edges])
    rest = evaluate_cage(body)

    def geometry(points):
        n = np.cross(points[triangles[:, 1]] - points[triangles[:, 0]], points[triangles[:, 2]] - points[triangles[:, 0]])
        a = np.linalg.norm(n, axis=1)
        return n / np.maximum(a[:, None], 1e-18), a

    rest_normals, rest_areas = geometry(rest)
    rest_lengths = np.linalg.norm(rest[edges[:, 0]] - rest[edges[:, 1]], axis=1)
    neck_zone = rest[:, 2] > rest[:, 2].max() - 0.34  # tête et cou seulement : on isole les défauts du cou des autres régions
    colors = vertex_colors(body)
    head_bone = rig.data.bones["head"]
    centre = (0.0, float(rest[neck_zone][:, 1].mean()), float(rest[:, 2].max() - 0.2))
    rows = {}
    for name, rotations, angle in POSES:
        for sign in (1.0, -1.0):
            for bone, axis, fraction in rotations:
                value = [0.0, 0.0, 0.0]
                value[axis] = np.radians(angle * fraction) * sign
                rig.pose.bones[bone].rotation_euler = value
            points = evaluate_cage(body)
            normals, areas = geometry(points)
            flipped_mask = (np.einsum("ij,ij->i", normals, rest_normals) < 0) & (rest_areas > 1e-10)
            near = neck_zone[triangles].all(1)
            stretch = np.linalg.norm(points[edges[:, 0]] - points[edges[:, 1]], axis=1) / np.maximum(rest_lengths, 1e-9)
            near_edges = neck_zone[edges].all(1)
            row = {"retournees_cou_tete": int((flipped_mask & near).sum()), "retournees_total": int(flipped_mask.sum()), "etirement_max_cou_tete": round(float(stretch[near_edges].max()), 3),
                   "compression_min_cou_tete": round(float(stretch[near_edges].min()), 3), "etirement_max_total": round(float(stretch.max()), 3)}
            rows.setdefault(name, {})["signe_" + ("+" if sign > 0 else "-")] = row
            if IMAGES and name in IMAGE_POSES and sign > 0:
                for view, direction in (("face", (0, -1, 0)), ("profil", (1, 0, 0)), ("trois_quarts", (0.7, -0.7, 0.2)), ("arriere", (0, 1, 0))):
                    render(points, body, colors, OUT / f"cou_{TAG}_{label}_{name}_{view}.png", direction, centre, 0.42)
            for bone, _a, _f in rotations:
                rig.pose.bones[bone].rotation_euler = (0, 0, 0)
    results[label] = rows
    for name, r in rows.items():
        print("COU", TAG, METHOD, label, name, json.dumps(r, ensure_ascii=False))
(OUT / f"cou_{TAG}_{METHOD}.json").write_text(json.dumps(results, indent=1, ensure_ascii=False), encoding="utf-8")
