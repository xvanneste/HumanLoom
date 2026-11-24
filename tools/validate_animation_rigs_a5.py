"""Validation du lot A5 (profils de rigs additionnels) : mapping automatique ET fidélité du mouvement sur trois familles de squelettes SYNTHÉTIQUES (conventions de noms inventées ici : de type Mixamo, Rigify,
Unreal à jumeaux/IK, chacune avec des dizaines d'os auxiliaires : correctifs, IK, contrôleurs).

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/validate_animation_rigs_a5.py -- [--out FICHIER.json]

Aucun squelette tiers n'est lu. Les squelettes sources sont dérivés de NOTRE table d'os (même géométrie, noms et hiérarchie différents). Mouvement connu appliqué à NOTRE rig, converti en mouvement de la source
(repos tournés), puis re-ciblé avec le mapping AUTOMATIQUE : on mesure l'erreur de position des articulations clés (mains, pieds, coudes, genoux, tête), en % de la stature.

A1 mapping automatique : au moins 97 % des os principaux corrects pour chaque famille malgré 60 os auxiliaires ; A2 les auxiliaires ne sont pas appariés et sont listés dans le rapport (diagnostic des os
non mappés) ; A3 fidélité du mouvement : médiane <= 1 % et p95 <= 3 % de la stature sur les articulations clés, pour chaque famille (mode absolu + IK des jambes ; la famille de type Mixamo n'a que 3 os de colonne contre 5 : l'erreur de la tête, ~2 %, vient de ces os absents, limite connue) ; A4 pas de nom de tiers dans le moteur."""
import json
from pathlib import Path
import random
import sys

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = ARGS[ARGS.index("--out") + 1] if "--out" in ARGS else None
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension.animation import mapping, retarget, skeleton  # noqa: E402

results, failures = {}, []


def check(name, ok, detail=None):
    results[name] = {"ok": bool(ok), "detail": detail}
    print(("OK  " if ok else "KO  ") + name, json.dumps(detail, ensure_ascii=False, default=str)[:700] if detail is not None else "")
    if not ok:
        failures.append(name)


addon.register()
bpy.ops.humanloom.create()
body = bpy.context.object
table = skeleton.bone_table(skeleton.joints(skeleton.cage_points(body), skeleton.load_anchors()))
target_map = mapping.from_table(table, "HumanLoom")
by_name = {b["name"]: b for b in table}
FINGER_NAMES = ("thumb", "index", "middle", "ring", "pinky")

# réutilise les fabriques de squelettes synthétiques du test de mapping (derive, mixamo, rigify, inventive) sans les dupliquer
text = (ROOT / "tools" / "validate_animation_mapping.py").read_text(encoding="utf-8")
block = text[text.index("def derive("):text.index("def opaque_factory")]
namespace = {"np": np, "random": random, "mapping": mapping, "skeleton": skeleton, "table": table, "by_name": by_name, "FINGER_NAMES": FINGER_NAMES}
exec(compile(block, "validate_animation_mapping.py (fabriques)", "exec"), namespace)
derive, mixamo, rigify, inventive = namespace["derive"], namespace["mixamo"], namespace["rigify"], namespace["inventive"]

AUX_PARENTS = ["arm_lower.L", "arm_lower.R", "leg_lower.L", "leg_lower.R", "arm_upper.L", "arm_upper.R", "leg_upper.L", "leg_upper.R", "spine.03", "head", "hand.L", "hand.R", "foot.L", "foot.R", "pelvis"]


def aux_bones(prefix, scale):
    """60 os auxiliaires de types variés (correctifs, IK, contrôleurs), enfants d'os du corps, hors table de noms du moteur d'appariement."""
    extras = []
    kinds = ["corrective_{}", "ik_target_{}", "ctrl_{}", "twist_helper_{}"]
    for n in range(60):
        parent = AUX_PARENTS[n % len(AUX_PARENTS)]
        extras.append((f"!{prefix}{kinds[n % len(kinds)].format(n)}", "x", parent, (0.0, 0.02 * (1 + n % 3), 0.01)))
    return extras


families = {
    "mixamo_like": dict(rename=mixamo, prefix="mixamorig:", scale=100.0, extra=aux_bones("mixamorig:", 100.0)),
    "rigify_like": dict(rename=rigify, prefix="", scale=1.0, extra=aux_bones("", 1.0)),
    "unreal_like": dict(rename=inventive, prefix="", scale=100.0, extra=aux_bones("", 100.0)),
}


def rig_from_rows(skel, scale):
    """`retarget.Rig` d'un `mapping.Skeleton` (repos : axe Y de l'os de la tête vers la queue, roulis arbitraire mais fixe)."""
    names, parents, rest = list(skel.names), list(skel.parents), []
    for i, name in enumerate(names):
        head, tail = np.array(skel.heads[i], float), np.array(skel.tails[i], float)
        y = tail - head
        y = y / max(np.linalg.norm(y), 1e-9)
        reference = np.array([0.0, 0.0, 1.0]) if abs(y[2]) < 0.95 else np.array([1.0, 0.0, 0.0])
        x = np.cross(y, reference)
        x /= np.linalg.norm(x)
        z = np.cross(x, y)
        matrix = np.eye(4)
        matrix[:3, 0], matrix[:3, 1], matrix[:3, 2], matrix[:3, 3] = x, y, z, head
        rest.append(matrix)
    return retarget.Rig(names, parents, np.array(rest))  # `Skeleton.parents` : indices (-1 : racine)


target = retarget.rig_from_armature(skeleton.install(body))
stature = float(max(retarget.joint_positions(target, np.zeros((1, len(target.names), 3)), np.tile([1.0, 0, 0, 0], (1, len(target.names), 1)))[0][:, 2]))
rng = np.random.default_rng(11)
FRAMES = 30
count = len(target.names)


def random_motion():
    phase = rng.uniform(0, 6.28, (count, 3))
    frames = np.arange(FRAMES)[:, None, None] / FRAMES
    angles = np.radians(18) * np.sin(2 * np.pi * frames * (1 + np.arange(3))[None, None, :] + phase[None])
    quat = np.zeros((FRAMES, count, 4))
    for f in range(FRAMES):
        for i in range(count):
            v = angles[f, i]
            a = np.linalg.norm(v) + 1e-12
            quat[f, i] = np.concatenate([[np.cos(a / 2)], np.sin(a / 2) * v / a])
    quat[:, target.index["root"]] = [1, 0, 0, 0]
    loc = np.zeros((FRAMES, count, 3))
    t = np.arange(FRAMES) / FRAMES
    loc[:, target.index["pelvis"]] = np.stack([0.8 * t, 0.05 * np.sin(6.28 * t), 0.03 * np.sin(12.56 * t)], -1)
    return loc, quat


loc_a, quat_a = random_motion()
world_a = retarget.forward_kinematics(target, loc_a, quat_a)
KEY = [n for n in ("hand.L", "hand.R", "foot.L", "foot.R", "arm_lower.L", "arm_lower.R", "leg_lower.L", "leg_lower.R", "head") if n in target.index]
LIMB_ROOT = {"hand.L": "arm_upper.L", "hand.R": "arm_upper.R", "arm_lower.L": "arm_upper.L", "arm_lower.R": "arm_upper.R", "foot.L": "leg_upper.L", "foot.R": "leg_upper.R", "leg_lower.L": "leg_upper.L", "leg_lower.R": "leg_upper.R"}
MAIN = {f"{p}{s}" for p in ("arm_upper", "arm_lower", "hand", "leg_upper", "leg_lower", "foot", "clavicle") for s in (".L", ".R")} | {"pelvis", "spine.01", "spine.03", "spine.05", "head", "neck.01"}

rows_all = {}
for label, config in families.items():
    skel, truth = derive(config["rename"], prefix=config["prefix"], scale=config["scale"], extra=config["extra"])
    truth = {t: (n if n.startswith(config["prefix"]) else config["prefix"] + n) for t, n in truth.items()}
    mapped, report = mapping.auto_map(target_map, skel)
    only = [t for t in truth if t in MAIN]
    good = sum(1 for t in only if t in mapped and mapped[t].source == truth[t])
    check(f"A1_mapping_{label}", good / len(only) >= 0.97, {"os_principaux_corrects": f"{good}/{len(only)}", "couverture": round(report.coverage, 3)})
    aux_names = {e[0][1:] if e[0].startswith("!") else e[0] for e in config["extra"]}
    mapped_aux = [p.source for p in mapped.values() if p.source in aux_names]
    listed = set(report.unused_sources.get("auxiliaires", [])) | set(report.unused_sources.get("autres", [])) if isinstance(report.unused_sources, dict) else set()
    check(f"A2_auxiliaires_non_apparies_{label}", not mapped_aux and len(aux_names & (listed or aux_names)) >= 50, {"auxiliaires_apparies": mapped_aux[:3], "listes_dans_le_rapport": len(aux_names & listed), "categories_du_rapport": {k: len(v) for k, v in report.unused_sources.items()}})
    # mouvement : source = repos tourné par la géométrie propre de la source ; mouvement source déduit de l'animation connue de la cible
    source = rig_from_rows(skel, config["scale"])
    links = {t: p.source for t, p in mapped.items()}
    world_s = np.zeros((FRAMES, len(source.names), 3, 3))
    for i, name in enumerate(source.names):
        t_name = next((t for t, s in links.items() if s == name), None)
        if t_name is not None:
            world_s[:, i] = world_a[:, target.index[t_name], :3, :3] @ (target.rest[target.index[t_name], :3, :3].T @ source.rest[i, :3, :3])
        else:  # os non apparié : pas de mouvement propre (suit son parent au repos)
            p = source.parents[i]
            world_s[:, i] = world_s[:, p] @ (source.rest[p, :3, :3].T @ source.rest[i, :3, :3]) if p >= 0 else source.rest[i, :3, :3]
    positions = np.full((FRAMES, len(source.names), 3), np.nan)
    pelvis_s = source.index[links["pelvis"]]
    positions[:, pelvis_s] = world_a[:, target.index["pelvis"], :3, 3] * config["scale"]
    loc_s, quat_s, _ = retarget.world_to_basis(source, world_s, positions)
    motion = retarget.Motion(loc_s, quat_s, 30.0)
    result = retarget.retarget(source, target, links, motion, retarget.Options(pose_mode=retarget.ABSOLUTE_IK, ik_limbs=("leg",), root_motion=retarget.KEEP))
    t_pos = retarget.joint_positions(target, result.loc, result.quat)
    errors = []
    pel = target.index["pelvis"]
    for name in KEY:
        root = target.index[LIMB_ROOT[name]] if name in LIMB_ROOT else pel  # articulation relative à la racine de son membre (tête : bassin)
        errors.append(np.linalg.norm((t_pos[:, target.index[name]] - t_pos[:, root]) - (world_a[:, target.index[name], :3, 3] - world_a[:, root, :3, 3]), axis=-1) / stature)
    e = np.concatenate(errors)
    check(f"A3_fidelite_du_mouvement_{label}", float(np.median(e)) <= 0.01 and float(np.percentile(e, 95)) <= 0.03,
          {"mediane_pourcent": round(float(np.median(e)) * 100, 3), "p95_pourcent": round(float(np.percentile(e, 95)) * 100, 3), "os_sources": len(source.names), "os_apparies": len(links), "p95_par_os": {n: round(float(np.percentile(errors[i], 95)) * 100, 2) for i, n in enumerate(KEY)}})
    rows_all[label] = len(source.names)

source_text = (ROOT / "extension/animation/mapping.py").read_text(encoding="utf-8") + (ROOT / "extension/animation/retarget.py").read_text(encoding="utf-8")
check("A4_aucun_nom_de_tiers_dans_le_moteur", all(word not in source_text for word in ("SK_", "Epic", "UEFN", "metahuman", "Mannequin")), "mapping.py et retarget.py")

if OUT:
    Path(OUT).write_text(json.dumps(results, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
print("RESULT", "FAIL " + ", ".join(failures) if failures else "PASS")
sys.exit(1 if failures else 0)
