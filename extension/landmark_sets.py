"""Portable vertex landmarks with exact indexed-topology checks and rollback."""

import hashlib
import math
from contextlib import contextmanager

import bpy
import numpy as np

from . import anatomy, human
from .proportions import BASE_ID


FORMAT = "human_modeling.landmarks"
VERSION = 1
STATUSES = {"manual", "mirrored_review"}
PAIRS = (("al_l", "al_r"), ("ch_l", "ch_r"), ("en_l", "en_r"))


def topology(body):
    """Hash original polygon/loop indices; coordinates and morphs may differ."""
    mesh = body.data
    loops = np.empty(len(mesh.loops), dtype="<i4")
    counts = np.empty(len(mesh.polygons), dtype="<i4")
    edges = np.empty(len(mesh.edges) * 2, dtype="<i4")
    mesh.loops.foreach_get("vertex_index", loops)
    mesh.polygons.foreach_get("loop_total", counts)
    mesh.edges.foreach_get("vertices", edges)
    digest = hashlib.sha256()
    digest.update(np.asarray((len(mesh.vertices), len(mesh.edges), len(mesh.polygons)), dtype="<i4").tobytes())
    digest.update(counts.tobytes())
    digest.update(loops.tobytes())
    digest.update(edges.tobytes())
    return digest.hexdigest()


def validate(payload):
    if not isinstance(payload, dict) or payload.get("format") != FORMAT:
        raise ValueError("Ce fichier ne contient pas un jeu de repères Human Modeling.")
    if type(payload.get("version")) is not int or payload["version"] != VERSION:
        raise ValueError("Version de jeu de repères non prise en charge.")
    count, fingerprint = payload.get("vertex_count"), payload.get("topology_sha256")
    if (payload.get("base") != BASE_ID or type(count) is not int or not 0 < count < 10_000_000
            or not isinstance(fingerprint, str) or len(fingerprint) != 64
            or any(char not in "0123456789abcdef" for char in fingerprint)):
        raise ValueError("L’identité de topologie des repères est invalide.")
    points = payload.get("points")
    known = {entry[0] for entry in anatomy.LANDMARKS}
    if not isinstance(points, dict) or set(points) - known:
        raise ValueError("La liste des repères contient des identifiants invalides.")
    normalized = {}
    for key, entry in points.items():
        if (not isinstance(entry, dict) or type(entry.get("vertex")) is not int
                or not 0 <= entry["vertex"] < count or not isinstance(entry.get("status", "manual"), str)
                or entry.get("status", "manual") not in STATUSES):
            raise ValueError("Sommet ou statut de repère invalide : " + key)
        normalized[key] = {"vertex": entry["vertex"], "status": entry.get("status", "manual")}
    for a, b in PAIRS:
        if a in normalized and b in normalized and normalized[a]["vertex"] == normalized[b]["vertex"]:
            raise ValueError("Les deux repères d’une paire occupent le même sommet.")
    return {"format": FORMAT, "version": VERSION, "base": BASE_ID,
            "vertex_count": count, "topology_sha256": fingerprint, "points": normalized}


def capture(body):
    records = anatomy.landmarks(body, bpy.context)
    points = {}
    for key, record in records.items():
        obj = next(obj for obj in body.children if obj.get(anatomy.LANDMARK_KEY) == key)
        if obj.type != "EMPTY":
            raise ValueError("Un repère doit être un objet Empty : " + key)
        points[key] = {"vertex": record["vertex"], "status": obj.get("hm_placement_status", "manual")}
    return validate({"format": FORMAT, "version": VERSION, "base": body.data.get("human_modeling_base", BASE_ID),
                     "vertex_count": len(body.data.vertices), "topology_sha256": topology(body), "points": points})


def check_compatible(body, requested):
    if (body.data.get("human_modeling_base") != requested["base"]
            or len(body.data.vertices) != requested["vertex_count"]
            or topology(body) != requested["topology_sha256"]):
        raise ValueError("Les repères utilisent une autre topologie. Aucun repère n’a été modifié.")
    if not body.is_editable or not body.data.is_editable:
        raise ValueError("Le personnage doit être éditable.")


@contextmanager
def transaction(body):
    capture(body)  # Check all existing markers before any mutation.
    known = {entry[0] for entry in anatomy.LANDMARKS}
    existing = {obj.get(anatomy.LANDMARK_KEY): obj for obj in body.children if obj.get(anatomy.LANDMARK_KEY) in known}
    snapshots = {}
    attributes = ("parent_type", "parent_vertices", "location", "matrix_parent_inverse", "empty_display_type",
                  "empty_display_size", "show_in_front", "hide_render")
    for key, obj in existing.items():
        if not obj.is_editable:
            raise ValueError("Un repère à remplacer n’est pas éditable.")
        values = {}
        for name in attributes:
            value = getattr(obj, name)
            values[name] = value.copy() if hasattr(value, "copy") else tuple(value) if name == "parent_vertices" else value
        snapshots[key] = (values, dict(obj.items()))
    before = set(body.children)
    try:
        yield
    except Exception:
        for obj in set(body.children) - before:
            bpy.data.objects.remove(obj, do_unlink=True)
        for key, (values, properties) in snapshots.items():
            obj = existing[key]
            for name, value in values.items():
                setattr(obj, name, value)
            for name in tuple(obj.keys()):
                if name not in properties:
                    del obj[name]
            for name, value in properties.items():
                obj[name] = value
        bpy.context.view_layer.update()
        raise
    bpy.context.view_layer.update()


def apply(body, payload):
    """Merge supplied points. Existing unmentioned landmarks remain unchanged."""
    requested = validate(payload)
    check_compatible(body, requested)
    with transaction(body):
        for key, entry in requested["points"].items():
            marker = anatomy.attach(body, key, entry["vertex"])
            marker["hm_placement_status"] = entry["status"]


def mirrored(body):
    """Fill missing partners by reflection on the neutral mesh, without overwrites."""
    payload = capture(body)
    if not human.is_native(body) and body.data.shape_keys is None:
        raise ValueError("Le personnage ne dispose pas de sa forme neutre.")
    coords = human.base_coordinates(body)
    tolerance = float(np.ptp(coords[:, 2])) * .003
    added = []
    for a, b in PAIRS:
        if (a in payload["points"]) == (b in payload["points"]):
            continue
        source, target = (a, b) if a in payload["points"] else (b, a)
        index = payload["points"][source]["vertex"]
        reflection = coords[index] * (-1, 1, 1)
        distances = np.linalg.norm(coords - reflection, axis=1)
        candidate = int(np.argmin(distances))
        if candidate == index or not math.isfinite(distances[candidate]) or distances[candidate] > tolerance:
            raise ValueError("Aucun sommet symétrique assez proche pour " + target)
        payload["points"][target] = {"vertex": candidate, "status": "mirrored_review"}
        added.append(target)
    return payload, added
