"""Planche de gros plan des yeux (lot paupières / I-49) : yeux ouverts (ouverture 0) et fermés (ouverture -1), de face et de trois quarts, sur 3 morphologies (rendu Workbench).

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/render_eyes_board.py -- DOSSIER_DE_SORTIE

Sortie : `yeux_<morphologie>_<ouverts|fermes>_<face|trois_quarts>.png`. La commande `eyelid_aperture` (-1 = fermé) est celle du corps natif ; les morphologies sont celles où des croisements apparaissaient
avant la couche de dépliage (femme jeune : 4 paires près d'un oeil ; homme âgé : 8 ; sexe 1 âge 3 : 4)."""
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension import human  # noqa: E402

OUT = Path(sys.argv[sys.argv.index("--") + 1])
OUT.mkdir(parents=True, exist_ok=True)
MORPHOLOGIES = {"femme_jeune": {"sex": 1.0, "age": 1.0}, "homme_age": {"sex": 0.0, "age": 3.0}, "femme_agee": {"sex": 1.0, "age": 3.0}}
addon.register()

for label, values in MORPHOLOGIES.items():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.ops.humanloom.create()
    body = bpy.context.object
    for name, value in values.items():
        human.set_value(body, name, value)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x, scene.render.resolution_y = 900, 450
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_cavity = True
    scene.world = bpy.data.worlds.new("w") if scene.world is None else scene.world
    scene.world.color = (1, 1, 1)
    from extension.animation import skeleton  # noqa: E402
    cage = skeleton.cage_points(body)
    top = cage[:, 2].max()
    eye_zone = cage[(cage[:, 2] > top - 0.15) & (cage[:, 2] < top - 0.105) & (cage[:, 1] < cage[cage[:, 2] > top - 0.15][:, 1].mean())]
    centre = np.array([0.0, float(eye_zone[:, 1].min()) + 0.02, float(top - 0.106)])  # niveau des yeux déduit de la cage (les objets-yeux ne suivent pas toujours la morphologie en mode headless)
    eyes = []
    camera_data = bpy.data.cameras.new("cam")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = 0.14
    camera = bpy.data.objects.new("cam", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    for state, aperture in (("ouverts", 0.0), ("fermes", -1.0)):
        human.set_value(body, "eyelid_aperture", aperture)
        bpy.context.view_layer.update()
        for view, direction in (("face", Vector((0, -1, 0.0))), ("trois_quarts", Vector((0.45, -0.89, 0.05)))):
            direction = direction.normalized()
            target = centre if view == "face" else centre + np.array([0.03, 0.0, 0.0])  # trois quarts : sur l'oeil du côté de la caméra
            camera.location = Vector(target.tolist()) + direction * 0.6
            camera.rotation_euler = (-direction).to_track_quat("-Z", "Y").to_euler()
            scene.render.filepath = str(OUT / f"yeux_{label}_{state}_{view}.png")
            bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(camera, do_unlink=True)
    print("PLANCHE", label)
