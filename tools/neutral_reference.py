"""Référence figée de la forme neutre de l'asset actuel (D-19) : lecture et comparaison.

Le fichier `tools/data/neutral_reference.json` est produit par `tools/make_neutral_reference.py` et régénéré
volontairement quand la forme de l'asset change. Il contient, pour chaque (sexe, stade d'âge), un sous-échantillon de
sommets de la cage (modificateurs coupés, toutes les autres commandes à 0) et l'empreinte SHA-256 de `realistic.blend`.
Échantillon du corps : 1 sommet sur 25 + pieds (1 sur 16) + mains (1 sur 16) + tous les sommets du pourtour des yeux (zones de
défauts connus) ; yeux : 1 sommet sur 12 de chacun des deux globes.
Un test qui l'utilise échoue si l'asset change sans régénération ou si la forme s'écarte de plus de TOLERANCE."""
import hashlib
import json
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ASSET = ROOT / "tools/data/realistic.blend"
REFERENCE = Path(__file__).resolve().parent / "data/neutral_reference.json"
SEXES = (0., .5, 1.)
STAGES = (0., .5, 1., 1.5, 2., 2.5, 3.)
STRIDE = 25
ZONE_STRIDE = 16
EYE_STRIDE = 12
EYELID_RADIUS = .03  # m autour du centre de chaque globe
TOLERANCE = 1e-5  # mètres


def asset_sha256():
    return hashlib.sha256(ASSET.read_bytes()).hexdigest()


def cage(body):
    """Positions des sommets de la cage évaluée par les clés de forme seules (modificateurs coupés le temps de la mesure)."""
    states = [(m, m.show_viewport) for m in body.modifiers]
    for modifier, _ in states:
        modifier.show_viewport = False
    try:
        body.data.shape_keys.update_tag()
        bpy.context.view_layer.update()
        evaluated = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
        mesh = evaluated.to_mesh()
        points = np.array([v.co[:] for v in mesh.vertices])
        evaluated.to_mesh_clear()
        return points
    finally:
        for modifier, shown in states:
            modifier.show_viewport = shown
        bpy.context.view_layer.update()


def set_state(body, sex, stage):
    keys = body.data.shape_keys
    keys.key_blocks["Morphologie"].value = sex
    keys["human_modeling_age"] = stage


def key(sex, stage):
    return f"{sex:g}|{stage:g}"


def basis(obj):
    return np.array([v.co[:] for v in obj.data.shape_keys.key_blocks["Basis"].data])


def eyes_of(body):
    eyes = [o for o in body.children if o.type == "MESH" and o.data.shape_keys and "Morphologie" in o.data.shape_keys.key_blocks]
    return sorted(eyes, key=lambda o: o.data.shape_keys.key_blocks["Basis"].data[0].co.x)


def body_indices(body):
    """Indices des sommets de la cage mesurés : fonction de la seule Basis (l'empreinte de l'asset garantit qu'elle est stable)."""
    base = basis(body)
    height = base[:, 2].max() - base[:, 2].min()
    feet = np.where(base[:, 2] < base[:, 2].min() + .06 * height)[0][::ZONE_STRIDE]
    hands = np.where(np.abs(base[:, 0]) > .75 * np.abs(base[:, 0]).max())[0][::ZONE_STRIDE]
    centres = [basis(e).mean(axis=0) for e in eyes_of(body)]
    lids = np.where(np.any([np.linalg.norm(base - c, axis=1) < EYELID_RADIUS for c in centres], axis=0))[0]
    return np.unique(np.concatenate([np.arange(0, len(base), STRIDE), feet, hands, lids]))


def evaluated_points(obj):
    obj.data.shape_keys.update_tag()
    bpy.context.view_layer.update()
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    points = np.array([v.co[:] for v in mesh.vertices])
    evaluated.to_mesh_clear()
    return points


def sample(body):
    """(points du corps, points des deux yeux) de la référence pour l'état courant de `body`."""
    return cage(body)[body_indices(body)], [evaluated_points(e)[::EYE_STRIDE] for e in eyes_of(body)]


def fingerprint(points):
    """Empreinte informative (arrondi à 1e-6 m) ; la comparaison réelle se fait avec TOLERANCE."""
    return hashlib.sha256(np.round(points, 6).astype(np.float32).tobytes()).hexdigest()


def load():
    data = json.loads(REFERENCE.read_text(encoding="utf-8"))
    if data["asset_sha256"] != asset_sha256():
        raise AssertionError("realistic.blend a changé depuis la référence figée : exécuter tools/make_neutral_reference.py "
                             "(régénération volontaire) puis revoir le diff")
    return data


def check(body, reference, sex, stage, tolerance=TOLERANCE):
    """Écart maximal (m) entre `body` (et ses yeux) et la référence ; AssertionError au-delà de la tolérance."""
    state = reference["states"][key(sex, stage)]
    points, eyes = sample(body)
    expected = np.array(state["points"]).reshape(-1, 3)
    assert points.shape == expected.shape, (points.shape, expected.shape)
    difference = float(np.abs(points - expected).max())
    assert len(eyes) == len(state["eyes"]), "les deux yeux doivent être présents"
    for got, want in zip(eyes, state["eyes"]):
        difference = max(difference, float(np.abs(got - np.array(want).reshape(-1, 3)).max()))
    assert difference < tolerance, (sex, stage, difference)
    return difference
