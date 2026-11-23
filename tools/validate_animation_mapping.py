"""Validation du lot A2b : moteur de mapping (extension/animation/mapping.py) sur des squelettes SYNTHÉTIQUES.

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/validate_animation_mapping.py -- [--out FICHIER.json]

Les squelettes sources sont dérivés de NOTRE table d'os (positions d'un corps réel) puis renommés selon des conventions INVENTÉES ici (de type
Mixamo, Rigify, Unreal, et noms opaques) : os supprimés, colonne à 3 os, torsions absentes, bouts d'os, échelle et décalage, os IK. La vérité
terrain est connue ; on mesure la part d'appariements corrects. Aucun squelette tiers n'est lu (voir validate_animation_mapping_library.py).
"""
import json
from pathlib import Path
import random
import shutil
import sys
import tempfile

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = ARGS[ARGS.index("--out") + 1] if "--out" in ARGS else None
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
body = bpy.context.object
table = skeleton.bone_table(skeleton.joints(skeleton.cage_points(body), skeleton.load_anchors()))
target = mapping.from_table(table, "HumanLoom")
by_name = {b["name"]: b for b in table}
FINGER_NAMES = ("thumb", "index", "middle", "ring", "pinky")


def derive(rename, prefix="", scale=1.0, offset=(0.0, 0.0, 0.0), extra=None, shuffle=None, flip_x=False, noise=0.0, x_scale=1.0):
    """Squelette source : `rename(nom_cible) -> nom_source | None` ; parent = plus proche ancêtre conservé ; retourne (Skeleton, vérité {cible: source})."""
    kept = {b["name"]: rename(b["name"]) for b in table if b["name"] != skeleton.JAW}  # les bibliothèques de corps n'ont pas de mâchoire
    kept = {k: (prefix + v) for k, v in kept.items() if v}
    def kept_parent(name):
        parent = by_name[name]["parent"]
        while parent and parent not in kept:
            parent = by_name[parent]["parent"]
        return kept.get(parent)
    rows = []
    for name, new in kept.items():
        head, tail = np.array(by_name[name]["head"]) * scale + offset, np.array(by_name[name]["tail"]) * scale + offset
        if flip_x:
            head, tail = head * [-1, 1, 1], tail * [-1, 1, 1]
        if x_scale != 1.0:
            head, tail = head * [x_scale, 1, 1], tail * [x_scale, 1, 1]
        if noise:  # proportions et placements d'un autre rig : bruit gaussien en fraction de la stature
            generator = np.random.default_rng(abs(hash(name)) % 1000)
            head, tail = head + generator.normal(0, noise * 1.66 * scale, 3), tail + generator.normal(0, noise * 1.66 * scale, 3)
        rows.append({"name": new, "parent": kept_parent(name), "head": head, "tail": tail})
    for name, _unused, parent_target, direction in (extra or []):
        base = np.array(by_name[parent_target]["tail"]) * scale + offset
        rows.append({"name": name[1:] if name.startswith("!") else prefix + name, "parent": kept.get(parent_target), "head": base, "tail": base + np.array(direction) * scale})
    if shuffle is not None:
        random.Random(shuffle).shuffle(rows)  # ordre des os quelconque : le mapping ne doit pas en dépendre
        parents_by_name = {r["name"]: r["parent"] for r in rows}
        ordered, seen = [], set()
        def place(row):
            if row["name"] in seen:
                return
            if row["parent"]:
                place(next(r for r in rows if r["name"] == row["parent"]))
            seen.add(row["name"])
            ordered.append(row)
        for row in rows:
            place(row)
        rows = ordered
    return mapping.from_table(rows, "synthetique"), {t: s for t, s in kept.items()}


def side(name):
    return "L" if name.endswith(".L") else "R" if name.endswith(".R") else ""


def mixamo(name):
    base, s = (name[:-2], side(name)) if side(name) else (name, "")
    word = {"L": "Left", "R": "Right"}.get(s, "")
    fixed = {"pelvis": "Hips", "spine.01": "Spine", "spine.03": "Spine1", "spine.05": "Spine2", "neck.01": "Neck", "head": "Head"}
    if name in fixed:
        return fixed[name]
    for part, new in (("clavicle", "Shoulder"), ("arm_upper", "Arm"), ("arm_lower", "ForeArm"), ("hand", "Hand"), ("leg_upper", "UpLeg"), ("leg_lower", "Leg"), ("foot", "Foot"), ("toe", "ToeBase")):
        if base == part:
            return word + new
    for finger in FINGER_NAMES:
        for n in (1, 2, 3):
            if base == f"{finger}.0{n}":
                return f"{word}Hand{finger.capitalize()}{n}"
    return None


def rigify(name):
    base, s = (name[:-2], side(name)) if side(name) else (name, "")
    tail = f".{s}" if s else ""
    fixed = {"pelvis": "pelvis", "spine.01": "spine", "spine.02": "spine.001", "spine.03": "spine.002", "spine.04": "spine.003", "spine.05": "spine.004", "neck.01": "neck", "neck.02": "neck.001", "head": "head"}
    if name in fixed:
        return fixed[name]
    simple = {"clavicle": "shoulder", "arm_upper": "upper_arm", "arm_lower": "forearm", "hand": "hand", "leg_upper": "thigh", "leg_lower": "shin", "foot": "foot", "toe": "toe"}
    if base in simple:
        return simple[base] + tail
    for number, finger in enumerate(FINGER_NAMES):
        for n in (0, 1, 2, 3):
            if base == f"{finger}.0{n}":
                if finger == "thumb":
                    return f"thumb.0{n}{tail}" if n else None
                return f"palm.0{number}{tail}" if n == 0 else f"f_{finger}.0{n}{tail}"
    return None


def inventive(name):
    base, s = (name[:-2], side(name)) if side(name) else (name, "")
    tail = f"_{s}" if s else ""
    if name == "root":
        return "Root"
    fixed = {"pelvis": "Pelvis", "head": "Head"}
    if name in fixed:
        return fixed[name]
    if base.startswith("spine."):
        return f"Spine_{base[-2:]}"
    if base.startswith("neck."):
        return f"Neck_{base[-2:]}"
    simple = {"clavicle": "Clavicle", "arm_upper": "UpperArm", "arm_lower": "LowerArm", "hand": "Hand", "leg_upper": "Thigh", "leg_lower": "Calf", "foot": "Foot", "toe": "Ball"}
    if base in simple:
        return simple[base] + tail
    for part, new in (("arm_upper_twist", "UpperArm_Twist"), ("arm_lower_twist", "LowerArm_Twist"), ("leg_upper_twist", "Thigh_Twist"), ("leg_lower_twist", "Calf_Twist")):
        if base.startswith(part + "."):
            return f"{new}_{base[-2:]}{tail}"
    for finger in FINGER_NAMES:
        if base.startswith(finger + "."):
            n = base[-2:]
            return f"{finger.capitalize()}_{'Meta' if n == '00' else n}{tail}"
    return None


def opaque_factory():
    counter = {}

    def rename(name):
        keep = mixamo(name)  # sous-ensemble sans torsions, colonne à 3 os, sans métacarpes
        if keep is None:
            return None
        counter[name] = f"J{len(counter) + 11:03d}"
        return counter[name]

    return rename


def accuracy(mapped, truth, only=None):
    keys = [t for t in truth if (only is None or t in only)]
    good = sum(1 for t in keys if t in mapped and mapped[t].source == truth[t])
    return good, len(keys)


def run(label, skel, truth, minimum, only=None):
    mapped, report = mapping.auto_map(target, skel)
    good, total = accuracy(mapped, truth, only)
    wrong = [(t, mapped[t].source if t in mapped else None, truth[t]) for t in truth if (only is None or t in only) and (t not in mapped or mapped[t].source != truth[t])]
    check(label, good / total >= minimum, {"corrects": f"{good}/{total}", "part": round(good / total, 3), "minimum": minimum, "erreurs": wrong[:4], "rapport": report.summary()})
    return mapped, report


# --- conventions de noms ---------------------------------------------------------------------------------------------------------------------------------
mixamo_skel, mixamo_truth = derive(mixamo, prefix="mixamorig:", scale=100.0, extra=[("!HeadTop_End", "x", "head", (0, 0, 0.1))] + [(f"!{'Left' if s == 'L' else 'Right'}HandThumb4", "x", f"thumb.03.{s}", (0, -0.02, -0.02)) for s in "LR"])
mixamo_truth = {t: "mixamorig:" + n if not n.startswith("mixamorig:") else n for t, n in mixamo_truth.items()}
mapped, report = run("M1_convention_Mixamo_like", mixamo_skel, {t: s for t, s in mixamo_truth.items()}, 0.97)
rigify_skel, rigify_truth = derive(rigify)
run("M2_convention_Rigify_like", rigify_skel, rigify_truth, 0.97)
extra = [("!IK_Foot_L", "x", "foot.L", (0, 0, 0.0)), ("!IK_Hand_R", "x", "hand.R", (0, 0, 0.0))]
inventive_skel, inventive_truth = derive(inventive, scale=100.0, extra=[("!IK_Foot_L", "x", "foot.L", (0.0, 0.0, 0.05)), ("!IK_Hand_R", "x", "hand.R", (0.0, 0.0, 0.05))])
mapped_i, report_i = run("M3_convention_Unreal_like_inventee", inventive_skel, inventive_truth, 0.97)
check("M4_os_auxiliaires_non_appariés", {"IK_Foot_L", "IK_Hand_R"} <= set(report_i.unused_sources["auxiliaires"]) and not any(p.source.startswith("IK_") for p in report_i.pairs), report_i.unused_sources["auxiliaires"])
mixamo_mirror, mirror_truth = derive(mixamo, prefix="mixamorig:", scale=100.0, flip_x=True)
run("M5_convention_gauche_a_x_negatif", mixamo_mirror, {t: "mixamorig:" + n if not n.startswith("mixamorig:") else n for t, n in mirror_truth.items()}, 0.97)

# --- noms opaques : structure et géométrie seules (colonne à 3 os, sans torsions, échelle 1,12, décalage, ordre des os mélangé) ---------------------------------
rename = opaque_factory()
opaque_skel, opaque_truth = derive(rename, scale=1.12, offset=(0.05, 0.08, 0.0), shuffle=5)
key_bones = {f"{p}{s}" for p in ("arm_upper", "arm_lower", "hand", "leg_upper", "leg_lower", "foot", "clavicle") for s in (".L", ".R")} | {"pelvis", "spine.01", "spine.03", "spine.05", "head", "neck.01"}
mapped_o, report_o = run("M6_noms_opaques_os_principaux", opaque_skel, opaque_truth, 0.85, only=key_bones)
good_all, total_all = accuracy(mapped_o, opaque_truth)
check("M7_noms_opaques_ensemble", good_all / total_all >= 0.75, {"corrects": f"{good_all}/{total_all}", "méthodes": sorted({p.method for p in report_o.pairs})})
check("M8_scores_de_confiance", all(0 < p.score <= 1 for p in report_o.pairs) and np.mean([p.score for p in mapped.values()]) > 0.8 and np.mean([p.score for p in mapped_o.values()]) < np.mean([p.score for p in mapped.values()]),
      {"moyenne_noms": round(float(np.mean([p.score for p in mapped.values()])), 3), "moyenne_opaques": round(float(np.mean([p.score for p in mapped_o.values()])), 3), "faible_confiance_opaques": len(report_o.low_confidence)})

# --- proportions différentes (bruit 1,5 % de la stature, rig 15 % plus large) et structure (un os de chaque bras sans nom reconnaissable) ----------------------------
noisy_skel, noisy_truth = derive(opaque_factory(), scale=1.05, offset=(0.02, 0.04, 0.0), shuffle=9, noise=0.015, x_scale=1.15)
_, report_noisy = run("M13_noms_opaques_proportions_differentes", noisy_skel, noisy_truth, 0.8, only=key_bones)


def half_named(name):
    base = name[:-2] if side(name) else name
    return f"Q{side(name)}" if base == "arm_lower" else mixamo(name)


half_skel, half_truth = derive(half_named, prefix="mixamorig:", scale=100.0)
half_truth = {t: n if n.startswith("mixamorig:") or n.startswith("Q") else "mixamorig:" + n for t, n in half_truth.items()}
mapped_half, _ = run("M14_structure_os_sans_nom_reconnu", half_skel, half_truth, 0.97)
check("M14b_methode_structure", all(mapped_half[t].method in ("structure", "géométrie") for t in ("arm_lower.L", "arm_lower.R")), {t: mapped_half[t].method for t in ("arm_lower.L", "arm_lower.R")})

# --- rapport, conflits, profils, édition ----------------------------------------------------------------------------------------------------------------
summary = report.summary()
check("M9_rapport", set(summary) >= {"appariés", "cibles_sans_source", "sources_inutilisées", "conflits", "faible_confiance", "parents_incohérents", "couverture"} and report.coverage > 0.5
      and report.unmapped_targets and all(isinstance(n, str) for n in report.unmapped_targets), summary)
edited = {t: p.source for t, p in mapped.items()}
edited["arm_lower.L"] = edited["arm_upper.L"]  # conflit introduit à la main
conflicts = mapping.duplicates(edited)
check("M10_detection_de_conflit", list(conflicts.values()) == [["arm_upper.L", "arm_lower.L"]] and not mapping.duplicates({t: p.source for t, p in mapped.items()}), conflicts)
work = Path(tempfile.mkdtemp(prefix="hl_mapping_"))
try:
    path = mapping.save_profile(work, mixamo_skel, mapped, "mon profil")
    data, problems = mapping.load_profile(path, mixamo_skel)
    stale = mapping.Skeleton([("Z" + n) if n.endswith("Hips") else n for n in mixamo_skel.names], mixamo_skel.parents, mixamo_skel.heads, mixamo_skel.tails, "autre")
    _, stale_problems = mapping.load_profile(path, stale)
    applied = mapping.apply_profile(data, stale)
    bad = work / "mauvais.json"
    bad.write_text('{"x": 1}', encoding="utf-8")
    try:
        mapping.load_profile(bad)
        refused = False
    except ValueError:
        refused = True
    check("M11_profils_json", not problems and len(data["mapping"]) == len(mapped) and stale_problems and len(applied) < len(mapped) and refused and path.parent.name == "profiles",
          {"enregistrés": len(data["mapping"]), "problèmes_source_modifiée": stale_problems, "appliqués_sur_source_modifiée": len(applied), "fichier_invalide_refusé": refused})
finally:
    shutil.rmtree(work, ignore_errors=True)
# aucun nom de tiers dans le moteur : le dictionnaire est générique (revue du code source du module)
source_text = (ROOT / "extension/animation/mapping.py").read_text(encoding="utf-8")
check("M12_dictionnaire_generique", all(word not in source_text for word in ("mixamorig:", "SK_", "Epic", "UEFN", "metahuman")) and "FINGER_RULES" in source_text, "pas de nom de rig tiers dans le moteur (le préfixe de convention Mixamo-like est un jeton générique)")

if OUT:
    Path(OUT).write_text(json.dumps(results, indent=1, ensure_ascii=False), encoding="utf-8")
print("RESULT", "FAIL " + ", ".join(failures) if failures else "PASS")
sys.exit(1 if failures else 0)
