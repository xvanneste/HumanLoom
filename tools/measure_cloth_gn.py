"""Mesures préalables (lot V4) du tissu NATIF de Blender 5.2 « Cloth Dynamics (Experimental) » (groupe de nœuds géométriques + solveur XPBD, modificateur « Collider ») : même scénario que `measure_cloth.py`.

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/measure_cloth_gn.py -- [--out FICHIER.json] [--frames 40] [--offset 30] [--substeps 5] [--constraint-steps 15] [--piece veste]

Montage : vêtement procédural (V1) à décalage ample ; groupe de nœuds « Cloth Dynamics (Experimental) » du fichier d'assets fourni avec Blender (`geometry_nodes_dynamics_assets.blend`), rendu local ; entrées : groupe d'épinglage, pas de
sous-étapes, étapes de contraintes, collection d'effecteurs ; le corps porte un modificateur « Collider » placé APRÈS son Armature. Mesures : stabilité, pénétration dans le corps animé, coût par image, reproductibilité,
rejouabilité après enregistrement/réouverture."""
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
FRAMES = int(ARGS[ARGS.index("--frames") + 1]) if "--frames" in ARGS else 40
OFFSET = float(ARGS[ARGS.index("--offset") + 1]) if "--offset" in ARGS else 30.0
SUBSTEPS = int(ARGS[ARGS.index("--substeps") + 1]) if "--substeps" in ARGS else 5
STEPS = int(ARGS[ARGS.index("--constraint-steps") + 1]) if "--constraint-steps" in ARGS else 15
PIECE = ARGS[ARGS.index("--piece") + 1] if "--piece" in ARGS else "veste"
RADIUS = float(ARGS[ARGS.index("--radius") + 1]) if "--radius" in ARGS else 0.01

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
rig.animation_data_create()
for pb in rig.pose.bones:
    pb.rotation_mode = "XYZ"
best = {}
for sign in (1.0, -1.0):  # sens de rotation Z qui LÈVE le bras gauche (la main monte) : mesuré
    rig.pose.bones["arm_upper.L"].rotation_euler = Euler((0.0, 0.0, sign * np.radians(60)))
    bpy.context.view_layer.update()
    best[sign] = float((rig.matrix_world @ rig.pose.bones["hand.L"].head).z)
RAISE = 1.0 if best[1.0] > best[-1.0] else -1.0
rig.pose.bones["arm_upper.L"].rotation_euler = (0.0, 0.0, 0.0)
for frame, (arm, spine) in {1: (0.0, 0.0), FRAMES // 2: (80.0 * RAISE, 25.0), FRAMES: (0.0, 0.0)}.items():
    rig.pose.bones["arm_upper.L"].rotation_euler = Euler((0.0, 0.0, np.radians(arm)))
    rig.pose.bones["spine.03"].rotation_euler = Euler((0.0, np.radians(spine), 0.0))
    rig.pose.bones["arm_upper.L"].keyframe_insert("rotation_euler", frame=frame)
    rig.pose.bones["spine.03"].keyframe_insert("rotation_euler", frame=frame)

piece = garments.add_garment(body, PIECE, offset_mm=OFFSET)
points = np.array([v.co[:] for v in piece.data.vertices])
top = points[:, 2].max()
pin = piece.vertex_groups.new(name="Epinglage")
pinned = [i for i, p in enumerate(points) if p[2] > top - 0.06 and abs(p[0]) < 0.30]
pin.add(pinned, 1.0, "REPLACE")
for name in ("Epaisseur", "Degagement"):
    if name in piece.modifiers:
        piece.modifiers.remove(piece.modifiers[name])

path = Path(bpy.utils.system_resource("DATAFILES")) / "assets/nodes/geometry_nodes_dynamics_assets.blend"
with bpy.data.libraries.load(str(path), link=False) as (source, target):
    target.node_groups = ["Cloth Dynamics (Experimental)", "Collider"]
cloth_group, collider_group = target.node_groups

# collider : le corps, APRÈS l'Armature (la géométrie utilisée est celle présente à ce point de la pile)
collider = body.modifiers.new("Collider", "NODES")
collider.node_group = collider_group
deforming_id = next(i.identifier for i in collider_group.interface.items_tree if i.item_type == "SOCKET" and i.in_out == "INPUT" and i.name == "Deforming")
if "--no-deforming" not in ARGS:
    getattr(collider.properties.inputs, deforming_id).value = True  # corps animé : indispensable (sinon le tissu traverse le corps qui bouge)
colliders = bpy.data.collections.new("Colliders")
scene.collection.children.link(colliders)
# le corps reste dans sa collection de scène ; une collection d'effecteurs peut contenir le même objet
colliders.objects.link(body)

cloth = piece.modifiers.new("Tissu", "NODES")
cloth.node_group = cloth_group
inputs = {i.name: i for i in cloth_group.interface.items_tree if i.item_type == "SOCKET" and i.in_out == "INPUT"}
def set_input(name, value):
    setattr(getattr(cloth.properties.inputs, inputs[name].identifier), "value", value)


set_input("Substeps", SUBSTEPS)
set_input("Constraint Steps", STEPS)
set_input("Collision Radius", RADIUS)
set_input("Effectors Collection", colliders)
pin_input = getattr(cloth.properties.inputs, inputs["Pin Group"].identifier)
pin_input.attribute_name = "Epinglage"  # champ alimenté par le groupe de sommets


result = {"deformant": "--no-deforming" not in ARGS, "piece": PIECE, "decalage_mm": OFFSET, "sommets": len(points), "epingles": len(pinned), "images": FRAMES, "pas": SUBSTEPS, "etapes_de_contraintes": STEPS, "rayon_collision_m": RADIUS}


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
            depths = []
            for c in p:
                r = tree.find_nearest(Vector(c))
                if r[0] is not None and (Vector(c) - r[0]).dot(r[1]) < 0 and r[3] > 0.001:
                    depths.append(r[3])
            penetration.append((len(depths) / len(p), max(depths, default=0.0)))
    return np.array(positions), times, penetration


positions, times, penetration = run_pass()
if len(positions) != FRAMES or positions.shape[1] != len(points):
    result["alerte"] = f"nombre de sommets évalués {positions.shape[1]} (entrée {len(points)})"
steps = np.linalg.norm(np.diff(positions, axis=0), axis=-1)
result["stabilite"] = {"valeurs_non_finies": bool(not np.isfinite(positions).all()), "deplacement_max_par_image_m": round(float(steps.max()), 4), "deplacement_p99_par_image_m": round(float(np.percentile(steps, 99)), 4),
                       "etendue_max_m": round(float(np.abs(positions).max()), 2), "explosion": bool(steps.max() > 0.5 or not np.isfinite(positions).all())}
result["penetration"] = {"part_max_pourcent": round(max(p[0] for p in penetration) * 100, 2), "profondeur_max_mm": round(max(p[1] for p in penetration) * 1000, 1), "part_moyenne_pourcent": round(float(np.mean([p[0] for p in penetration])) * 100, 2)}
result["cout_par_image_ms"] = {"moyenne": round(float(np.mean(times[1:])), 1), "mediane": round(float(np.median(times[1:])), 1), "max": round(float(np.max(times[1:])), 1), "premiere_image": round(times[0], 1)}
# mouvement : le tissu suit-il le corps ? (distance moyenne du tissu au corps à la dernière image)
positions_two, _, _ = run_pass()
result["reproductibilite"] = {"ecart_max_m_entre_deux_passages": float(np.abs(positions - positions_two).max()), "identique_bit_a_bit": bool(np.array_equal(positions, positions_two))}

# bake (nœuds de simulation) et relecture après enregistrement
start = time.perf_counter()
baked = False
modifier_bakes = [(b.bake_id, getattr(b, "bake_target", None), getattr(b, "bake_mode", None), getattr(b, "use_custom_simulation_frame_range", None), getattr(b, "frame_start", None), getattr(b, "frame_end", None)) for b in cloth.bakes]
result["bakes_declarees"] = [str(x) for x in modifier_bakes]
for b in cloth.bakes:
    if hasattr(b, "use_custom_simulation_frame_range"):
        b.use_custom_simulation_frame_range = True
        b.frame_start, b.frame_end = 1, FRAMES
    if hasattr(b, "bake_target"):
        b.bake_target = "PACKED"
bpy.ops.object.select_all(action="DESELECT")
piece.select_set(True)
bpy.context.view_layer.objects.active = piece
try:
    with bpy.context.temp_override(scene=scene, active_object=piece, object=piece):
        bpy.ops.object.simulation_nodes_cache_bake(selected=True)
    baked = True
except Exception as error:  # noqa: BLE001
    result["bake_erreur"] = str(error)[:200]
result["bake"] = {"duree_s": round(time.perf_counter() - start, 1), "cache_cuit": baked}
if baked:
    reference = {}
    for f in (10, FRAMES // 2, FRAMES):
        scene.frame_set(f)
        bpy.context.view_layer.update()
        reference[f] = evaluated_positions(piece)
    path = Path(tempfile.mkdtemp(prefix="hl_clothgn_")) / "tissu.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(path), compress=True)
    result["bake"]["taille_blend_mo"] = round(path.stat().st_size / 2 ** 20, 2)
    piece_name = piece.name
    bpy.ops.wm.open_mainfile(filepath=str(path))
    piece = bpy.data.objects[piece_name]
    scene = bpy.context.scene
    gaps = {}
    start = time.perf_counter()
    for f in reference:
        scene.frame_set(f)
        bpy.context.view_layer.update()
        gaps[f] = float(np.abs(evaluated_positions(piece) - reference[f]).max())
    result["bake"]["relecture_apres_reouverture"] = {"ecart_max_m": max(gaps.values()), "duree_s": round(time.perf_counter() - start, 2)}

print("MESURE_TISSU_GN", json.dumps(result, ensure_ascii=False))
if OUT:
    Path(OUT).write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding="utf-8")
