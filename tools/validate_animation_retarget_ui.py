"""Validation du lot A3 (interface) : appliquer une animation de la galerie au rig, de bout en bout, hors écran.

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/validate_animation_retarget_ui.py -- [--out FICHIER.json]

Bibliothèque de test fabriquée ici : un fichier .blend contenant UNE action (écrite pour un rig copie du nôtre) + un inventory.json. Source = copie de notre rig, donc le
mapping est l'identité. Vérifie : aperçu non destructif, fin d'aperçu, ajout au NLA, remplacement, cache (2e passe), refus sans mapping, dessin du panneau.
"""
import json
from pathlib import Path
import shutil
import sys
import tempfile
from unittest import mock

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = ARGS[ARGS.index("--out") + 1] if "--out" in ARGS else None
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension.animation import importer, retarget, retarget_bpy, retarget_ui, skeleton, ui  # noqa: E402

results, failures = {}, []


def check(name, ok, detail=None):
    results[name] = {"ok": bool(ok), "detail": detail}
    print(("OK  " if ok else "KO  ") + name, detail if detail is not None else "")
    if not ok:
        failures.append(name)


addon.register()
bpy.ops.humanloom.create()
body = bpy.context.object
rig = skeleton.install(body)
work = Path(tempfile.mkdtemp(prefix="hl_ret_ui_"))
try:
    target = retarget.rig_from_armature(rig)
    # action source : balancement des bras + avance du bassin, écrite pour notre rig puis rangée dans un fichier de bibliothèque
    frames = 30
    quat = np.zeros((frames, len(target.names), 4))
    quat[..., 0] = 1
    loc = np.zeros((frames, len(target.names), 3))
    for f in range(frames):
        angle = np.radians(40) * np.sin(2 * np.pi * f / frames)
        for name in ("arm_upper.L", "arm_upper.R"):
            quat[f, target.index[name]] = [np.cos(angle / 2), np.sin(angle / 2), 0, 0]
        loc[f, target.index["pelvis"]] = [0, -0.04 * f, 0]
    action = retarget_bpy.write_action(rig, retarget.Result(quat, loc, {"noms_cibles": list(target.names)}), "SourceTest__balancement", first_frame=1)
    library = work / "bibliotheque"
    library.mkdir()
    arm_copy = rig.data.copy()
    arm_copy.name = "armature_source_test"
    bpy.data.libraries.write(str(library / "HumanLoom_Actions.blend"), {action, arm_copy}, fake_user=True)
    bpy.data.actions.remove(action)
    entry = {"id": "/Test/balancement", "name": "balancement", "action": "SourceTest__balancement", "folder": "Animations/Test", "skeleton": "SourceTest", "frame_rate": 30.0, "length": 1.0, "num_frames": frames,
             "root_motion": True, "additive": "NONE", "flags": ["root_motion"]}
    (library / "inventory.json").write_text(json.dumps({"schema": 1, "generator": importer.GENERATOR, "animations": {entry["id"]: entry}, "imported_sources": {}}), encoding="utf-8")
    ui.OVERRIDE.update(library_dir=str(library), cache_dir=str(work / "cache"))
    wm = bpy.context.window_manager
    bpy.ops.humanloom.animation_refresh()
    wm.hl_anim_active = 0
    # source = copie de notre rig (sans marqueur) : le mapping automatique est l'identité
    source = rig.copy()
    source.data = bpy.data.armatures.get("armature_source_test") or rig.data.copy()
    source.name = "source_copie"
    del source[skeleton.MARKER]
    source.parent = None
    bpy.context.scene.collection.objects.link(source)
    bpy.context.view_layer.objects.active = body
    wm.hl_map_source = source
    try:
        bpy.ops.humanloom.animation_apply(action="PREVIEW")
        refused = False
    except RuntimeError:
        refused = True
    check("R1_refus_sans_mapping", refused)
    bpy.ops.humanloom.mapping_auto()
    mapped = sum(1 for r in wm.hl_map_rows if r.source)
    check("R2_mapping_identite", mapped >= 75, {"appariés": mapped})
    rig.pose.bones["hand.L"].rotation_mode = "QUATERNION"
    rig.pose.bones["hand.L"].rotation_quaternion = (0.9, 0.1, 0.2, 0.3)
    bpy.context.scene.frame_set(5)
    before = {b.name: (tuple(b.location), tuple(b.rotation_quaternion)) for b in rig.pose.bones}
    result = bpy.ops.humanloom.animation_apply(action="PREVIEW")
    first_message = retarget_ui._state["message"]
    bpy.context.scene.frame_set(15)
    bpy.context.view_layer.update()
    swing = abs(rig.pose.bones["arm_upper.L"].rotation_quaternion[1])
    check("R3_apercu", result == {"FINISHED"} and rig.animation_data.action is not None and rig.animation_data.action.name.endswith("@HumanLoom") and swing > 0.05 and "calcul" in first_message,
          {"action": rig.animation_data.action.name, "rotation_bras": round(float(swing), 3), "message": first_message})
    bpy.ops.humanloom.animation_apply(action="STOP")
    bpy.context.view_layer.update()
    after = {b.name: (tuple(b.location), tuple(b.rotation_quaternion)) for b in rig.pose.bones}
    check("R4_fin_d_apercu_restaure", before == after and bpy.context.scene.frame_current == 5 and (rig.animation_data is None or rig.animation_data.action is None), {"pose_restaurée": before == after})
    bpy.ops.humanloom.animation_apply(action="NLA")
    second_message = retarget_ui._state["message"]
    check("R5_nla_et_cache", len(rig.animation_data.nla_tracks) == 1 and "cache" in second_message, {"pistes": len(rig.animation_data.nla_tracks), "message": second_message})
    wm.hl_ret_root = retarget.IN_PLACE
    wm.hl_ret_pose = retarget.DELTA
    bpy.ops.humanloom.animation_apply(action="REPLACE")
    check("R6_remplacement_et_options", rig.animation_data.action is not None and "calcul" in retarget_ui._state["message"], retarget_ui._state["message"])
    # réglages : vitesse x2 et découpe
    wm.hl_ret_root, wm.hl_ret_pose = retarget.KEEP, retarget.ABSOLUTE
    wm.hl_ret_speed, wm.hl_ret_trim_start, wm.hl_ret_trim_end = 2.0, 4, 24
    bpy.ops.humanloom.animation_apply(action="REPLACE")
    shaped = rig.animation_data.action
    frame_count = int(round(shaped.frame_range[1] - shaped.frame_range[0])) + 1
    wm.hl_ret_speed, wm.hl_ret_trim_start, wm.hl_ret_trim_end = 1.0, 0, 0
    check("R9_reglages_vitesse_et_decoupe", frame_count == 11, {"images_après_découpe_4_24_et_vitesse_2": frame_count, "attendu": 11})
    # pagination et grille
    check("R10_pagination", wm.hl_anim_page == 0 and bpy.ops.humanloom.animation_page(delta=1) == {"FINISHED"} and wm.hl_anim_page == 0, {"page": wm.hl_anim_page, "résultats": len(wm.hl_anim_results)})
    # vignettes hors processus
    wm.hl_anim_active = 0
    result_thumbs = bpy.ops.humanloom.animation_thumbnails()
    thread = retarget_ui._state["thumb_thread"]
    if thread is not None:
        thread.join(timeout=180)
    retarget_ui.poll_thumbnails()
    from extension.animation import thumbnails as thumbs_module
    source_rig = retarget.rig_from_armature(wm.hl_map_source)
    revision = thumbs_module.library_revision(library / "HumanLoom_Actions.blend")
    scope = thumbs_module.scope_for(source_rig, revision)
    key = thumbs_module.key_for(entry["id"], entry["action"], scope)
    thumb_file = thumbs_module.thumb_path(work / "cache", key)
    check("R11_vignettes_hors_processus", result_thumbs == {"FINISHED"} and thumb_file.is_file() and thumb_file.stat().st_size > 200 and "1 générée" in retarget_ui._state["message"],
          {"fichier": thumb_file.name, "octets": thumb_file.stat().st_size if thumb_file.is_file() else 0, "message": retarget_ui._state["message"]})
    ui.preview_icon(key, work / "cache")  # en arrière-plan l'identifiant d'icône peut valoir 0 (pas de GPU) : on vérifie le chargement
    check("R12_icone_du_cache", ui._previews["collection"] is not None and key in ui._previews["collection"])
    # publication des favoris dans l'Asset Browser
    bpy.ops.humanloom.animation_favorite(entry_id=entry["id"])
    published = bpy.ops.humanloom.animation_publish_favorites()
    assets = [a for a in bpy.data.actions if a.asset_data is not None]
    check("R13_publication_des_favoris", published == {"FINISHED"} and len(assets) == 1 and assets[0].name.startswith("balancement@HumanLoom") and "Test" in {t.name for t in assets[0].asset_data.tags},
          {"assets": [a.name for a in assets], "étiquettes": [t.name for t in assets[0].asset_data.tags] if assets else None})
    layout = mock.MagicMock()
    retarget_ui.HUMANLOOM_PT_animation_apply.draw(mock.MagicMock(layout=layout), mock.MagicMock(window_manager=wm, active_object=body))
    check("R7_panneau", {"column", "operator", "row"} <= {c[0] for c in layout.method_calls})
finally:
    ui.OVERRIDE.clear()
    shutil.rmtree(work, ignore_errors=True)
addon.unregister()
check("R8_desenregistrement", not hasattr(bpy.types.WindowManager, "hl_ret_pose"))

if OUT:
    Path(OUT).write_text(json.dumps(results, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
print("RESULT", "FAIL " + ", ".join(failures) if failures else "PASS")
sys.exit(1 if failures else 0)
