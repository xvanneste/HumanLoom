"""Moteur de foule natif (lots C1 et C2) : ensembles d'éléments variables, tirage à graine, foule FIGÉE, comportements, trajectoires, évitement, décalage de phase, niveaux de détail.

Principes
- Un `spec` (dictionnaire JSON) décrit des ENSEMBLES : plages de morphologie (sexe, âge, contrôles du corps), expressions, comportements pondérés (marche, course, attente, discussion, saut, traversée),
  vitesses, zones (trottoirs, passages piétons, aire libre), variantes extensibles (`variants` : tenues, coiffures… ; appliquées par des « applicateurs » enregistrés par les lots qui les fournissent).
- Le tirage de chaque personnage est déterministe : `default_rng([graine, régénération, indice])`. La foule est FIGÉE : spec, tirages et résultats sont enregistrés dans la scène (`scene["humanloom_crowd"]`)
  et dans les objets ; rien n'est recalculé à la réouverture ni au changement d'un réglage. Seules `generate(replace=True)`, `regenerate_member` et `regenerate_all` la modifient.
- Garde-fous : valeurs bornées par les prises du groupe de nœuds, somme adiposité + muscles bornée, distance minimale entre personnages dans l'espace des paramètres (pas de clones).
- Les animations de comportement viennent de `spec["clips"][comportement]` (noms d'actions déjà re-ciblées ou sélecteurs `{"action": nom, "slot_handle": entier}`) ; à défaut, des clips SYNTHÉTIQUES simples (balancement
  des jambes et des bras, respiration, gestes) servent de bouchon et pour les tests. Aucune donnée tierce n'est livrée.
- Niveaux de détail (C2) : 0 complet ; 1 surface de subdivision coupée et dents masquées ; 2 cage figée (nœuds géométriques retirés, groupes de poids conservés) ; 3 cage décimée.
"""
import json
import math
from collections import Counter
from contextlib import contextmanager
from numbers import Integral, Real
from typing import NamedTuple

import bpy
import numpy as np
from bpy_extras.anim_utils import action_get_channelbag_for_slot

from . import human
from .animation import dental, face, skeleton

KEY = "humanloom_crowd"
OBJECT_KEY = "hl_crowd_id"
LIBRARY_CLIPS_KEY = "hl_crowd_library_clips"
CLIP_HISTORY_KEY = "hl_crowd_clip_history"
CLIP_ANCHOR_KEY = "hl_crowd_clip_anchor"
COLLECTION = "Foule HumanLoom"
OWNED_KEY = "hl_crowd_owned"
VERSION = 1
BEHAVIORS = ("walk", "run", "wait", "chat", "jump", "cross")
MOVING = ("walk", "run", "cross")
CONTROL_KEYS = ("shoulders", "waist", "hips", "torso_depth", "neck", "legs", "torso", "whole_body", "adiposity", "muscles", "head_width", "head_height", "jaw", "chin", "cheeks", "nose_length", "nose_width", "mouth", "lips",
                "eye_spacing", "eye_height", "forehead", "ears_size", "nose_bridge")  # contrôles tirés (les plages sont réglables dans le spec)
FACE_SET = ("neutre", "joie", "tristesse", "surprise", "colere")
LOD_LEVELS = (0, 1, 2, 3)
_BUILDING = False
VARIANT_APPLIERS = {}  # catégorie -> fonction(body, valeur) : enregistrée par les lots tenues, coiffures, accessoires


class CleanupError(RuntimeError):
    """L'opération de foule est publiée, mais une purge définitive a échoué."""


class RollbackError(RuntimeError):
    """Le retour arrière de l'opération a rencontré une erreur supplémentaire."""


class _ClipContext(NamedTuple):
    anchor: str | None = None
    bands: tuple = ()
    history: dict | None = None
    duplicate_anchor: bool = False


def register_variant_applier(category, function):
    VARIANT_APPLIERS[category] = function


def default_spec(count=20, seed=1):
    return {
        "version": VERSION, "seed": int(seed), "count": int(count), "regeneration": 0, "rig": True, "frames": 240, "fps": 24, "avoidance": True, "min_distance": 0.12,
        "ranges": {"sex": [0.0, 1.0], "age": [1.0, 3.0], **{k: [-0.6, 0.6] for k in CONTROL_KEYS}},
        "expressions": {k: 1.0 for k in FACE_SET},
        "behaviors": {"walk": 5.0, "run": 1.0, "wait": 2.0, "chat": 2.0, "jump": 0.3},
        "speed": {"walk": [1.0, 1.6], "run": [2.6, 4.2]},
        "clips": {},  # {comportement: [nom ou {"action": nom, "slot_handle": entier}]}
        "area": [-12.0, -12.0, 12.0, 12.0],
        "zones": [],  # [{"kind": "sidewalk" | "crossing", "rect": [x0, y0, x1, y1]}]
        "light_cycle_s": 20.0,
        "variants": {},  # {"outfit": [...], "hair": [...]} : tirage uniforme parmi les valeurs
        "lod": {"near_m": 12.0, "mid_m": 30.0, "far_m": 60.0},
    }


# --- validation du spec
def _finite_number(value, label):
    try:
        if isinstance(value, Real) and not isinstance(value, bool) and math.isfinite(value):
            return float(value)
    except OverflowError:
        pass
    raise ValueError(f"{label} doit être un nombre fini.")


def _integer(value, label, minimum=0):
    if isinstance(value, bool) or not isinstance(value, Integral) or value < minimum:
        raise ValueError(f"{label} doit être un entier supérieur ou égal à {minimum}.")
    return int(value)


def _spec_flag(spec, field):
    value = spec.get(field)
    if not isinstance(value, bool):
        raise ValueError(f"{field} doit être un booléen.")
    return value


def _simulation_step(spec, count):
    frames = _integer(spec.get("frames"), "frames", 1)
    # Deux coordonnées et un cap en double précision pour chaque membre et image.
    bytes_per_frame = 3 * np.dtype(float).itemsize * max(1, count)
    if frames > np.iinfo(np.intp).max // bytes_per_frame:
        raise ValueError("frames et count dépassent la capacité d'adressage de la simulation.")
    fps = _finite_number(spec.get("fps"), "fps")
    if fps <= 0:
        raise ValueError("fps doit être strictement positif.")
    dt = 1.0 / fps
    if not math.isfinite(dt) or not math.isfinite((frames - 1) * dt):
        raise ValueError("fps est trop faible pour calculer la durée de la simulation.")
    return frames, dt


def _limits_of(value, size, label):
    if not isinstance(value, (list, tuple)) or len(value) != size:
        raise ValueError(f"{label} doit contenir {size} nombres.")
    return [_finite_number(number, f"{label}[{i}]") for i, number in enumerate(value)]


def _rectangle(value, label):
    x0, y0, x1, y1 = _limits_of(value, 4, label)
    width, height = x1 - x0, y1 - y0
    if not (0 < width < math.inf and 0 < height < math.inf):
        raise ValueError(f"{label} doit avoir une largeur et une hauteur finies et strictement positives.")


def _lod_thresholds(spec):
    lod = spec.get("lod")
    if not isinstance(lod, dict):
        raise ValueError("lod doit contenir les seuils near_m, mid_m et far_m.")
    near, mid, far = (_finite_number(lod.get(name), f"lod.{name}") for name in ("near_m", "mid_m", "far_m"))
    if not 0 <= near <= mid <= far:
        raise ValueError("Les seuils lod doivent respecter 0 ≤ near_m ≤ mid_m ≤ far_m.")
    return near, mid, far


def _validate_json(value, label):
    try:
        json.dumps(value, ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError, RecursionError) as error:
        raise ValueError(f"{label} doit contenir des données JSON valides et finies : {error}.") from error


def _validate_spec(spec):
    """Vérifie les entrées de tirage et de simulation avant de préparer une foule."""
    if not isinstance(spec, dict):
        raise ValueError("Le spec de foule doit être un dictionnaire.")
    count = _integer(spec.get("count"), "count", 1)
    _simulation_step(spec, count)
    _integer(spec.get("seed"), "seed")
    _integer(spec.get("regeneration", 0), "regeneration")
    _spec_flag(spec, "avoidance")
    _spec_flag(spec, "rig")
    _lod_thresholds(spec)

    for field in ("behaviors", "expressions"):
        weights = spec.get(field)
        if not isinstance(weights, dict) or not weights:
            raise ValueError(f"{field} doit contenir des poids.")
        values = []
        for name, weight in weights.items():
            label = f"{field}[{name!r}]"
            if not isinstance(name, str) or not name:
                raise ValueError(f"{field} doit être indexé par des noms non vides.")
            if field == "behaviors" and name not in BEHAVIORS:
                raise ValueError(f"{label} désigne un comportement inconnu.")
            value = _finite_number(weight, f"{field}[{name}]")
            if value < 0:
                raise ValueError(f"{label} ne peut pas avoir un poids négatif.")
            values.append(value)
        if not 0 < sum(values) < math.inf:
            raise ValueError(f"La somme des poids de {field} doit être finie et strictement positive.")

    _rectangle(spec.get("area"), "area")
    zones = spec.get("zones")
    if not isinstance(zones, (list, tuple)):
        raise ValueError("zones doit être une liste de zones.")
    for i, zone in enumerate(zones):
        if not isinstance(zone, dict) or zone.get("kind") not in ("sidewalk", "crossing"):
            raise ValueError(f"zones[{i}].kind doit être sidewalk ou crossing.")
        _rectangle(zone.get("rect"), f"zones[{i}].rect")

    for field in ("ranges", "speed"):
        ranges = spec.get(field)
        if not isinstance(ranges, dict):
            raise ValueError(f"{field} doit contenir des intervalles.")
        for name, interval in ranges.items():
            if not isinstance(name, str) or not name:
                raise ValueError(f"{field} doit être indexé par des noms non vides.")
            label = f"{field}[{name}]"
            low, high = _limits_of(interval, 2, label)
            if not 0 <= high - low < math.inf:
                raise ValueError(f"{label} doit être un intervalle ordonné et d'étendue finie.")
            if field == "speed" and low < 0:
                raise ValueError(f"{label} doit contenir des vitesses positives ou nulles.")
    for field in ("min_distance", "light_cycle_s"):
        if _finite_number(spec.get(field), field) < 0:
            raise ValueError(f"{field} doit être positif ou nul.")

    clips = spec.get("clips")
    if not isinstance(clips, dict):
        raise ValueError("clips doit associer les comportements à des listes de clips.")
    for behavior, selectors in clips.items():
        label = f"clips[{behavior!r}]"
        if behavior not in BEHAVIORS:
            raise ValueError(f"{label} désigne un comportement inconnu.")
        if selectors is None:
            continue
        if not isinstance(selectors, (list, tuple)):
            raise ValueError(f"{label} doit contenir une liste de clips.")
        for i, selector in enumerate(selectors):
            _clip_selector(selector, f"pour {label}[{i}]")

    variants = spec.get("variants")
    if not isinstance(variants, dict):
        raise ValueError("variants doit associer les catégories à des listes de valeurs.")
    for category, values in variants.items():
        if not isinstance(category, str) or not category:
            raise ValueError("variants doit être indexé par des noms de catégorie non vides.")
        if not isinstance(values, (list, tuple)):
            raise ValueError(f"variants[{category!r}] doit contenir une liste de valeurs.")
        _validate_json(values, f"variants[{category!r}]")
    _validate_json(spec, "Le spec de foule")


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
    diverse = False
    for attempt in range(50):
        rng = np.random.default_rng([spec["seed"], spec.get("regeneration", 0), index, attempt])
        params = {k: float(rng.uniform(*spec["ranges"][k])) for k in spec["ranges"]}
        guard(params)
        v = vector(params)
        if all(np.linalg.norm(v - vector(o["params"])) >= spec["min_distance"] for o in existing):
            diverse = True
            break
    behavior = _weighted(rng, spec["behaviors"])
    member = {"id": index, "attempt": attempt, "diversite_garantie": diverse, "params": params, "expression": _weighted(rng, spec["expressions"]), "behavior": behavior, "phase": float(rng.uniform(0, 1)),
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
MIN_NORMAL_DISTANCE = math.sqrt(np.finfo(float).tiny)
BLENDER_COORD_LIMIT = np.finfo(np.float32).max


def _check_motion(positions, yaws, members, blender=False):
    # Blender écrit ses coordonnées et ses clés en simple précision.
    limit = BLENDER_COORD_LIMIT if blender else math.inf
    for name, values in (("positions", positions), ("caps", yaws)):
        invalid = ~np.isfinite(values) | (np.abs(values) > limit)
        if invalid.any():
            frame, index, *_ = np.unravel_index(invalid.argmax(), invalid.shape)
            raise ValueError(f"Simulation de foule : {name} non représentables à l'image {frame + 1}, personnage {members[index]['id']}.")


def simulate(spec, members):
    """Positions (F, N, 2) et caps (F, N, radians) dans l'ordre d'entrée."""
    frames, dt = _simulation_step(spec, len(members))
    seed = _integer(spec.get("seed"), "seed")
    avoidance = _spec_flag(spec, "avoidance")
    ids = [_integer(member.get("id"), "Identifiant du personnage") for member in members]
    if len(set(ids)) != len(ids):
        raise ValueError("Les identifiants des personnages de foule doivent être distincts.")

    # Le calcul des sommes et le choix des directions suivent le même ordre pour chaque appel.
    order = sorted(range(len(ids)), key=ids.__getitem__)
    ordered = [members[i] for i in order]
    try:
        with np.errstate(over="raise", invalid="raise", divide="raise", under="ignore"):
            positions, yaws = _simulate(frames, dt, seed, avoidance, ordered)
    except FloatingPointError as error:
        raise ValueError(f"Simulation de foule : calcul non fini ({error}).") from error
    except MemoryError as error:
        raise ValueError("Mémoire insuffisante pour les valeurs de frames et count de la simulation.") from error
    _check_motion(positions, yaws, ordered)
    if order != list(range(len(ids))):
        inverse = np.argsort(order)
        positions, yaws = positions[:, inverse], yaws[:, inverse]
    return positions, yaws


def _simulate(frames, dt, seed, avoidance, members):
    n = len(members)
    pos = np.empty((n, 2))
    lateral, speed, delay = np.empty(n), np.empty(n), np.empty(n)
    paths = []
    for i, member in enumerate(members):
        label = f"Personnage {member['id']}"
        start = np.asarray(member["start"], dtype=float)
        if start.shape != (2,) or not np.isfinite(start).all():
            raise ValueError(f"{label} : start doit contenir deux coordonnées finies.")
        path = np.asarray(member["path"], dtype=float)
        if path.shape == (0,):
            path = path.reshape(0, 2)
        if path.ndim != 2 or path.shape[1] != 2 or not np.isfinite(path).all():
            raise ValueError(f"{label} : path doit contenir des points de deux coordonnées finies.")
        pos[i] = start
        paths.append(path)
        lateral[i] = _finite_number(member["lateral"], f"{label}.lateral")
        speed[i] = _finite_number(member["speed"], f"{label}.speed")
        delay[i] = _finite_number(member.get("delay_s", 0.0), f"{label}.delay_s")
        if speed[i] < 0 or delay[i] < 0:
            raise ValueError(f"{label} : speed et delay_s doivent être positifs ou nuls.")
    target_index = [0] * n
    moving = np.array([m["behavior"] in MOVING for m in members])
    yaw = np.array([float(np.random.default_rng([seed, m["id"], 3]).uniform(-math.pi, math.pi)) for m in members])
    ids = {m["id"]: i for i, m in enumerate(members)}
    for i, m in enumerate(members):
        if "partner" in m:
            if m["partner"] not in ids:
                raise ValueError(f"Personnage {m['id']} : partenaire de discussion introuvable.")
            d = pos[ids[m["partner"]]] - pos[i]
            yaw[i] = math.atan2(d[1], d[0])
    out_pos, out_yaw = np.zeros((frames, n, 2)), np.zeros((frames, n))
    finished = np.zeros(n, bool)
    separation = None
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
        if avoidance:
            diff = pos[:, None] - pos[None]
            dist = np.linalg.norm(diff, axis=-1)
            np.fill_diagonal(dist, 1e9)
            tiny = dist < MIN_NORMAL_DISTANCE
            if tiny.any():
                row, col = np.nonzero(tiny)
                offsets = diff[row, col]
                scale = np.max(np.abs(offsets), axis=1)
                coincident = scale == 0.0
                # Les écarts non nuls gardent leur direction, même si leur carré sous-déborde.
                offsets /= np.where(coincident, 1.0, scale)[:, None]
                if coincident.any():
                    if separation is None:
                        # Les IDs triés occupent des points distincts sur le cercle.
                        # La corde entre deux points donne des forces opposées.
                        phase = np.random.default_rng([seed, 4]).uniform(0, 2 * math.pi)
                        angles = phase + np.arange(n) * (2 * math.pi / n)
                        separation = np.stack((np.cos(angles), np.sin(angles)), axis=-1)
                    offsets[coincident] = separation[row[coincident]] - separation[col[coincident]]
                unit = diff / np.where(tiny, 1.0, dist)[..., None]
                unit[row, col] = offsets / np.linalg.norm(offsets, axis=-1)[:, None]
            else:
                unit = diff / dist[..., None]
            strength = np.clip((RADIUS - dist) / RADIUS, 0.0, None)[..., None]
            side = np.stack([-unit[..., 1], unit[..., 0]], axis=-1)  # contournement : chacun dévie du même côté (sa droite), ce qui évite l'impasse face à face
            repulsion = (strength * (unit + SIDESTEP * side)).sum(axis=1) * GAIN
            active = np.any(desired != 0.0, axis=1, keepdims=True)
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


def _clip_selector(clip, label):
    if clip is None:
        return None, None
    if isinstance(clip, str):
        return clip, None
    if (isinstance(clip, dict) and isinstance(clip.get("action"), str)
            and type(clip.get("slot_handle")) is int and clip["slot_handle"] > 0):
        return clip["action"], clip["slot_handle"]
    raise ValueError(f"Sélecteur de clip de foule invalide {label} : {clip!r}.")


def _requested_action(member):
    name, handle = _clip_selector(member.get("clip"), f"pour le membre {member['id']}")
    if name is None:
        return None, None
    action = bpy.data.actions.get(name)
    if action is None:
        raise ValueError(f"Clip de foule {name!r} introuvable pour le membre {member['id']} ({member['behavior']}).")
    return action, handle


def _curve_range(armature, curve):
    if curve.mute or (curve.group is not None and curve.group.mute) or curve.is_empty:
        return None
    try:
        value = armature.path_resolve(curve.data_path)
        if isinstance(value, Real):
            if curve.array_index != 0:
                return None
        elif curve.array_index < 0 or not isinstance(value[curve.array_index], Real):
            return None
    except (ValueError, TypeError, IndexError, KeyError):
        return None
    bounds = tuple(curve.range())
    return bounds if all(math.isfinite(frame) for frame in bounds) else None


def _clip_slot(armature, action, handle, old_clip):
    """Résout le slot et son intervalle sur les seuls canaux exploitables."""
    candidates = {}
    pose_handles = set()
    for slot in action.slots:
        if slot.target_id_type != "OBJECT":
            continue
        channelbag = action_get_channelbag_for_slot(action, slot)
        if channelbag is None:
            continue
        object_ranges, pose_ranges = [], []
        declares_pose = False
        for curve in channelbag.fcurves:
            is_pose = curve.data_path.startswith("pose.bones[")
            declares_pose |= is_pose
            bounds = _curve_range(armature, curve)
            if bounds is not None:
                (pose_ranges if is_pose else object_ranges).append(bounds)
        if pose_ranges or (object_ranges and not declares_pose):
            candidates[slot.handle] = (slot, pose_ranges + object_ranges)
            if pose_ranges:
                pose_handles.add(slot.handle)

    def incompatible(issue):
        return ValueError(f"Clip de foule {action.name!r} pour {armature.name!r} : {issue}.")

    old_clip = old_clip or _ClipContext()
    history = old_clip.history or {}
    historical = {old_handle for old_action, old_handle in old_clip.bands if old_action == action}
    if handle is not None:
        if handle not in candidates:
            raise incompatible(f"aucun slot compatible pour le handle explicite {handle}")
    elif historical:
        if len(historical) != 1:
            raise incompatible("plusieurs slots compatibles possibles dans les bandes NLA historiques")
        handle = next(iter(historical))
        if handle not in candidates:
            raise incompatible(f"aucun slot compatible pour le handle NLA historique {handle}")
    elif action in history:
        handle = history[action]
        if handle not in candidates:
            raise incompatible(f"aucun slot compatible pour le handle NLA mémorisé {handle}")
    else:
        preferred = pose_handles or candidates.keys()
        if len(preferred) == 1:
            handle = next(iter(preferred))
        elif len(preferred) > 1 and old_clip.anchor is not None:
            if old_clip.duplicate_anchor:
                raise incompatible(f"ancre historique dupliquée {old_clip.anchor!r}")
            named = [candidate for candidate in preferred if candidates[candidate][0].name_display == old_clip.anchor]
            if len(named) == 1:
                handle = named[0]

    if handle is None:
        raise incompatible("plusieurs slots compatibles" if candidates else "aucun slot compatible")
    slot, ranges = candidates[handle]
    if action.use_frame_range:
        return slot, tuple(action.frame_range)
    return slot, (min(bounds[0] for bounds in ranges), max(bounds[1] for bounds in ranges))


def _synthetic_clip(armature, animation, behavior, rng, length):
    previous = animation.action
    previous_slot = animation.action_slot
    animation.action = None
    try:
        for bone_name, keys in _bone_keys(behavior, rng).items():
            pose = armature.pose.bones.get(bone_name)
            if pose is None:
                continue
            pose.rotation_mode = "XYZ"
            for t, degrees in keys:
                pose.rotation_euler = (math.radians(degrees), 0.0, 0.0)
                pose.keyframe_insert("rotation_euler", frame=1 + t * length)
            pose.rotation_euler = (0.0, 0.0, 0.0)
        return animation.action, animation.action_slot
    finally:
        animation.action = previous
        if previous is not None:
            animation.action_slot = previous_slot


def make_clip(armature, member, rng, old_clip=None):
    """Place un clip dans une piste NLA « Foule ». Retourne (bande, longueur d'un cycle)."""
    behavior = member["behavior"]
    length = CLIP_FRAMES[behavior]
    name = f"foule_{member['id']:03d}_{behavior}"
    source, handle = _requested_action(member)
    if source is not None:
        slot, (first, last) = _clip_slot(armature, source, handle, old_clip)
        last = max(first + 1, last)
        length = last - first
        animation = armature.animation_data_create()
        action = source
    else:
        animation = armature.animation_data_create()
        action, slot = _synthetic_clip(armature, animation, behavior, rng, length)
        action.name = name
    track = animation.nla_tracks.get("Foule") or animation.nla_tracks.new()
    track.name = "Foule"
    scale = 1.0
    if behavior in ("walk", "run", "cross"):
        scale = float(np.clip(1.4 / max(member["speed"], 0.3), 0.5, 1.8)) if behavior != "run" else float(np.clip(3.2 / max(member["speed"], 0.5), 0.6, 1.6))
    cycle = length * scale
    start = 1.0 - member["phase"] * cycle  # décalage de phase : la foule ne marche pas au pas
    strip = track.strips.new(name, int(math.floor(start)), action)
    strip.action_slot = slot
    if strip.action_slot != slot or slot is None:
        raise ValueError(f"Impossible de lier le slot du clip {action.name!r} au membre {member['id']}.")
    strip.use_sync_length = False
    if source is not None:
        strip.action_frame_end = last
        strip.action_frame_start = first
        # Référence persistante pour la purge, même si le clip est renommé.
        if LIBRARY_CLIPS_KEY not in armature:
            armature[LIBRARY_CLIPS_KEY] = {}
        armature[LIBRARY_CLIPS_KEY][strip.name] = source
    history = dict(old_clip.history or {}) if old_clip else {}
    if source is not None and len(source.slots) > 1:
        history[source] = slot.handle
    if history:
        armature[CLIP_HISTORY_KEY] = {str(index): {"action": clip, "slot_handle": handle}
                                     for index, (clip, handle) in enumerate(history.items())}
    strip.scale = scale
    strip.repeat = max(1.0, (member["_frames"] - start) / max(cycle, 1.0) + 1.0)
    return strip, cycle


# --- construction, figeage, régénération ---------------------------------------------------------------------------------------------------------------
def members_of(scene):
    return sorted((o for o in scene.objects if o.get(OBJECT_KEY) is not None and o.type == "MESH" and o.parent is None), key=lambda o: o[OBJECT_KEY])


def _make_body(context, spec, member, shared):
    if "template" not in shared:  # un seul chargement des nœuds et du maillage de base
        template = shared["template"] = human.create_human(context)
        template.hide_viewport = template.hide_render = True
    body = human.duplicate_human(context, shared["template"], share_mesh=True)
    body.hide_viewport = body.hide_render = False
    for child in body.children_recursive:
        child.hide_viewport = child.hide_render = False
    for name, value in member["params"].items():
        if human.has_control(body, name):
            human.set_value(body, name, value)
    body[OBJECT_KEY] = member["id"]
    body.name = f"Foule {member['id']:03d}"
    if spec["rig"]:
        skeleton.install(body, weights=not shared.get("rigged", False), correctives=False)
        shared["rigged"] = True
        face_pose = face.builtin_poses().get("expression:" + member["expression"])
        if face_pose is not None:
            face.apply_pose(body, face_pose["pose"])
    for category, value in member["variants"].items():
        applier = VARIANT_APPLIERS.get(category)
        if applier is not None:
            applier(body, value)
    return body


def _animate(body, member, positions, yaws, spec, old_clip):
    """Trajet figé : clés de position et de cap toutes les 5 images (interpolation linéaire) sur le corps ; clip de comportement en NLA sur l'armature."""
    keyframe = bpy.context.preferences.edit
    old = keyframe.keyframe_new_interpolation_type
    keyframe.keyframe_new_interpolation_type = "LINEAR"
    try:
        body.animation_data_create()
        body.animation_data.action = None
        yaw_unwrapped = np.unwrap(yaws)
        forward_yaw = math.atan2(skeleton.FORWARD[1], skeleton.FORWARD[0])
        for f in range(0, spec["frames"], 5):
            body.location = (float(positions[f, 0]), float(positions[f, 1]), 0.0)
            body.rotation_euler = (0.0, 0.0, float(yaw_unwrapped[f]) - forward_yaw)
            body.keyframe_insert("location", frame=1 + f)
            body.keyframe_insert("rotation_euler", frame=1 + f)
    finally:
        keyframe.keyframe_new_interpolation_type = old
    body.animation_data.action.name = f"foule_{member['id']:03d}_trajet"
    rigs = skeleton.rigs_of(body)
    anchor = old_clip.anchor if old_clip else None
    if anchor is None and rigs:
        # Le nom d'un nouveau rig devient un état historique pour l'opération
        # suivante. Il ne départage jamais les slots pendant sa construction.
        anchor = rigs[0].name
    if anchor is not None:
        body[CLIP_ANCHOR_KEY] = anchor
    if rigs:
        rng = np.random.default_rng([spec["seed"], member["id"], 55])
        member["_frames"] = spec["frames"]
        strip, cycle = make_clip(rigs[0], member, rng, old_clip)
        member["cycle_frames"] = float(cycle)
        member["strip_start"] = float(strip.frame_start)
        member.pop("_frames", None)


def _clip_history(armature):
    return {entry["action"]: entry["slot_handle"] for entry in armature.get(CLIP_HISTORY_KEY, {}).values()
            if isinstance(entry.get("action"), bpy.types.Action) and type(entry.get("slot_handle")) is int}


def _clip_anchor(body):
    anchor = body.get(CLIP_ANCHOR_KEY)
    if isinstance(anchor, str) and anchor:
        return anchor
    rigs = skeleton.rigs_of(body)
    return rigs[0].name if len(rigs) == 1 else None


def _old_clip(body, anchor, duplicate_anchor, rig_enabled):
    rigs = skeleton.rigs_of(body)
    if not rig_enabled or not rigs:
        return _ClipContext(anchor, duplicate_anchor=duplicate_anchor)
    if len(rigs) > 1:
        raise ValueError(f"Le membre {body[OBJECT_KEY]} possède plusieurs rigs HumanLoom.")
    rig = rigs[0]
    history = _clip_history(rig)
    animation = rig.animation_data
    if animation is None:
        return _ClipContext(anchor, history=history, duplicate_anchor=duplicate_anchor)
    library_clips = rig.get(LIBRARY_CLIPS_KEY, {})
    bands = tuple((strip.action, strip.action_slot_handle)
                  for track in animation.nla_tracks for strip in track.strips
                  if strip.action is not None and (track.name == "Foule" or library_clips.get(strip.name) == strip.action))
    for source in {action for action, _ in bands if len(action.slots) > 1}:
        handles = {handle for action, handle in bands if action == source and handle > 0}
        if len(handles) == 1:
            history[source] = next(iter(handles))
    return _ClipContext(anchor, bands, history, duplicate_anchor)


def _check_build_context(context):
    if _BUILDING:
        raise ValueError("Une construction de foule est déjà en cours.")
    if context.mode != "OBJECT":
        raise ValueError("La construction de foule requiert le mode Objet.")


@contextmanager
def _crowd_changes():
    global _BUILDING
    if _BUILDING:
        raise ValueError("Une construction de foule est déjà en cours.")
    handlers = bpy.app.handlers.depsgraph_update_post
    handler = human._on_depsgraph
    index = handlers.index(handler) if handler in handlers else None
    # Les gabarits et duplications attribuent eux-mêmes leurs UUID. Les mises à
    # jour du graphe de préparation ne doivent pas réécrire les UUID du fichier.
    if index is not None:
        handlers.pop(index)
    _BUILDING = True
    try:
        yield
    finally:
        _BUILDING = False
        if index is not None and handler not in handlers:
            # La prochaine actualisation seule ne doit pas traiter les mutations
            # internes de Crowd comme une duplication hors de l'opération.
            human.mark_objects_current()
            handlers.insert(index, handler)


def _scene_collections(scene):
    return {scene.collection, *scene.collection.children_recursive}


def _is_crowd_collection(collection):
    prefix, separator, suffix = collection.name.rpartition(".")
    return collection.name == COLLECTION or (separator and prefix == COLLECTION and suffix.isdecimal())


def _crowd_collection(scene, others):
    choices = [c for c in _scene_collections(scene) - others
               if _is_crowd_collection(c) and c.is_editable]
    if len(choices) > 1:
        raise ValueError("Plusieurs collections de foule existent dans cette scène.")
    return next(iter(choices), None)


def _unused_ids(ids, users):
    """Retire de la purge tout ID accessible depuis un utilisateur conservé."""
    dependencies = {item: [] for item in ids}
    keep = set()
    for item in ids:
        for owner in users[item]:
            if owner in ids:
                dependencies[owner].append(item)
            else:
                keep.add(item)
    queue = list(keep)
    for owner in queue:
        for item in dependencies[owner]:
            if item not in keep:
                keep.add(item)
                queue.append(item)
    return ids - keep


def _owned_dependencies(objects, users):
    # Un maillage ou une action sans marque peut provenir d'une bibliothèque.
    library_actions = {action for obj in objects for action in obj.get(LIBRARY_CLIPS_KEY, {}).values()}
    library_actions.update(action for obj in objects for action in _clip_history(obj))
    found = set(objects)
    for body in objects:
        if body.get(OBJECT_KEY) is None or body.get(OWNED_KEY, False):
            continue
        # Les yeux natifs des anciennes foules sont des copies privées dont les
        # pilotes de clés de forme visent le corps. Un emprunteur conserve ces IDs.
        for eye in (body.humanloom.eye_left, body.humanloom.eye_right):
            if eye not in objects or not isinstance(eye.data, bpy.types.Mesh):
                continue
            mesh, keys = eye.data, eye.data.shape_keys
            if keys in users[body] and all(item.is_editable and not item.use_fake_user for item in (mesh, keys)):
                found.update((mesh, keys))
    by_owner = {}
    for item, owners in users.items():
        if (item.is_editable and not item.use_fake_user and item.get(OWNED_KEY, False)
                and item not in library_actions):
            for owner in owners:
                by_owner.setdefault(owner, []).append(item)
    queue = list(found)
    for owner in queue:
        for item in by_owner.get(owner, ()):
            if item not in found:
                found.add(item)
                queue.append(item)
    return found


def _detach_old(links):
    for obj, collections in links.items():
        for collection in collections:
            collection.objects.unlink(obj)


def _external_collections(scene, users):
    other_collections = {c for other in bpy.data.scenes if other != scene for c in _scene_collections(other)}
    instanced = {c for c, owners in users.items() if isinstance(c, bpy.types.Collection)
                 and any(not isinstance(owner, (bpy.types.Scene, bpy.types.Collection)) for owner in owners)}
    return other_collections | instanced | {child for c in instanced for child in c.children_recursive}


def _old_links(scene, old_bodies, initial_users):
    external = _external_collections(scene, initial_users)
    editable = _scene_collections(scene) - external
    links = {}
    for body in old_bodies:
        objects = body.children_recursive
        known = {body.humanloom.eye_left, body.humanloom.eye_right, *skeleton.rigs_of(body), *dental.parts_of(body)}
        if any(obj not in known and not obj.get(OWNED_KEY, False) for obj in objects):
            raise ValueError(f"Provenance indéterminée d'un objet rattaché au membre {body[OBJECT_KEY]}.")
        links.update((obj, tuple(obj.users_collection)) for obj in (body, *objects))
    if any(not obj.is_editable or obj.use_fake_user or any(c not in editable or not c.is_editable for c in collections)
           for obj, collections in links.items()):
        raise ValueError("La foule contient des objets liés à une autre scène ou à une collection non modifiable.")
    return links, external


def _restore_old(scene, links, had_record, record):
    for obj, collections in links.items():
        for collection in collections:
            if obj not in collection.objects.values():
                collection.objects.link(obj)
    if had_record and scene.get(KEY) != record:
        scene[KEY] = record
    elif not had_record and KEY in scene:
        del scene[KEY]


def _purge(ids):
    # Une fois l'opération publiée, Blender ne peut pas recréer l'identité d'un ID supprimé.
    try:
        if ids:
            bpy.data.batch_remove(ids=ids)
    except Exception as error:
        raise CleanupError(f"Opération de foule publiée, purge incomplète : {error}") from error


def _view_states(scene):
    return [(layer, layer.objects.active, layer.active_layer_collection,
             {obj for obj in layer.objects if obj.select_get(view_layer=layer)})
            for layer in scene.view_layers]


def _restore_views(states):
    for layer, active, active_collection, selected in states:
        layer.update()
        layer.active_layer_collection = active_collection
        objects = set(layer.objects)
        for obj in objects:
            was_selected = obj in selected
            if obj.select_get(view_layer=layer) != was_selected:
                obj.select_set(was_selected, view_layer=layer)
        layer.objects.active = active if active in objects else None


def _discard_staging(context, previous_ids):
    allocated = {item for item in bpy.data.user_map() if item.session_uid not in previous_ids}
    if not allocated:
        return
    if context.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    # Détache les allocations même si Blender ne peut ensuite purger leurs IDs.
    for obj in allocated:
        if isinstance(obj, bpy.types.Object):
            for collection in tuple(obj.users_collection):
                collection.objects.unlink(obj)
    for parent in (*bpy.data.collections, *(scene.collection for scene in bpy.data.scenes)):
        for child in tuple(parent.children):
            if child in allocated:
                parent.children.unlink(child)
    bpy.data.batch_remove(ids=allocated)


def _refuse_active_cloth(bodies):
    """Lot E : la simulation de tissu d'une robe (modificateur « Tissu », collection « HL Colliders », cache cuit) vit hors des collections de la foule ; effacer ou régénérer le personnage la laisserait en objets orphelins (mesuré :
    « La foule contient des objets liés à une autre scène… » sans cause lisible, 4 collections de collision laissées). Refus clair AVANT toute modification : désactiver la simulation (panneau Tissu) puis recommencer."""
    from . import cloth_sim, garments
    active = [g.name for b in bodies for g in garments.garments_of(b) if cloth_sim.is_enabled(g)]
    if active:
        raise ValueError("La simulation de tissu est active sur %d robe(s) de la foule (%s) : désactivez-la (panneau Tissu) avant d'effacer ou de régénérer." % (len(active), ", ".join(active[:3])))


@_crowd_changes()
def _replace(context, spec, members, prepared, positions, yaws, old_bodies, result):
    """Prépare les candidats dans le graphe, publie les liens et le JSON, puis retire les IDs devenus inutiles."""
    for member in prepared:
        if not np.isfinite(member["start"]).all() or np.max(np.abs(member["start"])) > BLENDER_COORD_LIMIT:
            raise ValueError(f"Personnage {member['id']} : position de départ non représentable dans Blender.")
    scene, view = context.scene, context.view_layer
    _refuse_active_cloth(old_bodies)
    initial_users = bpy.data.user_map()
    old_links, external_collections = _old_links(scene, old_bodies, initial_users)
    old_objects = set(old_links)
    destination = _crowd_collection(scene, external_collections)
    old_clips = {}
    if old_bodies:
        anchors = {body: _clip_anchor(body) for body in members_of(scene)}
        counts = Counter(anchors.values())
        old_clips = {body[OBJECT_KEY]: _old_clip(body, anchors[body], counts[anchors[body]] > 1, spec["rig"])
                     for body in old_bodies}
    previous_ids = {item.session_uid for item in initial_users}
    had_record, record = KEY in scene, scene.get(KEY)
    view_states = _view_states(scene)

    try:
        staging = bpy.data.collections.new("Préparation foule HumanLoom")
        scene.collection.children.link(staging)
        view.update()
        layer = view.layer_collection.children[staging.name]
        shared = {}
        candidate_bodies = []
        for i, member in enumerate(prepared):
            view.active_layer_collection = layer
            body = _make_body(context, spec, member, shared)
            candidate_bodies.append(body)
            body.location = (member["start"][0], member["start"][1], 0.0)
            _animate(body, member, positions[:, i], yaws[:, i], spec, old_clips.get(member["id"]))
        serialized = json.dumps({"spec": spec, "members": members}, ensure_ascii=False, allow_nan=False)
        value = result()

        template = shared.get("template")
        templates = {template, *template.children_recursive} if template is not None else set()
        if any(body.parent is not None or body.get(OBJECT_KEY) != member["id"] or staging not in body.users_collection
               for body, member in zip(candidate_bodies, prepared)):
            raise ValueError("Une variante a déplacé ou modifié l'identité d'un candidat de la foule.")
        if any(item.session_uid in previous_ids for item in (*staging.all_objects, *staging.children_recursive)):
            raise ValueError("Une variante a ajouté des objets ou des collections préexistants à la préparation de la foule.")
        staging_collections = {staging, *staging.children_recursive}
        if (staging_collections & _external_collections(scene, bpy.data.user_map())
                or any(staging in collection.children.values() for collection in bpy.data.collections)
                or any(obj.session_uid not in previous_ids and any(c not in staging_collections for c in obj.users_collection)
                       for obj in bpy.data.objects)):
            raise ValueError("Une variante a lié des objets préparés à une collection extérieure.")
        candidates = {obj for body in candidate_bodies for obj in (body, *body.children_recursive)}
        if staging.children or set(staging.objects) != (candidates | templates):
            raise ValueError("Une variante de foule doit lier chaque objet préparé au personnage dans la collection de préparation.")
        if destination is None:
            destination = bpy.data.collections.new(COLLECTION)
            scene.collection.children.link(destination)
        for obj in staging.objects:
            if obj not in templates:
                destination.objects.link(obj)
        scene.collection.children.unlink(staging)
        _restore_views(view_states)
        scene[KEY] = serialized
        _detach_old(old_links)
        for layer in scene.view_layers:
            layer.update()

        users = bpy.data.user_map()
        allocated = {item for item in users if item.session_uid not in previous_ids}
        # Les IDs préexistants sans marque ont une provenance inconnue, notamment les actions.
        garbage = _unused_ids(allocated | _owned_dependencies(old_objects, users), users)
        if not old_objects <= garbage or not templates <= garbage:
            raise ValueError("Des objets de la foule sont utilisés hors de leur collection de préparation.")
        for item in allocated - garbage - {destination}:
            if item.is_editable:
                item[OWNED_KEY] = True
    except Exception as error:
        failures = []
        for label, restore in (
            ("foule", lambda: _restore_old(scene, old_links, had_record, record)),
            ("allocations", lambda: _discard_staging(context, previous_ids)),
            ("calques de vue", lambda: _restore_views(view_states)),
        ):
            try:
                restore()
            except Exception as rollback_error:
                failures.append(f"{label} : {rollback_error}")
        if failures:
            raise RollbackError(f"{error}. Restauration incomplète ({', '.join(failures)}).") from error
        raise
    _purge(garbage)
    return value


def generate(context, spec, replace=False):
    """Crée la foule FIGÉE : tire, place, anime et enregistre (scène + objets). Refuse si une foule existe déjà et `replace` est faux. Retourne le résumé."""
    _check_build_context(context)
    scene = context.scene
    if scene.get(KEY) and not replace:
        raise ValueError("Une foule figée existe déjà : « Régénérer » est la seule façon de la modifier.")
    if isinstance(spec, dict) and spec.get("fps_scene", True):
        # Cadence (ANI-003) : les clés de trajet sont posées à UNE image de scène par pas de simulation ; la simulation doit donc tourner à la cadence de la scène, sinon les personnages marchent plus vite ou plus lentement
        # que leurs vitesses (m/s) dans une scène à 30 ou 60 i/s. `fps_scene` à faux conserve le `fps` du spec (cadence de simulation imposée).
        spec = dict(spec, fps=scene.render.fps / scene.render.fps_base)
    _validate_spec(spec)
    members = plan(spec, sample_members(spec))
    if spec["rig"]:
        for member in members:
            _requested_action(member)
    positions, yaws = simulate(spec, members)
    _check_motion(positions, yaws, members, blender=True)
    old = members_of(scene) if scene.get(KEY) else ()

    def summary():
        return {"personnages": len(members), "diversite": diversity_report(members), "diversite_non_garantie": [m["id"] for m in members if not m.get("diversite_garantie", True)],  # ANI-021 : après 50 essais le dernier tirage est gardé même trop proche d'un autre ; la liste le dit au lieu de le taire
                "comportements": {b: sum(1 for m in members if m["behavior"] == b) for b in BEHAVIORS}}

    return _replace(context, spec, members, members, positions, yaws, old, summary)


def load(scene):
    raw = scene.get(KEY)
    if not raw:
        return None
    data = json.loads(raw)
    return data["spec"], data["members"]


@_crowd_changes()
def clear(scene):
    """Supprime les personnages de la foule et l'enregistrement."""
    if bpy.context.scene == scene and bpy.context.mode != "OBJECT":
        raise ValueError("L'effacement de la foule requiert le mode Objet.")
    _refuse_active_cloth(members_of(scene))
    links, _ = _old_links(scene, members_of(scene), bpy.data.user_map())
    if any(obj.mode != "OBJECT" for obj in links):
        raise ValueError("L'effacement de la foule requiert le mode Objet.")
    had_record, record = KEY in scene, scene.get(KEY)
    view_states = _view_states(scene)
    try:
        _detach_old(links)
        for layer in scene.view_layers:
            layer.update()
        users = bpy.data.user_map()
        objects = set(links)
        garbage = _unused_ids(_owned_dependencies(objects, users), users)
        if not objects <= garbage:
            raise ValueError("Des objets de la foule sont utilisés hors de leurs collections.")
        if KEY in scene:
            del scene[KEY]
    except Exception:
        _restore_old(scene, links, had_record, record)
        _restore_views(view_states)
        raise
    _purge(garbage)


def regenerate_member(context, index):
    """Régénère UN personnage (nouveau tirage : la régénération de ce personnage est comptée dans son `attempt`) ; les autres ne changent pas."""
    _check_build_context(context)
    scene = context.scene
    loaded = load(scene)
    if loaded is None:
        raise ValueError("Aucune foule figée.")
    spec, members = loaded
    _validate_spec(spec)
    _validate_json(members, "Les membres de la foule")
    old = next(m for m in members if m["id"] == index)
    body = next(o for o in members_of(scene) if o[OBJECT_KEY] == index)
    sub_spec = dict(spec, regeneration=spec.get("regeneration", 0) + 1000 + old.get("regenerated", 0) + 1)
    new = sample_member(sub_spec, index, [m for m in members if m["id"] != index])
    new["regenerated"] = old.get("regenerated", 0) + 1
    plan_spec = dict(sub_spec, count=len(members))
    planned = plan(plan_spec, [new])[0]
    if spec["rig"]:
        _requested_action(planned)
    simulated = [planned, *(m for m in members if m["id"] != index)]
    positions, yaws = simulate(spec, simulated)  # le nouveau personnage évite les autres tels qu'ils sont
    _check_motion(positions, yaws, simulated, blender=True)
    members[members.index(old)] = planned
    return _replace(context, spec, members, [planned], positions, yaws, [body], lambda: planned)


def regenerate_all(context):
    """Nouvelle foule avec la graine incrémentée de la régénération (demande explicite)."""
    spec, _ = load(context.scene)
    spec = dict(spec, regeneration=_integer(spec.get("regeneration", 0), "regeneration") + 1)
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
    thresholds = _lod_thresholds(spec)
    for body in members_of(scene):
        distance = (body.matrix_world.translation - camera.matrix_world.translation).length
        level = sum(1 for t in thresholds if distance >= t)
        try:
            apply_lod(body, max(level, lod_of(body)))
        except ValueError:
            pass
        out[body[OBJECT_KEY]] = lod_of(body)
    return out


# --- élimination hors caméra (culling) -------------------------------------------------------------------------------------------------------------------------
CULL_KEY = "humanloom_crowd_cull"
CULL_PROPERTIES = ("hide_viewport", "hide_render")


def _body_family(body):
    return [body, *body.children_recursive]


def _location_curves(body):
    """Courbes d'animation de la position du corps (trajet figé de la foule) : {indice d'axe: courbe}."""
    animation = body.animation_data
    action = animation.action if animation else None
    if action is None:
        return {}
    channelbag = action_get_channelbag_for_slot(action, animation.action_slot)
    if channelbag is None:
        return {}
    return {c.array_index: c for c in channelbag.fcurves if c.data_path == "location"}


def _trajectory(body, frames):
    """Position du corps à chaque image demandée, lue sur les courbes (sans changer d'image : aucune évaluation du graphe)."""
    curves = _location_curves(body)
    base = np.array(body.location, float)
    out = np.tile(base, (len(frames), 1))
    for axis, curve in curves.items():
        out[:, axis] = [curve.evaluate(f) for f in frames]
    return out


def uncull(scene):
    """Retire l'élimination hors caméra : supprime les clés de visibilité des personnages et de leurs enfants et les remet visibles. Retourne le nombre de courbes retirées."""
    removed = 0
    for body in members_of(scene):
        for obj in _body_family(body):
            animation = obj.animation_data
            action = animation.action if animation else None
            if action is not None:
                channelbag = action_get_channelbag_for_slot(action, animation.action_slot)
                if channelbag is not None:
                    for curve in [c for c in channelbag.fcurves if c.data_path in CULL_PROPERTIES]:
                        channelbag.fcurves.remove(curve)
                        removed += 1
                if obj is not body and not any(True for layer in action.layers for strip in layer.strips for bag in strip.channelbags for _ in bag.fcurves):
                    animation.action = None
                    if action.users == 0:
                        bpy.data.actions.remove(action)
            obj.hide_viewport = obj.hide_render = False
    if CULL_KEY in scene:
        del scene[CULL_KEY]
    return removed


def _sphere_corners(center, radius):
    offsets = np.array([(sx, sy, sz) for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)], float) * radius
    return np.vstack([center[None, :], center[None, :] + offsets])


def cull(scene, camera=None, margin=0.05, extra_m=2.0, viewport=True, render=True, frame_range=None):
    """Élimination hors caméra : pour chaque image, un personnage dont la sphère englobante (rayon 1,1 m + `extra_m`, pour les ombres et reflets proches) est ENTIÈREMENT hors du champ de la caméra (marge normalisée `margin`)
    ou derrière elle est masqué (`hide_viewport` et/ou `hide_render`, clés CONSTANTES sur le corps et ses enfants). Blender n'évalue pas les objets masqués : le coût par image baisse avec le nombre de personnages
    hors champ. La caméra peut être animée. Le résultat est FIGÉ comme le reste de la foule : à refaire (ou `uncull`) si la caméra ou les trajets changent ; régénérer un personnage supprime ses clés de visibilité.
    Retourne {"personnages": n, "images": nombre d'images, "masques_par_image_moyen": ..., "jamais_visibles": [...], "toujours_visibles": n}."""
    from bpy_extras.object_utils import world_to_camera_view
    from mathutils import Vector
    camera = camera or scene.camera
    if camera is None:
        raise ValueError("Aucune caméra : définir la caméra de la scène.")
    bodies = members_of(scene)
    if not bodies:
        raise ValueError("Aucune foule dans la scène.")
    if bpy.context.mode != "OBJECT":
        raise ValueError("L'élimination hors caméra requiert le mode Objet.")
    uncull(scene)
    start, end = frame_range or (scene.frame_start, scene.frame_end)
    frames = list(range(int(start), int(end) + 1))
    original = scene.frame_current
    families = {b.name: _body_family(b) for b in bodies}
    saved = [(o, o.hide_viewport, o.hide_render) for fam in families.values() for o in fam]
    for obj, _v, _r in saved:  # foule masquée pendant le balayage des images : le changement d'image n'évalue que le reste de la scène
        obj.hide_viewport = True
    trajectories = {b.name: _trajectory(b, frames) for b in bodies}
    hidden = {b.name: np.zeros(len(frames), bool) for b in bodies}
    try:
        for k, frame in enumerate(frames):
            scene.frame_set(frame)
            for b in bodies:
                p = trajectories[b.name][k]
                points = _sphere_corners(np.array([p[0], p[1], p[2] + 0.95]), 1.1 + extra_m)
                views = np.array([world_to_camera_view(scene, camera, Vector(q)) for q in points])
                x, y, z = views[:, 0], views[:, 1], views[:, 2]
                outside = bool((z < 0.0).all() or (x < -margin).all() or (x > 1.0 + margin).all() or (y < -margin).all() or (y > 1.0 + margin).all())
                hidden[b.name][k] = outside
    finally:
        for obj, v, r in saved:
            obj.hide_viewport, obj.hide_render = v, r
    props = [p for p in CULL_PROPERTIES if (p == "hide_viewport" and viewport) or (p == "hide_render" and render)]
    keyframe = bpy.context.preferences.edit
    old = keyframe.keyframe_new_interpolation_type
    keyframe.keyframe_new_interpolation_type = "CONSTANT"
    changed = 0
    try:
        for b in bodies:
            states = hidden[b.name]
            if not states.any():
                continue
            changes = [0] + [k for k in range(1, len(frames)) if states[k] != states[k - 1]]
            for obj in families[b.name]:
                for k in changes:
                    for prop in props:
                        setattr(obj, prop, bool(states[k]))
                        obj.keyframe_insert(prop, frame=frames[k])
                for prop in props:
                    setattr(obj, prop, bool(states[0]))
            changed += 1
    finally:
        keyframe.keyframe_new_interpolation_type = old
    scene.frame_set(original)
    never = [int(b[OBJECT_KEY]) for b in bodies if hidden[b.name].all()]
    summary = {"personnages": len(bodies), "images": len(frames), "masques_par_image_moyen": round(float(np.sum([h for h in hidden.values()], axis=0).mean()), 2), "jamais_visibles": never,
               "toujours_visibles": int(sum(1 for b in bodies if not hidden[b.name].any())), "personnages_a_cles_de_visibilite": changed, "camera": camera.name, "marge": margin, "marge_m": extra_m}
    scene[CULL_KEY] = json.dumps(summary)
    return summary
