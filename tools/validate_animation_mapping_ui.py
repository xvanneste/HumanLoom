"""Validation du lot A2b (interface) : opérateurs et panneau du mapping, hors écran.

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/validate_animation_mapping_ui.py -- [--out FICHIER.json]

Source : une armature de 17 os fabriquée ici (noms inventés, positions copiées de NOTRE rig). Vérifie : appariement automatique depuis l'interface,
édition manuelle d'une ligne, détection de conflit, enregistrement et rechargement d'un profil, profil périmé, dessin du panneau, désenregistrement.
"""
import json
from pathlib import Path
import shutil
import sys
import tempfile
from unittest import mock

import bpy

ROOT = Path(__file__).resolve().parents[1]
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = ARGS[ARGS.index("--out") + 1] if "--out" in ARGS else None
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension.animation import mapping, mapping_ui, skeleton, ui  # noqa: E402

results, failures = {}, []


def check(name, ok, detail=None):
    results[name] = {"ok": bool(ok), "detail": detail}
    print(("OK  " if ok else "KO  ") + name, detail if detail is not None else "")
    if not ok:
        failures.append(name)


addon.register()
bpy.ops.humanloom.create()
body = bpy.context.object
skeleton.install(body)
rig = skeleton.rigs_of(body)[0]
renames = {"pelvis": "Hips", "spine.01": "Spine", "spine.05": "Spine1", "head": "Head", "arm_upper": "Arm", "arm_lower": "ForeArm", "hand": "Hand", "leg_upper": "UpLeg", "leg_lower": "Leg", "foot": "Foot"}
truth = {}
bpy.ops.object.select_all(action="DESELECT")
data = bpy.data.armatures.new("source_inventee")
source = bpy.data.objects.new("source_inventee", data)
bpy.context.scene.collection.objects.link(source)
bpy.context.view_layer.objects.active = source
bpy.ops.object.mode_set(mode="EDIT")
made = {}
for bone in rig.data.bones:
    base = bone.name[:-2] if bone.name.endswith((".L", ".R")) else bone.name
    if base not in renames:
        continue
    new = {"L": "Left", "R": "Right"}.get(bone.name[-1] if bone.name.endswith((".L", ".R")) else "", "") + renames[base]
    edit = data.edit_bones.new("mixamorig:" + new)
    edit.head, edit.tail = bone.head_local, bone.tail_local
    made[bone.name] = edit
    truth[bone.name] = edit.name
for name, edit in made.items():
    parent = rig.data.bones[name].parent
    while parent is not None and parent.name not in made:
        parent = parent.parent
    edit.parent = made[parent.name] if parent else None
bpy.ops.object.mode_set(mode="OBJECT")
bpy.context.view_layer.objects.active = body
wm = bpy.context.window_manager
wm.hl_map_source = source

check("U1_enregistrement", hasattr(bpy.types.WindowManager, "hl_map_rows") and hasattr(bpy.ops.humanloom, "mapping_auto") and bpy.ops.humanloom.mapping_auto.poll(), "opérateurs enregistrés, poll vrai avec rig et source")
result = bpy.ops.humanloom.mapping_auto()
rows = {r.target: r for r in wm.hl_map_rows}
good = sum(1 for t, s in truth.items() if rows[t].source == s)
check("U2_appariement_automatique", result == {"FINISHED"} and len(rows) == len(rig.data.bones) == 80 and good == len(truth) == 16, {"lignes": len(rows), "corrects": f"{good}/{len(truth)}", "erreurs": [(t, rows[t].source, s) for t, s in truth.items() if rows[t].source != s], "sans_source": sum(1 for r in rows.values() if not r.source)})
rows["arm_lower.L"].source = rows["arm_upper.L"].source  # édition manuelle qui crée un conflit
conflict = mapping.duplicates({r.target: r.source for r in wm.hl_map_rows if r.source})
cache = Path(tempfile.mkdtemp(prefix="hl_map_ui_"))
try:
    ui.OVERRIDE.update(library_dir=str(cache), cache_dir=str(cache))
    try:
        bpy.ops.humanloom.mapping_save()
        refused = False
    except RuntimeError:  # l'opérateur signale l'erreur (self.report ERROR) : bpy la relève en exception
        refused = True
    rows["arm_lower.L"].source = truth["arm_lower.L"]
    bpy.ops.humanloom.mapping_clear_row(index=list(rows).index("toe.L"))
    check("U3_edition_et_conflit", list(conflict.values()) == [["arm_upper.L", "arm_lower.L"]] and refused and rows["toe.L"].method == "manuel", {"conflit": conflict, "enregistrement_refusé_avec_conflit": refused})
    saved = bpy.ops.humanloom.mapping_save() == {"FINISHED"}
    files = sorted((cache / "profiles").glob("*.json"))
    wm.hl_map_rows.clear()
    reload = bpy.ops.humanloom.mapping_load(filepath=str(files[0])) if files else {"CANCELLED"}
    reloaded = {r.target: r.source for r in wm.hl_map_rows if r.source}
    check("U4_profil_enregistre_et_recharge", saved and len(files) == 1 and reload == {"FINISHED"} and len(reloaded) == 16 and all(reloaded[t] == s for t, s in truth.items()), {"fichiers": [f.name for f in files], "rechargés": len(reloaded)})
    # source modifiée : un os renommé -> problème signalé, appariement ignoré pour cet os
    source.data.bones["mixamorig:Hips"].name = "mixamorig:HipsRenamed"
    bpy.ops.humanloom.mapping_load(filepath=str(files[0]))
    stale = {r.target: r.source for r in wm.hl_map_rows if r.source}
    check("U5_profil_perime", len(stale) == 15 and "pelvis" not in stale and any("absents" in p for p in mapping_ui._state["problems"]), mapping_ui._state["problems"])
    layout = mock.MagicMock()
    context = mock.MagicMock(window_manager=wm, active_object=body)
    bpy.context.view_layer.objects.active = body
    mapping_ui.HUMANLOOM_PT_mapping.draw(mock.MagicMock(layout=layout), context)
    names_drawn = {c[0] for c in layout.method_calls}
    check("U6_dessin_du_panneau", "template_list" in names_drawn and "operator" in names_drawn and "prop" in names_drawn, sorted(names_drawn))
finally:
    ui.OVERRIDE.clear()
    shutil.rmtree(cache, ignore_errors=True)
extension_unregistered = None
addon.unregister()
check("U7_desenregistrement", not hasattr(bpy.types.WindowManager, "hl_map_rows") and not hasattr(bpy.types, "HUMANLOOM_PT_mapping"))

if OUT:
    Path(OUT).write_text(json.dumps(results, indent=1, ensure_ascii=False), encoding="utf-8")
print("RESULT", "FAIL " + ", ".join(failures) if failures else "PASS")
sys.exit(1 if failures else 0)
