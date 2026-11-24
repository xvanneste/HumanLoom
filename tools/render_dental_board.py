"""Planche ombrée des dents, gencives et langue (lot F0-f) : bouche ouverte à 20°, vue de face et de trois quarts, sur 3 morphologies (rendu Workbench, corps en fil de fer).

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/render_dental_board.py -- DOSSIER_DE_SORTIE [--angle 20]

Sortie : `dents_<morphologie>_face.png`, `_trois_quarts.png`, `_profil.png`. Couleurs = matériaux procéduraux de HumanLoom (email, gencive, langue) : valeurs de modélisation, pas des mesures."""
import math
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension import human  # noqa: E402
from extension.animation import dental, skeleton  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:]
OUT = Path(ARGS[0])
OUT.mkdir(parents=True, exist_ok=True)
ANGLE = float(ARGS[ARGS.index("--angle") + 1]) if "--angle" in ARGS else 20.0
MORPHOLOGIES = {"neutre": {}, "homme_age": {"sex": 0.0, "age": 3.0}, "femme_jeune": {"sex": 1.0, "age": 1.0}}
addon.register()

for label, values in MORPHOLOGIES.items():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.ops.humanloom.create()
    body = bpy.context.object
    for name, value in values.items():
        human.set_value(body, name, value)
    rig = skeleton.install(body)
    pose = rig.pose.bones[skeleton.JAW]
    pose.rotation_mode = "XYZ"
    best = None
    for sign in (1.0, -1.0):
        pose.rotation_euler = (sign * math.radians(ANGLE), 0, 0)
        bpy.context.view_layer.update()
        evaluated = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
        z = evaluated.to_mesh().vertices[skeleton.JAW_CHIN].co.z
        evaluated.to_mesh_clear()
        if best is None or z < best[0]:
            best = (z, sign)
    pose.rotation_euler = (best[1] * math.radians(ANGLE), 0, 0)
    if human.has_control(body, "mouth_open"):  # correctif d'ouverture (convergence des commissures, lèvre basse lissée) : proportionnel à l'angle, 1 à 30°
        human.set_value(body, "mouth_open", min(1.0, ANGLE / 30.0))
    bpy.context.view_layer.update()
    body.display_type = "WIRE"
    for modifier in body.modifiers:  # la cage seulement (le Subsurf alourdit le fil de fer)
        modifier.show_render = modifier.name in (human.MODIFIER_NAME, skeleton.MODIFIER_NAME, skeleton.DQS_MODIFIER)
    for eye in human.get_eyes(body) if hasattr(human, "get_eyes") else []:
        eye.hide_render = True
    parts = dental.parts_of(body)
    center = np.mean([np.array((p.matrix_world @ Vector(v)).to_tuple()) for p in parts for v in p.bound_box], axis=0)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = scene.render.resolution_y = 700
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_cavity = True
    scene.render.film_transparent = False
    scene.world = bpy.data.worlds.new("w") if scene.world is None else scene.world
    scene.world.color = (1, 1, 1)
    camera_data = bpy.data.cameras.new("cam")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = 0.13
    camera = bpy.data.objects.new("cam", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    for view, direction in (("face", Vector((0, -1, 0.0))), ("trois_quarts", Vector((0.7, -0.7, 0.45))), ("profil", Vector((1, 0, 0.0)))):
        direction = direction.normalized()
        camera.location = Vector(center.tolist()) + direction * 0.6
        camera.rotation_euler = (-direction).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = str(OUT / f"dents_{label}_{view}.png")
        bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(camera, do_unlink=True)
    print("PLANCHE", label, [p.name for p in parts])
