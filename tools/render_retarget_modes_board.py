"""Planche avant/après du retargeting : pour des actions RÉELLES de la bibliothèque locale (lecture seule), 3 images clés (25 / 50 / 75 %) rendues avec deux réglages d'IK : « bras + jambes » (ancien défaut) et « jambes seules ».

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/render_retarget_modes_board.py -- DOSSIER_DE_SORTIE --library DOSSIER [--size 300]

Sortie : `<action>_<mode>_<k>.png` (k = 0, 1, 2) et `actions.json` (noms choisis). Rendu Workbench du maillage déformé par le vrai rig, vue de trois quarts. Assemblage : `tools/assemble_retarget_modes_board.py`."""
import json
import math
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
ARGS = sys.argv[sys.argv.index("--") + 1:]
OUT = Path(ARGS[0])
OUT.mkdir(parents=True, exist_ok=True)
library = Path(ARGS[ARGS.index("--library") + 1]).glob("*.blend").__next__()
SIZE = int(ARGS[ARGS.index("--size") + 1]) if "--size" in ARGS else 300
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension.animation import mapping, retarget, retarget_bpy, skeleton  # noqa: E402

WANTED = [("marche", ("Walk_Fwd_Loop", "Walk_F_Loop", "Walk_Loop", "Walk_Fwd")), ("course", ("Run_Fwd_Loop", "Run_F_Loop", "Run_Loop", "Run_Fwd")), ("accroupi", ("Stand_to_Crouch",)),
          ("geste", ("gesture_come_on_in",)), ("bras_leves", ("ragdoll_reach_up",))]
addon.register()
for obj in list(bpy.data.objects):  # scène de démarrage : retire le cube par défaut
    bpy.data.objects.remove(obj, do_unlink=True)
bpy.ops.humanloom.create()
body = bpy.context.object
rig_object = skeleton.install(body)
target = retarget.rig_from_armature(rig_object)
target_map = mapping.from_armature(rig_object)
with bpy.data.libraries.load(str(library), link=False) as (names, _):
    armature_names, action_names = list(names.armatures), list(names.actions)
best = None
for name in armature_names:
    with bpy.data.libraries.load(str(library), link=False) as (_, wanted):
        wanted.armatures = [name]
    data = wanted.armatures[0]
    if len(data.bones) < 80:
        bpy.data.armatures.remove(data)
        continue
    pairs, report = mapping.auto_map(target_map, mapping.from_armature(data))
    score = (report.coverage, -len(report.low_confidence))
    if best is None or score > best[0]:
        best = (score, name, {t: p.source for t, p in pairs.items()})
    bpy.data.armatures.remove(data)
with bpy.data.libraries.load(str(library), link=False) as (_, wanted):
    wanted.armatures = [best[1]]
source = retarget.rig_from_armature(wanted.armatures[0])
links = best[2]

scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.render.resolution_x = scene.render.resolution_y = SIZE
scene.display.shading.light = "STUDIO"
scene.display.shading.color_type = "MATERIAL"
scene.display.shading.show_cavity = True
scene.world = bpy.data.worlds.new("w") if scene.world is None else scene.world
scene.world.color = (1, 1, 1)
camera_data = bpy.data.cameras.new("cam")
camera_data.type = "ORTHO"
camera_data.ortho_scale = 2.3
camera = bpy.data.objects.new("cam", camera_data)
scene.collection.objects.link(camera)
scene.camera = camera
for pose_bone in rig_object.pose.bones:
    pose_bone.rotation_mode = "QUATERNION"
order = {pb.name: i for i, pb in enumerate(rig_object.pose.bones)}
index = {n: i for i, n in enumerate(target.names)}
chosen = {}
MODES = {"bras_jambes": ("arm", "leg"), "jambes": ("leg",)}
for label, keys in WANTED:
    action_name = next((a for key in keys for a in action_names if key in a and "Rfoot" not in a and "Lfoot" not in a), None) or next((a for key in keys for a in action_names if key in a), None)
    if action_name is None:
        continue
    chosen[label] = action_name
    with bpy.data.libraries.load(str(library), link=False) as (_, wanted):
        wanted.actions = [action_name]
    action = wanted.actions[0]
    motion, _first = retarget_bpy.read_action(action, source)
    bpy.data.actions.remove(action)
    for mode_label, limbs in MODES.items():
        result = retarget.retarget(source, target, links, motion, retarget.Options(pose_mode=retarget.ABSOLUTE_IK, ik_limbs=limbs, root_motion=retarget.IN_PLACE))
        for k, fraction in enumerate((0.25, 0.5, 0.75)):
            frame = int(fraction * (motion.frames - 1))
            for pose_bone in rig_object.pose.bones:
                i = index[pose_bone.name]
                pose_bone.rotation_quaternion = result.quat[frame, i]
                if pose_bone.name in ("pelvis", "root"):
                    pose_bone.location = result.loc[frame, i]
            bpy.context.view_layer.update()
            pelvis = rig_object.matrix_world @ rig_object.pose.bones["pelvis"].head
            a = math.radians(35)
            camera.location = Vector((pelvis.x + 5 * math.sin(a), pelvis.y - 5 * math.cos(a), 0.9))
            camera.rotation_euler = (math.radians(90), 0.0, a)
            scene.render.filepath = str(OUT / f"{label}_{mode_label}_{k}.png")
            bpy.ops.render.render(write_still=True)
(OUT / "actions.json").write_text(json.dumps(chosen, indent=1, ensure_ascii=False), encoding="utf-8")
print("RETARGET_PLANCHE", chosen)
