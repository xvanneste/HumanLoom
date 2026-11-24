"""Mesures préalables de la simulation de tissu (lot V4, avant toute implémentation) : stabilité, pénétration, coût par image, reproductibilité, cache.

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/measure_cloth.py -- [--out FICHIER.json] [--frames 60] [--quality 5] [--offset 30] [--piece veste]

Montage mesuré (conforme au manuel 5.2, « Cloth on Armature ») : vêtement procédural (V1) à un décalage AMPLE (par défaut 30 mm) ; modificateur Cloth placé APRÈS l'Armature ; groupe de sommets d'épinglage sur les épaules ;
le corps reçoit un modificateur Collision APRÈS son Armature ; animation synthétique du bras gauche et de la colonne. Mesures : (1) stabilité : plus grand déplacement d'un sommet entre deux images et absence de valeurs non finies ;
(2) pénétration du tissu dans le corps animé (part des sommets à plus de 1 mm à l'intérieur, profondeur maximale) ; (3) coût moyen par image ; (4) reproductibilité : deux passages depuis la première image donnent-ils les mêmes
positions ? ; (5) bake : durée, taille du cache, rejouabilité après enregistrement et réouverture du .blend (cache dans le fichier)."""
import json
from pathlib import Path
import sys
import tempfile
import time

import bpy
import numpy as np
from mathutils import Euler, Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension import garments  # noqa: E402
from extension.animation import skeleton  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:]
OUT = ARGS[ARGS.index("--out") + 1] if "--out" in ARGS else None
FRAMES = int(ARGS[ARGS.index("--frames") + 1]) if "--frames" in ARGS else 60
QUALITY = int(ARGS[ARGS.index("--quality") + 1]) if "--quality" in ARGS else 5
OFFSET = float(ARGS[ARGS.index("--offset") + 1]) if "--offset" in ARGS else 30.0
PIECE = ARGS[ARGS.index("--piece") + 1] if "--piece" in ARGS else "veste"
SELF = "--self" in ARGS
DISTANCE = float(ARGS[ARGS.index("--distance") + 1]) if "--distance" in ARGS else 0.004
COLLISION_QUALITY = int(ARGS[ARGS.index("--collision-quality") + 1]) if "--collision-quality" in ARGS else 2

addon.register()
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
bpy.ops.humanloom.create()
body = bpy.context.object
rig = skeleton.install(body)
body.modifiers["Human Modeling · Surface"].show_viewport = False
scene = bpy.context.scene
scene.frame_start, scene.frame_end = 1, FRAMES
scene.render.fps = 24

# animation synthétique du squelette : bras gauche levé puis rabaissé, torsion de la colonne
rig.animation_data_create()
for pb in rig.pose.bones:
    pb.rotation_mode = "XYZ"
for frame, (arm, spine) in {1: (0.0, 0.0), FRAMES // 2: (-80.0, 25.0), FRAMES: (0.0, 0.0)}.items():
    rig.pose.bones["arm_upper.L"].rotation_euler = Euler((0.0, 0.0, np.radians(arm)))
    rig.pose.bones["spine.03"].rotation_euler = Euler((0.0, np.radians(spine), 0.0))
    rig.pose.bones["arm_upper.L"].keyframe_insert("rotation_euler", frame=frame)
    rig.pose.bones["spine.03"].keyframe_insert("rotation_euler", frame=frame)

# vêtement ample + épinglage
piece = garments.add_garment(body, PIECE, offset_mm=OFFSET)
points = np.array([v.co[:] for v in piece.data.vertices])
top = points[:, 2].max()
pin = piece.vertex_groups.new(name="Epinglage")
pinned = [i for i, p in enumerate(points) if p[2] > top - 0.06 and abs(p[0]) < 0.30]  # épaules et haut du dos
pin.add(pinned, 1.0, "REPLACE")
for name in ("Epaisseur", "Degagement"):
    if name in piece.modifiers:
        piece.modifiers.remove(piece.modifiers[name])
cloth = piece.modifiers.new("Cloth", "CLOTH")
settings = cloth.settings
settings.quality = QUALITY
settings.vertex_group_mass = "Epinglage"
settings.mass = 0.3
settings.tension_stiffness = settings.compression_stiffness = settings.shear_stiffness = 15.0
settings.bending_stiffness = 0.5
settings.air_damping = 1.0
cloth.collision_settings.use_collision = True
cloth.collision_settings.distance_min = DISTANCE
cloth.collision_settings.collision_quality = COLLISION_QUALITY
cloth.collision_settings.use_self_collision = SELF
cloth.point_cache.frame_start, cloth.point_cache.frame_end = 1, FRAMES
body.modifiers.new("Collision", "COLLISION")
body.collision.thickness_outer = 0.002

result = {"piece": PIECE, "decalage_mm": OFFSET, "sommets": len(points), "epingles": len(pinned), "images": FRAMES, "qualite": QUALITY, "qualite_collision": COLLISION_QUALITY, "auto_collision": SELF, "distance_collision_m": DISTANCE}


def evaluated_positions(obj):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    out = np.array([(obj.matrix_world @ v.co)[:] for v in mesh.vertices])
    evaluated.to_mesh_clear()
    return out


def posed_body_tree():
    evaluated = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    mesh.calc_loop_triangles()
    tree = BVHTree.FromPolygons([body.matrix_world @ v.co for v in mesh.vertices], [t.vertices[:] for t in mesh.loop_triangles])
    evaluated.to_mesh_clear()
    return tree


def run_pass():
    """Simule de la première à la dernière image (séquentiellement) ; retourne positions (F, N, 3), durées (ms), pénétrations."""
    scene.frame_set(1)
    bpy.context.view_layer.update()
    positions, times, penetration = [], [], []
    for f in range(1, FRAMES + 1):
        start = time.perf_counter()
        scene.frame_set(f)
        bpy.context.view_layer.update()
        p = evaluated_positions(piece)
        times.append((time.perf_counter() - start) * 1000.0)
        positions.append(p)
        if f % 5 == 0:
            tree = posed_body_tree()
            inside = [(c, tree.find_nearest(Vector(c))) for c in p]
            depths = [r[3] for c, r in inside if r[0] is not None and (Vector(c) - r[0]).dot(r[1]) < 0 and r[3] > 0.001]
            penetration.append((len(depths) / len(p), max(depths, default=0.0)))
    return np.array(positions), times, penetration


positions, times, penetration = run_pass()
steps = np.linalg.norm(np.diff(positions, axis=0), axis=-1)
result["stabilite"] = {"valeurs_non_finies": bool(not np.isfinite(positions).all()), "deplacement_max_par_image_m": round(float(steps.max()), 4), "deplacement_p99_par_image_m": round(float(np.percentile(steps, 99)), 4),
                       "etendue_max_m": round(float(np.abs(positions).max()), 2), "explosion": bool(steps.max() > 0.5 or not np.isfinite(positions).all())}
result["penetration"] = {"part_max_pourcent": round(max(p[0] for p in penetration) * 100, 2), "profondeur_max_mm": round(max(p[1] for p in penetration) * 1000, 1), "part_moyenne_pourcent": round(float(np.mean([p[0] for p in penetration])) * 100, 2)}
result["cout_par_image_ms"] = {"moyenne": round(float(np.mean(times[1:])), 1), "mediane": round(float(np.median(times[1:])), 1), "max": round(float(np.max(times[1:])), 1), "premiere_image": round(times[0], 1)}

# reproductibilité : deuxième passage depuis la première image (cache libéré)
bpy.ops.ptcache.free_bake_all() if False else None
cloth.point_cache.frame_start = 1
scene.frame_set(1)
positions_two, _, _ = run_pass()
result["reproductibilite"] = {"ecart_max_m_entre_deux_passages": float(np.abs(positions - positions_two).max()), "identique_bit_a_bit": bool(np.array_equal(positions, positions_two))}

# bake et cache dans le .blend
start = time.perf_counter()
override = {"scene": scene, "active_object": piece, "point_cache": cloth.point_cache}
try:
    with bpy.context.temp_override(**override):
        bpy.ops.ptcache.free_bake()
        bpy.ops.ptcache.bake(bake=True)
    baked = cloth.point_cache.is_baked
except Exception as error:  # noqa: BLE001
    baked, error_text = False, str(error)[:200]
    result["bake_erreur"] = error_text
bake_s = time.perf_counter() - start
result["bake"] = {"duree_s": round(bake_s, 1), "cache_cuit": bool(baked)}
if baked:
    path = Path(tempfile.mkdtemp(prefix="hl_cloth_")) / "tissu.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(path), compress=True)
    result["bake"]["taille_blend_mo"] = round(path.stat().st_size / 2 ** 20, 2)
    reference = {f: None for f in (10, FRAMES // 2, FRAMES)}
    for f in reference:
        scene.frame_set(f)
        bpy.context.view_layer.update()
        reference[f] = evaluated_positions(piece)
    piece_name, body_name = piece.name, body.name
    bpy.ops.wm.open_mainfile(filepath=str(path))
    piece = bpy.data.objects[piece_name]
    body = bpy.data.objects[body_name]
    scene = bpy.context.scene
    start = time.perf_counter()
    gaps = {}
    for f in reference:
        scene.frame_set(f)
        bpy.context.view_layer.update()
        gaps[f] = float(np.abs(evaluated_positions(piece) - reference[f]).max())
    result["bake"]["relecture_apres_reouverture"] = {"ecart_max_m": max(gaps.values()), "duree_s": round(time.perf_counter() - start, 2), "images_comparees": list(gaps)}

print("MESURE_TISSU", json.dumps(result, ensure_ascii=False))
if OUT:
    Path(OUT).write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding="utf-8")
