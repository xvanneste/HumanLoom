"""Run once in the editor to verify which Unreal Python APIs this exporter
relies on exist in your 5.8.x build:

  py "<...>/unreal/ue_probe.py"

Prints OK / MISSING for each symbol and tries to read one real AnimSequence.
Paste the MISSING lines back if something needs adapting.
"""
import unreal

NEEDED = [
    "AssetRegistryHelpers.get_asset_registry", "ARFilter", "TopLevelAssetPath",
    "AssetExportTask", "Exporter.run_asset_export_task", "FbxExportOption",
    "FbxExportCompatibility", "AnimSequenceExporterFBX",
    "SkeletalMeshExporterFBX", "ScopedSlowTask", "SystemLibrary.collect_garbage",
    "SystemLibrary.get_project_content_directory",
    "SystemLibrary.get_project_saved_directory",
    "SystemLibrary.get_engine_version", "SystemLibrary.get_game_name",
    "AnimationLibrary.get_sequence_length", "AnimationLibrary.get_num_frames",
    "AnimationLibrary.get_frame_rate", "AnimationLibrary.get_animation_track_names",
    "AnimationLibrary.get_animation_curve_names",
]


def resolve(path):
    o = unreal
    for part in path.split("."):
        o = getattr(o, part)
    return o


for n in NEEDED:
    try:
        resolve(n)
        unreal.log(f"[UALM-PROBE] OK      unreal.{n}")
    except Exception:  # noqa: BLE001
        unreal.log_warning(f"[UALM-PROBE] MISSING unreal.{n}")

ar = unreal.AssetRegistryHelpers.get_asset_registry()
flt = unreal.ARFilter(class_paths=[unreal.TopLevelAssetPath("/Script/Engine", "AnimSequence")],
                      package_paths=["/Game"], recursive_paths=True)
assets = ar.get_assets(flt)
unreal.log(f"[UALM-PROBE] AnimSequences under /Game: {len(assets)}")
if assets:
    a = assets[0].get_asset()
    unreal.log(f"[UALM-PROBE] sample: {a.get_path_name()}")
    for p in ("skeleton", "additive_anim_type", "enable_root_motion",
              "retarget_source", "target_frame_rate", "root_motion_root_lock"):
        try:
            unreal.log(f"[UALM-PROBE]   {p} = {a.get_editor_property(p)}")
        except Exception as e:  # noqa: BLE001
            unreal.log_warning(f"[UALM-PROBE]   {p}: unreadable ({e})")
