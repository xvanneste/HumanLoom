"""Unreal Engine 5.8 side, step 2: incremental FBX export driven by the
manifest. Only new / modified / previously failed animations are exported.
"""
import os
import time

import unreal

import ue_inventory as inv
from ue_inventory import core, log, warn

DEFAULT_OUT = None  # set at runtime: <Project>/Saved/BlenderExport


def default_output_dir():
    return os.path.join(unreal.SystemLibrary.get_project_saved_directory(),
                        "BlenderExport")


def make_fbx_options(mesh=False):
    """FbxExportOption tuned for Blender. Unknown option names are skipped
    with a warning so a renamed property never aborts the whole export."""
    o = unreal.FbxExportOption()
    wanted = {
        "ascii": False,
        "collision": False,
        "export_local_time": True,        # animation time starts at 0
        "export_morph_targets": mesh,
        "export_preview_mesh": False,     # skeleton + anim only (no mesh)
        "level_of_detail": False,
        "map_skeletal_motion_to_root": False,   # keep bone hierarchy intact
        "vertex_color": mesh,
        "force_front_x_axis": False,
    }
    for k, v in wanted.items():
        try:
            o.set_editor_property(k, v)
        except Exception as e:  # noqa: BLE001
            warn(f"FbxExportOption.{k} not settable: {e}")
    try:
        o.set_editor_property("fbx_export_compatibility",
                              unreal.FbxExportCompatibility.FBX_2020)
    except Exception as e:  # noqa: BLE001
        warn(f"fbx_export_compatibility not settable: {e}")
    return o


def _run_export(obj, filename, exporter, options):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    t = unreal.AssetExportTask()
    t.object = obj
    t.filename = filename
    t.automated = True
    t.prompt = False
    t.replace_identical = True
    t.exporter = exporter
    t.options = options
    ok = unreal.Exporter.run_asset_export_task(t)
    return bool(ok)


def anim_rel_path(entry):
    parts = [entry["skeleton"], *[core.sanitize(p) for p in
                                  entry["folder"].split("/") if p],
             core.sanitize(entry["name"]) + ".fbx"]
    return "animations/" + "/".join(parts)


def mesh_rel_path(char):
    return f"characters/{char['skeleton']}/{core.sanitize(char['name'])}.fbx"


def _needs_export(new, old, root, force):
    if force or old is None:
        return True
    if old.get("status") != core.ST_OK:
        return True
    if core.anim_fingerprint(old) != core.anim_fingerprint(new):
        return True
    f = old.get("file")
    if not f or core.check_fbx(os.path.join(root, f)):
        return True
    return False


def export_all(out_dir=None, roots=("/Game",), force=False, include_meshes=True,
               analyze_only=False, only_skeleton=None, name_filter=None,
               batch_size=100, progress=True):
    out_dir = os.path.abspath(out_dir or default_output_dir())
    os.makedirs(out_dir, exist_ok=True)
    old = None
    try:
        old = core.load_manifest(out_dir)
        log(f"Existing manifest found ({len(old['animations'])} animations)")
    except FileNotFoundError:
        log("No previous manifest: full export")
    except Exception as e:  # noqa: BLE001
        warn(f"Previous manifest unreadable ({e}); full export")

    man = inv.build_inventory(roots, include_meshes, progress=progress)
    summary = man["inventory_summary"]
    log(f"DETECTED: {summary['animations']} animations, "
        f"{summary['skeletons']} skeletons, {summary['characters']} meshes "
        f"(additive {summary['additive']}, retargeted {summary['retargeted']}, "
        f"control-rig dependent {summary['control_rig_dependent']})")
    core.atomic_write_json(os.path.join(out_dir, "inventory.json"), man)
    if analyze_only:
        return {"manifest": man, "report": None}

    old_a = (old or {}).get("animations", {})
    old_c = (old or {}).get("characters", {})
    todo_a, todo_c = [], []
    report_unchanged = 0
    for aid, e in man["animations"].items():
        if e.get("status") == core.ST_FAILED:      # analysis failure
            continue
        if only_skeleton and e["skeleton"] != only_skeleton:
            continue
        if name_filter and name_filter.lower() not in aid.lower():
            continue
        if _needs_export(e, old_a.get(aid), out_dir, force):
            todo_a.append(aid)
        else:                                    # carry over previous result
            report_unchanged += 1
            for k in ("file", "fbx_sha1", "fbx_size", "status", "error"):
                if k in old_a[aid]:
                    e[k] = old_a[aid][k]
    for cid, c in man["characters"].items():
        o = old_c.get(cid)
        if only_skeleton and c["skeleton"] != only_skeleton:
            continue
        ok_prev = (o and o.get("status") == core.ST_OK
                   and o.get("source_hash") == c.get("source_hash")
                   and c.get("source_hash")
                   and not core.check_fbx(os.path.join(out_dir, o.get("file", "x"))))
        if force or not ok_prev:
            todo_c.append(cid)
        else:
            c.update({k: o[k] for k in ("file", "fbx_sha1", "status") if k in o})

    report = {"started": core.now_iso(), "out_dir": out_dir, "force": force,
              "new_or_changed": len(todo_a), "skipped_unchanged": 0, "exported": 0,
              "failed": [], "meshes_exported": 0, "mesh_failed": [],
              "removed_from_unreal": sorted(set(old_a) - set(man["animations"]))}
    report["skipped_unchanged"] = report_unchanged
    total = len(todo_a) + len(todo_c)
    log(f"To export: {len(todo_a)} animations, {len(todo_c)} meshes "
        f"(skipping {report_unchanged} already exported/unchanged; "
        f"{len(man['animations']) - len(todo_a) - report_unchanged} outside filter)")

    anim_exp = unreal.AnimSequenceExporterFBX()
    mesh_exp = unreal.SkeletalMeshExporterFBX()
    a_opt, m_opt = make_fbx_options(False), make_fbx_options(True)
    t0 = time.time()
    task = unreal.ScopedSlowTask(max(total, 1), "UALM: exporting FBX")
    if progress:
        task.make_dialog(True)
    done = 0
    with task:
        # characters first: they define the reference armatures
        for cid in todo_c:
            if progress and task.should_cancel():
                break
            c = man["characters"][cid]
            if progress:
                task.enter_progress_frame(1, f"mesh {c['name']}")
            rel = mesh_rel_path(c)
            try:
                obj = unreal.load_asset(c["asset_path"])
                if not obj:
                    raise RuntimeError("load_asset returned None")
                if not _run_export(obj, os.path.join(out_dir, rel), mesh_exp, m_opt):
                    raise RuntimeError("exporter returned False")
                err = core.check_fbx(os.path.join(out_dir, rel))
                if err:
                    raise RuntimeError(err)
                c.update(file=rel, status=core.ST_OK,
                         fbx_sha1=core.sha1_file(os.path.join(out_dir, rel)))
                report["meshes_exported"] += 1
            except Exception as e:  # noqa: BLE001 - continue on error
                c.update(status=core.ST_FAILED, error=str(e))
                report["mesh_failed"].append({"id": cid, "error": str(e)})
                warn(f"mesh export failed {cid}: {e}")

        for aid in todo_a:
            if progress and task.should_cancel():
                warn("Export cancelled; manifest saved, re-run to resume")
                break
            e = man["animations"][aid]
            if progress:
                task.enter_progress_frame(1, f"{done + 1}/{len(todo_a)} {e['name']}")
            rel = anim_rel_path(e)
            path = os.path.join(out_dir, rel)
            try:
                obj = unreal.load_asset(aid)
                if not obj:
                    raise RuntimeError("load_asset returned None")
                if not _run_export(obj, path, anim_exp, a_opt):
                    raise RuntimeError("exporter returned False")
                err = core.check_fbx(path)
                if err:
                    raise RuntimeError(err)
                e.update(file=rel, status=core.ST_OK, fbx_size=os.path.getsize(path),
                         fbx_sha1=core.sha1_file(path))
                e.pop("error", None)
                report["exported"] += 1
            except Exception as ex:  # noqa: BLE001 - continue on error
                e.update(status=core.ST_FAILED, error=str(ex))
                report["failed"].append({"id": aid, "error": str(ex)})
                warn(f"export failed {aid}: {ex}")
            done += 1
            if done % batch_size == 0:         # checkpoint + free memory
                _merge_pending(man, old)
                core.save_manifest(man, out_dir)
                unreal.SystemLibrary.collect_garbage()
                log(f"checkpoint {done}/{len(todo_a)} "
                    f"({done / max(time.time() - t0, 1e-6):.1f} anim/s)")

    _merge_pending(man, old)
    report["finished"] = core.now_iso()
    report["seconds"] = round(time.time() - t0, 1)
    core.save_manifest(man, out_dir)
    core.atomic_write_json(os.path.join(out_dir, "export_report.json"), report)
    log(f"DONE in {report['seconds']}s: exported {report['exported']}, "
        f"failed {len(report['failed'])}, unchanged {report['skipped_unchanged']}, "
        f"meshes {report['meshes_exported']} (failed {len(report['mesh_failed'])}). "
        f"Manifest: {os.path.join(out_dir, core.MANIFEST_NAME)}")
    return {"manifest": man, "report": report}


def _merge_pending(man, old):
    """Animations not yet processed (interrupted run) keep their previous
    exported state if any, so a resume never loses information."""
    if not old:
        return
    for aid, e in man["animations"].items():
        if e.get("status") == core.ST_PENDING and aid in old["animations"]:
            o = old["animations"][aid]
            if o.get("status") == core.ST_OK:
                # keep the OLD fingerprint inputs so it is detected as modified
                for k in ("source_hash", "file", "fbx_sha1", "fbx_size", "status",
                          "export_settings"):
                    if k in o:
                        e[k] = o[k]
