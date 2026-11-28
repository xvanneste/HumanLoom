"""Dégagement PROPRE AU VÊTEMENT aux charnières (coude, genou) : clés de forme de la PIÈCE, pilotées par l'angle de flexion de l'os (CONCEPTION_RIG_CORRECTIFS.md §17).

Problème : au creux du coude ou du genou plié, la peau (linéaire + quaternions duals) écrase la surface du corps ; un vêtement décalé de quelques millimètres du corps (veste : 14 mm) est alors traversé par le corps (8 à 13 mm mesurés).
Principe : pour chaque pièce, côté et angle (30° à 150° par pas de 15°), on évalue le vêtement posé et le corps posé, on repousse chaque sommet qui entre dans la zone d'interdiction (distance signée au corps < dégagement) le long de la normale
du corps (itérations, lissage du champ de déplacement), puis on ramène ce déplacement dans l'espace de REPOS du vêtement par la jacobienne EXACTE de la peau (la peau d'un sommet est affine en sa position de repos : déplacement de repos = A⁻¹ · déplacement posé).
Les clés « HLG <articulation>_<côté> <angle> » sont mélangées par fonctions chapeau de l'angle, lu par des pilotes à expression simple sur la rotation locale de l'os (même mécanisme que `animation/correctives`, mais indépendant : il ne dépend
ni du corps (clés HLC) ni du réglage « Correctifs de flexion »). Aucune clé sur le corps : fonctionne pour toute pièce, y compris robes et pièces importées en mode « pose », et en foule (chaque pièce a son propre maillage).
Coût d'exécution : un mélange de clés par pièce (pas de reconstruction d'arbre : ~1 ms), contre ~15 ms par pièce et par image pour la passe « Dégagement » (Shrinkwrap)."""
import json
import math

import bpy
import numpy as np
from mathutils import Quaternion
from mathutils.bvhtree import BVHTree

KEY_PREFIX = "HLG "
PROP_PREFIX = "hlg_angle_"
BASIS = "Basis"
TEMP_KEY = "tmp_degagement"
JOINTS = {"coude": {"bone": "arm_lower", "radius": 0.22, "angles": [0, 30, 45, 60, 70, 80, 85, 90, 95, 100, 105, 110, 115, 120, 125, 130, 135, 138, 141, 144, 147, 150]},
          "hanche": {"bone": "leg_upper", "radius": 0.30, "forward": True, "defaut": False, "angles": [0, 15, 30, 45, 60, 70, 80, 90, 100, 110, 120]},
          "genou": {"bone": "leg_lower", "radius": 0.26, "angles": [0, 30, 45, 60, 70, 80, 85, 90, 95, 100, 105, 110, 115, 120, 125, 130, 135, 138, 141, 144, 147, 150]}}
CLEARANCE_RATIO = 0.6       # dégagement visé = 0,6 × décalage de la pièce (comme la passe Shrinkwrap)
WATCH_MARGIN = 0.012        # seuls les sommets à moins de 12 mm au-delà du dégagement sont surveillés pendant le repoussement
ENVELOPE = 1               # voisinage (en clés) de l'enveloppe en angle
MIN_PUSH = 2e-5             # sous ce déplacement (m) le sommet n'est pas stocké
SETTLE_ITERATIONS = 30      # itérations de repoussement avant lissage
WARM = 1.0                  # part du déplacement de l'angle précédent reprise comme point de départ
DAMPING = 0.01              # amortissement de l'inversion de la peau (au creux, la peau s'effondre : la jacobienne est presque singulière et le déplacement de repos exploserait)
INFLATE = 1.0               # gonflement du champ avant lissage (le lissage réduit les pointes ; la correction finale ramène à la tolérance)
SMOOTH_PASSES = 2           # passes de lissage du champ de déplacement
FIX_ITERATIONS = 8         # itérations de correction après lissage (le dégagement garanti prime sur le lissage)
ENABLED_PROP = "hlg_actifs"  # sur l'objet pièce : 0 = clés muettes (défaut 1)


def _co(data):
    array = np.empty(len(data) * 3, np.float32)
    data.foreach_get("co", array)
    return array.reshape(-1, 3).astype(np.float64)


def keys_of(mesh):
    keys = getattr(mesh, "shape_keys", None)
    return [] if keys is None else [k for k in keys.key_blocks if k.name.startswith(KEY_PREFIX)]


def installed(obj):
    return bool(keys_of(obj.data))


def _weight_expression(angles, index):
    a = angles[index]
    if index == 0:  # clé de repos (0°) : pleine à 0° et en extension, décroît jusqu'à la clé suivante
        return f"max(0, min(1, ({angles[1]:g} - x) / {angles[1] - a:g}))"
    p = angles[index - 1]
    if index == len(angles) - 1:
        return f"max(0, min(1, (x - {p:g}) / {a - p:g}))"
    n = angles[index + 1]
    return f"max(0, min((x - {p:g}) / {a - p:g}, ({n:g} - x) / {n - a:g}))"


def _add_driver(owner, path, expression, variables):
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
            variable.targets[0].rotation_mode = "QUATERNION"
        else:
            armature, prop = target
            variable.targets[0].id_type = "OBJECT"
            variable.targets[0].id = armature
            variable.targets[0].data_path = f'["{prop}"]'


def _sign(label, armature, body):
    """Sens de rotation (+1 / -1) qui plie l'articulation (mesuré sur la pose : la queue de l'os se rapproche de la tête du parent)."""
    joint, side = label.split("_")
    pose_bone = armature.pose.bones[f"{JOINTS[joint]['bone']}.{side}"]
    saved = pose_bone.rotation_mode, tuple(pose_bone.rotation_quaternion)
    pose_bone.rotation_mode = "QUATERNION"
    scores = {}
    for sign in (1.0, -1.0):
        pose_bone.rotation_quaternion = Quaternion((1.0, 0.0, 0.0), math.radians(40 * sign))
        bpy.context.view_layer.update()
        tail = np.array((armature.matrix_world @ pose_bone.tail)[:])
        scores[sign] = float(np.linalg.norm(tail - np.array((armature.matrix_world @ pose_bone.parent.head)[:])))
    pose_bone.rotation_quaternion = saved[1]
    pose_bone.rotation_mode = saved[0]
    return 1.0 if scores[1.0] <= scores[-1.0] else -1.0


def _ensure_angle_prop(armature, label, sign):
    prop = PROP_PREFIX + label
    if prop in armature.keys():
        return prop
    joint, side = label.split("_")
    bone = f"{JOINTS[joint]['bone']}.{side}"
    armature[prop] = 0.0
    _add_driver(armature, f'["{prop}"]', f"{sign:g} * 114.59156 * atan2(qx * qw / (abs(qw) + 0.000000001), abs(qw))",
                [("qx", "TRANSFORMS", (armature, bone, "ROT_X")), ("qw", "TRANSFORMS", (armature, bone, "ROT_W"))])
    return prop


def _body_skin_only(body):
    """Ne laisse actifs que les modificateurs de peau du corps (morphologie + armatures) ; retourne l'état à rétablir."""
    from . import human
    from .animation import skeleton
    saved = [(m, m.show_viewport) for m in body.modifiers]
    for m in body.modifiers:
        m.show_viewport = m.name in (human.MODIFIER_NAME, skeleton.MODIFIER_NAME, skeleton.DQS_MODIFIER)
    return saved


def _body_tree(body, restrict=True):
    """Arbre BVH du corps posé (modificateurs de peau seulement si `restrict`), repère du monde."""
    saved = _body_skin_only(body) if restrict else []
    bpy.context.view_layer.update()
    evaluated = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    buffer = np.empty(len(mesh.vertices) * 3, np.float32)
    mesh.vertices.foreach_get("co", buffer)
    world = np.array(body.matrix_world)
    points = buffer.reshape(-1, 3).astype(np.float64) @ world[:3, :3].T + world[:3, 3]
    mesh.calc_loop_triangles()
    triangles = np.empty(len(mesh.loop_triangles) * 3, np.int32)
    mesh.loop_triangles.foreach_get("vertices", triangles)
    triangles = triangles.reshape(-1, 3).tolist()
    evaluated.to_mesh_clear()
    points = points.tolist()
    for m, state in saved:
        m.show_viewport = state
    return BVHTree.FromPolygons(points, triangles)


def _garment_points(obj, normals=False):
    """Sommets du vêtement évalués (repère local de l'objet), modificateurs Armature seuls ; avec `normals`, retourne aussi les normales des sommets."""
    bpy.context.view_layer.update()
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    buffer = np.empty(len(mesh.vertices) * 3, np.float32)
    mesh.vertices.foreach_get("co", buffer)
    if normals:
        shading = np.empty(len(mesh.vertices) * 3, np.float32)
        mesh.vertex_normals.foreach_get("vector", shading)
    evaluated.to_mesh_clear()
    points = buffer.reshape(-1, 3).astype(np.float64)
    return (points, shading.reshape(-1, 3).astype(np.float64)) if normals else points


def _dominant_side(obj):
    """Côté (« L » / « R » / «  ») de l'os dominant de chaque sommet de la pièce, d'après ses groupes de sommets nommés par os."""
    from .animation import skeleton
    names = {g.index: g.name for g in obj.vertex_groups}
    sides = []
    for vertex in obj.data.vertices:
        best, side = 0.0, ""
        for g in vertex.groups:
            name = names.get(g.group, "")
            if name in (skeleton.GROUP_LBS, skeleton.GROUP_DQS) or g.weight <= best:
                continue
            best = g.weight
            side = name[-1] if name[-2:-1] == "." and name[-1] in "LR" else ""
        sides.append(side)
    return np.array(sides)


def _adjacency(mesh, count):
    neighbours = [[] for _ in range(count)]
    for edge in mesh.edges:
        a, b = edge.vertices
        neighbours[a].append(b)
        neighbours[b].append(a)
    return neighbours


def _blur(field, region_index, neighbours, factor=0.5):
    """Un passage de lissage du champ de déplacement sur la région (les voisins hors région comptent pour 0)."""
    result = field.copy()
    for i in region_index:
        ring = neighbours[i]
        if ring:
            result[i] = (1 - factor) * field[i] + factor * np.mean([field[j] for j in ring], axis=0)
    return result


def _skin_only(obj):
    saved = [(m, m.show_viewport) for m in obj.modifiers]
    for m in obj.modifiers:
        m.show_viewport = m.type == "ARMATURE"
    return saved


def remove(obj, armature=None):
    """Retire les clés « HLG » de la pièce (et sa clé de base si elle est la seule restante), leurs pilotes, et les propriétés d'angle de l'armature si `armature` est donnée. Retourne le nombre de clés retirées."""
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
    if armature is not None and armature.animation_data is not None:
        for fcurve in [f for f in armature.animation_data.drivers if f.data_path.startswith(f'["{PROP_PREFIX}')]:
            armature.animation_data.drivers.remove(fcurve)
        for prop in [k for k in armature.keys() if k.startswith(PROP_PREFIX)]:
            del armature[prop]
    return removed


def set_enabled(obj, state):
    """Active ou coupe (muet) les clés de dégagement de la pièce. Retourne le nombre de clés modifiées."""
    obj[ENABLED_PROP] = 1 if state else 0
    changed = 0
    for key in keys_of(obj.data):
        if key.mute != (not state):
            key.mute = not state
            changed += 1
    return changed


def enabled(obj):
    return bool(obj.get(ENABLED_PROP, 1))


def _clearance_of(obj):
    try:
        offset = float(json.loads(obj.get("hl_garment_params", "{}")).get("decalage_mm", 6.0))
    except (TypeError, ValueError):
        offset = 6.0
    return max(offset, 1.0) / 1000.0 * CLEARANCE_RATIO


def _envelope(deltas, radius=ENVELOPE):
    """Enveloppe en angle : pour chaque sommet et chaque clé, le déplacement de plus grande norme parmi les clés voisines (± `radius`). Entre deux clés, le mélange linéaire de deux déplacements qui ne varient pas brusquement ne
    peut plus laisser un sommet dans le corps (mesuré : sans enveloppe, des pointes de plusieurs millimètres entre les clés, à cause des sommets dont le point le plus proche du corps change de côté au creux)."""
    norms = np.linalg.norm(deltas, axis=2)
    result = deltas.copy()
    for k in range(len(deltas)):
        window = list(range(max(0, k - radius), min(len(deltas), k + radius + 1)))
        best = np.argmax(norms[window], axis=0)
        result[k] = deltas[np.array(window)[best], np.arange(deltas.shape[1])]
    return result


def _penetration_state(tree, points, indices):
    """Pour chaque sommet de `indices` : (distance signée au corps, normale du corps au point le plus proche)."""
    signed = np.empty(len(indices))
    normals = np.zeros((len(indices), 3))
    for row, i in enumerate(indices):
        location, normal, _index, _dist = tree.find_nearest(points[i].tolist())
        if location is None:
            signed[row] = 1.0
            continue
        signed[row] = float((points[i] - np.array(location)) @ np.array(normal))
        normals[row] = normal
    return signed, normals


def _forward_sign(label, armature):
    """Hanche : sens de rotation qui fait avancer le genou (direction du pied au repos), seul repère sans ambiguïté pour une flexion avant."""
    joint, side = label.split("_")
    pose_bone = armature.pose.bones[f"{JOINTS[joint]['bone']}.{side}"]
    foot = armature.pose.bones[f"foot.{side}"]
    forward = np.array((armature.matrix_world.to_3x3() @ (foot.tail - foot.head))[:])
    forward[2] = 0.0
    forward /= max(np.linalg.norm(forward), 1e-9)
    saved = pose_bone.rotation_mode, tuple(pose_bone.rotation_quaternion)
    pose_bone.rotation_mode = "QUATERNION"
    pose_bone.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
    bpy.context.view_layer.update()
    rest = np.array((armature.matrix_world @ pose_bone.tail)[:])
    best, value = 1.0, -1e9
    for sign in (1.0, -1.0):
        pose_bone.rotation_quaternion = Quaternion((1.0, 0.0, 0.0), math.radians(40 * sign))
        bpy.context.view_layer.update()
        move = np.array((armature.matrix_world @ pose_bone.tail)[:]) - rest
        if float(move @ forward) > value:
            best, value = sign, float(move @ forward)
    pose_bone.rotation_quaternion = saved[1]
    pose_bone.rotation_mode = saved[0]
    return best


def generate(obj, body, armature, joints=None, report=None):
    """GÉNÉRATEUR qui calcule et installe les clés de dégagement de la pièce `obj` (voir l'en-tête) ; produit `(étiquette, étape, total)`. Remet les os dans leur pose d'origine à la fin. Retourne
    `{étiquette: nombre de sommets déplacés}`. `report` (dict) reçoit pour chaque étiquette et angle la profondeur maximale avant déplacement et le résidu prédit (information)."""
    remove(obj)
    wanted = [j for j in (joints or [k for k, v in JOINTS.items() if v.get("defaut", True)]) if j in JOINTS]
    mesh = obj.data
    count = len(mesh.vertices)
    sides = _dominant_side(obj)
    neighbours = _adjacency(mesh, count)
    clearance = _clearance_of(obj)
    world = np.array(obj.matrix_world.to_3x3())
    world_inverse = np.linalg.inv(world)
    translation = np.array(obj.matrix_world.translation)
    animation = armature.animation_data
    saved_animation = (animation.action, animation.use_nla) if animation is not None else None
    if animation is not None:  # une animation (foule : bandes NLA) réécrirait la pose à chaque mise à jour du graphe
        animation.action = None
        animation.use_nla = False
    saved_all = {b.name: (tuple(b.location), b.rotation_mode, tuple(b.rotation_quaternion), tuple(b.rotation_euler), tuple(b.scale)) for b in armature.pose.bones}
    for b in armature.pose.bones:
        b.location, b.rotation_mode, b.rotation_quaternion, b.scale = (0.0, 0.0, 0.0), "QUATERNION", (1.0, 0.0, 0.0, 0.0), (1.0, 1.0, 1.0)  # pose de repos : le calcul ne dépend pas de la pose courante
    bpy.context.view_layer.update()
    saved_mods = _skin_only(obj)
    saved_body = _body_skin_only(body)
    was_basis = mesh.shape_keys is None
    if was_basis:
        obj.shape_key_add(name=BASIS, from_mix=False)
    basis_block = mesh.shape_keys.key_blocks[0]
    basis = _co(basis_block.data)
    temp = obj.shape_key_add(name=TEMP_KEY, from_mix=False)
    temp.relative_key = basis_block
    temp.value = 1.0
    payload = {}
    pending = [(joint, side) for joint in wanted for side in ("L", "R") if f"{JOINTS[joint]['bone']}.{side}" in armature.pose.bones]
    total = sum(len(JOINTS[j]["angles"]) for j, _ in pending)
    done = 0
    try:
        for joint, side in pending:
            spec = JOINTS[joint]
            label = f"{joint}_{side}"
            bone_name = f"{spec['bone']}.{side}"
            pose_bone = armature.pose.bones[bone_name]
            pose_bone.rotation_mode = "QUATERNION"
            pose_bone.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
            bpy.context.view_layer.update()
            pivot = np.array((armature.matrix_world @ pose_bone.head)[:])
            allowed = np.ones(count, bool)  # pas de filtre de côté : un vêtement peut être traversé par le membre opposé (cuisse contre le centre d'une jupe) ; seuls les sommets qui pénètrent réellement sont déplacés
            sign = _forward_sign(label, armature) if spec.get("forward") else _sign(label, armature, body)
            deltas = []
            previous = np.zeros((count, 3))  # déplacement de repos de l'angle précédent : point de départ du suivant (champ continu en angle, donc interpolable entre les clés)
            for angle in spec["angles"]:
                pose_bone.rotation_quaternion = Quaternion((1.0, 0.0, 0.0), math.radians(sign * angle))
                tree = _body_tree(body, restrict=False)
                temp.data.foreach_set("co", basis.ravel())
                zero = _garment_points(obj)
                start = zero @ world.T + translation
                near = np.where((np.linalg.norm(start - pivot, axis=1) < spec["radius"]) & allowed)[0]
                if len(near) == 0:
                    deltas.append(np.zeros((count, 3)))
                    done += 1
                    yield label, done, total
                    continue
                # jacobienne exacte de la peau (déplacement simultané de tous les sommets : la peau agit sommet par sommet)
                eps = 0.001
                jac = np.zeros((count, 3, 3))
                for k in range(3):
                    shifted = basis.copy()
                    shifted[:, k] += eps
                    temp.data.foreach_set("co", shifted.ravel())
                    jac[:, :, k] = (_garment_points(obj) - zero) / eps
                temp.data.foreach_set("co", basis.ravel())
                push = WARM * np.einsum("vij,vj->vi", jac, previous) @ world.T
                push[np.setdiff1d(np.arange(count), near)] = 0.0
                signed0, _normals = _penetration_state(tree, start + push, near)
                watch = near[signed0 < clearance + WATCH_MARGIN]  # seuls ces sommets (et leurs voisins) peuvent entrer dans la zone d'interdiction pendant le repoussement
                if len(watch):
                    ring = np.concatenate([np.array(neighbours[i], int) for i in watch if neighbours[i]] + [watch])
                    watch = np.intersect1d(np.unique(ring), near)

                def settle(limit, push, watch=watch, tree=tree, start=start):
                    for _ in range(limit):
                        signed, normals = _penetration_state(tree, start + push, watch)
                        need = clearance - signed
                        move = need > 3e-4
                        if not move.any():
                            break
                        push[watch[move]] += need[move, None] * normals[move]
                    return push

                push = settle(SETTLE_ITERATIONS, push)
                for _ in range(SMOOTH_PASSES):
                    push = _blur(push, watch, neighbours)
                push = settle(FIX_ITERATIONS, push)
                if report is not None:
                    residual, _n = _penetration_state(tree, start + push, near)
                    report.setdefault(label, {})[angle] = {"penetration_max_mm": round(float(-signed0.min()) * 1000, 2), "residuel_predit_mm": round(float(-residual.min()) * 1000, 2),
                                                           "sommets_deplaces": int((np.linalg.norm(push, axis=1) > MIN_PUSH).sum())}
                local_push = push @ world_inverse.T
                delta = np.zeros((count, 3))
                for i in np.where(np.linalg.norm(local_push, axis=1) > MIN_PUSH)[0]:
                    delta[i] = np.linalg.solve(jac[i].T @ jac[i] + DAMPING * np.eye(3), jac[i].T @ local_push[i])
                deltas.append(delta)
                previous = delta
                done += 1
                yield label, done, total
            deltas = np.array(deltas)
            active = np.where(np.abs(deltas).max(axis=(0, 2)) > MIN_PUSH)[0]
            if len(active):
                payload[label] = {"sign": sign, "angles": list(spec["angles"]), "vertices": active, "delta": deltas[:, active]}
    finally:
        obj.shape_key_remove(temp)
        for name, (location, mode, quaternion, euler, scale) in saved_all.items():
            b = armature.pose.bones[name]
            b.location, b.rotation_mode, b.rotation_quaternion, b.rotation_euler, b.scale = location, mode, quaternion, euler, scale
        if animation is not None:
            animation.action, animation.use_nla = saved_animation
        for m, state in saved_mods + saved_body:
            m.show_viewport = state
        bpy.context.view_layer.update()
    created = {}
    for label, data in payload.items():
        prop = _ensure_angle_prop(armature, label, data["sign"])
        angles = data["angles"]
        for index, angle in enumerate(angles):
            key = obj.shape_key_add(name=f"{KEY_PREFIX}{label} {angle:g}", from_mix=False)
            coords = basis.copy()
            coords[data["vertices"]] += data["delta"][index]
            key.data.foreach_set("co", coords.ravel())
            key.value = 0.0
            key.relative_key = basis_block
            key.mute = not enabled(obj)
            _add_driver(mesh.shape_keys, f'key_blocks["{key.name}"].value', _weight_expression(angles, index), [("x", "SINGLE_PROP", (armature, prop))])
        created[label] = int(len(data["vertices"]))
    if not created and was_basis and mesh.shape_keys is not None and len(mesh.shape_keys.key_blocks) == 1:
        obj.shape_key_remove(mesh.shape_keys.key_blocks[0])
    from . import crowd
    if mesh.shape_keys is not None and mesh.get(crowd.OWNED_KEY):  # pièce d'un personnage de foule : le bloc de clés créé ici appartient à la foule (effacement / régénération)
        mesh.shape_keys[crowd.OWNED_KEY] = True
    return created


def build(obj, body=None, armature=None, joints=None, report=None):
    """Calcul complet (consomme le générateur) ; retourne `{étiquette: sommets déplacés}`. Sans squelette : ne fait rien."""
    from .animation import skeleton
    body = body or obj.parent
    if armature is None:
        rigs = skeleton.rigs_of(body)
        if not rigs:
            return {}
        armature = rigs[0]
    return _drain(generate(obj, body, armature, joints, report))


def _drain(generator):
    try:
        while True:
            next(generator)
    except StopIteration as stop:
        return stop.value
