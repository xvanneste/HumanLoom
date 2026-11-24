"""Validation du regard (lot visage L1) : os `eye.L` / `eye.R`, `skeleton.set_gaze` / `track_gaze` / `clear_gaze`, opérateurs.

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/validate_gaze.py -- [--out FICHIER.json]

G1 les yeux sont rattachés aux os de regard et ne bougent pas à l'installation ; G2 `set_gaze` : angles horizontal et vertical atteints à 0,1° près, centre de l'œil immobile (< 0,1 mm) ;
G3 convergence : angle entre les axes des deux yeux = valeur demandée (± 0,2°) ; G4 suivi d'une cible : chaque œil vise la cible (< 0,5°), borné par la limite (45° / 35°, provisoire) ; G5 `clear_gaze` ;
G6 copie indépendante ; G7 opérateurs et panneau."""
import json
import math
from pathlib import Path
import sys

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension import human  # noqa: E402
from extension.animation import skeleton  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = ARGS[ARGS.index("--out") + 1] if "--out" in ARGS else None
results, failures = {}, []


def check(name, ok, detail=None):
    results[name] = {"ok": bool(ok), "detail": detail}
    print(("OK  " if ok else "KO  ") + name, json.dumps(detail, ensure_ascii=False, default=str)[:700] if detail is not None else "")
    if not ok:
        failures.append(name)


addon.register()
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
bpy.ops.humanloom.create()
body = bpy.context.object
eyes = skeleton.eyes_of(body)
centres_before = {e.name: np.array((e.matrix_world @ e.data.vertices[0].co)[:]) for e in eyes}
rig = skeleton.install(body)
bpy.context.view_layer.update()
drift = max(float(np.linalg.norm(np.array((e.matrix_world @ e.data.vertices[0].co)[:]) - centres_before[e.name])) for e in eyes)
check("G1_yeux_sur_les_os_de_regard", all(e.parent == rig and e.parent_type == "BONE" and e.parent_bone in skeleton.EYE_BONES for e in eyes) and {e.parent_bone for e in eyes} == set(skeleton.EYE_BONES) and drift < 1e-4,
      {"os": sorted(e.parent_bone for e in eyes), "derive_m": drift})


def angles(side):
    d = skeleton.gaze_direction(rig, side)
    return math.degrees(math.atan2(d[0], -d[1])), math.degrees(math.asin(np.clip(d[2], -1, 1)))


def vertex_world(eye):
    return np.array((eye.matrix_world @ eye.data.vertices[0].co)[:])


def eye_centre_world(eye):
    return np.mean([np.array((eye.matrix_world @ v.co)[:]) for v in eye.data.vertices], axis=0)


centre0 = {e.name: eye_centre_world(e) for e in eyes}
skeleton.set_gaze(body, 20.0, 15.0)
yl, pl = angles("L")
yr, pr = angles("R")
moved = max(float(np.linalg.norm(eye_centre_world(e) - centre0[e.name])) for e in eyes)
check("G2_orientation_horizontale_et_verticale", abs(yl - 20) < 0.1 and abs(yr - 20) < 0.1 and abs(pl - 15) < 0.1 and abs(pr - 15) < 0.1 and moved < 1e-4,
      {"yaw": [round(yl, 2), round(yr, 2)], "pitch": [round(pl, 2), round(pr, 2)], "centre_deplace_mm": round(moved * 1000, 4)})
skeleton.set_gaze(body, 0.0, 0.0, 8.0)
yl, _ = angles("L")
yr, _ = angles("R")
check("G3_convergence", abs((yr - yl) - 8.0) < 0.2 and yl < 0 < yr + 1e-9 or abs((yl - yr) - 8.0) < 0.2, {"axe_gauche_deg": round(yl, 2), "axe_droit_deg": round(yr, 2), "angle_entre_axes": round(abs(yl - yr), 2)})

skeleton.clear_gaze(body)
target = bpy.data.objects.new("cible", None)
bpy.context.scene.collection.objects.link(target)
head_z = float(np.mean([eye_centre_world(e)[2] for e in eyes]))
rows = {}
for label, location in (("devant_a_60_cm", (0.0, -0.66, head_z)), ("a_gauche_et_en_haut", (0.25, -0.5, head_z + 0.10)), ("tres_a_droite", (-1.5, 0.2, head_z))):
    target.location = location
    skeleton.track_gaze(body, target)
    errors, limited = [], []
    for e in eyes:
        side = skeleton.eye_side(body, e)
        want = np.array(location) - eye_centre_world(e)
        want /= np.linalg.norm(want)
        got = skeleton.gaze_direction(rig, side)
        errors.append(math.degrees(math.acos(np.clip(float(want @ got), -1, 1))))
        limited.append(angles(side))
    rows[label] = {"erreur_deg": [round(x, 2) for x in errors], "angles": [[round(a, 1), round(b, 1)] for a, b in limited]}
near_ok = max(rows["devant_a_60_cm"]["erreur_deg"]) < 0.5 and max(rows["a_gauche_et_en_haut"]["erreur_deg"]) < 0.5
clamped = all(abs(a[0]) <= skeleton.GAZE_LIMITS["horizontal_deg"] + 0.5 for a in rows["tres_a_droite"]["angles"]) and max(rows["tres_a_droite"]["erreur_deg"]) > 1.0
check("G4_suivi_de_cible_et_limites", near_ok and clamped, rows)
skeleton.clear_gaze(body)
yl, pl = angles("L")
check("G5_regard_droit_devant", abs(yl) < 0.05 and abs(pl) < 0.05 and not any(c.name.startswith(skeleton.GAZE_CONSTRAINT) for p in rig.pose.bones for c in p.constraints), {"yaw": round(yl, 3), "pitch": round(pl, 3)})

skeleton.set_gaze(body, 25.0, 0.0)
clone = human.duplicate_human(bpy.context, body)
clone_rig = skeleton.rigs_of(clone)[0]
bpy.context.view_layer.update()
cl = skeleton.gaze_direction(clone_rig, "L")
skeleton.set_gaze(clone, -10.0, 0.0)
original_after = math.degrees(math.atan2(*(lambda d: (d[0], -d[1]))(skeleton.gaze_direction(rig, "L"))))
clone_after = math.degrees(math.atan2(*(lambda d: (d[0], -d[1]))(skeleton.gaze_direction(clone_rig, "L"))))
check("G6_copie_independante", abs(original_after - 25) < 0.1 and abs(clone_after + 10) < 0.1 and all(e.parent == clone_rig for e in skeleton.eyes_of(clone)), {"original": round(original_after, 2), "copie": round(clone_after, 2)})

bpy.context.view_layer.objects.active = body
skeleton.clear_gaze(body)
ok_set = bpy.ops.humanloom.gaze_set(yaw=10.0, pitch=5.0, convergence=0.0) == {"FINISHED"}
y10, p5 = angles("L")
bpy.ops.humanloom.gaze_clear()
panel_ok = hasattr(bpy.types, "HUMANLOOM_PT_rig")
check("G7_operateurs_et_panneau", ok_set and abs(y10 - 10) < 0.1 and abs(p5 - 5) < 0.1 and panel_ok and "humanloom.gaze_track" in [o for o in ["humanloom.gaze_track"] if hasattr(bpy.ops.humanloom, "gaze_track")], {"yaw": round(y10, 2), "pitch": round(p5, 2)})

# G8 : les paupières suivent le regard (commandes pilotées par l'os eye.L) ; copie indépendante ; retrait propre
skeleton.clear_gaze(body)
on = skeleton.attach_lid_follow(body)
bpy.context.view_layer.update()
rest_cage = skeleton.cage_points(body)


def lids():
    bpy.context.view_layer.update()
    return {n: round(human.get_value(body, n), 4) for n in ("blink_L", "blink_R", "eye_wide")}


skeleton.set_gaze(body, 0.0, -30.0)
down = lids()
down_shift = float(np.abs(skeleton.cage_points(body) - rest_cage).max()) * 1000
skeleton.set_gaze(body, 0.0, 30.0)
up = lids()
skeleton.set_gaze(body, 0.0, 0.0)
straight = lids()
clone2 = human.duplicate_human(bpy.context, body)
skeleton.set_gaze(clone2, 0.0, -30.0)
bpy.context.view_layer.update()
clone_down = human.get_value(clone2, "blink_L")
body_straight = human.get_value(body, "blink_L")
skeleton.detach_lid_follow(body)
off = skeleton.lid_follow_enabled(body)
check("G8_paupieres_suivent_le_regard", on and down["blink_L"] > 0.2 and down["blink_R"] > 0.2 and down["eye_wide"] == 0 and up["eye_wide"] > 0.2 and up["blink_L"] == 0
      and all(v == 0 for v in straight.values()) and down_shift > 0.1 and clone_down > 0.2 and body_straight == 0 and not off,
      {"bas": down, "haut": up, "droit": straight, "deplacement_cage_mm": round(down_shift, 2), "copie_regard_bas": round(clone_down, 3)})

if OUT:
    Path(OUT).write_text(json.dumps(results, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
print("RESULT", "FAIL " + ", ".join(failures) if failures else "PASS")
sys.exit(1 if failures else 0)
