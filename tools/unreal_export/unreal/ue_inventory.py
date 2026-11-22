"""Unreal Engine 5.8 side, step 1: analyse the project and build the inventory.

Run inside the editor (Output Log / Python console):

    py "<...>/Tools/UnrealBlenderBridge/unreal/run_export.py" --analyze-only

Everything that touches the `unreal` module is wrapped by small `_try`
helpers because a handful of property/function names (frame rate, additive
type, root-motion flags...) have moved between engine releases. Run
`ue_probe.py` once to see which ones your 5.8.x build exposes; the exporter
records what it could not read in each entry's `flags`/`warnings`.
"""
import os
import re
import sys

import unreal

_HERE = os.path.dirname(os.path.abspath(__file__))
_ADDON = os.path.normpath(os.path.join(_HERE, "..",
                                       "unreal_animation_library_manager"))
if _ADDON not in sys.path:
    sys.path.insert(0, _ADDON)
import ualm_core as core  # noqa: E402

ENGINE_CLASSES = {
    "anim": ("/Script/Engine", "AnimSequence"),
    "mesh": ("/Script/Engine", "SkeletalMesh"),
    "skeleton": ("/Script/Engine", "Skeleton"),
    "abp": ("/Script/Engine", "AnimBlueprint"),
    "montage": ("/Script/Engine", "AnimMontage"),
    "composite": ("/Script/Engine", "AnimComposite"),
    "blendspace": ("/Script/Engine", "BlendSpace"),
    "pose": ("/Script/Engine", "PoseAsset"),
}
CONTROL_RIG_CLASSES = [("/Script/ControlRigDeveloper", "ControlRigBlueprint"),
                       ("/Script/ControlRig", "ControlRigBlueprint")]


# ------------------------------------------------------------------ helpers
def log(msg):
    unreal.log(f"[UALM] {msg}")


def warn(msg):
    unreal.log_warning(f"[UALM] {msg}")


def _try(*fns, default=None):
    """Call each zero-arg callable until one works and returns non-None."""
    for fn in fns:
        try:
            v = fn()
            if v is not None:
                return v
        except Exception:  # noqa: BLE001 - API probing
            continue
    return default


def prop(obj, *names, default=None):
    for n in names:
        try:
            return obj.get_editor_property(n)
        except Exception:  # noqa: BLE001
            continue
    return default


def _clean_name(v):
    """unreal.Name('None') is truthy: treat it (and '') as 'no value'."""
    t = str(v) if v is not None else ""
    return None if t in ("", "None") else t


def enum_name(v):
    if v is None:
        return None
    return getattr(v, "name", str(v)).split(".")[-1]


def asset_path_of(obj):
    """'/Game/Foo/Bar.Bar' -> '/Game/Foo/Bar' (long package name)."""
    if obj is None:
        return None
    return obj.get_path_name().split(".")[0]


def get_assets(ar, cls, roots):
    """All assets of class `cls` ('/Script/X', 'Name') under `roots`."""
    try:
        flt = unreal.ARFilter(
            class_paths=[unreal.TopLevelAssetPath(*cls)],
            package_paths=list(roots), recursive_paths=True,
            recursive_classes=True)
        return list(ar.get_assets(flt))
    except Exception as e:  # noqa: BLE001
        warn(f"get_assets({cls[1]}) failed: {e}")
        return []


def package_to_disk(package_name):
    """Absolute .uasset path for a /Game package, or None (plugins/engine)."""
    if not package_name.startswith("/Game/"):
        return None
    content = unreal.SystemLibrary.get_project_content_directory()
    p = os.path.join(content, package_name[len("/Game/"):] + ".uasset")
    return p if os.path.isfile(p) else None


def source_hash(package_name):
    """Content hash of the saved asset file ('' if it cannot be resolved)."""
    p = package_to_disk(package_name)
    return core.sha1_file(p) if p else ""


def skeleton_id(skel_pkg):
    return core.sanitize(skel_pkg.replace("/Game/", "", 1).strip("/")
                         .replace("/", "_"))


# -------------------------------------------------------- per-asset readers
def read_skeleton_of(anim):
    return prop(anim, "skeleton") or _try(lambda: anim.get_skeleton()) or \
        _try(lambda: getattr(anim, "skeleton"))


def read_anim_info(anim):
    """Technical properties of one AnimSequence (best effort)."""
    warnings = []
    lib = getattr(unreal, "AnimationLibrary", None)

    length = _try(lambda: lib.get_sequence_length(anim),
                  lambda: anim.get_play_length(),
                  lambda: prop(anim, "sequence_length"))
    frames = _try(lambda: lib.get_num_frames(anim),
                  lambda: anim.get_number_of_sampled_keys(),
                  lambda: prop(anim, "number_of_frames"))
    fr = _try(lambda: lib.get_frame_rate(anim),
              lambda: anim.get_data_model().get_frame_rate(),
              lambda: prop(anim, "target_frame_rate"))
    rate = None
    if fr is not None:
        try:
            rate = float(fr.numerator) / float(fr.denominator)
        except Exception:  # noqa: BLE001
            rate = None
    if length is None:
        warnings.append("length unreadable")
    if frames is None:
        warnings.append("frame count unreadable")
        frames = int(round(length * (rate or 30.0))) + 1 if length else 0
    if rate is None and length:
        rate = frames / length if length and frames > 0 else 30.0  # UE: length = NumFrames / rate

    additive = enum_name(prop(anim, "additive_anim_type", default=None)) \
        or "AAT_None"
    ref_type = enum_name(prop(anim, "ref_pose_type", default=None))
    root_motion = bool(prop(anim, "enable_root_motion", default=False))
    root_lock = enum_name(prop(anim, "root_motion_root_lock", default=None))
    retarget_src = prop(anim, "retarget_source")
    retarget_asset = asset_path_of(prop(anim, "retarget_source_asset"))
    tracks = _try(lambda: lib.get_animation_track_names(anim),
                  lambda: lib.get_raw_track_names(anim), default=[])
    curves = _try(lambda: lib.get_animation_curve_names(
        anim, unreal.RawCurveTrackTypes.RCT_FLOAT), default=[])
    return {
        "length": round(float(length), 6) if length is not None else None,
        "num_frames": int(frames),
        "frame_rate": round(float(rate), 4) if rate else None,
        "additive": additive.replace("AAT_", "").upper(),  # NONE/LOCALSPACEBASE/...
        "additive_ref": ref_type,
        "root_motion": root_motion,
        "root_motion_lock": root_lock,
        "retarget_source": _clean_name(retarget_src),
        "retarget_source_asset": retarget_asset,
        "bone_tracks": [str(t) for t in tracks],
        "num_curves": len(curves),
        "warnings": warnings,
    }


def dependency_flags(ar, package_name):
    """Best effort: does this animation depend on a Control Rig / ABP?"""
    flags = []
    deps = _try(lambda: ar.get_dependencies(
        unreal.Name(package_name), unreal.AssetRegistryDependencyOptions(
            include_soft_package_references=True,
            include_hard_package_references=True)), default=[]) or []
    for d in deps:
        s = str(d)
        if not s.startswith("/Game"):      # /Script/ControlRig etc. = every asset
            continue
        base = s.rsplit("/", 1)[-1]
        if "ControlRig" in s or base.startswith("CR_") or "CtrlRig" in s:
            flags.append("control_rig_dependency")
            break
    return flags


# ------------------------------------------------------------------ main
def build_inventory(roots=("/Game",), include_meshes=True, with_hash=True,
                    progress=True):
    """Scan the project; returns a manifest dict (no files exported yet)."""
    project = unreal.SystemLibrary.get_game_name()
    manifest = core.new_manifest(project, unreal.SystemLibrary.get_engine_version())
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    try:
        ar.scan_paths_synchronous(list(roots), True)
    except Exception:  # noqa: BLE001
        pass

    anim_assets = get_assets(ar, ENGINE_CLASSES["anim"], roots)
    mesh_assets = get_assets(ar, ENGINE_CLASSES["mesh"], roots) \
        if include_meshes else []
    abps = get_assets(ar, ENGINE_CLASSES["abp"], roots)
    crs = []
    for c in CONTROL_RIG_CLASSES:
        crs += get_assets(ar, c, roots)
    unsupported = {k: len(get_assets(ar, ENGINE_CLASSES[k], roots))
                   for k in ("montage", "composite", "blendspace", "pose")}
    manifest["unsupported_assets"] = unsupported
    log(f"Found {len(anim_assets)} AnimSequences, {len(mesh_assets)} "
        f"SkeletalMeshes, {len(abps)} AnimBPs, {len(crs)} Control Rigs "
        f"(not exported: {unsupported})")

    skeletons = manifest["skeletons"]

    def ensure_skel(skel_obj):
        pkg = asset_path_of(skel_obj)
        sid = skeleton_id(pkg)
        if sid not in skeletons:
            skeletons[sid] = {
                "id": sid, "asset_path": pkg, "name": skel_obj.get_name(),
                "reference_mesh": None, "meshes": [], "anim_blueprints": [],
                "control_rigs": [], "source_hash": source_hash(pkg)
                if with_hash else ""}
        return sid

    # --- skeletal meshes => characters + skeletons
    for ad in mesh_assets:
        mesh = ad.get_asset()
        skel = read_skeleton_of(mesh) if mesh else None
        if skel is None:
            continue
        sid = ensure_skel(skel)
        pkg = str(ad.package_name)
        cid = core.sanitize(pkg.replace("/Game/", "", 1).replace("/", "_"))
        manifest["characters"][cid] = {
            "id": cid, "name": str(ad.asset_name), "asset_path": pkg,
            "skeleton": sid, "source_hash": source_hash(pkg) if with_hash
            else "", "status": core.ST_PENDING,
            "folder": str(ad.package_path)}
        skeletons[sid]["meshes"].append(cid)

    # --- animations
    task = unreal.ScopedSlowTask(max(len(anim_assets), 1),
                                 "UALM: analysing animations")
    if progress:
        task.make_dialog(True)
    n_bad = 0
    with task:
        for i, ad in enumerate(anim_assets):
            if progress:
                if task.should_cancel():
                    warn("Analysis cancelled by user")
                    break
                task.enter_progress_frame(1, f"{i + 1}/{len(anim_assets)} "
                                             f"{ad.asset_name}")
            try:
                anim = ad.get_asset()
                skel = read_skeleton_of(anim)
                if skel is None:
                    raise RuntimeError("no skeleton")
                sid = ensure_skel(skel)
                pkg = str(ad.package_name)
                info = read_anim_info(anim)
                folder = str(ad.package_path).replace("/Game", "", 1).strip("/")
                flags = dependency_flags(ar, pkg)
                if info["additive"] != "NONE":
                    flags.append("additive")
                if info["retarget_source"] or info["retarget_source_asset"] \
                        or "retarget" in pkg.lower():
                    flags.append("retargeted")
                if info["root_motion"]:
                    flags.append("root_motion")
                entry = {
                    "id": pkg, "name": str(ad.asset_name), "folder": folder,
                    "skeleton": sid, "asset_path": pkg,
                    "source_hash": source_hash(pkg) if with_hash else "",
                    "export_settings": EXPORT_SETTINGS_TAG,
                    "flags": sorted(set(flags)),
                    "needs_bake": "control_rig_dependency" in flags,
                    "status": core.ST_PENDING, **info}
                entry["bone_count_hint"] = len(entry.pop("bone_tracks"))
                manifest["animations"][pkg] = entry
            except Exception as e:  # noqa: BLE001
                n_bad += 1
                warn(f"analysis failed for {ad.package_name}: {e}")
                manifest["animations"][str(ad.package_name)] = {
                    "id": str(ad.package_name), "name": str(ad.asset_name),
                    "folder": "", "skeleton": "", "status": core.ST_FAILED,
                    "error": f"analysis: {e}", "flags": []}
            if (i + 1) % 250 == 0:
                unreal.SystemLibrary.collect_garbage()

    # --- AnimBP / Control Rig per skeleton (informational)
    for ad in abps:
        skel = prop(ad.get_asset(), "target_skeleton")
        if skel is not None:
            sid = ensure_skel(skel)
            skeletons[sid]["anim_blueprints"].append(str(ad.package_name))
    for ad in crs:
        a = ad.get_asset()
        skel = _try(lambda: prop(a, "preview_skeletal_mesh"),
                    lambda: a.get_preview_mesh())
        skel = read_skeleton_of(skel) if skel else None
        if skel is not None:
            sid = ensure_skel(skel)
            skeletons[sid]["control_rigs"].append(str(ad.package_name))

    # --- reference mesh per skeleton: skeleton preview mesh, else first mesh
    for sid, s in skeletons.items():
        pref = None
        sk = unreal.load_asset(s["asset_path"])
        pm = _try(lambda: sk.get_preview_mesh())
        if pm is not None and asset_path_of(pm):
            pcid = core.sanitize(asset_path_of(pm).replace("/Game/", "", 1)
                                 .replace("/", "_"))
            if pcid in manifest["characters"]:
                pref = pcid
        if pref is None and s["meshes"]:
            pref = sorted(s["meshes"])[0]
        s["reference_character"] = pref

    manifest["inventory_summary"] = summarize(manifest)
    return manifest


EXPORT_SETTINGS_TAG = "fbx2020;nomesh;localtime;v1"


def summarize(manifest):
    anims = manifest["animations"]
    per_skel = {}
    for e in anims.values():
        per_skel[e.get("skeleton", "")] = per_skel.get(e.get("skeleton", ""), 0) + 1
    return {
        "animations": len(anims),
        "skeletons": len(manifest["skeletons"]),
        "characters": len(manifest["characters"]),
        "additive": sum("additive" in e.get("flags", []) for e in anims.values()),
        "retargeted": sum("retargeted" in e.get("flags", []) for e in anims.values()),
        "control_rig_dependent": sum(e.get("needs_bake", False) for e in anims.values()),
        "root_motion": sum("root_motion" in e.get("flags", []) for e in anims.values()),
        "animations_per_skeleton": per_skel,
    }
