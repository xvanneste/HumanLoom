"""Validation du lot A1c : enregistrement et interface de la bibliothèque d'animations (extension/animation/ui.py), hors écran.

Exécution : blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/validate_animation_ui.py -- [--out FICHIER.json]
Bibliothèque de test fabriquée ici (noms inventés, aucun fichier tiers). Vérifie : enregistrement sans lecture de .blend, préférences,
actualisation, recherche, filtres, favoris persistants, correction de catégorie, dessin du panneau (mise en page simulée), import en fil
d'arrière-plan d'un fichier généré, désenregistrement propre.
"""
import json
from pathlib import Path
import shutil
import sys
import tempfile
import time
from unittest import mock

import bpy

ROOT = Path(__file__).resolve().parents[1]
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = ARGS[ARGS.index("--out") + 1] if "--out" in ARGS else None
sys.path.insert(0, str(ROOT))
import extension  # noqa: E402
from extension.animation import importer, ui  # noqa: E402

results, failures = {}, []


def check(name, ok, detail=None):
    results[name] = {"ok": bool(ok), "detail": detail}
    print(("OK  " if ok else "KO  ") + name, detail if detail is not None else "")
    if not ok:
        failures.append(name)


work = Path(tempfile.mkdtemp(prefix="hl_anim_ui_"))
try:
    # La règle « register() ne lit aucun .blend » est vérifiée en conditions réelles par tools/validate_install.py (bpy.data restreint au démarrage).
    extension.register()
    check("U1_enregistrement", all(hasattr(bpy.types.WindowManager, n) for n in ("hl_anim_query", "hl_anim_results")) and hasattr(bpy.ops.humanloom, "animation_refresh")
          and ui._state["index"] is None, {"index_chargé_au_démarrage": ui._state["index"] is not None})

    library, cache = work / "lib", work / "cache"
    library.mkdir()
    names = ["Walk_Fwd_01", "Walk_Bwd_01", "Run_Fwd_01", "Run_Start_Fwd", "Idle_Loop", "Idle_Look_Around", "Crouch_Idle", "Jump_Start", "Jump_Land", "Wave_Hand"]
    animations = {}
    for number, name in enumerate(names):
        folder = "Animations/" + name.split("_")[0]
        animations[f"/Test/{name}"] = {"id": f"/Test/{name}", "name": name, "folder": folder, "skeleton": "TestRig", "frame_rate": 30.0, "length": 1.0, "num_frames": 31,
                                        "root_motion": name.startswith(("Walk", "Run")), "additive": "NONE", "flags": [], "action": f"TestRig__{name}"}
    (library / "inventory.json").write_text(json.dumps({"schema": 1, "generator": importer.GENERATOR, "animations": animations, "imported_sources": {}}), encoding="utf-8")
    wm = bpy.context.window_manager

    ui.OVERRIDE.update(library_dir=str(library), cache_dir=str(cache))
    check("U2_refresh", bpy.ops.humanloom.animation_refresh() == {"FINISHED"} and len(wm.hl_anim_results) == 10 and ui._state["origin"] == "inventory", {"résultats": len(wm.hl_anim_results)})
    started = time.perf_counter()
    bpy.ops.humanloom.animation_refresh()
    again = time.perf_counter() - started
    check("U3_refresh_depuis_le_cache", ui._state["origin"] == "cache" and again < 1.0, {"origine": ui._state["origin"], "secondes": round(again, 3)})

    wm.hl_anim_query = "run fwd"
    names_found = sorted(i.name for i in wm.hl_anim_results)
    wm.hl_anim_query = "wal"
    walk = sorted(i.name for i in wm.hl_anim_results)
    wm.hl_anim_query = ""
    wm.hl_anim_category = "Idle"
    idle = sorted(i.name for i in wm.hl_anim_results)
    wm.hl_anim_category = ui.ALL
    check("U4_recherche_et_categorie", names_found == ["Run_Fwd_01", "Run_Start_Fwd"] and walk == ["Walk_Bwd_01", "Walk_Fwd_01"] and idle == ["Idle_Look_Around", "Idle_Loop"],
          {"run fwd": names_found, "wal": walk, "Idle": idle})

    target = next(i for i in wm.hl_anim_results if i.name == "Jump_Land").entry_id
    bpy.ops.humanloom.animation_favorite(entry_id=target)
    wm.hl_anim_favorites = True
    favorites = [i.name for i in wm.hl_anim_results]
    wm.hl_anim_favorites = False
    saved = json.loads((cache / "user.json").read_text(encoding="utf-8"))
    check("U5_favoris_persistants", favorites == ["Jump_Land"] and saved["favorites"] == [target], {"favoris": favorites})

    wm.hl_anim_active = next(n for n, i in enumerate(wm.hl_anim_results) if i.name == "Wave_Hand")
    bpy.ops.humanloom.animation_set_category(category="Gestes")
    saved = json.loads((cache / "user.json").read_text(encoding="utf-8"))
    categories = dict(ui._state["categories"])
    check("U6_categorie_corrigee", saved["categories"] == {"/Test/Wave_Hand": "Gestes"} and categories.get("Gestes") == 1 and categories.get("Wave") in (None, 0), categories)

    # Dessin du panneau avec une mise en page simulée : aucun plantage, pas de lecture de .blend.
    layout = mock.MagicMock()
    panel = ui.HUMANLOOM_PT_animation_library
    context = mock.MagicMock(window_manager=wm)
    context.preferences.addons.get.return_value = None
    with mock.patch.object(panel, "layout", layout, create=True):
        panel.draw(mock.MagicMock(layout=layout), context)
    drawn = [c[0] for c in layout.method_calls]
    check("U7_dessin_du_panneau", "grid_flow" in drawn and "operator" in drawn and "prop" in drawn, {"appels": sorted(set(drawn))})

    # Import en fil d'arrière-plan d'un glTF généré (processus Blender séparé), puis index mis à jour.
    bpy.ops.object.armature_add()
    arm = bpy.context.object
    arm.name = "UiRig"
    bpy.ops.object.mode_set(mode="POSE")
    arm.pose.bones[0].rotation_mode = "QUATERNION"
    for frame, w in ((1, 1.0), (31, 0.9)):
        arm.pose.bones[0].rotation_quaternion = (w, 0.3 * (1 - w) * 10, 0, 0)
        arm.pose.bones[0].keyframe_insert("rotation_quaternion", frame=frame)
    bpy.ops.object.mode_set(mode="OBJECT")
    glb = work / "Gestes" / "salut.glb"
    glb.parent.mkdir()
    bpy.ops.export_scene.gltf(filepath=str(glb), use_selection=True)
    # La bibliothèque de test porte notre marqueur : l'import y est accepté. Le fichier ajouté doit apparaître après la fin du fil.
    result = bpy.ops.humanloom.animation_import(filepath=str(glb), directory_mode=False)
    thread = ui._state["thread"]
    deadline = time.time() + 120
    while thread is not None and thread.is_alive() and time.time() < deadline:
        time.sleep(0.2)
    ui.poll_import()
    check("U8_import_en_arriere_plan", result == {"FINISHED"} and ui._state["thread"] is None and len(ui._state["index"]) == 11 and "1 ajoutée" in ui._state["import_message"],
          {"message": ui._state["import_message"], "entrées": len(ui._state["index"]) if ui._state["index"] else None})

    ui.OVERRIDE.update(library_dir="")
    check("U9_sans_bibliotheque", bpy.ops.humanloom.animation_refresh() == {"CANCELLED"} and ui._state["error"] and ui._state["index"] is None, ui._state["error"])
    ui.OVERRIDE.clear()
    extension.unregister()
    check("U10_desenregistrement", not hasattr(bpy.types.WindowManager, "hl_anim_query") and not hasattr(bpy.types, "HUMANLOOM_PT_animation_library"))
finally:
    shutil.rmtree(work, ignore_errors=True)

if OUT:
    Path(OUT).write_text(json.dumps(results, indent=1, ensure_ascii=False), encoding="utf-8")
print("RESULT", "FAIL " + ", ".join(failures) if failures else "PASS")
sys.exit(1 if failures else 0)
