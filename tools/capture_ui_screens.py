"""Captures d'écran de l'interface de HumanLoom (panneaux Squelette, Mapping, Bibliothèque, Appliquer l'animation) dans une fenêtre Blender ISOLÉE (lot F0-d).

  blender --python-expr "import bpy; bpy.context.preferences.view.show_splash = False; bpy.ops.wm.save_userpref(); bpy.ops.wm.quit_blender()"   (une fois, pour un dossier de configuration neuf)
  blender --factory-startup --window-geometry 0 0 1500 1800 --python tools/capture_ui_screens.py -- DOSSIER_DE_SORTIE

À lancer avec un dossier de configuration dédié (`BLENDER_USER_RESOURCES=<dossier temporaire>`) : ni la session ni la configuration de l'utilisateur ne sont touchées. Une fenêtre
s'ouvre quelques secondes puis se ferme toute seule. Les panneaux sont dépliés pour la capture (leur état par défaut est replié). Bibliothèque de démonstration : fabriquée ici (noms inventés).
"""
import json
from pathlib import Path
import sys
import tempfile

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(sys.argv[sys.argv.index("--") + 1])
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension.animation import importer, mapping_ui, retarget, retarget_bpy, retarget_ui, rig_ui, skeleton, ui  # noqa: E402

for module in (ui, rig_ui, mapping_ui, retarget_ui):  # panneaux dépliés pour la capture
    for cls in module.CLASSES:
        if hasattr(cls, "bl_options") and issubclass(cls, bpy.types.Panel):
            cls.bl_options = set()
addon.register()
bpy.context.preferences.view.ui_scale = 1.0

# scène de démonstration
bpy.ops.humanloom.create()
body = bpy.context.object
rig = skeleton.install(body)
work = Path(tempfile.mkdtemp(prefix="hl_shots_"))
target = retarget.rig_from_armature(rig)
frames = 30
quat = np.zeros((frames, len(target.names), 4))
quat[..., 0] = 1
loc = np.zeros((frames, len(target.names), 3))
library = work / "bibliotheque"
library.mkdir()
entries = {}
names = ["Marche_Avant_01", "Marche_Arriere_01", "Course_Debut", "Course_Boucle", "Saut_Debut", "Saut_Reception", "Repos_Boucle", "Accroupi_Repos", "Salut_Main", "Geste_Assis"]
arm_copy = rig.data.copy()
arm_copy.name = "armature_source_demo"
saved = []
for number, name in enumerate(names):
    for f in range(frames):
        angle = np.radians(20 + 4 * number) * np.sin(2 * np.pi * f / frames)
        quat[f, target.index["arm_upper.L"]] = [np.cos(angle / 2), np.sin(angle / 2), 0, 0]
        quat[f, target.index["leg_upper.R"]] = [np.cos(angle / 2), np.sin(angle / 2), 0, 0]
    action = retarget_bpy.write_action(rig, retarget.Result(quat.copy(), loc, {"noms_cibles": list(target.names)}), f"Demo__{name}", first_frame=1)
    saved.append(action)
    folder = "Animations/" + name.split("_")[0]
    entries[f"/Demo/{name}"] = {"id": f"/Demo/{name}", "name": name, "action": f"Demo__{name}", "folder": folder, "skeleton": "Demo", "frame_rate": 30.0, "length": 1.0, "num_frames": frames,
                                "root_motion": number % 2 == 0, "additive": "NONE", "flags": []}
bpy.data.libraries.write(str(library / "HumanLoom_Actions.blend"), set(saved) | {arm_copy}, fake_user=True)
(library / "inventory.json").write_text(json.dumps({"schema": 1, "generator": importer.GENERATOR, "animations": entries, "imported_sources": {}}), encoding="utf-8")
ui.OVERRIDE.update(library_dir=str(library), cache_dir=str(work / "cache"))
wm = bpy.context.window_manager
bpy.ops.humanloom.animation_refresh()
source = rig.copy()
source.data = bpy.data.armatures["armature_source_demo"]
source.name = "armature_source_demo"
del source[skeleton.MARKER]
source.parent = None
bpy.context.scene.collection.objects.link(source)
source.hide_viewport = True
wm.hl_map_source = source
bpy.context.view_layer.objects.active = body
bpy.ops.humanloom.mapping_auto()
bpy.ops.humanloom.animation_favorite(entry_id="/Demo/Salut_Main")
wm.hl_anim_active = 2
bpy.ops.humanloom.animation_thumbnails()
if ui._state is not None and retarget_ui._state["thumb_thread"] is not None:
    retarget_ui._state["thumb_thread"].join(timeout=180)
retarget_ui.poll_thumbnails()

window = bpy.context.window_manager.windows[0]
area = next(a for a in window.screen.areas if a.type == "VIEW_3D")
space = area.spaces[0]
space.show_region_ui = True
region = next(r for r in area.regions if r.type == "UI")
PANELS = [("squelette", rig_ui.HUMANLOOM_PT_rig), ("mapping", mapping_ui.HUMANLOOM_PT_mapping), ("galerie", ui.HUMANLOOM_PT_animation_library), ("appliquer", retarget_ui.HUMANLOOM_PT_animation_apply)]
for _name, panel in PANELS:  # un seul panneau à la fois, dans l'onglet actif « Item » (fenêtre haute)
    bpy.utils.unregister_class(panel)
    panel.bl_category = "Item"
state = {"step": 0, "phase": 0}


def tick():
    index = state["step"]
    if index >= len(PANELS):
        bpy.ops.wm.quit_blender()
        return None
    name, panel = PANELS[index]
    if state["phase"] == 0:
        bpy.utils.register_class(panel)
        area.tag_redraw()
        state["phase"] = 1
        return 1.5
    with bpy.context.temp_override(window=window, area=area, region=region):
        bpy.ops.screen.screenshot_area(filepath=str(OUT / f"ui_{name}.png"))
    bpy.utils.unregister_class(panel)
    state["step"], state["phase"] = index + 1, 0
    return 0.5


bpy.app.timers.register(tick, first_interval=3.0)
