"""Travail d'importation exécuté DANS un processus Blender séparé (lot A1b) : `blender --background --python import_worker.py -- job.json result.json`.

Une source (FBX, BVH, glTF/GLB ou .blend) → des actions ajoutées à la bibliothèque de l'utilisateur (`HumanLoom_Actions.blend`, fichier à nous).
La source n'est jamais ouverte en écriture. Un plantage de ce processus n'affecte que ce fichier (le parent le consigne comme échec).
Piège mesuré (Blender 5.2) : charger plusieurs blocs d'un .blend à la fois peut planter ; une source .blend est donc lue une action par appel.

Métadonnées écrites sur chaque action, compatibles avec celles de l'outil UALM : ualm_id, ualm_name, ualm_category, ualm_family, ualm_skeleton,
ualm_flags, ualm_fps, ualm_digest (+ ualm_rest_height, ualm_bone_count pour l'application ultérieure : échelle cm/m, rig compatible).
"""
import hashlib
import json
from pathlib import Path
import re
import sys
import traceback

import bpy

FAMILY = "HumanLoom import"
NAME_LIMIT = 63
ROOT_MOTION_RATIO = 0.05  # déplacement de l'os racine > 5 % de la hauteur au repos : drapeau root_motion (heuristique mesurée, non déclarée par la source)


def digest(action):
    """Empreinte du contenu d'une action (courbes triées, images clés arrondies) : indépendante du nom et de l'ordre de création."""
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


def bvh_fps(path):
    with open(path, encoding="utf-8", errors="ignore") as stream:
        for line in stream:
            if line.strip().lower().startswith("frame time"):
                try:
                    return round(1.0 / float(line.split(":")[1]), 3)
                except (ValueError, ZeroDivisionError):
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
        candidate = base[:NAME_LIMIT - len(suffix)] + suffix
        number += 1
    return candidate


def category_folder(job, extra=None):
    folder = extra or job.get("category") or "Importées"
    return f"Animations/{folder.strip('/')}"


def main(job_path, result_path):
    job = json.loads(Path(job_path).read_text(encoding="utf-8"))
    source = Path(job["source"])
    library = Path(job["library_blend"])
    result = {"source": source.name, "entries": [], "skipped_duplicates": [], "errors": [], "added": 0}
    try:
        if library.is_file():
            bpy.ops.wm.open_mainfile(filepath=str(library))
        else:
            bpy.ops.wm.read_factory_settings(use_empty=True)
        known = {a.get("ualm_digest"): a.name for a in bpy.data.actions if a.get("ualm_digest")}
        before_actions, before_objects = set(a.name for a in bpy.data.actions), set(o.name for o in bpy.data.objects)
        scene = bpy.context.scene
        suffix = source.suffix.lower()
        fps_hint = None
        collected = []  # (action, armature, name, category_override, extra_props)
        if suffix == ".fbx":
            bpy.ops.import_scene.fbx(filepath=str(source), ignore_leaf_bones=True)
            fps_hint = float(scene.render.fps) / (scene.render.fps_base or 1.0)
        elif suffix == ".bvh":
            fps_hint = bvh_fps(source) or float(job.get("fps", 30.0))
            scene.render.fps = int(round(fps_hint))
            bpy.ops.import_anim.bvh(filepath=str(source), use_fps_scale=False)
        elif suffix in (".glb", ".gltf"):
            fps_hint = float(job.get("fps", 30.0))  # glTF stocke des secondes : les images dépendent de la cadence choisie
            scene.render.fps = int(round(fps_hint))
            bpy.ops.import_scene.gltf(filepath=str(source))
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
                    if action is not None:
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

        taken = set(a.name for a in bpy.data.actions)
        for action, owner, name, category_override, _ in collected:
            code, curves = digest(action)
            if code in known:
                result["skipped_duplicates"].append({"name": name, "same_as": known[code]})
                if action.name not in before_actions:
                    bpy.data.actions.remove(action)
                continue
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
            height = rest_height(owner)
            flags = parse_flags(action.get("ualm_flags")) if suffix == ".blend" else []
            if declared:
                flags = [str(f) for f in (declared.get("flags") or ())]
                if declared.get("root_motion") and "root_motion" not in flags:
                    flags.append("root_motion")
                if declared.get("additive") not in (None, "NONE", "") and "additive" not in flags:
                    flags.append("additive")
            elif suffix != ".blend" and owner is not None and height > 0 and root_travel(action, owner) > ROOT_MOTION_RATIO * height:
                flags.append("root_motion")
            category = category_override or job.get("category") or ("Importées/" + source.stem if suffix == ".blend" else "Importées")
            folder = declared["folder"] if declared and declared.get("folder") else category_folder(job, category)
            action_name = safe_name(prefix, name if suffix != ".blend" else (name.partition("__")[2] or name), taken - {action.name})
            taken.discard(action.name)
            taken.add(action_name)
            action.name = action_name
            action.use_fake_user = True
            identifier = declared["id"] if declared and declared.get("id") else f"/Import/{folder}/{action_name}"
            for key, value in (("ualm_id", identifier), ("ualm_name", action_name.partition("__")[2] or action_name), ("ualm_category", declared["folder"] if declared and declared.get("folder") else (folder.partition("/")[2] or folder)),
                               ("ualm_family", FAMILY), ("ualm_skeleton", skeleton), ("ualm_flags", ",".join(flags)), ("ualm_fps", fps), ("ualm_digest", code),
                               ("ualm_rest_height", height), ("ualm_bone_count", len(owner.data.bones) if owner else 0)):
                action[key] = value
            result["entries"].append({
                "id": identifier, "name": action_name.partition("__")[2] or action_name, "action": action_name, "folder": folder, "skeleton": skeleton,
                "frame_rate": fps, "length": round((frames - 1) / fps, 6) if fps else 0.0, "num_frames": frames, "root_motion": "root_motion" in flags,
                "additive": "ADDITIVE" if "additive" in flags else "NONE", "flags": flags, "digest": code, "num_curves": curves,
                "bone_count_hint": len(owner.data.bones) if owner else 0, "rest_height": round(height, 4), "source_format": suffix[1:],
                "metadata": "déclarées" if declared else "heuristique",
                "declared_frames": int(declared.get("num_frames") or 0) if declared else None})
            known[code] = action_name
            result["added"] += 1

        for obj in [o for o in bpy.data.objects if o.name not in before_objects]:
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
        if result["added"]:
            library.parent.mkdir(parents=True, exist_ok=True)
            bpy.ops.wm.save_as_mainfile(filepath=str(library), compress=False)
    except Exception as error:  # noqa: BLE001
        result["errors"].append({"message": f"{type(error).__name__}: {error}", "trace": traceback.format_exc()[-600:]})
    Path(result_path).write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")


if "--" in sys.argv:
    arguments = sys.argv[sys.argv.index("--") + 1:]
    if len(arguments) >= 2:
        main(arguments[0], arguments[1])
