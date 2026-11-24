"""Moteur de foule natif (lots C1 et C2) : ensembles d'éléments variables, tirage à graine, foule FIGÉE, comportements, trajectoires, évitement, décalage de phase, niveaux de détail.

Principes
- Un `spec` (dictionnaire JSON) décrit des ENSEMBLES : plages de morphologie (sexe, âge, contrôles du corps), expressions, comportements pondérés (marche, course, attente, discussion, saut, traversée),
  vitesses, zones (trottoirs, passages piétons, aire libre), variantes extensibles (`variants` : tenues, coiffures… ; appliquées par des « applicateurs » enregistrés par les lots qui les fournissent).
- Le tirage de chaque personnage est déterministe : `default_rng([graine, régénération, indice])`. La foule est FIGÉE : spec, tirages et résultats sont enregistrés dans la scène (`scene["humanloom_crowd"]`)
  et dans les objets ; rien n'est recalculé à la réouverture ni au changement d'un réglage. Seules `generate(replace=True)`, `regenerate_member` et `regenerate_all` la modifient.
- Garde-fous : valeurs bornées par les prises du groupe de nœuds, somme adiposité + muscles bornée, distance minimale entre personnages dans l'espace des paramètres (pas de clones).
- Les animations de comportement viennent de `spec["clips"][comportement]` (noms d'actions de la bibliothèque de l'utilisateur, déjà re-ciblées) ; à défaut, des clips SYNTHÉTIQUES simples (balancement
  des jambes et des bras, respiration, gestes) servent de bouchon et pour les tests. Aucune donnée tierce n'est livrée.
- Niveaux de détail (C2) : 0 complet ; 1 surface de subdivision coupée et dents masquées ; 2 cage figée (nœuds géométriques retirés, groupes de poids conservés) ; 3 cage décimée.
"""
import json
import math

import bpy
import numpy as np

from . import human
from .animation import dental, face, skeleton

KEY = "humanloom_crowd"
OBJECT_KEY = "hl_crowd_id"
COLLECTION = "Foule HumanLoom"
VERSION = 1
BEHAVIORS = ("walk", "run", "wait", "chat", "jump", "cross")
MOVING = ("walk", "run", "cross")
CONTROL_KEYS = ("shoulders", "waist", "hips", "torso_depth", "neck", "legs", "torso", "whole_body", "adiposity", "muscles", "head_width", "head_height", "jaw", "chin", "cheeks", "nose_length", "nose_width", "mouth", "lips",
                "eye_spacing", "eye_height", "forehead", "ears_size", "nose_bridge")  # contrôles tirés (les plages sont réglables dans le spec)
FACE_SET = ("neutre", "joie", "tristesse", "surprise", "colere")
LOD_LEVELS = (0, 1, 2, 3)
_SHARED = {}  # maillage et groupe de nœuds du premier personnage de la génération en cours
VARIANT_APPLIERS = {}  # catégorie -> fonction(body, valeur) : enregistrée par les lots tenues, coiffures, accessoires


def register_variant_applier(category, function):
    VARIANT_APPLIERS[category] = function


def default_spec(count=20, seed=1):
    return {
        "version": VERSION, "seed": int(seed), "count": int(count), "regeneration": 0, "rig": True, "frames": 240, "fps": 24, "avoidance": True, "min_distance": 0.12,
        "ranges": {"sex": [0.0, 1.0], "age": [1.0, 3.0], **{k: [-0.6, 0.6] for k in CONTROL_KEYS}},
        "expressions": {k: 1.0 for k in FACE_SET},
        "behaviors": {"walk": 5.0, "run": 1.0, "wait": 2.0, "chat": 2.0, "jump": 0.3},
        "speed": {"walk": [1.0, 1.6], "run": [2.6, 4.2]},
        "clips": {},  # {comportement: [noms d'actions]} ; vide : clips synthétiques
        "area": [-12.0, -12.0, 12.0, 12.0],
        "zones": [],  # [{"kind": "sidewalk" | "crossing", "rect": [x0, y0, x1, y1]}]
        "light_cycle_s": 20.0,
        "variants": {},  # {"outfit": [...], "hair": [...]} : tirage uniforme parmi les valeurs
        "lod": {"near_m": 12.0, "mid_m": 30.0, "far_m": 60.0},
    }


# --- tirage ----------------------------------------------------------------------------------------------------------------------------------------
def _limits(name):
    entry = human.sockets().get(name)
    return (entry[2], entry[3]) if entry else (-1.0, 1.0)


def guard(params):
    """Garde-fous anatomiques : bornes des prises et adiposité + muscles <= 1,4 (un tirage extrême sur les deux à la fois n'est pas plausible)."""
    for name, value in list(params.items()):
        lo, hi = _limits(name)
        params[name] = float(min(max(value, lo), hi))
    total = abs(params.get("adiposity", 0.0)) + abs(params.get("muscles", 0.0))
    if total > 1.4:
        factor = 1.4 / total
        params["adiposity"], params["muscles"] = params.get("adiposity", 0.0) * factor, params.get("muscles", 0.0) * factor
    return params


def _weighted(rng, weights):
    names = sorted(weights)
    p = np.array([float(weights[n]) for n in names])
    return names[int(rng.choice(len(names), p=p / p.sum()))]


def vector(params):
    """Représentation d'un personnage dans l'espace de diversité (chaque dimension rapportée à l'étendue de sa prise)."""
    keys = ["sex", "age"] + list(CONTROL_KEYS)
    out = []
    for k in keys:
        lo, hi = _limits(k)
        out.append((params.get(k, 0.0) - lo) / max(hi - lo, 1e-9))
    return np.array(out)


def sample_member(spec, index, existing=()):
    """Tire le personnage `index` (déterministe). Un tirage trop proche d'un existant (distance < `min_distance`) est retiré, au plus 50 fois."""
    for attempt in range(50):
        rng = np.random.default_rng([spec["seed"], spec.get("regeneration", 0), index, attempt])
        params = {k: float(rng.uniform(*spec["ranges"][k])) for k in spec["ranges"]}
        guard(params)
        v = vector(params)
        if all(np.linalg.norm(v - vector(o["params"])) >= spec["min_distance"] for o in existing):
            break
    behavior = _weighted(rng, spec["behaviors"])
    member = {"id": index, "attempt": attempt, "params": params, "expression": _weighted(rng, spec["expressions"]), "behavior": behavior, "phase": float(rng.uniform(0, 1)),
              "variants": {cat: values[int(rng.integers(len(values)))] for cat, values in sorted(spec["variants"].items()) if values}}
    low, high = spec["speed"].get("run" if behavior == "run" else "walk", [1.0, 1.4])
    member["speed"] = float(rng.uniform(low, high)) if behavior in ("walk", "run", "cross") else 0.0
    member["clip"] = None
    clips = spec["clips"].get(behavior) or []
    if clips:
        member["clip"] = clips[int(rng.integers(len(clips)))]
    member["lateral"] = float(rng.uniform(-0.35, 0.35))
    return member


def sample_members(spec):
    members = []
    for i in range(spec["count"]):
        members.append(sample_member(spec, i, members))
    return members


def diversity_report(members):
    """Distances par paire dans l'espace de diversité : minimale, médiane, et plage couverte par dimension."""
    vectors = np.array([vector(m["params"]) for m in members])
    if len(vectors) < 2:
        return {"paires": 0}
    diff = np.linalg.norm(vectors[:, None] - vectors[None], axis=-1)
    upper = diff[np.triu_indices(len(vectors), 1)]
    return {"paires": int(len(upper)), "distance_min": float(upper.min()), "distance_mediane": float(np.median(upper)), "couverture_age": float(np.ptp(vectors[:, 1])), "couverture_sexe": float(np.ptp(vectors[:, 0]))}


# --- trajectoires et évitement -------------------------------------------------------------------------------------------------------------------
def _rects(spec, kind):
    return [z["rect"] for z in spec["zones"] if z["kind"] == kind]


def plan(spec, members):
    """Départ, trajet et attente de chaque personnage (tirages déterministes). Retourne une liste de dictionnaires (ajoutés aux membres)."""
    area = spec["area"]
    sidewalks, crossings = _rects(spec, "sidewalk"), _rects(spec, "crossing")
    chatters = [m for m in members if m["behavior"] == "chat"]
    for m in members:
        rng = np.random.default_rng([spec["seed"], spec.get("regeneration", 0), m["id"], 999])
        behavior = m["behavior"]
        if behavior == "cross" and not crossings:
            behavior = m["behavior"] = "walk"
        if behavior == "cross":
            x0, y0, x1, y1 = crossings[int(rng.integers(len(crossings)))]
            horizontal = (x1 - x0) >= (y1 - y0)
            a, b = ((x0, rng.uniform(y0, y1)), (x1, rng.uniform(y0, y1))) if horizontal else ((rng.uniform(x0, x1), y0), (rng.uniform(x0, x1), y1))
            if rng.random() < 0.5:
                a, b = b, a
            m["start"], m["path"], m["delay_s"] = [float(a[0]), float(a[1])], [[float(b[0]), float(b[1])]], float(rng.uniform(0, spec["light_cycle_s"]))
        elif behavior in ("walk", "run"):
            if sidewalks:
                x0, y0, x1, y1 = sidewalks[int(rng.integers(len(sidewalks)))]
                horizontal = (x1 - x0) >= (y1 - y0)
                sx, sy = rng.uniform(x0, x1), rng.uniform(y0, y1)
                end = [x1 if rng.random() < 0.5 else x0, sy] if horizontal else [sx, y1 if rng.random() < 0.5 else y0]
                m["start"], m["path"] = [float(sx), float(sy)], [[float(end[0]), float(end[1])], [float(sx), float(sy)]]
            else:
                start = [rng.uniform(area[0], area[2]), rng.uniform(area[1], area[3])]
                m["start"], m["path"] = [float(start[0]), float(start[1])], [[float(rng.uniform(area[0], area[2])), float(rng.uniform(area[1], area[3]))] for _ in range(3)]
            m["delay_s"] = 0.0
        else:
            start = [rng.uniform(area[0], area[2]), rng.uniform(area[1], area[3])]
            if sidewalks:
                x0, y0, x1, y1 = sidewalks[int(rng.integers(len(sidewalks)))]
                start = [rng.uniform(x0, x1), rng.uniform(y0, y1)]
            m["start"], m["path"], m["delay_s"] = [float(start[0]), float(start[1])], [], 0.0
    for first, second in zip(chatters[0::2], chatters[1::2]):  # les discussions sont des paires face à face à 1 m
        centre = np.array(first["start"])
        angle = float(np.random.default_rng([spec["seed"], first["id"], 7]).uniform(0, 2 * math.pi))
        offset = 0.5 * np.array([math.cos(angle), math.sin(angle)])
        first["start"], second["start"] = (centre + offset).tolist(), (centre - offset).tolist()
        first["partner"], second["partner"] = second["id"], first["id"]
    for m in members:
        if m["behavior"] == "chat" and "partner" not in m:
            m["behavior"] = "wait"
    return members


RADIUS, SIDESTEP, GAIN = 1.1, 1.2, 3.0  # évitement : rayon d'influence (m), part de contournement latéral, gain


def simulate(spec, members):
    """Positions (F, N, 2) et caps (F, N, radians) image par image : trajet à vitesse propre, retard de départ, évitement par répulsion entre voisins (rayon 0,9 m), attente et discussion immobiles."""
    frames, fps = spec["frames"], spec["fps"]
    dt = 1.0 / fps
    n = len(members)
    pos = np.array([m["start"] for m in members], float)
    lateral = np.array([m["lateral"] for m in members])
    paths = [np.array(m["path"], float).reshape(-1, 2) for m in members]
    target_index = [0] * n
    speed = np.array([m["speed"] for m in members])
    moving = np.array([m["behavior"] in MOVING for m in members])
    delay = np.array([m.get("delay_s", 0.0) for m in members])
    yaw = np.array([float(np.random.default_rng([spec["seed"], m["id"], 3]).uniform(-math.pi, math.pi)) for m in members])
    ids = {m["id"]: i for i, m in enumerate(members)}
    for i, m in enumerate(members):
        if "partner" in m:
            d = pos[ids[m["partner"]]] - pos[i]
            yaw[i] = math.atan2(d[1], d[0])
    out_pos, out_yaw = np.zeros((frames, n, 2)), np.zeros((frames, n))
    finished = np.zeros(n, bool)
    for f in range(frames):
        t = f * dt
        desired = np.zeros((n, 2))
        for i in range(n):
            if not moving[i] or t < delay[i] or finished[i] or len(paths[i]) == 0:
                continue
            goal = paths[i][target_index[i]] + np.array([0.0, lateral[i]])
            d = goal - pos[i]
            dist = float(np.linalg.norm(d))
            if dist < 0.25:
                if members[i]["behavior"] == "cross":
                    finished[i] = True
                    continue
                target_index[i] = (target_index[i] + 1) % len(paths[i])  # les marcheurs font des allers-retours / boucles
                continue
            desired[i] = d / dist * speed[i]
        velocity = desired.copy()
        if spec["avoidance"]:
            diff = pos[:, None] - pos[None]
            dist = np.linalg.norm(diff, axis=-1) + np.eye(n) * 1e9
            unit = diff / dist[..., None]
            strength = np.clip((RADIUS - dist) / RADIUS, 0.0, None)[..., None]
            side = np.stack([-unit[..., 1], unit[..., 0]], axis=-1)  # contournement : chacun dévie du même côté (sa droite), ce qui évite l'impasse face à face
            repulsion = (strength * (unit + SIDESTEP * side)).sum(axis=1) * GAIN
            active = (np.linalg.norm(desired, axis=1) > 0)[:, None]
            velocity = velocity + repulsion * active  # seuls les marcheurs s'écartent ; les immobiles sont des obstacles fixes
            norm = np.linalg.norm(velocity, axis=1, keepdims=True)
            limit = np.maximum(speed[:, None] * 1.3, 1e-9)
            velocity = np.where(norm > limit, velocity / np.maximum(norm, 1e-9) * limit, velocity)
        pos = pos + velocity * dt
        speed_now = np.linalg.norm(velocity, axis=1)
        heading = np.arctan2(velocity[:, 1], velocity[:, 0])
        turn = (heading - yaw + math.pi) % (2 * math.pi) - math.pi
        yaw = np.where(speed_now > 0.05, yaw + turn * 0.25, yaw)
        out_pos[f], out_yaw[f] = pos, yaw
    return out_pos, out_yaw


# --- clips synthétiques ----------------------------------------------------------------------------------------------------------------------------
CLIP_FRAMES = {"walk": 24, "run": 16, "wait": 48, "chat": 48, "jump": 36, "cross": 24}


def _bone_keys(kind, rng):
    """{os: [(image 0-1, rotation X en degrés), ...]} d'un clip synthétique en boucle (bouchon : balancement des jambes/bras, respiration, gestes, saut)."""
    amp = {"walk": 24, "run": 40, "cross": 24}.get(kind, 0)
    swing = float(rng.uniform(0.85, 1.15))
    if kind in ("walk", "run", "cross"):
        a = amp * swing
        return {"leg_upper.L": [(0, a), (0.5, -a), (1, a)], "leg_upper.R": [(0, -a), (0.5, a), (1, -a)], "arm_upper.L": [(0, -0.6 * a), (0.5, 0.6 * a), (1, -0.6 * a)], "arm_upper.R": [(0, 0.6 * a), (0.5, -0.6 * a), (1, 0.6 * a)]}
    if kind == "jump":
        return {"leg_upper.L": [(0, 0), (0.3, 35), (0.5, -10), (1, 0)], "leg_upper.R": [(0, 0), (0.3, 35), (0.5, -10), (1, 0)], "spine.01": [(0, 0), (0.3, 12), (0.5, -6), (1, 0)]}
    if kind == "chat":
        return {"head": [(0, 0), (0.25, 8), (0.5, -4), (0.75, 6), (1, 0)], "arm_upper.R": [(0, 0), (0.4, 25 * swing), (0.7, 5), (1, 0)], "spine.03": [(0, 0), (0.5, 3), (1, 0)]}
    return {"spine.03": [(0, 0), (0.5, 2.0 * swing), (1, 0)], "head": [(0, 0), (0.5, 1.5), (1, 0)]}  # attente : respiration


def make_clip(armature, member, rng):
    """Crée (action synthétique ou action de la bibliothèque) et la place dans une piste NLA « Foule » de l'armature, avec décalage de phase et échelle de vitesse. Retourne (bande, longueur d'un cycle)."""
    behavior = member["behavior"]
    length = CLIP_FRAMES[behavior]
    animation = armature.animation_data_create()
    previous = animation.action
    animation.action = None
    if member.get("clip") and member["clip"] in bpy.data.actions:
        action = bpy.data.actions[member["clip"]]
        animation.action = action
        length = max(2, int(action.frame_range[1] - action.frame_range[0]))
    else:
        for bone_name, keys in _bone_keys(behavior, rng).items():
            pose = armature.pose.bones.get(bone_name)
            if pose is None:
                continue
            pose.rotation_mode = "XYZ"
            for t, degrees in keys:
                pose.rotation_euler = (math.radians(degrees), 0.0, 0.0)
                pose.keyframe_insert("rotation_euler", frame=1 + t * length)
            pose.rotation_euler = (0.0, 0.0, 0.0)
        action = animation.action
    action.name = f"foule_{member['id']:03d}_{behavior}"
    track = animation.nla_tracks.get("Foule") or animation.nla_tracks.new()
    track.name = "Foule"
    scale = 1.0
    if behavior in ("walk", "run", "cross"):
        scale = float(np.clip(1.4 / max(member["speed"], 0.3), 0.5, 1.8)) if behavior != "run" else float(np.clip(3.2 / max(member["speed"], 0.5), 0.6, 1.6))
    cycle = length * scale
    start = 1.0 - member["phase"] * cycle  # décalage de phase : la foule ne marche pas au pas
    strip = track.strips.new(action.name, int(math.floor(start)), action)
    strip.scale = scale
    strip.repeat = max(1.0, (member["_frames"] - start) / max(cycle, 1.0) + 1.0)
    strip.use_sync_length = False
    animation.action = previous
    return strip, cycle


# --- construction, figeage, régénération ---------------------------------------------------------------------------------------------------------------
def _collection(scene):
    collection = bpy.data.collections.get(COLLECTION)
    if collection is None:
        collection = bpy.data.collections.new(COLLECTION)
        scene.collection.children.link(collection)
    return collection


def members_of(scene):
    return sorted((o for o in scene.objects if o.get(OBJECT_KEY) is not None and o.type == "MESH" and o.parent is None), key=lambda o: o[OBJECT_KEY])


def _make_body(context, spec, member, collection):
    context.view_layer.active_layer_collection = context.view_layer.layer_collection  # le corps est créé dans la collection active
    if "template" not in _SHARED or _SHARED["template"].name not in bpy.data.objects:  # gabarit caché : un seul chargement du groupe de nœuds et du maillage de base pour toute la foule
        _SHARED["template"] = human.create_human(context)
        _SHARED["template"].hide_viewport = _SHARED["template"].hide_render = True
        shared = False
    else:
        shared = True
    body = human.duplicate_human(context, _SHARED["template"], share_mesh=True)
    body.hide_viewport = body.hide_render = False
    for child in body.children_recursive:
        child.hide_viewport = child.hide_render = False
    for other in list(body.users_collection):
        other.objects.unlink(body)
    collection.objects.link(body)
    for child in body.children_recursive:  # yeux : dans la collection de la foule
        for other in list(child.users_collection):
            other.objects.unlink(child)
        collection.objects.link(child)
    for name, value in member["params"].items():
        if human.has_control(body, name):
            human.set_value(body, name, value)
    body[OBJECT_KEY] = member["id"]
    body.name = f"Foule {member['id']:03d}"
    if spec["rig"]:
        armature = skeleton.install(body, weights=not _SHARED.get("rigged", False))
        _SHARED["rigged"] = True
        for other in list(armature.users_collection):
            if other != collection:
                other.objects.unlink(armature)
        if collection not in armature.users_collection:
            collection.objects.link(armature)
        face_pose = face.builtin_poses().get("expression:" + member["expression"])
        if face_pose is not None:
            face.apply_pose(body, face_pose["pose"])
    for category, value in member["variants"].items():
        applier = VARIANT_APPLIERS.get(category)
        if applier is not None:
            applier(body, value)
    return body


def _animate(body, member, positions, yaws, spec):
    """Trajet figé : clés de position et de cap toutes les 5 images (interpolation linéaire) sur le corps ; clip de comportement en NLA sur l'armature."""
    keyframe = bpy.context.preferences.edit
    old = keyframe.keyframe_new_interpolation_type
    keyframe.keyframe_new_interpolation_type = "LINEAR"
    try:
        body.animation_data_create()
        body.animation_data.action = None
        yaw_unwrapped = np.unwrap(yaws)
        for f in range(0, spec["frames"], 5):
            body.location = (float(positions[f, 0]), float(positions[f, 1]), 0.0)
            body.rotation_euler = (0.0, 0.0, float(yaw_unwrapped[f]) - math.pi / 2)  # l'avant du corps est -Y : cap 0 = +X
            body.keyframe_insert("location", frame=1 + f)
            body.keyframe_insert("rotation_euler", frame=1 + f)
    finally:
        keyframe.keyframe_new_interpolation_type = old
    body.animation_data.action.name = f"foule_{member['id']:03d}_trajet"
    rigs = skeleton.rigs_of(body)
    if rigs:
        rng = np.random.default_rng([spec["seed"], member["id"], 55])
        member["_frames"] = spec["frames"]
        strip, cycle = make_clip(rigs[0], member, rng)
        member["cycle_frames"] = float(cycle)
        member["strip_start"] = float(strip.frame_start)
        member.pop("_frames", None)


def generate(context, spec, replace=False):
    """Crée la foule FIGÉE : tire, place, anime et enregistre (scène + objets). Refuse si une foule existe déjà et `replace` est faux. Retourne le résumé."""
    scene = context.scene
    if scene.get(KEY) and not replace:
        raise ValueError("Une foule figée existe déjà : « Régénérer » est la seule façon de la modifier.")
    if scene.get(KEY):
        clear(scene)
    members = plan(spec, sample_members(spec))
    positions, yaws = simulate(spec, members)
    collection = _collection(scene)
    _SHARED.clear()  # le gabarit est supprimé en fin de génération
    for i, member in enumerate(members):
        body = _make_body(context, spec, member, collection)
        body.location = (member["start"][0], member["start"][1], 0.0)
        _animate(body, member, positions[:, i], yaws[:, i], spec)
    _drop_template()
    scene[KEY] = json.dumps({"spec": spec, "members": members}, ensure_ascii=False)
    return {"personnages": len(members), "diversite": diversity_report(members), "comportements": {b: sum(1 for m in members if m["behavior"] == b) for b in BEHAVIORS}}


def _drop_template():
    template = _SHARED.pop("template", None)
    _SHARED.pop("rigged", None)
    if template is not None and template.name in bpy.data.objects:
        _remove_tree(template)


def load(scene):
    raw = scene.get(KEY)
    if not raw:
        return None
    data = json.loads(raw)
    return data["spec"], data["members"]


def _remove_tree(body):
    """Supprime un personnage (corps, armature, yeux, dents…) avec ses maillages, armatures et actions devenus orphelins."""
    queue = [body]
    for obj in queue:
        queue.extend(obj.children)
    datas, actions = [], []
    for obj in queue:
        if obj.data is not None:
            datas.append(obj.data)
        for holder in (obj, getattr(obj.data, "shape_keys", None)):
            animation = getattr(holder, "animation_data", None)
            if animation:
                if animation.action:
                    actions.append(animation.action)
                actions += [s.action for t in animation.nla_tracks for s in t.strips if s.action]
    for obj in reversed(queue):
        bpy.data.objects.remove(obj, do_unlink=True)
    for data in datas:
        if data.users == 0:
            collection = bpy.data.meshes if isinstance(data, bpy.types.Mesh) else bpy.data.armatures if isinstance(data, bpy.types.Armature) else None
            if collection is not None:
                collection.remove(data)
    for action in actions:
        if action.users == 0 and action.name in bpy.data.actions:
            bpy.data.actions.remove(action)


def clear(scene):
    """Supprime les personnages de la foule et l'enregistrement."""
    for body in members_of(scene):
        _remove_tree(body)
    if KEY in scene:
        del scene[KEY]


def regenerate_member(context, index):
    """Régénère UN personnage (nouveau tirage : la régénération de ce personnage est comptée dans son `attempt`) ; les autres ne changent pas."""
    scene = context.scene
    loaded = load(scene)
    if loaded is None:
        raise ValueError("Aucune foule figée.")
    spec, members = loaded
    old = next(m for m in members if m["id"] == index)
    body = next(o for o in members_of(scene) if o[OBJECT_KEY] == index)
    _SHARED.clear()
    sub_spec = dict(spec, regeneration=spec.get("regeneration", 0) + 1000 + old.get("regenerated", 0) + 1)
    new = sample_member(sub_spec, index, [m for m in members if m["id"] != index])
    new["regenerated"] = old.get("regenerated", 0) + 1
    plan_spec = dict(sub_spec, count=len(members))
    planned = plan(plan_spec, [new])[0]
    others = [m for m in members if m["id"] != index]
    positions, yaws = simulate(spec, [planned] + others)  # le nouveau personnage évite les autres tels qu'ils sont
    _remove_tree(body)
    new_body = _make_body(context, spec, planned, _collection(scene))
    _animate(new_body, planned, positions[:, 0], yaws[:, 0], spec)
    _drop_template()
    members[members.index(old)] = planned
    scene[KEY] = json.dumps({"spec": spec, "members": members}, ensure_ascii=False)
    return planned


def regenerate_all(context):
    """Nouvelle foule avec la graine incrémentée de la régénération (demande explicite)."""
    spec, _ = load(context.scene)
    spec = dict(spec, regeneration=spec.get("regeneration", 0) + 1)
    return generate(context, spec, replace=True)


# --- niveaux de détail (C2) --------------------------------------------------------------------------------------------------------------------------
def triangle_count(body):
    bpy.context.view_layer.update()
    evaluated = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    mesh.calc_loop_triangles()
    count = len(mesh.loop_triangles)
    evaluated.to_mesh_clear()
    return count


def lod_of(body):
    return int(body.get("hl_lod", 0))


def apply_lod(body, level):
    """Niveau de détail du personnage. 0 complet ; 1 subdivision coupée + dents masquées ; 2 cage figée (sans nœuds géométriques) ; 3 cage décimée. Le passage à 2 ou 3 est destructif pour les
    contrôles du corps : `restore_lod` régénère le personnage depuis ses tirages enregistrés."""
    if level not in LOD_LEVELS:
        raise ValueError("Niveau de détail inconnu : %r" % (level,))
    current = lod_of(body)
    if level == current:
        return level
    if level < current:
        raise ValueError("Revenir à un niveau plus détaillé : utiliser restore_lod (régénération).")
    surface = body.modifiers.get("Human Modeling · Surface")
    if level >= 1:
        if surface is not None:
            surface.levels = surface.render_levels = 0
        for part in dental.parts_of(body):
            part.hide_viewport = part.hide_render = True
    if level >= 2 and current < 2:
        node = body.modifiers.get(human.MODIFIER_NAME)
        armature_states = [(m, m.show_viewport) for m in body.modifiers if m.type == "ARMATURE"]
        saved = [(m, m.show_viewport) for m in body.modifiers]
        for m in body.modifiers:
            m.show_viewport = m is node
        bpy.context.view_layer.update()
        mesh = bpy.data.meshes.new_from_object(body.evaluated_get(bpy.context.evaluated_depsgraph_get()))
        for m, state in saved:
            m.show_viewport = state
        old_mesh = body.data
        body.data = mesh
        if node is not None:
            body.modifiers.remove(node)
        if surface is not None:
            body.modifiers.remove(surface)
        for polygon in mesh.polygons:
            polygon.use_smooth = True
        for key in ("humanloom",):  # propriétés personnalisées conservées sur l'objet
            pass
        if old_mesh.users == 0:
            bpy.data.meshes.remove(old_mesh)
        del armature_states
    if level >= 3:
        decimate = body.modifiers.get("Foule LOD") or body.modifiers.new("Foule LOD", "DECIMATE")
        decimate.ratio = 0.3
        decimate.use_collapse_triangulate = True
    body["hl_lod"] = int(level)
    return level


def auto_lod(scene, camera=None):
    """Niveau selon la distance à la caméra (seuils du spec : proche < near, moyen < mid, lointain < far, au-delà : 3). Retourne {indice: niveau}. Ne fait que monter de niveau (voir `apply_lod`)."""
    loaded = load(scene)
    spec = loaded[0] if loaded else default_spec()
    camera = camera or scene.camera
    out = {}
    if camera is None:
        return out
    thresholds = (spec["lod"]["near_m"], spec["lod"]["mid_m"], spec["lod"]["far_m"])
    for body in members_of(scene):
        distance = (body.matrix_world.translation - camera.matrix_world.translation).length
        level = sum(1 for t in thresholds if distance >= t)
        try:
            apply_lod(body, max(level, lod_of(body)))
        except ValueError:
            pass
        out[body[OBJECT_KEY]] = lod_of(body)
    return out
