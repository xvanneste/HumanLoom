"""Génération de vignettes HORS du processus principal (lot F0-b) : `blender --background --python thumbnail_worker.py -- job.json result.json`.

Pour chaque action de la bibliothèque de l'utilisateur (une par chargement, lecture seule) : figure en bâtons du squelette source à l'image médiane de l'action (cinématique directe,
vue de face), écrite en PNG dans le cache disque. Aucune donnée de la bibliothèque n'est écrite ailleurs que dans ce cache utilisateur.
"""
from contextlib import nullcontext
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import traceback

import bpy
import numpy as np

job = json.loads(Path(sys.argv[sys.argv.index("--") + 1]).read_text(encoding="utf-8"))
sys.path.insert(0, job["package_dir"])
import retarget  # noqa: E402  (importés à plat : le paquet complet n'est pas nécessaire)
import retarget_bpy  # noqa: E402
from thumbnails import library_revision  # noqa: E402

SIZE = int(job.get("size", 96))
produced, errors = [], []


def draw(points, parents, path):
    """Figure en bâtons (x, z) normalisée dans l'image."""
    image = np.ones((SIZE, SIZE, 4), np.float32)
    image[..., :3] = 0.16
    xs, zs = points[:, 0], points[:, 2]
    span = max(float(zs.max() - zs.min()), 1e-6)
    scale = 0.85 * SIZE / span
    cx = float(np.median(xs))
    px = (xs - cx) * scale + SIZE / 2
    py = (zs - float(zs.min())) * scale + 0.075 * SIZE
    for child, parent in enumerate(parents):
        if parent < 0:
            continue
        n = int(max(abs(px[child] - px[parent]), abs(py[child] - py[parent]))) + 2
        x = np.linspace(px[parent], px[child], n).astype(int)
        y = np.linspace(py[parent], py[child], n).astype(int)
        ok = (x >= 0) & (x < SIZE) & (y >= 0) & (y < SIZE)
        image[y[ok], x[ok], :3] = (0.95, 0.62, 0.2)
    picture = bpy.data.images.new("thumb", SIZE, SIZE, alpha=True)
    picture.pixels = image.ravel().tolist()
    try:
        staging_dir = job.get("staging_dir")
        staging = nullcontext(staging_dir) if staging_dir else TemporaryDirectory(prefix=".hl-t-", dir=path.parent)
        with staging as folder:
            staged = Path(folder) / path.name
            picture.filepath_raw = str(staged)
            picture.file_format = "PNG"
            picture.save()
            os.replace(staged, path)
    finally:
        bpy.data.images.remove(picture)


try:
    library = job["library_blend"]
    revision = job.get("revision")
    euler_order = job.get("euler_order", "XYZ")
    if revision is not None and library_revision(library) != revision:
        raise ValueError("La bibliothèque a changé. Relancez les vignettes.")
    source_rig = job.get("source_rig")
    if source_rig is not None:
        source = retarget.Rig(**source_rig)
    else:
        with bpy.data.libraries.load(library, link=False) as (_available, wanted):
            wanted.armatures = [job["source_armature"]]
        source = retarget.rig_from_armature(wanted.armatures[0])
    out_dir = Path(job["out_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    for key, action_name in job["actions"]:
        try:
            with bpy.data.libraries.load(library, link=False) as (_available, wanted):  # une action par chargement
                wanted.actions = [action_name]
            action = wanted.actions[0]
            if action is None:
                raise ValueError(f"Action introuvable dans la bibliothèque : {action_name}.")
            try:
                if revision is not None and library_revision(library) != revision:
                    raise ValueError("La bibliothèque a changé. Relancez les vignettes.")
                motion, _first = retarget_bpy.read_action(action, source, euler_order=euler_order)
            finally:
                bpy.data.actions.remove(action)
            frame = motion.frames // 2
            world = retarget.forward_kinematics(source, motion.loc[frame:frame + 1], motion.quat[frame:frame + 1])[0]
            draw(world[:, :3, 3], source.parents, out_dir / f"{key}.png")
            produced.append(key)
        except retarget_bpy.EulerOrderRequired as error:
            errors.append({"key": key, "message": str(error), "reason": "Choisissez l’ordre Euler du clip source."})
        except retarget_bpy.ActionSlotRequired as error:
            errors.append({"key": key, "message": str(error)[:200], "reason": "Plusieurs emplacements : exportez un seul slot."})
        except Exception as error:  # noqa: BLE001 - une action en échec n'arrête pas le lot
            errors.append({"key": key, "message": str(error)[:200]})
except Exception as error:  # noqa: BLE001
    errors.append({"message": f"{type(error).__name__}: {error}", "trace": traceback.format_exc()[-500:]})
Path(sys.argv[sys.argv.index("--") + 2]).write_text(json.dumps({"produced": produced, "errors": errors}), encoding="utf-8")
