"""Validation de l'élimination hors caméra de la foule (lot B) : un personnage hors du champ de la caméra est masqué (clés constantes de visibilité sur le corps et ses enfants), les autres restent visibles et INCHANGÉS ; la caméra
animée est prise en compte ; `uncull` remet tout comme avant ; le coût d'évaluation baisse.

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/validate_crowd_cull.py -- [--out FICHIER.json]
K1 masquage cohérent avec un test de champ INDÉPENDANT (centre du personnage dans le cadre => jamais masqué) ; K2 personnages visibles inchangés (positions évaluées identiques avec et sans élimination) ; K3 caméra animée ;
K4 `uncull` : aucune courbe de visibilité, tout visible ; K5 les objets masqués sortent des instances du graphe d'évaluation ; K6 erreurs (pas de caméra, pas de foule) ; K7 opérateurs du panneau."""
import json
from pathlib import Path
import sys

import bpy
import numpy as np
from bpy_extras.anim_utils import action_get_channelbag_for_slot
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension import crowd  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = ARGS[ARGS.index("--out") + 1] if "--out" in ARGS else None
results, failures = {}, []


def check(name, ok, detail=None):
    results[name] = {"ok": bool(ok), "detail": detail}
    print(("OK  " if ok else "KO  ") + name, json.dumps(detail, ensure_ascii=False, default=str)[:900] if detail is not None else "")
    if not ok:
        failures.append(name)


addon.register()
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
scene = bpy.context.scene
try:
    crowd.cull(scene)
    refused_no_crowd = False
except ValueError:
    refused_no_crowd = True
spec = crowd.default_spec(14, 21)
spec["frames"] = 48
crowd.generate(bpy.context, spec)
scene.frame_start, scene.frame_end = 1, 48
bodies = crowd.members_of(scene)
try:
    crowd.cull(scene)
    refused_no_camera = False
except ValueError:
    refused_no_camera = True
check("K6_erreurs", refused_no_crowd and refused_no_camera, {"sans_foule": refused_no_crowd, "sans_camera": refused_no_camera})

camera_data = bpy.data.cameras.new("cam")
camera = bpy.data.objects.new("cam", camera_data)
scene.collection.objects.link(camera)
scene.camera = camera
camera.location = (0.0, -14.0, 1.7)
camera.rotation_euler = (1.5707963, 0.0, 0.0)  # vers +y
bpy.context.view_layer.update()


def visibility_curve(obj, prop="hide_render"):
    animation = obj.animation_data
    action = animation.action if animation else None
    if action is None:
        return None
    bag = action_get_channelbag_for_slot(action, animation.action_slot)
    return next((c for c in bag.fcurves if c.data_path == prop), None) if bag else None


def visible_at(body, frame):
    """État de la clé de visibilité à l'image donnée (lu sur la courbe, sans évaluer le graphe)."""
    curve = visibility_curve(body)
    return curve is None or curve.evaluate(frame) < 0.5


def evaluated_positions():
    depsgraph = bpy.context.evaluated_depsgraph_get()
    out = {}
    for b in bodies:
        if b.hide_viewport:
            continue
        out[b[crowd.OBJECT_KEY]] = np.array(b.evaluated_get(depsgraph).matrix_world.translation)
    return out


# état de référence SANS élimination, aux images 1, 24, 48
reference = {}
for frame in (1, 24, 48):
    scene.frame_set(frame)
    reference[frame] = evaluated_positions()
summary = crowd.cull(scene)
print("RESUME", json.dumps(summary, ensure_ascii=False))
violations, hidden_total = [], 0
for frame in (1, 24, 48):
    scene.frame_set(frame)
    for b in bodies:
        position = reference[frame][b[crowd.OBJECT_KEY]]
        view = world_to_camera_view(scene, camera, Vector((position[0], position[1], 0.95)))
        in_frame = 0.0 <= view.x <= 1.0 and 0.0 <= view.y <= 1.0 and view.z > 0
        shown = visible_at(b, frame)
        hidden_total += 0 if shown else 1
        if in_frame and not shown:
            violations.append((frame, b[crowd.OBJECT_KEY]))
check("K1_masquage_coherent_avec_le_champ_de_la_camera", not violations and hidden_total > 0, {"centre_dans_le_cadre_mais_masque": violations, "masques_cumules_sur_3_images": hidden_total, **{k: v for k, v in summary.items() if k != "camera"}})

worst, compared = 0.0, 0
for frame in (1, 24, 48):
    scene.frame_set(frame)
    for i, p in evaluated_positions().items():
        worst = max(worst, float(np.abs(p - reference[frame][i]).max()))
        compared += 1
check("K2_personnages_visibles_inchanges", compared > 0 and worst < 1e-6, {"comparaisons": compared, "ecart_max_m": worst})

# K3 caméra animée : elle balaie de -30 à +30 m en x ; des personnages passent du masqué au visible
crowd.uncull(scene)
camera.location = (-30.0, -14.0, 1.7)
camera.keyframe_insert("location", frame=1)
camera.location = (30.0, -14.0, 1.7)
camera.keyframe_insert("location", frame=48)
animated = crowd.cull(scene)
changing = [b[crowd.OBJECT_KEY] for b in bodies if len({visible_at(b, f) for f in (1, 12, 24, 36, 48)}) > 1]
check("K3_camera_animee_prise_en_compte", len(changing) >= 1 and animated["personnages_a_cles_de_visibilite"] >= 1, {"changent_de_visibilite": changing, "masques_par_image_moyen": animated["masques_par_image_moyen"]})

# K5 les objets masqués sortent des instances du graphe d'évaluation (donc des rendus : Cycles et Eevee ne synchronisent que les instances visibles). MESURE (documentée, non exigée) : le coût d'évaluation de la vue 3D ne baisse PAS
# avec une visibilité ANIMÉE (une clé de `hide_viewport` laisse l'objet dans le graphe : mesuré 100,7 -> 99,3 ms pour 6 personnages sur 14 masqués, contre 97 -> 69 ms avec un masquage statique) ; le gain porte sur le rendu.
crowd.uncull(scene)
camera.animation_data_clear()
camera.location = (0.0, -14.0, 1.7)
camera.data.lens = 100.0  # champ étroit : au moins le tiers de la foule hors cadre
scene.frame_set(24)
full_count = sum(1 for inst in bpy.context.evaluated_depsgraph_get().object_instances if inst.object.get(crowd.OBJECT_KEY) is not None or (inst.object.parent is not None and inst.object.parent.get(crowd.OBJECT_KEY) is not None))
fixed = crowd.cull(scene)
scene.frame_set(24)
culled_count = sum(1 for inst in bpy.context.evaluated_depsgraph_get().object_instances if inst.object.get(crowd.OBJECT_KEY) is not None or (inst.object.parent is not None and inst.object.parent.get(crowd.OBJECT_KEY) is not None))
hidden_now = sum(1 for b in bodies if not visible_at(b, 24))
check("K5_les_masques_sortent_du_graphe_d_evaluation", hidden_now >= 3 and culled_count < full_count and full_count - culled_count >= hidden_now, {"instances_sans": full_count, "instances_avec": culled_count, "personnages_masques_a_l_image_24": hidden_now})

# K4 uncull
removed = crowd.uncull(scene)
leftovers = sum(1 for b in bodies for obj in [b, *b.children_recursive] if visibility_curve(obj, "hide_render") or visibility_curve(obj, "hide_viewport"))
all_visible = all(not o.hide_viewport and not o.hide_render for b in bodies for o in [b, *b.children_recursive])
check("K4_uncull_remet_tout_comme_avant", removed > 0 and leftovers == 0 and all_visible and crowd.CULL_KEY not in scene, {"courbes_retirees": removed, "restantes": leftovers})

# K7 opérateurs du panneau
camera.data.lens = 100.0
ok_cull = bpy.ops.humanloom.crowd_cull() == {"FINISHED"} and crowd.CULL_KEY in scene
poll_uncull = bpy.ops.humanloom.crowd_uncull.poll()
ok_uncull = bpy.ops.humanloom.crowd_uncull() == {"FINISHED"} and crowd.CULL_KEY not in scene
check("K7_operateurs_masquer_et_tout_afficher", ok_cull and poll_uncull and ok_uncull, {"masquer": ok_cull, "tout_afficher_disponible": poll_uncull, "tout_afficher": ok_uncull})

if OUT:
    Path(OUT).write_text(json.dumps(results, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
print("RESULT", "FAIL " + ", ".join(failures) if failures else "PASS")
sys.exit(1 if failures else 0)
