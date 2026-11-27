"""Travail d'importation exécuté DANS un processus Blender séparé (lot A1b) : `blender --background --python import_worker.py -- job.json result.json`.

Une source (FBX, BVH, glTF/GLB ou .blend) produit un candidat qui ne contient que les actions indexées.
La source n'est jamais ouverte en écriture. Un plantage de ce processus n'affecte que ce fichier (le parent le consigne comme échec).
Piège mesuré (Blender 5.2) : charger plusieurs blocs d'un .blend à la fois peut planter ; une source .blend est donc lue une action par appel.

Métadonnées écrites sur chaque action, compatibles avec celles de l'outil UALM : ualm_id, ualm_name, ualm_category, ualm_family, ualm_skeleton,
ualm_flags, ualm_fps, ualm_digest (+ ualm_rest_height, ualm_bone_count pour l'application ultérieure : échelle cm/m, rig compatible).
"""
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import traceback
from tempfile import TemporaryDirectory

import bpy

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
from blend_action_state import action_states

FAMILY = "HumanLoom import"
NAME_LIMIT = 63
ROOT_MOTION_RATIO = 0.05  # déplacement de l'os racine > 5 % de la hauteur au repos : drapeau root_motion (heuristique mesurée, non déclarée par la source)


def legacy_digest(action):
    """Empreinte v0, utilisée uniquement pour la relecture transactionnelle des anciennes entrées."""
    sha = hashlib.sha1()
    curves = []
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                curves.extend(bag.fcurves)
    for curve in sorted(curves, key=lambda c: (c.data_path, c.array_index)):
        sha.update(f"{curve.data_path}[{curve.array_index}]".encode())
        for key in curve.keyframe_points:
            sha.update(f"{key.co[0]:.3f},{key.co[1]:.4f};".encode())
    return sha.hexdigest(), len(curves)


def stable_value(value):
    if isinstance(value, (bool, int, float, str)) or value is None:
        return value
    if isinstance(value, dict):
        return {key: stable_value(item) for key, item in value.items()}
    if isinstance(value, set):
        return sorted(value)
    if hasattr(value, "to_dict"):
        return {key: stable_value(item) for key, item in value.to_dict().items()}
    if hasattr(value, "to_list"):
        return [stable_value(item) for item in value.to_list()]
    return [stable_value(item) for item in value]


def rna_content(item):
    result = {}
    for prop in item.bl_rna.properties:
        name = prop.identifier
        if name in {"rna_type", "id_data"}:
            continue
        value = getattr(item, name)
        if prop.type == "COLLECTION":
            result[name] = [rna_content(child) for child in value]
        elif prop.type == "POINTER":
            if value is None:
                result[name] = None
            elif isinstance(value, bpy.types.ActionSlot):
                result[name] = value.handle
            elif isinstance(value, bpy.types.ActionGroup):
                result[name] = value.name
            elif item.bl_rna.identifier == "ActionGroup" and name == "colors":
                result[name] = rna_content(value)
            else:
                raise ValueError(f"Dépendance RNA non prise en charge : {item.bl_rna.identifier}.{name}")
        elif not prop.is_readonly or name in {"type", "handle", "identifier"}:
            result[name] = stable_value(value)
    return result


def action_signature(action):
    properties = {}
    for key, value in action.items():
        try:
            ui_data = action.id_properties_ui(key).as_dict()
        except TypeError:  # Les groupes d'IDProperty n'ont pas de métadonnées UI.
            ui_data = None
        properties[key] = (stable_value(value), stable_value(ui_data))
    content = [
        action.name, action.use_fake_user, action.use_extra_user, action.use_frame_range,
        action.frame_start, action.frame_end, action.use_cyclic, properties,
        [rna_content(marker) for marker in action.pose_markers],
        [rna_content(slot) for slot in action.slots], [rna_content(layer) for layer in action.layers],
        rna_content(action.asset_data) if action.asset_data else None,
        rna_content(action.preview) if action.preview else None,
    ]
    return hashlib.sha256(json.dumps(content, ensure_ascii=False, sort_keys=True, allow_nan=False).encode("utf-8")).hexdigest()

# La sérialisation certifie aussi l'influence de couche et les bornes et
# décalage de strip, accessibles dans le .blend mais absents de RNA.
IDENTITY_VERSION = 2
IDENTITY_METADATA = (
    "ualm_fps", "ualm_bvh_frame_time", "ualm_skeleton",
    "ualm_flags", "ualm_rest_height", "ualm_bone_count",
)
IMPORT_PROPERTIES = frozenset(IDENTITY_METADATA) | {
    "ualm_id", "ualm_name", "ualm_category", "ualm_family", "ualm_digest", "ualm_digest_version",
}
# STEPPED expose deux paires de bornes sous les mêmes noms dans RNA 5.2.
SUPPORTED_MODIFIERS = {"GENERATOR", "FNGENERATOR", "ENVELOPE", "CYCLES", "NOISE", "LIMITS", "SMOOTH"}


def modifier_identity(modifier):
    if not hasattr(modifier, "type") or modifier.type not in SUPPORTED_MODIFIERS:
        raise ValueError("Modificateur non qualifié")
    return {
        key: value for key, value in rna_content(modifier).items()
        if key not in {"name", "active", "show_expanded"}
    } | {"is_valid": modifier.is_valid}


def curve_identity(curve, probe):
    keys = [
        (
            tuple(key.co), tuple(key.handle_left), tuple(key.handle_right),
            key.handle_left_type, key.handle_right_type, key.interpolation,
            key.easing, key.amplitude, key.back, key.period,
        )
        for key in curve.keyframe_points
    ]
    samples = [tuple(point.co) for point in curve.sampled_points]
    if curve.driver is not None or (keys and samples):
        raise ValueError("Stockage de courbe non qualifié")
    modifiers = [modifier_identity(modifier) for modifier in curve.modifiers]

    # Les deux drapeaux d’évaluation INT_VALUES/DISCRETE_VALUES ne sont pas
    # exposés par RNA. Ce signal linéaire sur une copie distingue les quatre états.
    while probe.modifiers:
        probe.modifiers.remove(probe.modifiers[-1])
    if samples:
        probe.convert_to_keyframes(0, 2)
        if probe.sampled_points:
            raise ValueError("Impossible d’isoler les drapeaux des échantillons")
    probe.keyframe_points.clear()
    probe.keyframe_points.insert(0, 0.25).interpolation = "LINEAR"
    probe.keyframe_points.insert(2, 2.25).interpolation = "LINEAR"
    mode = (probe.evaluate(0), probe.evaluate(1))
    if mode not in {(0.25, 1.25), (0.25, 0.25), (0.0, 1.0), (0.0, 0.0)}:
        raise ValueError("Drapeaux de lecture de courbe non qualifiés")

    return (
        curve.data_path, curve.array_index, curve.extrapolation, curve.auto_smoothing,
        curve.mute, curve.is_valid, bool(curve.group and curve.group.mute),
        mode, keys, samples, modifiers,
    )


def identity_bytes(action, metadata, hidden_state):
    """Document canonique exact des actions séparables, ou None si la preuve manque."""
    if hidden_state is None or action.asset_data or len(action.layers) != 1:
        return None
    layer = action.layers[0]
    if len(layer.strips) != 1 or layer.strips[0].type != "KEYFRAME":
        return None
    strip = layer.strips[0]
    probe = action.copy()
    try:
        probe_strip = probe.layers[0].strips[0]
        bags = []
        for bag, probe_bag in zip(strip.channelbags, probe_strip.channelbags, strict=True):
            if bag.slot is None or bag.slot_handle != probe_bag.slot_handle:
                return None
            curves = [
                curve_identity(curve, probe_curve)
                for curve, probe_curve in zip(bag.fcurves, probe_bag.fcurves, strict=True)
            ]
            bags.append((bag.slot_handle, curves))
        if not any(curves for _, curves in bags):
            return None
        value = (
            IDENTITY_VERSION, metadata, hidden_state,
            action.use_frame_range, tuple(action.frame_range), action.use_cyclic,
            [(slot.handle, slot.identifier, slot.target_id_type) for slot in action.slots],
            [rna_content(marker) for marker in action.pose_markers],
            {key: stable_value(value) for key, value in action.items() if key not in IMPORT_PROPERTIES},
            bags,
        )
        # Le JSON de Python conserve exactement les flottants finis à la
        # relecture, y compris le signe de zéro.
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (AttributeError, RuntimeError, TypeError, ValueError):
        return None
    finally:
        bpy.data.actions.remove(probe)


def identity_digest(payload):
    return hashlib.sha256(payload).hexdigest() if payload is not None else None


def stored_metadata(action):
    return {key: action.get(key) for key in IDENTITY_METADATA}


def serialized_states(actions, directory):
    if not actions or bpy.app.version[:2] != (5, 2):
        return {}
    try:
        with TemporaryDirectory(prefix="action-state-", dir=directory) as scratch:
            path = Path(scratch) / "snapshot.blend"
            bpy.data.libraries.write(str(path), set(actions), compress=False)
            by_name = action_states(path)
            return {action: by_name.get(action.name) for action in actions}
    except (OSError, RuntimeError, ValueError):
        return {}


def content_signature(action, hidden_state):
    # Le contrôle ANI-005 reste distinct de l'identité de lecture.
    content = action_signature(action)
    if action.get("ualm_digest_version") == IDENTITY_VERSION and hidden_state is not None:
        payload = json.dumps([content, hidden_state], separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()
    return content


def verified_action(action, hidden_state):
    version = action.get("ualm_digest_version")
    if version == IDENTITY_VERSION:
        code = identity_digest(identity_bytes(action, stored_metadata(action), hidden_state))
    elif version is None:
        code = legacy_digest(action)[0]
    else:
        raise ValueError("Version de l’empreinte d’action non prise en charge")
    return [action.get("ualm_id"), code, content_signature(action, hidden_state), version]


def actions_only(path):
    with bpy.data.libraries.load(str(path), link=False) as (source, _):
        names = list(source.actions)
        extra = [name for name in dir(source) if not name.startswith("_") and name != "actions"
                 and isinstance(getattr(source, name), list) and getattr(source, name)]
    if extra or not names:
        raise ValueError("Le candidat ne contient pas exclusivement des actions")
    actions = []
    for name in names:
        with bpy.data.libraries.load(str(path), link=False) as (_, target):
            target.actions = [name]
        action = target.actions[0]
        if action is None or action.name != name or action.get("ualm_family") != FAMILY:
            raise ValueError(f"Action de bibliothèque invalide : {name}")
        action.use_fake_user = True  # L’ajout depuis une bibliothèque désactive ce drapeau.
        actions.append(action)
    return actions


def bvh_frame_time(path):
    with open(path, encoding="utf-8", errors="ignore") as stream:
        for line in stream:
            if line.strip().lower().startswith("frame time"):
                try:
                    period = float(line.split(":")[1])
                    return period if period > 0 and math.isfinite(period) else None
                except (ValueError, IndexError):
                    return None
    return None


def skeleton_short(skeleton):
    """Préfixe court d'action (convention UALM) : fin du nom de squelette après « _Meshes_ » ; nom entier sinon."""
    return skeleton.partition("_Meshes_")[2] or skeleton


def parse_flags(value):
    """`ualm_flags` : chaîne « root_motion,additive » (mesuré sur la bibliothèque UALM) ou liste de chaînes ; autre type → aucun drapeau."""
    if isinstance(value, str):
        return [f.strip() for f in re.split(r"[,;| ]+", value) if f.strip()]
    if isinstance(value, (list, tuple)) or hasattr(value, "to_list"):
        return [str(f) for f in (value.to_list() if hasattr(value, "to_list") else value) if f]
    return []


def rest_height(armature):
    if armature is None or not armature.data.bones:
        return 0.0
    zs = []
    for bone in armature.data.bones:
        zs.append((armature.matrix_world @ bone.head_local).z)
        zs.append((armature.matrix_world @ bone.tail_local).z)
    return max(zs) - min(zs)


def root_travel(action, armature):
    """Déplacement maximal (diagonale de l'étendue) de la translation des os sans parent."""
    if armature is None:
        return 0.0
    roots = {b.name for b in armature.data.bones if b.parent is None}
    best = 0.0
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                spans = {}
                for curve in bag.fcurves:
                    match = re.match(r'pose\.bones\["(.+)"\]\.location$', curve.data_path)
                    if match and match.group(1) in roots and len(curve.keyframe_points):
                        values = [k.co[1] for k in curve.keyframe_points]
                        spans.setdefault(match.group(1), []).append(max(values) - min(values))
                for axes in spans.values():
                    best = max(best, sum(a * a for a in axes) ** 0.5)
    return best


def safe_name(skeleton, name, taken):
    base = f"{skeleton}__{name}".encode("utf-8")[:NAME_LIMIT].decode("utf-8", "ignore")
    candidate, number = base, 1
    while candidate in taken:
        suffix = f"_{number:02d}"
        stem = base.encode("utf-8")[:NAME_LIMIT - len(suffix)].decode("utf-8", "ignore")
        candidate = stem + suffix
        number += 1
    return candidate


def category_folder(job, extra=None):
    folder = extra or job.get("category") or "Importées"
    return f"Animations/{folder.strip('/')}"


def main(job_path, result_path):
    job = json.loads(Path(job_path).read_text(encoding="utf-8"))
    result = {"entries": [], "skipped_duplicates": [], "errors": [], "added": 0}
    try:
        if bpy.ops.wm.read_factory_settings(use_empty=True) != {"FINISHED"}:
            raise ValueError("Impossible d’initialiser le worker")
        if "verify_blend" in job:
            actions = actions_only(Path(job["verify_blend"]))
            states = serialized_states(actions, Path(result_path).parent)
            result["actions"] = {a.name: verified_action(a, states.get(a)) for a in actions}
            Path(result_path).write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
            return
        source = Path(job["source"])
        library = Path(job["candidate_blend"])
        if job["previous_blend"]:
            actions_only(Path(job["previous_blend"]))
        previous_actions = list(bpy.data.actions)
        before_actions, before_objects = set(a.name for a in bpy.data.actions), set(o.name for o in bpy.data.objects)
        scene = bpy.context.scene
        suffix = source.suffix.lower()
        fps_hint = None
        bvh_period = None
        collected = []  # (action, armature, name, category_override, extra_props)
        if suffix == ".fbx":
            if bpy.ops.import_scene.fbx(filepath=str(source), ignore_leaf_bones=True) != {"FINISHED"}:
                raise ValueError(f"Import Blender interrompu : {suffix}")
            fps_hint = float(scene.render.fps) / (scene.render.fps_base or 1.0)
        elif suffix == ".bvh":
            bvh_period = bvh_frame_time(source)
            # Conserver la cadence publiée et la durée historiques. La période
            # source est comparée séparément, à sa précision de lecture.
            fps_hint = (round(1.0 / bvh_period, 3) if bvh_period else None) or float(job.get("fps", 30.0))
            scene.render.fps = int(round(fps_hint))
            if bpy.ops.import_anim.bvh(filepath=str(source), use_fps_scale=False) != {"FINISHED"}:
                raise ValueError(f"Import Blender interrompu : {suffix}")
        elif suffix in (".glb", ".gltf"):
            fps_hint = float(job.get("fps", 30.0))  # glTF stocke des secondes : les images dépendent de la cadence choisie
            scene.render.fps = int(round(fps_hint))
            if bpy.ops.import_scene.gltf(filepath=str(source)) != {"FINISHED"}:
                raise ValueError(f"Import Blender interrompu : {suffix}")
        elif suffix == ".blend":
            with bpy.data.libraries.load(str(source), link=False) as (data_from, _data_to):
                names = list(data_from.actions)
            pattern = job.get("name_filter")
            if pattern:
                names = [n for n in names if re.search(pattern, n, re.IGNORECASE)]
            if job.get("limit"):
                names = names[:int(job["limit"])]
            result["listed"] = len(names)
            for name in names:  # une action par chargement
                try:
                    with bpy.data.libraries.load(str(source), link=False) as (data_from, data_to):
                        data_to.actions = [name]
                    action = data_to.actions[0]
                    if action is None:
                        raise ValueError("Action non chargée")
                    collected.append((action, None, name, action.get("ualm_category"), {}))
                except Exception as error:  # noqa: BLE001
                    result["errors"].append({"action": name, "message": str(error)})
        else:
            raise ValueError(f"Format non pris en charge : {suffix}")

        armatures = [o for o in bpy.data.objects if o.type == "ARMATURE" and o.name not in before_objects]
        if suffix != ".blend":
            new = [a for a in bpy.data.actions if a.name not in before_actions]
            if not new:
                raise ValueError("Aucune action dans ce fichier (maillage seul, ou animation absente)")
            for index, action in enumerate(new):
                owner = next((o for o in armatures if o.animation_data and o.animation_data.action == action), armatures[0] if armatures else None)
                label = source.stem if len(new) == 1 else f"{source.stem}_{re.sub(r'[^0-9A-Za-z]+', '_', action.name).strip('_')}"
                collected.append((action, owner, label, None, {}))

        states = serialized_states(previous_actions + [item[0] for item in collected], Path(result_path).parent)
        known = {}
        legacy_eligible = set(job.get("legacy_eligible", ()))
        for action in previous_actions:
            # La réinspection v0 applique la preuve courante au bloc relu.
            # Le SHA-1 historique ne sert jamais à choisir un doublon.
            if action.get("ualm_digest_version") == IDENTITY_VERSION:
                code = action.get("ualm_digest")
            elif action.name in legacy_eligible:
                code = identity_digest(identity_bytes(action, stored_metadata(action), states.get(action)))
            else:
                code = None
            if code:
                known.setdefault(code, []).append(action)
        known_ids = {action.get("ualm_id") for action in previous_actions}
        taken = set(a.name for a in bpy.data.actions)
        for action, owner, name, category_override, _ in collected:
            skeleton = (owner.name if owner else None) or action.get("ualm_skeleton") or (action.name.partition("__")[0] if "__" in action.name else "Importé")
            declared = job.get("declared") if suffix != ".blend" else None
            prefix = skeleton
            if declared:  # dossier d'export de l'outil Unreal : métadonnées déclarées, pas d'heuristique
                skeleton = declared.get("skeleton") or skeleton
                prefix = skeleton_short(skeleton)
                name = declared.get("name") or name
            fps = float(declared.get("frame_rate") or 0.0) if declared else float(action.get("ualm_fps") or fps_hint or 0.0)
            start, end = action.frame_range
            frames = int(round(end - start)) + 1
            height = rest_height(owner) if owner else float(action.get("ualm_rest_height") or 0.0)
            bone_count = len(owner.data.bones) if owner else int(action.get("ualm_bone_count") or 0)
            flags = parse_flags(action.get("ualm_flags")) if suffix == ".blend" else []
            if declared:
                flags = [str(f) for f in (declared.get("flags") or ())]
                if declared.get("root_motion") and "root_motion" not in flags:
                    flags.append("root_motion")
                if declared.get("additive") not in (None, "NONE", "") and "additive" not in flags:
                    flags.append("additive")
            elif suffix != ".blend" and owner is not None and height > 0 and root_travel(action, owner) > ROOT_MOTION_RATIO * height:
                flags.append("root_motion")
            metadata = {
                "ualm_fps": fps,
                "ualm_bvh_frame_time": bvh_period if suffix == ".bvh" else action.get("ualm_bvh_frame_time"),
                "ualm_skeleton": skeleton,
                "ualm_flags": ",".join(flags),
                "ualm_rest_height": height,
                "ualm_bone_count": bone_count,
            }
            payload = identity_bytes(action, metadata, states.get(action))
            code = identity_digest(payload)
            duplicate = next(
                (prior for prior in known.get(code, ()) if payload == identity_bytes(prior, stored_metadata(prior), states.get(prior))),
                None,
            )
            if duplicate is not None:
                result["skipped_duplicates"].append({"name": name, "same_as": duplicate["ualm_id"], "digest": code})
                taken.discard(action.name)
                bpy.data.actions.remove(action)
                continue
            curves = sum(
                len(bag.fcurves) for layer in action.layers
                for strip in layer.strips for bag in strip.channelbags
            )
            category = category_override or job.get("category") or ("Importées/" + source.stem if suffix == ".blend" else "Importées")
            folder = declared["folder"] if declared and declared.get("folder") else category_folder(job, category)
            action_name = safe_name(prefix, name if suffix != ".blend" else (name.partition("__")[2] or name), taken - {action.name})
            taken.discard(action.name)
            taken.add(action_name)
            action.name = action_name
            if action.name != action_name:
                raise ValueError("Nom d’action tronqué ou modifié par Blender")
            action.use_fake_user = True
            generated_id = f"/Import/{folder}/{action_name}"
            identifier = (declared or {}).get("id") or generated_id
            if identifier in known_ids:
                identifier = generated_id
                suffix_number = 1
                while identifier in known_ids:
                    identifier = f"{generated_id}_{suffix_number:02d}"
                    suffix_number += 1
            known_ids.add(identifier)
            action_properties = metadata | {
                "ualm_id": identifier,
                "ualm_name": action_name.partition("__")[2] or action_name,
                "ualm_category": declared["folder"] if declared and declared.get("folder") else (folder.partition("/")[2] or folder),
                "ualm_family": FAMILY,
                "ualm_digest": code or "",
                "ualm_digest_version": IDENTITY_VERSION,
            }
            for key, value in action_properties.items():
                if value is not None:
                    action[key] = value
            result["entries"].append({
                "id": identifier, "name": action_name.partition("__")[2] or action_name, "action": action_name, "folder": folder, "skeleton": skeleton,
                "frame_rate": fps, "length": round((frames - 1) / fps, 6) if fps else 0.0, "num_frames": frames, "root_motion": "root_motion" in flags,
                "additive": "ADDITIVE" if "additive" in flags else "NONE", "flags": flags, "digest": code, "digest_version": IDENTITY_VERSION, "num_curves": curves, "content_sha256": content_signature(action, states.get(action)),
                "bone_count_hint": bone_count, "rest_height": round(height, 4), "source_format": suffix[1:],
                "metadata": "déclarées" if declared else "heuristique",
                "declared_frames": int(declared.get("num_frames") or 0) if declared else None})
            if code is not None:
                known.setdefault(code, []).append(action)
            result["added"] += 1

        if result["added"] and not result["errors"]:
            names = before_actions | {entry["action"] for entry in result["entries"]}
            bpy.data.libraries.write(str(library), {bpy.data.actions[name] for name in names}, fake_user=True, compress=False)
    except Exception as error:  # noqa: BLE001
        result["errors"].append({"message": f"{type(error).__name__}: {error}", "trace": traceback.format_exc()[-600:]})
    Path(result_path).write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__" and "--" in sys.argv:
    arguments = sys.argv[sys.argv.index("--") + 1:]
    if len(arguments) >= 2:
        main(arguments[0], arguments[1])
