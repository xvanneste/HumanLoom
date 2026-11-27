"""Formes correctives des articulations à charnière (coude, genou) : clés de forme sur le maillage de base, pilotées par l'ANGLE de flexion de l'os (CONCEPTION_RIG_CORRECTIFS.md §6–9).

Principe : la peau (linéaire + quaternions duals) plisse et écrase les creux articulaires en flexion forte. Pour chaque articulation et chaque côté, des clés de forme calculées HORS LIGNE (`tools/build_hinge_correctives.py` : cibles par
optimisation, encodage par évaluation-et-correction dans le pipeline réel) sont mélangées par des fonctions chapeau de l'angle (interpolation linéaire entre les angles échantillonnés). L'angle est lu sur la rotation LOCALE de l'os
(quaternion : 2·atan2(x, w), sans décomposition d'Euler) par un pilote de propriété de l'armature ; les pilotes sont des expressions SIMPLES (aucun script Python à l'exécution).
Le mode de rotation de l'os est sans importance (la variable du pilote lit le quaternion local). Les correctifs ne touchent jamais le visage ni les yeux (régions autour des coudes et des genoux seulement).
Limites : générés sur le corps par défaut et appliqués aux autres morphologies par la morphologie du groupe de nœuds (mesuré par `tools/validate_correctives.py`) ; aucun effet si le fichier de données est absent."""
import math
from pathlib import Path

import bpy
import numpy as np
from mathutils import Quaternion

from . import correctives_solver as solver

DATA = Path(__file__).resolve().parent.parent / "data" / "human_rig_hinges.npz"
KEY_PREFIX = "HLC "
PROP_PREFIX = "hlc_angle_"
BONES = {"coude": "arm_lower", "genou": "leg_lower"}
BASIS = "Basis"
SOURCE_PROP = "hlc_source"          # « generique » (données livrées, corps par défaut) ou empreinte de la morphologie pour laquelle les correctifs ont été recalculés
JOINTS = {"coude": {"radius": 0.22, "dists": (0.0, 0.03, 0.06), "angles": [15, 30, 45, 60, 75, 90, 105, 120, 135, 150]},
          "genou": {"radius": 0.26, "dists": (0.0, 0.04, 0.08), "angles": [15, 30, 45, 60, 75, 90, 105, 120, 135, 150]}}  # 150° : la bibliothèque réelle va jusqu'à ~151° (mesuré)
SOLVE = {"la": 150.0, "ls": 2.0, "lf": 1.0}  # poids des termes d'aire de section, de lissage et de plis : réglés par mesure
TEMP_KEY = "tmp_correctif"
ENABLED_PROP = "hlc_actifs"         # correctifs ACTIFS (1) ou coupés (absent/0, défaut) : décision de l'utilisateur, le coude et le genou sans correctifs sont jugés corrects ; les rides des correctifs sont rejetées


def _co(data):
    """Positions d'un bloc de clé (ou des sommets) sous forme (n, 3) : lecture en bloc (beaucoup plus rapide qu'une boucle Python)."""
    array = np.empty(len(data) * 3, np.float32)
    data.foreach_get("co", array)
    return array.reshape(-1, 3).astype(np.float64)


def available():
    return DATA.exists()


def labels(data=None):
    """Étiquettes disponibles « coude_L »… d'après les données (fichier livré par défaut)."""
    if data is None:
        if not available():
            return []
        data = np.load(DATA, allow_pickle=False)
    return sorted(k[: -len("_angles")] for k in data if k.endswith("_angles"))


def _add_driver(owner, path, expression, variables):
    """Ajoute un pilote à expression simple sur `owner` (ID) ; `variables` : liste de (nom, type, cible)."""
    fcurve = owner.driver_add(path)
    driver = fcurve.driver
    driver.type = "SCRIPTED"
    driver.expression = expression
    for name, kind, target in variables:
        variable = driver.variables.new()
        variable.name = name
        variable.type = kind
        if kind == "TRANSFORMS":
            armature, bone, channel = target
            variable.targets[0].id = armature
            variable.targets[0].bone_target = bone
            variable.targets[0].transform_type = channel
            variable.targets[0].transform_space = "LOCAL_SPACE"
            variable.targets[0].rotation_mode = "QUATERNION"  # composantes du quaternion LOCAL quel que soit le mode de rotation de l'os (mesuré : sans cela ROT_W vaut 0)
        else:
            armature, prop = target
            variable.targets[0].id_type = "OBJECT"
            variable.targets[0].id = armature
            variable.targets[0].data_path = f'["{prop}"]'
    return driver


def _weight_expression(angles, index):
    """Chapeau linéaire de l'angle `x` autour de `angles[index]` (le premier voisin est 0 : repos sans correctif ; le dernier reste à 1 au-delà)."""
    a = angles[index]
    p = angles[index - 1] if index > 0 else 0.0
    if index == len(angles) - 1:
        return f"max(0, min(1, (x - {p:g}) / {a - p:g}))"
    n = angles[index + 1]
    return f"max(0, min((x - {p:g}) / {a - p:g}, ({n:g} - x) / {n - a:g}))"


def keys_of(mesh):
    keys = getattr(mesh, "shape_keys", None)
    return [] if keys is None else [k for k in keys.key_blocks if k.name.startswith(KEY_PREFIX)]


def installed(body):
    return bool(keys_of(body.data))


def enabled(body):
    """Vrai si les correctifs de flexion sont actifs (défaut : coupés)."""
    rigs = [c for c in body.children if c.type == "ARMATURE" and c.get("hl_rig")]
    return bool(rigs and rigs[0].get(ENABLED_PROP, 0))


def set_enabled(body, state):
    """Active ou coupe les correctifs de flexion du corps et de ses vêtements (clés muettes ; les pilotes restent en place). Retourne le nombre de clés modifiées."""
    rigs = [c for c in body.children if c.type == "ARMATURE" and c.get("hl_rig")]
    if rigs:
        rigs[0][ENABLED_PROP] = 1 if state else 0
    changed = 0
    for obj in [body] + list(_garments(body)):
        for key in keys_of(obj.data):
            if key.mute != (not state):
                key.mute = not state
                changed += 1
    return changed


def install(body, armature, data=None, source="generique"):
    """Crée les clés de forme et les pilotes sur `body` (maillage de base) d'après `data` (par défaut `human_rig_hinges.npz`) ; ne fait rien si les données sont absentes ou si c'est déjà installé. `source` est mémorisée sur l'armature.
    Retourne le nombre de clés créées."""
    if data is None:
        if not available():
            return 0
        data = np.load(DATA, allow_pickle=False)
    if installed(body):
        return 0
    mesh = body.data
    if mesh.shape_keys is None:
        body.shape_key_add(name=BASIS, from_mix=False)
    basis_block = mesh.shape_keys.key_blocks[0]
    basis = _co(basis_block.data)
    created = 0
    armature[SOURCE_PROP] = str(source)
    for label in labels(data):
        joint, side = label.split("_")
        bone = f"{BONES[joint]}.{side}"
        prop = PROP_PREFIX + label
        armature[prop] = 0.0
        sign = float(data[f"{label}_sign"])
        _add_driver(armature, f'["{prop}"]', f"{sign:g} * 114.59156 * atan2(qx * qw / (abs(qw) + 0.000000001), abs(qw))",
                    [("qx", "TRANSFORMS", (armature, bone, "ROT_X")), ("qw", "TRANSFORMS", (armature, bone, "ROT_W"))])
        angles = [float(a) for a in data[f"{label}_angles"]]
        vertices, deltas = data[f"{label}_vertices"], data[f"{label}_delta"]
        for index, angle in enumerate(angles):
            key = body.shape_key_add(name=f"{KEY_PREFIX}{label} {angle:g}", from_mix=False)
            coords = basis.copy()
            coords[vertices] += deltas[index]
            key.data.foreach_set("co", coords.ravel())
            key.value = 0.0
            key.relative_key = basis_block
            key.mute = not bool(armature.get(ENABLED_PROP, 0))
            _add_driver(mesh.shape_keys, f'key_blocks["{key.name}"].value', _weight_expression(angles, index), [("x", "SINGLE_PROP", (armature, prop))])
            created += 1
    for garment in _garments(body):
        attach_garment(garment, body)
    return created


def remove(body, armature=None):
    """Retire les clés de forme et les pilotes de correctifs (et la clé de base si elle est la seule restante) ; retire les propriétés de l'armature. Retourne le nombre d'éléments retirés."""
    removed = 0
    for garment in _garments(body):
        removed += detach_garment(garment)
    mesh = body.data
    keys = mesh.shape_keys
    if keys is not None:
        if keys.animation_data is not None:
            for fcurve in [f for f in keys.animation_data.drivers if f.data_path.startswith(f'key_blocks["{KEY_PREFIX}')]:
                keys.animation_data.drivers.remove(fcurve)
        for block in [b for b in keys.key_blocks if b.name.startswith(KEY_PREFIX)]:
            body.shape_key_remove(block)
            removed += 1
        if mesh.shape_keys is not None and len(mesh.shape_keys.key_blocks) == 1 and mesh.shape_keys.key_blocks[0].name == BASIS:
            body.shape_key_remove(mesh.shape_keys.key_blocks[0])
    if armature is not None:
        if armature.animation_data is not None:
            for fcurve in [f for f in armature.animation_data.drivers if f.data_path.startswith(f'["{PROP_PREFIX}')]:
                armature.animation_data.drivers.remove(fcurve)
        for prop in [k for k in armature.keys() if k.startswith(PROP_PREFIX) or k in (SOURCE_PROP, ENABLED_PROP)]:
            del armature[prop]
            removed += 1
    return removed


# --- recalcul sur la morphologie courante ----------------------------------------------------------------------------------------------------------------------

def _evaluate(body):
    """Cage posée (HL Human + armatures de HL Rig)."""
    from .. import human
    from . import skeleton
    saved = [(m, m.show_viewport) for m in body.modifiers]
    for m in body.modifiers:
        m.show_viewport = m.name in (human.MODIFIER_NAME, skeleton.MODIFIER_NAME, skeleton.DQS_MODIFIER)
    human.touch(body)
    bpy.context.view_layer.update()
    evaluated = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    points = np.array([v.co[:] for v in mesh.vertices])
    evaluated.to_mesh_clear()
    for m, state in saved:
        m.show_viewport = state
    return points


def generate(body, armature, joints=None):
    """GÉNÉRATEUR qui recalcule les correctifs sur la morphologie COURANTE du corps (cibles par optimisation, encodage exact par jacobienne de différences finies dans le pipeline réel) ; produit `(étiquette, étape, total)` après chaque angle
    et retourne le dictionnaire de données (même format que `human_rig_hinges.npz`). Les clés de correctifs existantes doivent avoir été retirées avant (voir `rebuild_steps`). Remet les os dans leur pose d'origine à la fin."""
    from . import skeleton
    mesh = body.data
    if mesh.shape_keys is None:
        body.shape_key_add(name=BASIS, from_mix=False)
    basis = np.array([v.co[:] for v in mesh.shape_keys.key_blocks[0].data])
    rest = skeleton.cage_points(body)
    mesh.calc_loop_triangles()
    tris = np.array([t.vertices[:] for t in mesh.loop_triangles])
    edges = np.array([e.vertices[:] for e in mesh.edges])
    n = len(rest)
    groups = {g.index: g.name for g in body.vertex_groups}
    dominant = []
    for vertex in mesh.vertices:
        candidates = [g for g in vertex.groups if groups[g.group] not in (skeleton.GROUP_LBS, skeleton.GROUP_DQS)]
        dominant.append(groups[max(candidates, key=lambda g: g.weight).group] if candidates else "")
    # sommets DU MÊME CÔTÉ : os dominant dont le nom finit par le suffixe du côté. Sans cela, la région autour d'un genou ou d'un coude englobe le membre OPPOSÉ ou le tronc (distance < rayon) : ses sommets recevaient
    # des déplacements pour une flexion qu'ils ne subissent pas (mesuré : jambe droite fléchie ⇒ plis +28 au genou gauche sur des poses réelles)
    same_side = {side: np.array([d.endswith("." + side) for d in dominant]) for side in ("L", "R")}
    wanted = list(joints or JOINTS)
    total = sum(len(JOINTS[j]["angles"]) for j in wanted) * 2
    done = 0
    payload = {}
    saved = {}
    key = None
    try:
        for joint in wanted:
            spec = JOINTS[joint]
            for side in ("L", "R"):
                bone_name = f"{BONES[joint]}.{side}"
                pose_bone = armature.pose.bones[bone_name]
                if bone_name not in saved:
                    saved[bone_name] = (pose_bone.rotation_mode, tuple(pose_bone.rotation_quaternion))
                pose_bone.rotation_mode = "QUATERNION"
                bone = armature.data.bones[bone_name]
                pivot = np.array(bone.head_local)
                axis = (np.array(bone.tail_local) - pivot) / np.linalg.norm(np.array(bone.tail_local) - pivot)
                dist = np.linalg.norm(rest - pivot, axis=1)
                free = np.where((dist < spec["radius"]) & same_side[side])[0]
                fade = np.clip((dist[free] - 0.8 * spec["radius"] + 0.05) / 0.1, 0.0, 1.0)
                pull = 1.0 + 300.0 * fade * fade * (3 - 2 * fade)
                region = np.zeros(n, bool)
                region[free] = True
                sections = []
                for d in spec["dists"]:
                    sel = solver.section_selection(rest, pivot, axis, pivot, d)
                    if len(sel) >= 8 and region[sel].all():
                        sections.append((sel, solver.section_area(rest, sel)))
                problem = solver.Problem(rest, edges, tris, free, sections, np.ones(len(free)), pull)
                parent = pose_bone.parent
                scores = {}
                for sign in (1.0, -1.0):
                    pose_bone.rotation_quaternion = Quaternion((1.0, 0.0, 0.0), math.radians(40 * sign))
                    bpy.context.view_layer.update()
                    tail = np.array((armature.matrix_world @ pose_bone.tail)[:])
                    scores[sign] = float(np.linalg.norm(tail - np.array((armature.matrix_world @ parent.head)[:])))
                sign = 1.0 if scores[1.0] <= scores[-1.0] else -1.0
                deltas = []
                for angle in spec["angles"]:
                    pose_bone.rotation_quaternion = Quaternion((1.0, 0.0, 0.0), math.radians(sign * angle))
                    if key is not None:
                        body.shape_key_remove(key)
                    key = body.shape_key_add(name=TEMP_KEY, from_mix=False)
                    key.value = 0.0
                    start = _evaluate(body)
                    target = problem.solve(start, **SOLVE)

                    def at(d, key=key, free=free):
                        coords = basis.copy()
                        coords[free] += d
                        key.data.foreach_set("co", coords.ravel())
                        key.value = 1.0
                        return _evaluate(body)

                    zero = at(np.zeros((len(free), 3)))[free]
                    eps = 0.001
                    jac = np.zeros((len(free), 3, 3))
                    for k in range(3):
                        shift = np.zeros((len(free), 3))
                        shift[:, k] = eps
                        jac[:, :, k] = (at(shift)[free] - zero) / eps
                    jtj = np.einsum("vji,vjk->vik", jac, jac) + 1e-4 * np.eye(3)[None]

                    def pseudo(r, jac=jac, jtj=jtj):
                        return np.linalg.solve(jtj, np.einsum("vji,vj->vi", jac, r)[:, :, None])[:, :, 0]

                    delta = pseudo((target - start)[free])
                    best, residual = delta.copy(), (target - at(delta))[free]
                    for _ in range(3):
                        candidate = best + pseudo(residual)
                        new = (target - at(candidate))[free]
                        better = np.linalg.norm(new, axis=1) < np.linalg.norm(residual, axis=1)
                        best[better], residual[better] = candidate[better], new[better]
                    worse = np.linalg.norm(residual, axis=1) > np.linalg.norm((target - start)[free], axis=1)
                    best[worse] = 0.0
                    deltas.append(best)
                    done += 1
                    yield f"{joint}_{side}", done, total
                deltas = np.array(deltas)
                active = np.where(np.abs(deltas).max(axis=(0, 2)) > 2e-5)[0]
                label = f"{joint}_{side}"
                payload[f"{label}_angles"] = np.array(spec["angles"], float)
                payload[f"{label}_sign"] = np.array(sign)
                payload[f"{label}_vertices"] = free[active].astype(np.int32)
                payload[f"{label}_delta"] = deltas[:, active].astype(np.float32)
    finally:
        if key is not None and mesh.shape_keys is not None and TEMP_KEY in mesh.shape_keys.key_blocks.keys():
            body.shape_key_remove(mesh.shape_keys.key_blocks[TEMP_KEY])
        for bone_name, (mode, quaternion) in saved.items():
            armature.pose.bones[bone_name].rotation_quaternion = quaternion
            armature.pose.bones[bone_name].rotation_mode = mode
        bpy.context.view_layer.update()
    return payload


def rebuild_steps(body, armature):
    """Générateur complet du recalcul : retire les correctifs en place, recalcule sur la morphologie courante, réinstalle ; produit `(étiquette, étape, total)`."""
    from . import skeleton
    remove(body, armature)
    payload = yield from generate(body, armature)
    install(body, armature, data=payload, source=skeleton.fingerprint(body))
    return payload


def status(body):
    """« absent » (aucun correctif), « generique » (données livrées pour le corps par défaut), « a_jour » (recalculés pour cette morphologie) ou « obsolete » (recalculés pour une autre)."""
    from . import skeleton
    rigs = skeleton.rigs_of(body)
    if not rigs or not installed(body):
        return "absent"
    source = str(rigs[0].get(SOURCE_PROP, "generique"))
    if source == "generique":
        return "generique"
    return "a_jour" if source == skeleton.fingerprint(body) else "obsolete"


# --- vêtements (sous-maillages du corps) ------------------------------------------------------------------------------------------------------------------------

def _garments(body):
    from .. import garments
    return garments.garments_of(body)


def _by_label(mesh):
    """{étiquette: [(angle, bloc de clé)]} trié par angle, d'après les noms « HLC coude_L 30 »."""
    table = {}
    for key in keys_of(mesh):
        label, angle = key.name[len(KEY_PREFIX):].rsplit(" ", 1)
        table.setdefault(label, []).append((float(angle), key))
    return {label: sorted(rows, key=lambda r: r[0]) for label, rows in table.items()}


def attach_garment(obj, body):
    """Reporte les correctifs du corps sur une pièce qui est un SOUS-MAILLAGE du corps (indices `sommets_du_corps`) : mêmes déplacements aux mêmes sommets, mêmes pilotes. Sans effet pour les robes, les pièces importées et si le corps n'a
    pas de correctifs. Retourne le nombre de clés créées."""
    import json
    from ..garments import PARAMS
    params = json.loads(obj.get(PARAMS, "{}"))
    used = params.get("sommets_du_corps") or []
    if not used or "robe" in params or "mode" in params or not installed(body) or keys_of(obj.data):
        return 0
    rigs = [c for c in body.children if c.type == "ARMATURE" and c.get("hl_rig")]
    if not rigs:
        return 0
    armature = rigs[0]
    used = np.array(used)
    body_basis = _co(body.data.shape_keys.key_blocks[0].data)
    mesh = obj.data
    if mesh.shape_keys is None:
        obj.shape_key_add(name=BASIS, from_mix=False)
    basis_block = mesh.shape_keys.key_blocks[0]
    basis = _co(basis_block.data)
    created = 0
    for label, rows in _by_label(body.data).items():
        angles = [a for a, _ in rows]
        prop = PROP_PREFIX + label
        for index, (angle, body_key) in enumerate(rows):
            delta = (_co(body_key.data) - body_basis)[used]
            key = obj.shape_key_add(name=body_key.name, from_mix=False)
            key.data.foreach_set("co", (basis + delta).ravel())
            key.value = 0.0
            key.relative_key = basis_block
            key.mute = body_key.mute  # même état que la clé du corps (coupées pendant une simulation de tissu)
            _add_driver(mesh.shape_keys, f'key_blocks["{key.name}"].value', _weight_expression(angles, index), [("x", "SINGLE_PROP", (armature, prop))])
            created += 1
    return created


def detach_garment(obj):
    """Retire les clés de correctifs d'une pièce (et sa clé de base si elle est la seule restante). Retourne le nombre de clés retirées."""
    mesh = obj.data
    keys = mesh.shape_keys
    removed = 0
    if keys is not None:
        if keys.animation_data is not None:
            for fcurve in [f for f in keys.animation_data.drivers if f.data_path.startswith(f'key_blocks["{KEY_PREFIX}')]:
                keys.animation_data.drivers.remove(fcurve)
        for block in [b for b in keys.key_blocks if b.name.startswith(KEY_PREFIX)]:
            obj.shape_key_remove(block)
            removed += 1
        if mesh.shape_keys is not None and len(mesh.shape_keys.key_blocks) == 1 and mesh.shape_keys.key_blocks[0].name == BASIS:
            obj.shape_key_remove(mesh.shape_keys.key_blocks[0])
    return removed


def garment_deltas(obj):
    """Déplacements (par clé) d'une pièce, à mémoriser AVANT de réécrire ses positions (`update_garment`) ; None si elle n'a pas de correctifs."""
    keys = keys_of(obj.data)
    if not keys:
        return None
    basis = _co(obj.data.shape_keys.key_blocks[0].data)
    return {k.name: _co(k.data) - basis for k in keys}


def garment_restore(obj, deltas):
    """Réécrit la clé de base de la pièce d'après ses positions courantes et reconstruit chaque clé = base + déplacement mémorisé."""
    if not deltas:
        return
    mesh = obj.data
    coords = _co(mesh.vertices)
    blocks = mesh.shape_keys.key_blocks
    blocks[0].data.foreach_set("co", coords.ravel())
    for name, delta in deltas.items():
        blocks[name].data.foreach_set("co", (coords + delta).ravel())
