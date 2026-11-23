"""Mesures M1/M3/M4 du mapping sur les armatures RÉELLES de la bibliothèque locale de l'utilisateur (lot A2b). Test IGNORÉ si la bibliothèque est absente.

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/validate_animation_mapping_library.py -- [--library DOSSIER | variable HL_ANIMATION_LIBRARY] [--out FICHIER.json]

Lecture seule, UNE armature (puis une action) par chargement. Seuls des NOMBRES sont affichés et écrits : aucun nom d'os de la bibliothèque n'est
consigné. Critères : pour chaque armature humanoïde (≥ 80 os, couverture ≥ 50 %), couverture des os cibles déformants ≥ 0,9 et ≤ 3 parents
incohérents ; sur 8 actions de l'armature qui s'apparie le mieux, ≥ 90 % des os animés sont appariés.
"""
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = ARGS[ARGS.index("--out") + 1] if "--out" in ARGS else None
library_arg = ARGS[ARGS.index("--library") + 1] if "--library" in ARGS else os.environ.get("HL_ANIMATION_LIBRARY")
blends = sorted(Path(library_arg).glob("*.blend")) if library_arg and Path(library_arg).is_dir() else []
if not blends:
    print("RESULT IGNORÉ : aucune bibliothèque (--library DOSSIER ou variable HL_ANIMATION_LIBRARY)")
    sys.exit(0)

import bpy  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension.animation import mapping, skeleton  # noqa: E402

results, failures = {}, []


def check(name, ok, detail=None):
    results[name] = {"ok": bool(ok), "detail": detail}
    print(("OK  " if ok else "KO  ") + name, detail if detail is not None else "")
    if not ok:
        failures.append(name)


addon.register()
bpy.ops.humanloom.create()
table = skeleton.bone_table(skeleton.joints(skeleton.cage_points(bpy.context.object), skeleton.load_anchors()))
target = mapping.from_table(table, "HumanLoom")
library = blends[0]
with bpy.data.libraries.load(str(library), link=False) as (source_names, _):
    armature_names = list(source_names.armatures)
    action_names = list(source_names.actions)

rows = []
for name in armature_names:
    with bpy.data.libraries.load(str(library), link=False) as (_, wanted):
        wanted.armatures = [name]
    data = wanted.armatures[0]
    skel = mapping.from_armature(data)
    if len(skel) < 80:
        bpy.data.armatures.remove(data)
        continue
    pairs, report = mapping.auto_map(target, skel)
    # M2 : placement de nos articulations par rapport à l'armature de la bibliothèque (têtes d'os appariées, relatives au bassin, ramenées à la stature de notre corps) ; M4 : repères
    main = [n for n in target.names if n.split(".")[0] in ("pelvis", "spine", "neck", "head", "clavicle", "arm_upper", "arm_lower", "hand", "leg_upper", "leg_lower", "foot", "toe") and n in pairs]
    sidx = {n: i for i, n in enumerate(skel.names)}
    tidx = {n: i for i, n in enumerate(target.names)}
    placement = []
    orientation = []
    if "pelvis" in pairs:
        s_height = float(np.percentile(skel.heads[:, 2], 99) - np.percentile(skel.heads[:, 2], 1))
        t_height = float(np.percentile(target.heads[:, 2], 99) - np.percentile(target.heads[:, 2], 1))
        factor = t_height / s_height
        s_pelvis, t_pelvis = skel.heads[sidx[pairs["pelvis"].source]], target.heads[tidx["pelvis"]]
        for n in main:
            s_vec = (skel.heads[sidx[pairs[n].source]] - s_pelvis) * factor
            t_vec = target.heads[tidx[n]] - t_pelvis
            placement.append(float(np.linalg.norm(s_vec - t_vec)) / t_height)
        for parent, child in (("arm_upper.L", "arm_lower.L"), ("arm_lower.L", "hand.L"), ("leg_upper.L", "leg_lower.L"), ("leg_lower.L", "foot.L"), ("neck.01", "head")):
            if parent in pairs and child in pairs:
                vs = skel.heads[sidx[pairs[child].source]] - skel.heads[sidx[pairs[parent].source]]
                vt = target.heads[tidx[child]] - target.heads[tidx[parent]]
                orientation.append(float(np.degrees(np.arccos(np.clip(vs @ vt / np.linalg.norm(vs) / np.linalg.norm(vt), -1, 1)))))
    rows.append({"placement_pourcent": [round(p * 100, 2) for p in placement], "angles_de_chaine_deg": [round(a, 1) for a in orientation], "index": len(rows), "os": len(skel), "couverture": round(report.coverage, 3), "parents_incohérents": len(report.parent_mismatches), "faible_confiance": len(report.low_confidence),
                 "os_sources_inutilisés": {k: len(v) for k, v in report.unused_sources.items()}, "mapped_sources": {p.source for p in pairs.values()},
                 "auxiliaires": set(report.unused_sources["auxiliaires"])})
    bpy.data.armatures.remove(data)
humanoid = [r for r in rows if r["couverture"] >= 0.5]
printable = [{k: v for k, v in r.items() if k not in ("mapped_sources", "auxiliaires", "placement_pourcent", "angles_de_chaine_deg")} for r in rows]
print("MESURE armatures de 80 os ou plus :", json.dumps(printable))
check("L1_armatures_humanoides_trouvees", len(humanoid) >= 1, {"armatures_80_os_ou_plus": len(rows), "humanoïdes": len(humanoid)})
reference = [r for r in rows if r["os"] == 88 and r["couverture"] >= 0.9 and r["placement_pourcent"]]
all_placement = np.array([p for r in reference for p in r["placement_pourcent"]]) if reference else np.array([100.0])
all_angles = np.array([a for r in reference for a in r["angles_de_chaine_deg"]]) if reference else np.array([180.0])
check("L4_M2_placement_des_articulations", len(reference) >= 1 and np.median(all_placement) <= 3 and np.percentile(all_placement, 95) <= 6,
      {"armatures_de_88_os": len(reference), "erreur_mediane_pourcent_de_la_stature": round(float(np.median(all_placement)), 2), "p95": round(float(np.percentile(all_placement, 95)), 2), "max": round(float(all_placement.max()), 2)})
check("L5_M4_directions_de_chaine", len(reference) >= 1 and np.median(all_angles) <= 20,
      {"écart_median_de_direction_de_chaine_deg": round(float(np.median(all_angles)), 1), "max_deg": round(float(all_angles.max()), 1), "note": "pose de repos différente : corrigée par le retargeting (mode absolu)"})
check("L2_couverture_par_armature", all(r["couverture"] >= 0.9 and r["parents_incohérents"] <= 3 for r in humanoid), [{k: r[k] for k in ("os", "couverture", "parents_incohérents")} for r in humanoid])

# M3 : les os animés par de vraies actions sont-ils appariés ? (une action par chargement)
best = max(humanoid, key=lambda r: (r["couverture"], -r["faible_confiance"])) if humanoid else None
fractions, auxiliary_share = [], []
if best is not None:
    candidates = [n for n in action_names][:: max(1, len(action_names) // 8)][:8]
    for name in candidates:
        with bpy.data.libraries.load(str(library), link=False) as (_, wanted):
            wanted.actions = [name]
        action = wanted.actions[0]
        animated = set()
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    for curve in bag.fcurves:
                        match = re.match(r'pose\.bones\["(.+?)"\]', curve.data_path)
                        if match:
                            animated.add(match.group(1))
        if animated:  # os auxiliaires de la source (IK, accessoires, aides) ignorés par conception : comptés à part
            main = animated - best["auxiliaires"]
            fractions.append(len(main & best["mapped_sources"]) / max(len(main), 1))
            auxiliary_share.append(len(animated & best["auxiliaires"]) / len(animated))
        bpy.data.actions.remove(action)
check("L3_os_animes_non_auxiliaires_apparies", bool(fractions) and min(fractions) >= 0.9, {"actions_testées": len(fractions), "part_minimale": round(min(fractions), 3) if fractions else None, "part_moyenne": round(float(np.mean(fractions)), 3) if fractions else None,
                                                                                          "part_des_os_animes_auxiliaires_ignores": round(float(np.mean(auxiliary_share)), 3) if auxiliary_share else None})

if OUT:
    Path(OUT).write_text(json.dumps(results, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
print("RESULT", "FAIL " + ", ".join(failures) if failures else "PASS")
sys.exit(1 if failures else 0)
