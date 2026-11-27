"""Pont Blender du retargeting (lot A3) : lecture d'une action source, écriture de l'action pour NOS os, aperçu non destructif, NLA, remplacement.

Règles : une action source par chargement (plantage mesuré avec plusieurs) ; l'aperçu restaure l'état initial (action, emplacement, transformations de pose,
image courante) ; le cache de conversion est un fichier .npz dans le dossier utilisateur (jamais dans le dépôt).
"""
import hashlib
from pathlib import Path
import re

import bpy
import numpy as np
from mathutils import Euler, Matrix, Quaternion

try:
    from . import retarget
except ImportError:  # importé à plat (processus de vignettes)
    import retarget

CURVE = re.compile(r'pose\.bones\["((?:[^"\\]|\\.)*)"\]\.(\w+)$')
CHANNELS = {
    "location": (0.0, 0.0, 0.0),
    "rotation_quaternion": (1.0, 0.0, 0.0, 0.0),
    "rotation_euler": (0.0, 0.0, 0.0),
    "rotation_axis_angle": (0.0, 0.0, 1.0, 0.0),
    "scale": (1.0, 1.0, 1.0),
}
ROTATION = {
    "QUATERNION": "rotation_quaternion",
    "AXIS_ANGLE": "rotation_axis_angle",
}
RIGID_TOLERANCE = 1e-5
EULER_ORDERS = ("XYZ", "XZY", "YXZ", "YZX", "ZXY", "ZYX")


class ActionSlotRequired(ValueError):
    """Un clip ne permet pas de déduire un emplacement unique."""


class EulerOrderRequired(ValueError):
    """Le mode exact n’est pas fourni pour un clip Euler détaché."""


def _action_slot(action, source_object, slot):
    if slot is not None:
        if not any(slot == candidate for candidate in action.slots):
            raise ValueError("L’emplacement demandé appartient à une autre action.")
    else:
        animation = source_object.animation_data if source_object is not None else None
        if animation and animation.action == action and animation.action_slot is not None:
            slot = animation.action_slot
        elif source_object is not None:
            raise ValueError("L’action n’est pas assignée à l’armature source ; indiquez son emplacement d’origine.")
        elif len(action.slots) == 1:
            slot = action.slots[0]
        elif action.slots:
            raise ActionSlotRequired(f"Action « {action.name} » : choisissez explicitement un emplacement (slot), ou exportez le clip avec un seul emplacement.")
        else:
            raise ValueError(f"Action « {action.name} » : aucun emplacement de pose.")
    if slot.target_id_type not in {"OBJECT", "UNSPECIFIED"}:
        raise ValueError(f"L’emplacement « {slot.identifier} » doit cibler un objet.")
    return slot


def _action_curves(action, slot):
    if len(action.layers) != 1 or len(action.layers[0].strips) != 1:
        raise ValueError(f"Action « {action.name} » : une couche et une bande de clés sont attendues.")
    strip = action.layers[0].strips[0]
    bag = strip.channelbag(slot) if strip.type == "KEYFRAME" else None
    if bag is None or not len(bag.fcurves):
        raise ValueError(f"L’emplacement « {slot.identifier} » ne contient aucune courbe.")
    return bag.fcurves


def _action_frames(action, curves):
    if action.use_frame_range:
        start, end = action.frame_start, action.frame_end
    else:
        ranges = [curve.range() for curve in curves if len(curve.keyframe_points) or len(curve.sampled_points)]
        if not ranges:
            raise ValueError(f"Action « {action.name} » : indiquez une plage d’images explicite.")
        start = min(bounds[0] for bounds in ranges)
        end = max(bounds[1] for bounds in ranges)
    if not np.isfinite([start, end]).all() or start > end:
        raise ValueError(f"Action « {action.name} » : plage d’images invalide.")
    return range(round(start), round(end) + 1)


def _source_bones(source_object, rig):
    if source_object is None:
        return None
    if source_object.type != "ARMATURE" or source_object.mode == "EDIT":
        raise ValueError("Choisissez une armature source hors du mode Édition.")
    actual = retarget.rig_from_armature(source_object)
    if actual.names != rig.names or actual.parents != rig.parents or not np.allclose(actual.rest, rig.rest, rtol=0, atol=RIGID_TOLERANCE):
        raise ValueError("Le squelette de repos ne correspond pas à l’armature source.")
    pose_bones = source_object.pose.bones
    animation = source_object.animation_data
    armature_animation = source_object.data.animation_data
    if (animation and animation.drivers) or (armature_animation and (armature_animation.action or armature_animation.drivers or armature_animation.nla_tracks)):
        raise ValueError("L’armature source utilise des pilotes ou des données d’armature animées ; échantillonnez son mouvement dans une action de pose autonome.")
    if any(not constraint.mute and constraint.influence != 0 for bone in pose_bones for constraint in bone.constraints):
        raise ValueError("L’armature source utilise des contraintes de pose ; échantillonnez son mouvement dans une action de pose autonome.")
    return pose_bones


def _pose_channels(curves, rig, frames):
    channels = {}
    recognized = False
    for curve in curves:
        if curve.is_empty:
            continue
        match = CURVE.fullmatch(curve.data_path)
        if not match:
            if not curve.mute and curve.data_path.startswith("pose.bones[") and "].constraints[" in curve.data_path:
                raise ValueError(f"Contrainte de pose animée non prise en charge : {curve.data_path}.")
            continue  # l'espace de l'armature exclut les canaux de l'objet et les autres propriétés
        name, channel = match.groups()
        name = bpy.utils.unescape_identifier(name)
        if name not in rig.index:
            continue
        if channel not in CHANNELS:
            if not curve.mute and channel == "rotation_mode":
                raise ValueError(f"Canal de pose non pris en charge : {curve.data_path}.")
            continue
        recognized = True
        if curve.mute:
            continue
        if not 0 <= curve.array_index < len(CHANNELS[channel]):
            raise ValueError(f"Indice invalide pour le canal {curve.data_path}.")
        fields = channels.setdefault(name, {})
        if channel not in fields:
            fields[channel] = np.tile(CHANNELS[channel], (len(frames), 1))
        values = np.fromiter((curve.evaluate(frame) for frame in frames), dtype=float, count=len(frames))
        if not np.isfinite(values).all():
            raise ValueError(f"Canal non fini : {curve.data_path}.")
        fields[channel][:, curve.array_index] = values
    return channels if recognized else None


def _rotation_mode(name, fields, source_bones, euler_order):
    if source_bones is not None:
        return source_bones[name].rotation_mode
    rotation = [(mode, channel) for mode, channel in (*ROTATION.items(), (euler_order, "rotation_euler")) if channel in fields]
    if len(rotation) > 1:
        raise ValueError(f"L’os « {name} » utilise plusieurs modes de rotation ; fournissez l’armature source.")
    if rotation and rotation[0][0] is None:
        raise EulerOrderRequired("Choisissez l’ordre Euler du clip source.")
    return rotation[0][0] if rotation else "QUATERNION"


def _quaternions(mode, values):
    if mode == "QUATERNION":
        norm = np.linalg.norm(values, axis=1, keepdims=True)
        # Blender utilise un demi-tour autour de X pour un quaternion entièrement nul.
        return np.divide(values, norm, out=np.tile((0.0, 1.0, 0.0, 0.0), (len(values), 1)), where=norm > 0)
    if mode == "AXIS_ANGLE":
        return np.array([tuple(Quaternion(row[1:], row[0])) for row in values])
    return np.array([tuple(Euler(row, mode).to_quaternion()) for row in values])


def _pose_bases(rig, channels, source_bones, frames, euler_order):
    loc = np.zeros((len(frames), len(rig.names), 3))
    quat = np.zeros((len(frames), len(rig.names), 4))
    quat[..., 0] = 1
    for name, fields in channels.items():
        i = rig.index[name]
        if "scale" in fields and not np.allclose(fields["scale"], 1.0, rtol=0, atol=RIGID_TOLERANCE):
            raise ValueError(f"L’os « {name} » a une échelle non unitaire, incompatible avec le mouvement rigide.")
        if "location" in fields:
            loc[:, i] = fields["location"]
        mode = _rotation_mode(name, fields, source_bones, euler_order)
        rotation = ROTATION.get(mode, "rotation_euler")
        if rotation in fields:
            quat[:, i] = _quaternions(mode, fields[rotation])
    return loc, quat


def _blender_pose_bases(rig, source_bones, loc, quat):
    """Convertit la pose Blender en bases locales pour le FK rigide de HumanLoom."""
    bones = [source_bones[name].bone for name in rig.names]
    for i, bone in enumerate(bones):
        if bone.use_connect:
            loc[:, i] = 0
    if all(bone.use_local_location and bone.use_inherit_rotation and bone.inherit_scale == "FULL" for bone in bones):
        return loc, quat
    local_rest = rig.local_rest()
    local_inverse = np.linalg.inv(local_rest)
    basis = retarget.basis_matrix(loc.reshape(-1, 3), quat.reshape(-1, 4)).reshape(*loc.shape[:2], 4, 4)
    world = np.empty_like(basis)
    for i, bone in enumerate(bones):
        parent = rig.parents[i]
        for f in range(len(basis)):
            inputs = {"parent_matrix": Matrix(world[f, parent]), "parent_matrix_local": bones[parent].matrix_local} if parent >= 0 else {}
            world[f, i] = bone.convert_local_to_pose(Matrix(basis[f, i]), bone.matrix_local, **inputs)
        world_local = np.linalg.solve(world[:, parent], world[:, i]) if parent >= 0 else world[:, i]
        basis[:, i] = local_inverse[i] @ world_local
    rotation = basis[..., :3, :3]
    orthogonal = np.swapaxes(rotation, -1, -2) @ rotation
    if (not np.isfinite(basis).all() or not np.allclose(orthogonal, np.eye(3), rtol=0, atol=RIGID_TOLERANCE)
            or not np.allclose(np.linalg.det(rotation), 1, rtol=0, atol=RIGID_TOLERANCE)):
        raise ValueError("Une matrice de pose contient une échelle, un cisaillement ou une réflexion incompatible avec le mouvement rigide.")
    return basis[..., :3, 3], retarget.matrix_to_quat(rotation)


def read_action(action, rig, fps=None, *, source_object=None, slot=None, euler_order="XYZ"):
    """Échantillonne une action de pose seule et neutre aux images entières.

    L’objet source d’origine fournit les modes de rotation et les options d’héritage.
    Il doit être lié à l’action ou fourni avec son slot d’origine connu.
    Sans objet, les courbes doivent décrire une pose autonome et un seul type de
    rotation par os ; euler_order détermine la convention, avec XYZ pour les
    anciens appels et None pour exiger un choix dans la galerie.
    Un slot est explicite, déjà lié à l’action sur l’objet, ou unique dans l’action.
    """
    if euler_order is not None and euler_order not in EULER_ORDERS:
        raise ValueError(f"Ordre Euler inconnu : {euler_order}.")
    source_bones = _source_bones(source_object, rig)
    slot = _action_slot(action, source_object, slot)
    curves = _action_curves(action, slot)
    frames = _action_frames(action, curves)
    channels = _pose_channels(curves, rig, frames)
    if channels is None:
        raise ValueError(f"L’emplacement « {slot.identifier} » ne contient aucun canal de pose reconnu.")
    loc, quat = _pose_bases(rig, channels, source_bones, frames, euler_order)
    if source_bones is not None:
        loc, quat = _blender_pose_bases(rig, source_bones, loc, quat)
    if fps is None:
        render = bpy.context.scene.render
        fps = float(action.get("ualm_fps") or render.fps / render.fps_base)
    if not np.isfinite(fps) or fps <= 0:
        raise ValueError("La cadence de l’action doit être finie et positive.")
    return retarget.Motion(loc, retarget.continuous(quat), fps), frames.start


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

def conversion_cache_key(source, target, links, options, motion, action_key):
    """Clé d’une conversion dont les données d’entrée ont déjà été évaluées."""
    stamp = retarget.signature(source, links, options, action_key)
    digest = hashlib.sha256(repr((stamp, tuple(target.names), tuple(source.parents),
                                  tuple(target.parents), motion.fps)).encode("utf-8"))
    for values in (source.rest, target.rest, motion.loc, motion.quat):
        digest.update(np.ascontiguousarray(values, dtype=np.float64).tobytes())
    return "pose-v4-" + digest.hexdigest()


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
