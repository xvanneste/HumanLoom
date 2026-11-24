"""Planche de contrôle du retargeting (lot A3) : 4 images clés d'une animation retargetée, os + maillage, de face et de profil, sur 3 morphologies.

  blender --background --factory-startup --offline-mode --python tools/render_retarget_board.py -- DOSSIER_DE_SORTIE [--library DOSSIER | HL_ANIMATION_LIBRARY] [--index N]

Avec une bibliothèque locale (lecture seule, une action à la fois) : l'action N de l'armature de 80 os ou plus la mieux appariée. Sans bibliothèque : animation synthétique
(marche stylisée : bras et jambes en opposition). Le maillage est déformé par le vrai rig (cage + Armature) ; projection orthographique tracée en numpy ; rouge = gauche, bleu = droite.
"""
import os
from pathlib import Path
import sys

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ARGS = sys.argv[sys.argv.index("--") + 1:]
OUT = Path(ARGS[0])
OUT.mkdir(parents=True, exist_ok=True)
library_arg = ARGS[ARGS.index("--library") + 1] if "--library" in ARGS else os.environ.get("HL_ANIMATION_LIBRARY")
ACTION_INDEX = int(ARGS[ARGS.index("--index") + 1]) if "--index" in ARGS else 40
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension import human  # noqa: E402
from extension.animation import mapping, retarget, retarget_bpy, skeleton  # noqa: E402

SIZE = 700
addon.register()


def line(image, p, q, color, width=1):
    n = int(max(abs(q[0] - p[0]), abs(q[1] - p[1]))) + 1
    xs, ys = np.linspace(p[0], q[0], n), np.linspace(p[1], q[1], n)
    for dx in range(-(width // 2), width // 2 + 1):
        for dy in range(-(width // 2), width // 2 + 1):
            x, y = (xs + dx).astype(int), (ys + dy).astype(int)
            ok = (x >= 0) & (x < SIZE) & (y >= 0) & (y < SIZE)
            image[y[ok], x[ok], :3] = color


def view(points, edges, bones, axes, center, extent):
    image = np.ones((SIZE, SIZE, 4), np.float32)
    ax, ay = axes
    project = lambda p: ((p[ax] - center[0]) / extent * SIZE + SIZE / 2, (p[ay] - center[1]) / extent * SIZE + SIZE / 2)
    flat = np.array([project(p) for p in points])
    for a, b in edges[::3]:
        line(image, flat[a], flat[b], (0.78, 0.78, 0.78))
    for name, head, tail in bones:
        color = (0.85, 0.1, 0.1) if name.endswith(".L") else (0.1, 0.2, 0.9) if name.endswith(".R") else (0, 0, 0)
        line(image, project(head), project(tail), color, 2)
    return image


def save(image, path):
    picture = bpy.data.images.new(str(path), image.shape[1], image.shape[0], alpha=True)
    picture.pixels = image.ravel().tolist()
    picture.filepath_raw = str(path)
    picture.file_format = "PNG"
    picture.save()
    bpy.data.images.remove(picture)


def synthetic(target):
    frames = 40
    quat = np.zeros((frames, len(target.names), 4))
    quat[..., 0] = 1
    for f in range(frames):
        swing = np.radians(35) * np.sin(2 * np.pi * f / frames)
        for name, sign in (("arm_upper.L", 1), ("arm_upper.R", -1), ("leg_upper.L", -1), ("leg_upper.R", 1)):
            quat[f, target.index[name]] = [np.cos(sign * swing / 2), np.sin(sign * swing / 2), 0, 0]
        knee = np.radians(40) * max(0, np.sin(2 * np.pi * f / frames + (0 if sign else 0)))
        quat[f, target.index["leg_lower.L"]] = [np.cos(knee / 2), np.sin(knee / 2), 0, 0]
    loc = np.zeros((frames, len(target.names), 3))
    loc[:, target.index["pelvis"], 1] = -0.02 * np.arange(frames)
    return retarget.Result(quat, loc, {"noms_cibles": list(target.names)})


for label, values in (("neutre", {}), ("femme_jeune", {"sex": 1.0, "age": 1.0}), ("homme_age", {"sex": 0.0, "age": 3.0})):
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.ops.humanloom.create()
    body = bpy.context.object
    for name, value in values.items():
        human.set_value(body, name, value)
    rig_object = skeleton.install(body)
    target = retarget.rig_from_armature(rig_object)
    result = synthetic(target)
    source_note = "synthétique"
    if library_arg and Path(library_arg).is_dir() and sorted(Path(library_arg).glob("*.blend")):
        library = sorted(Path(library_arg).glob("*.blend"))[0]
        with bpy.data.libraries.load(str(library), link=False) as (names, _):
            armature_names, action_names = list(names.armatures), list(names.actions)
        target_map = mapping.from_armature(rig_object)
        best = None
        for name in armature_names:
            with bpy.data.libraries.load(str(library), link=False) as (_, wanted):
                wanted.armatures = [name]
            data = wanted.armatures[0]
            if len(data.bones) >= 80:
                pairs, report = mapping.auto_map(target_map, mapping.from_armature(data))
                if best is None or report.coverage > best[0]:
                    best = (report.coverage, name, {t: p.source for t, p in pairs.items()})
            bpy.data.armatures.remove(data)
        with bpy.data.libraries.load(str(library), link=False) as (_, wanted):
            wanted.armatures = [best[1]]
        source_data = wanted.armatures[0]
        source = retarget.rig_from_armature(source_data)
        with bpy.data.libraries.load(str(library), link=False) as (_, wanted):
            wanted.actions = [action_names[ACTION_INDEX]]
        action = wanted.actions[0]
        motion, _first = retarget_bpy.read_action(action, source)
        bpy.data.actions.remove(action)
        result = retarget.retarget(source, target, best[2], motion, retarget.Options())
        source_note = f"bibliothèque locale, action {ACTION_INDEX}"
    frames = result.quat.shape[0]
    keys = [int(frames * k / 4) for k in range(4)]
    for pose_bone in rig_object.pose.bones:
        pose_bone.rotation_mode = "QUATERNION"
    names = [b.name for b in rig_object.data.bones]
    order = {n: i for i, n in enumerate(target.names)}
    edges = np.array([e.vertices[:] for e in body.data.edges])
    sheets = {"face": [], "profil": []}
    for frame in keys:
        for pose_bone in rig_object.pose.bones:
            i = order[pose_bone.name]
            pose_bone.rotation_quaternion = result.quat[frame, i]
            if pose_bone.name in ("pelvis", "root"):
                pose_bone.location = result.loc[frame, i]
        bpy.context.view_layer.update()
        saved = [(m, m.show_viewport) for m in body.modifiers]
        for modifier in body.modifiers:
            modifier.show_viewport = modifier.name in (human.MODIFIER_NAME, skeleton.MODIFIER_NAME, skeleton.DQS_MODIFIER)
        evaluated = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
        mesh = evaluated.to_mesh()
        buffer = np.empty(len(mesh.vertices) * 3, np.float32)
        mesh.vertices.foreach_get("co", buffer)
        evaluated.to_mesh_clear()
        for modifier, state in saved:
            modifier.show_viewport = state
        points = buffer.reshape(-1, 3).astype(float)
        bones = [(b.name, np.array(rig_object.matrix_world @ b.head), np.array(rig_object.matrix_world @ b.tail)) for b in rig_object.pose.bones]
        center_z = 0.9
        sheets["face"].append(view(points, edges, bones, (0, 2), (0.0, center_z), 2.0))
        sheets["profil"].append(view(points, edges, bones, (1, 2), (float(np.median(points[:, 1])) - 0.5 * frame / frames, center_z), 2.0))
    for kind, images in sheets.items():
        save(np.concatenate(images, axis=1), OUT / f"retarget_{label}_{kind}.png")
    print("PLANCHE", label, source_note, "images clés", keys)
