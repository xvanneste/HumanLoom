"""Pont Blender du retargeting (lot A3) : lecture d'une action source, écriture de l'action pour NOS os, aperçu non destructif, NLA, remplacement.

Règles : une action source par chargement (plantage mesuré avec plusieurs) ; l'aperçu restaure l'état initial (action, emplacement, transformations de pose,
image courante) ; le cache de conversion est un fichier .npz dans le dossier utilisateur (jamais dans le dépôt).
"""
from pathlib import Path
import re

import bpy
import numpy as np

try:
    from . import retarget
except ImportError:  # importé à plat (processus de vignettes)
    import retarget

CURVE = re.compile(r'pose\.bones\["(.+?)"\]\.(location|rotation_quaternion|rotation_euler)$')


def read_action(action, rig, fps=None):
    """Action → `retarget.Motion` pour les os de `rig` (os absents de l'action : identité). Les courbes sont interpolées linéairement à chaque image entière."""
    start, end = action.frame_range
    frames = np.arange(int(round(start)), int(round(end)) + 1)
    loc = np.zeros((len(frames), len(rig.names), 3))
    quat = np.zeros((len(frames), len(rig.names), 4))
    quat[..., 0] = 1
    euler = {}
    channels = {}
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    match = CURVE.match(curve.data_path)
                    if match and match.group(1) in rig.index and len(curve.keyframe_points):
                        points = np.empty(len(curve.keyframe_points) * 2)
                        curve.keyframe_points.foreach_get("co", points)
                        channels[(match.group(1), match.group(2), curve.array_index)] = points.reshape(-1, 2)
    for (bone, kind, axis), points in channels.items():
        values = np.interp(frames, points[:, 0], points[:, 1])
        i = rig.index[bone]
        if kind == "location":
            loc[:, i, axis] = values
        elif kind == "rotation_quaternion":
            quat[:, i, axis] = values
        else:
            euler.setdefault(i, np.zeros((len(frames), 3)))[:, axis] = values
    for i, angles in euler.items():  # euler XYZ (ordre de Blender : Z puis Y puis X appliqués dans cet ordre)
        cx, cy, cz = np.cos(angles / 2).T
        sx, sy, sz = np.sin(angles / 2).T
        qx = np.stack([cx, sx, 0 * cx, 0 * cx], -1)
        qy = np.stack([cy, 0 * cy, sy, 0 * cy], -1)
        qz = np.stack([cz, 0 * cz, 0 * cz, sz], -1)
        quat[:, i] = _mul(_mul(qz, qy), qx)
    norm = np.linalg.norm(quat, axis=-1, keepdims=True)
    quat = np.where(norm > 1e-12, quat / np.maximum(norm, 1e-12), np.array([1.0, 0, 0, 0]))
    if fps is None:
        fps = float(action.get("ualm_fps") or bpy.context.scene.render.fps)
    return retarget.Motion(loc, quat, fps), int(frames[0])


def _mul(a, b):
    w1, x1, y1, z1 = a.T
    w2, x2, y2, z2 = b.T
    return np.stack([w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2, w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2, w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2, w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2], -1)


def write_action(rig_object, result, name, first_frame=1):
    """Crée l'action des os de `rig_object` (rotation sur tous les os, translation sur pelvis et root), une clé par image, interpolation linéaire. Ne l'assigne pas."""
    action = bpy.data.actions.new(name)
    action.use_fake_user = True
    previous = rig_object.animation_data.action if rig_object.animation_data else None
    previous_slot = rig_object.animation_data.action_slot if rig_object.animation_data and previous else None
    if rig_object.animation_data is None:
        rig_object.animation_data_create()
    rig_object.animation_data.action = action  # assigne l'emplacement nécessaire à la création des courbes
    frames = np.arange(first_frame, first_frame + result.quat.shape[0], dtype=float)
    names = [b.name for b in rig_object.data.bones]
    moving = {"pelvis", "root"}
    order = {n: i for i, n in enumerate(result_names(result, names))}
    for bone in names:
        if bone not in order:
            continue
        i = order[bone]
        for axis in range(4):
            _fill(action, rig_object, f'pose.bones["{bone}"].rotation_quaternion', axis, frames, result.quat[:, i, axis])
        if bone in moving:
            for axis in range(3):
                _fill(action, rig_object, f'pose.bones["{bone}"].location', axis, frames, result.loc[:, i, axis])
    rig_object.animation_data.action = previous
    if previous is not None and previous_slot is not None:
        rig_object.animation_data.action_slot = previous_slot
    return action


def result_names(result, default):
    return result.report.get("noms_cibles") or default


def _fill(action, rig_object, path, index, frames, values):
    curve = action.fcurve_ensure_for_datablock(rig_object, path, index=index)
    curve.keyframe_points.add(len(frames))
    co = np.empty(len(frames) * 2)
    co[0::2], co[1::2] = frames, values
    curve.keyframe_points.foreach_set("co", co)
    for point in curve.keyframe_points:
        point.interpolation = "LINEAR"
    curve.update()


# --- aperçu non destructif, NLA, remplacement ---------------------------------------------------------------------------------------------------------

class Preview:
    """Assigne temporairement une action à un rig et restaure l'état initial au retrait."""

    def __init__(self):
        self.saved = None

    def start(self, rig_object, action):
        if self.saved is not None:
            self.stop()
        animation = rig_object.animation_data
        self.saved = {"rig": rig_object, "had_animation": animation is not None, "action": animation.action if animation else None,
                      "slot": animation.action_slot if animation and animation.action else None, "frame": bpy.context.scene.frame_current,
                      "pose": {b.name: (tuple(b.location), tuple(b.rotation_quaternion), tuple(b.rotation_euler), b.rotation_mode) for b in rig_object.pose.bones}}
        if animation is None:
            rig_object.animation_data_create()
        rig_object.animation_data.action = action

    def stop(self):
        state, self.saved = self.saved, None
        if state is None:
            return False
        rig = state["rig"]
        if state["had_animation"]:
            rig.animation_data.action = state["action"]
            if state["action"] is not None and state["slot"] is not None:
                rig.animation_data.action_slot = state["slot"]
        else:
            rig.animation_data_clear()
        for bone in rig.pose.bones:
            location, quaternion, euler, mode = state["pose"][bone.name]
            bone.rotation_mode = mode
            bone.location, bone.rotation_quaternion, bone.rotation_euler = location, quaternion, euler
        bpy.context.scene.frame_set(state["frame"])
        return True


def add_to_nla(rig_object, action, name=None, start=None):
    """Ajoute l'action comme bande d'une nouvelle piste NLA ; retourne la bande."""
    if rig_object.animation_data is None:
        rig_object.animation_data_create()
    track = rig_object.animation_data.nla_tracks.new()
    track.name = name or action.name
    first = int(round(action.frame_range[0])) if start is None else int(start)
    strip = track.strips.new(action.name, first, action)
    return strip


def replace_action(rig_object, action):
    if rig_object.animation_data is None:
        rig_object.animation_data_create()
    rig_object.animation_data.action = action


# --- cache de conversion ------------------------------------------------------------------------------------------------------------------------------

def cache_save(directory, key, result):
    path = Path(directory) / "retarget"
    path.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path / f"{key}.npz", quat=result.quat.astype(np.float32), loc=result.loc.astype(np.float32))


def cache_load(directory, key):
    path = Path(directory) / "retarget" / f"{key}.npz"
    if not path.is_file():
        return None
    data = np.load(path)
    return retarget.Result(data["quat"].astype(float), data["loc"].astype(float), {"cache": True})
