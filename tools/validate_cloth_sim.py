"""Validation des robes et de la simulation de tissu native (lot V4).

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/validate_cloth_sim.py -- [--out FICHIER.json] [--frames 40]

S1 géométrie des 4 pièces (robe courte, robe mi-longue, robe longue, jupe) sur 5 morphologies : finie, ourlet à la hauteur demandée (± 1 cm), aucune pénétration au repos, groupe d'épinglage ; S2 stabilité et pénétration sous
mouvement (marche, bras levé, torsion) sur 3 morphologies (pas d'explosion ; profondeur de pénétration <= 15 mm : seuil accepté par l'utilisateur pour la pénétration sous l'aisselle en gros plan) ; S3 reproductibilité ;
S4 cache emballé à plage fixée rejoué à l'identique après enregistrement et réouverture ; S5 opérateurs ; coûts par image et durée de cuisson rapportés."""
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
from extension import cloth_sim, garments, human  # noqa: E402
from extension.animation import skeleton  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = ARGS[ARGS.index("--out") + 1] if "--out" in ARGS else None
FRAMES = int(ARGS[ARGS.index("--frames") + 1]) if "--frames" in ARGS else 40
LIMIT_MM = 15.0
results, failures = {}, []


def check(name, ok, detail=None):
    results[name] = {"ok": bool(ok), "detail": detail}
    print(("OK  " if ok else "KO  ") + name, json.dumps(detail, ensure_ascii=False, default=str)[:1100] if detail is not None else "")
    if not ok:
        failures.append(name)


addon.register()
MORPHOLOGIES = {"defaut": {}, "femme_jeune": {"sex": 1.0, "age": 1.0}, "enfant": {"age": 0.0}, "homme_age": {"sex": 0.0, "age": 3.0}, "gabarit": {"legs": 1.0, "torso": -1.0}}
DRESSES = ("robe_courte", "robe_mi_longue", "robe_longue", "jupe")


def fresh(values=None):
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for collection in list(bpy.data.collections):
        bpy.data.collections.remove(collection)
    bpy.ops.humanloom.create()
    body = bpy.context.object
    for name, value in (values or {}).items():
        human.set_value(body, name, value)
    rig = skeleton.install(body)
    body.modifiers["Human Modeling · Surface"].show_viewport = False
    return body, rig


def rest_tree(body):
    points = skeleton.cage_points(body)
    mesh = body.data
    mesh.calc_loop_triangles()
    return BVHTree.FromPolygons([Vector(p) for p in points], [t.vertices[:] for t in mesh.loop_triangles]), points


# S1 géométrie au repos
rows, bad = {}, []
for label, values in MORPHOLOGIES.items():
    body, rig = fresh(values)
    tree, cage = rest_tree(body)
    stature = float(cage[:, 2].max() - cage[:, 2].min())
    for key in DRESSES:
        dress = garments.add_garment(body, key)
        pts = np.array([v.co[:] for v in dress.data.vertices])
        params = json.loads(dress[garments.PARAMS])
        first, last = params["robe"]["sommets_jupe"]
        skirt = pts[first:last]
        target_hem = float(cage[:, 2].min()) + garments.GARMENTS[key]["robe"]["ourlet"] * stature
        inside = sum(1 for p in skirt if (lambda r: r[0] is not None and (Vector(p) - r[0]).dot(r[1]) < 0)(tree.find_nearest(Vector(p))))
        closest = min(tree.find_nearest(Vector(p))[3] for p in skirt)
        rows[(label, key)] = {"hem_ecart_mm": round(abs(float(skirt[:, 2].min()) - target_hem) * 1000, 2), "interieur": inside, "distance_min_mm": round(closest * 1000, 1), "sommets": len(pts), "epinglage": "Epinglage" in dress.vertex_groups}
        if not np.isfinite(pts).all() or abs(float(skirt[:, 2].min()) - target_hem) > 0.01 or inside or "Epinglage" not in dress.vertex_groups:
            bad.append((label, key, rows[(label, key)]))
        garments.remove_garment(dress)
check("S1_robes_geometrie_ourlet_et_aucune_penetration_au_repos", not bad and len(rows) == 20, {"pieces_x_morphologies": len(rows), "echecs": bad[:3], "distance_min_au_corps_mm_pire": min(r["distance_min_mm"] for r in rows.values())})


# S2 stabilité et pénétration sous mouvements
def raise_sign(rig, side):
    """Signe de rotation Z de arm_upper.<side> qui LÈVE le bras (la main monte) : mesuré, pas supposé."""
    pb = rig.pose.bones["arm_upper." + side]
    pb.rotation_mode = "XYZ"
    best = {}
    for sign in (1.0, -1.0):
        pb.rotation_euler = (0.0, 0.0, sign * np.radians(60))
        bpy.context.view_layer.update()
        best[sign] = float((rig.matrix_world @ rig.pose.bones["hand." + side].head).z)
    pb.rotation_euler = (0.0, 0.0, 0.0)
    bpy.context.view_layer.update()
    return 1.0 if best[1.0] > best[-1.0] else -1.0


def animate(rig, kind, frames):
    sign_left, sign_right = raise_sign(rig, "L"), raise_sign(rig, "R")
    rig.animation_data_create()
    rig.animation_data.action = None
    for pb in rig.pose.bones:
        pb.rotation_mode = "XYZ"
        pb.rotation_euler = (0.0, 0.0, 0.0)
    keys = {"marche": [(1, {}), (frames // 4, {"leg_upper.L": (np.radians(35), 0, 0), "leg_upper.R": (np.radians(-35), 0, 0), "leg_lower.R": (np.radians(-40), 0, 0)}),
                       (frames // 2, {"leg_upper.L": (np.radians(-35), 0, 0), "leg_upper.R": (np.radians(35), 0, 0), "leg_lower.L": (np.radians(-40), 0, 0)}),
                       (3 * frames // 4, {"leg_upper.L": (np.radians(35), 0, 0), "leg_upper.R": (np.radians(-35), 0, 0), "leg_lower.R": (np.radians(-40), 0, 0)}), (frames, {})],
            "bras_leve": [(1, {}), (frames // 2, {"arm_upper.L": (0, 0, sign_left * np.radians(80)), "arm_upper.R": (0, 0, sign_right * np.radians(80)), "spine.03": (0, np.radians(20), 0)}), (frames, {})],
            "torsion": [(1, {}), (frames // 2, {"spine.03": (0, np.radians(40), 0), "pelvis": (0, np.radians(-15), 0)}), (frames, {})]}[kind]
    for frame, pose in keys:
        for pb in rig.pose.bones:
            pb.rotation_euler = pose.get(pb.name, (0.0, 0.0, 0.0))
            pb.keyframe_insert("rotation_euler", frame=frame)


def body_tree(body):
    evaluated = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    mesh.calc_loop_triangles()
    tree = BVHTree.FromPolygons([body.matrix_world @ v.co for v in mesh.vertices], [t.vertices[:] for t in mesh.loop_triangles])
    evaluated.to_mesh_clear()
    return tree


def run(body, dress, frames):
    scene = bpy.context.scene
    scene.frame_start, scene.frame_end = 1, frames
    scene.frame_set(1)
    bpy.context.view_layer.update()
    pos, times, depth_skirt, depth_bodice = [], [], 0.0, 0.0
    first, last = json.loads(dress[garments.PARAMS])["robe"]["sommets_jupe"]
    for f in range(1, frames + 1):
        started = time.perf_counter()
        scene.frame_set(f)
        bpy.context.view_layer.update()
        p = cloth_sim.positions(dress)
        times.append((time.perf_counter() - started) * 1000.0)
        pos.append(p)
        if f % 4 == 0:
            tree = body_tree(body)
            for index, c in enumerate(p):
                r = tree.find_nearest(Vector(c))
                if r[0] is not None and (Vector(c) - r[0]).dot(r[1]) < 0 and r[3] > 0.001:
                    if first <= index < last:
                        depth_skirt = max(depth_skirt, r[3])
                    else:
                        depth_bodice = max(depth_bodice, r[3])
    return np.array(pos), times, depth_skirt * 1000, depth_bodice * 1000


rows2, ok2 = {}, True
for label in ("defaut", "femme_jeune", "enfant"):
    for kind in ("marche", "bras_leve", "torsion"):
        body, rig = fresh(MORPHOLOGIES[label])
        dress = garments.add_garment(body, "robe_mi_longue")
        cloth_sim.enable(dress)
        animate(rig, kind, FRAMES)
        pos, times, depth_skirt, depth_bodice = run(body, dress, FRAMES)
        steps = np.linalg.norm(np.diff(pos, axis=0), axis=-1)
        stable = bool(np.isfinite(pos).all() and steps.max() < 0.3)
        rows2[f"{label}/{kind}"] = {"stable": stable, "pas_max_m": round(float(steps.max()), 3), "pen_jupe_mm": round(depth_skirt, 1), "pen_corsage_mm": round(depth_bodice, 1), "ms_par_image": round(float(np.mean(times[1:])), 1)}
        ok2 &= stable
worst_skirt = max(r["pen_jupe_mm"] for r in rows2.values())
worst_bodice = max(r["pen_corsage_mm"] for r in rows2.values())
check("S2a_stabilite_sans_explosion_3_morphologies_3_mouvements", ok2, {"essais": rows2})
check("S2b_penetration_<=_15_mm", worst_skirt <= LIMIT_MM and worst_bodice <= LIMIT_MM,
      {"seuil_mm": LIMIT_MM, "pire_jupe_mm": worst_skirt, "pire_corsage_mm_(armature_seule_aisselle)": worst_bodice, "detail": {k: [v["pen_jupe_mm"], v["pen_corsage_mm"]] for k, v in rows2.items()}})

# S3 reproductibilité et S4 cache emballé à plage fixée
body, rig = fresh()
dress = garments.add_garment(body, "robe_longue")
cloth_sim.enable(dress)
animate(rig, "marche", FRAMES)
first_run = run(body, dress, FRAMES)
second_run = run(body, dress, FRAMES)
check("S3_reproductibilite_bit_a_bit", bool(np.array_equal(first_run[0], second_run[0])), {"ecart_max_m": float(np.abs(first_run[0] - second_run[0]).max())})
info = cloth_sim.bake(dress, 1, FRAMES)
reference = {}
for f in (8, FRAMES // 2, FRAMES):
    bpy.context.scene.frame_set(f)
    bpy.context.view_layer.update()
    reference[f] = cloth_sim.positions(dress)
path = Path(tempfile.mkdtemp(prefix="hl_robe_")) / "robe.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(path), compress=True)
name = dress.name
bpy.ops.wm.open_mainfile(filepath=str(path))
dress2 = bpy.data.objects[name]
gaps = {}
started = time.perf_counter()
for f in reference:
    bpy.context.scene.frame_set(f)
    bpy.context.view_layer.update()
    gaps[f] = float(np.abs(cloth_sim.positions(dress2) - reference[f]).max())
replay = time.perf_counter() - started
check("S4_cache_emballe_a_plage_fixee_rejoue_apres_reouverture", max(gaps.values()) < 1e-6 and cloth_sim.baked_range(dress2) == (1, FRAMES), {"ecarts_m": gaps, "cuisson": info, "relecture_3_images_s": round(replay, 3), "taille_blend_mo": round(path.stat().st_size / 2 ** 20, 1)})

# S5 opérateurs
body, rig = fresh()
bpy.context.view_layer.objects.active = body
dress = garments.add_garment(body, "robe_courte")
bpy.context.scene.frame_start, bpy.context.scene.frame_end = 1, 12
ok_ops = bpy.ops.humanloom.cloth_enable(piece="robe_courte") == {"FINISHED"} and cloth_sim.is_enabled(dress)
ok_ops &= bpy.ops.humanloom.cloth_bake(piece="robe_courte") == {"FINISHED"} and cloth_sim.baked_range(dress) == (1, 12)
ok_ops &= bpy.ops.humanloom.cloth_clear(piece="robe_courte") == {"FINISHED"} and cloth_sim.baked_range(dress) is None
ok_ops &= bpy.ops.humanloom.cloth_disable(piece="robe_courte") == {"FINISHED"} and not cloth_sim.is_enabled(dress) and body.modifiers.get(cloth_sim.COLLIDER_MODIFIER) is None
tshirt = garments.add_garment(body, "t_shirt")
try:
    cloth_sim.enable(tshirt)
    refused = False
except ValueError:
    refused = True
check("S5_operateurs_panneau_et_pieces_non_simulables_refusees", ok_ops and refused and hasattr(bpy.types, "HUMANLOOM_PT_cloth"), {"operateurs": ok_ops, "t_shirt_refuse": refused})

# S6 cycle de vie (GRM-005) : l'état initial des correctifs de flexion et des ressources est restitué à la désactivation, au retrait de la dernière pièce simulée et après un échec d'activation
from extension.animation import correctives  # noqa: E402
body, rig = fresh()
dress = garments.add_garment(body, "robe_mi_longue")
keys = correctives.keys_of(body.data)
keys[0].mute = True  # mute volontaire de l'utilisateur : doit survivre au cycle
initial = {k.name: k.mute for k in keys}


def mutes():
    return {k.name: k.mute for k in correctives.keys_of(body.data)}


def owned():
    return (body.modifiers.get(cloth_sim.COLLIDER_MODIFIER) is not None, cloth_sim.SESSION_KEY in body, any(c.name.startswith(cloth_sim.COLLECTION) for c in bpy.data.collections))


cloth_sim.enable(dress)
active_ok = all(mutes().values()) and owned()[0]
cloth_sim.disable(dress)
disable_ok = mutes() == initial and owned() == (False, False, False)
cloth_sim.enable(dress)
try:
    garments.remove_garment(dress)  # l'API publique REFUSE de retirer une pièce simulée (protection skin_mask) : rien ne doit changer
    refused_public = False
except ValueError:
    refused_public = True
state_kept = refused_public and all(mutes().values()) and owned()[0]
garments._remove_garment(dress)  # retrait interne (remplacement/reconstruction) : doit passer par le cycle de vie et restituer l'état initial
remove_ok = state_kept and mutes() == initial and owned() == (False, False, False)
dress = garments.add_garment(body, "robe_mi_longue")
original_groups = cloth_sim._groups
cloth_sim._groups = lambda: (_ for _ in ()).throw(ValueError("échec simulé"))
try:
    cloth_sim.enable(dress)
    failed = False
except ValueError:
    failed = True
finally:
    cloth_sim._groups = original_groups
rollback_ok = failed and mutes() == initial and owned() == (False, False, False) and not cloth_sim.is_enabled(dress)
check("S6_cycle_de_vie_etat_initial_restitue", active_ok and disable_ok and remove_ok and rollback_ok, {"actif": active_ok, "desactivation": disable_ok, "retrait": remove_ok, "echec_puis_retour": rollback_ok})

if OUT:
    Path(OUT).write_text(json.dumps(results, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
print("RESULT", "FAIL " + ", ".join(failures) if failures else "PASS")
sys.exit(1 if failures else 0)
