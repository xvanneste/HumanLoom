"""Explicit surface landmarks and closed mesh sections. No inferred age norms."""

import math

import bpy
import numpy as np
from mathutils import Vector


LANDMARK_KEY = "hm_measurement_landmark"
LANDMARKS = (
    ("pelvis", "Bassin · repère de segmentation", "Placement manuel, sans équivalence automatique avec la taille assise"),
    ("waist_level", "Abdomen · niveau de coupe", "Choisir et documenter le niveau anatomique de la coupe"),
    ("hips_level", "Bassin · niveau de coupe", "Choisir le niveau de coupe sur le bassin"),
    ("chest_level", "Thorax · niveau de coupe", "Choisir le niveau de coupe sur le thorax"),
    ("al_l", "Nez · alare gauche", "Point latéral de l’aile du nez, côté gauche du personnage"),
    ("al_r", "Nez · alare droit", "Point latéral de l’aile du nez, côté droit du personnage"),
    ("ch_l", "Bouche · commissure gauche", "Jonction des lèvres à la commissure gauche du personnage"),
    ("ch_r", "Bouche · commissure droite", "Jonction des lèvres à la commissure droite du personnage"),
    ("en_l", "Œil · canthus interne gauche", "Jonction médiale des paupières gauches"),
    ("en_r", "Œil · canthus interne droit", "Jonction médiale des paupières droites"),
)
SECTION_IDS = ("waist_level", "hips_level", "chest_level")
DISTANCES = {
    "nose_width": ("Largeur du nez", "al_l", "al_r", "nose_width"),
    "mouth_width": ("Largeur de la bouche", "ch_l", "ch_r", "mouth"),
    "inner_eye_distance": ("Distance intercanthale", "en_l", "en_r", "eye_spacing"),
}
FIT_CONTROLS = {"waist_level": "waist", "hips_level": "hips", "chest_level": "torso_depth"}
FIT_CONTROLS.update({key: value[3] for key, value in DISTANCES.items()})
FIT_CONTROLS["pelvis_ratio"] = "legs"
MEASURES = tuple((key, dict((i, label) for i, label, _ in LANDMARKS)[key], "Périmètre de section") for key in SECTION_IDS)
MEASURES += tuple((key, value[0], "Distance droite entre deux repères") for key, value in DISTANCES.items())
MEASURES += (("pelvis_ratio", "Sol → repère / stature", "Rapport technique utilisant le repère bassin manuel"),)


def attach(body, identifier, vertex):
    if identifier not in {item[0] for item in LANDMARKS} or not 0 <= vertex < len(body.data.vertices):
        raise ValueError("Repère ou sommet invalide.")
    existing = [obj for obj in body.children if obj.get(LANDMARK_KEY) == identifier]
    if len(existing) > 1:
        raise ValueError("Plusieurs objets portent ce repère. Supprimez le doublon.")
    marker = existing[0] if existing else bpy.data.objects.new("Mesure · " + dict((i, label) for i, label, _ in LANDMARKS)[identifier], None)
    if not existing:
        body.users_collection[0].objects.link(marker)
    marker.parent = body
    marker.parent_type = "VERTEX"
    marker.parent_vertices = (vertex, 0, 0)
    marker.matrix_parent_inverse.identity()
    marker.location = (0, 0, 0)
    marker[LANDMARK_KEY] = identifier
    marker["vertex_count"] = len(body.data.vertices)
    marker["hm_placement_status"] = "manual"
    marker.empty_display_type = "SPHERE"
    marker.empty_display_size = .004 if identifier not in SECTION_IDS and identifier != "pelvis" else .008
    marker.show_in_front = True
    marker.hide_render = True
    return marker


def landmarks(body, context):
    result = {}
    graph = context.evaluated_depsgraph_get()
    for obj in body.children:
        identifier = obj.get(LANDMARK_KEY)
        if identifier not in {item[0] for item in LANDMARKS}:
            continue
        if identifier in result:
            raise ValueError("Repère en double : " + identifier)
        if (obj.type != "EMPTY" or obj.parent_type != "VERTEX" or obj.get("vertex_count") != len(body.data.vertices)
                or not 0 <= obj.parent_vertices[0] < len(body.data.vertices)):
            raise ValueError("Repère incompatible avec la topologie : " + identifier)
        if obj.location.length > 1e-8:
            raise ValueError("Repère déplacé hors de son sommet : " + identifier)
        point = obj.evaluated_get(graph).matrix_world.translation.copy()
        if not all(math.isfinite(value) for value in point):
            raise ValueError("Coordonnées de repère invalides.")
        result[identifier] = {"point": point, "vertex": obj.parent_vertices[0], "status": obj.get("hm_placement_status", "manual")}
    return result


def section_loops(coords, triangles, level):
    """Intersect a triangulated surface with local z=level and return simple cycles.

    Edge identities join adjacent triangles without coordinate rounding. A tiny
    upward displacement avoids planes passing exactly through a mesh vertex.
    """
    extent = max(float(np.ptp(coords[:, 2])), 1e-6)
    tolerance = extent * 1e-9
    actual = float(level)
    for _ in range(8):
        if np.min(np.abs(coords[:, 2] - actual)) > tolerance:
            break
        actual += tolerance * 4
    else:
        raise ValueError("Coupe dégénérée au niveau choisi.")
    heights = coords[:, 2] - actual
    tri_heights = heights[triangles]
    crossing = triangles[(tri_heights.min(axis=1) < 0) & (tri_heights.max(axis=1) > 0)]
    nodes, graph = {}, {}
    for tri in crossing:
        ends = []
        for a, b in ((tri[0], tri[1]), (tri[1], tri[2]), (tri[2], tri[0])):
            if (heights[a] > 0) == (heights[b] > 0):
                continue
            key = (int(min(a, b)), int(max(a, b)))
            if key not in nodes:
                nodes[key] = coords[a] + (coords[b] - coords[a]) * (-heights[a] / (heights[b] - heights[a]))
            ends.append(key)
        if len(ends) != 2:
            raise ValueError("Intersection ambiguë du maillage.")
        a, b = ends
        graph.setdefault(a, set()).add(b)
        graph.setdefault(b, set()).add(a)
    if not graph or any(len(neighbors) != 2 for neighbors in graph.values()):
        raise ValueError("La coupe ne forme pas des contours fermés simples.")
    remaining, loops = set(graph), []
    while remaining:
        first = min(remaining)
        previous, current, path = None, first, []
        while True:
            if current not in remaining:
                if current != first:
                    raise ValueError("Contour de coupe ambigu.")
                break
            remaining.remove(current)
            path.append(nodes[current])
            following = sorted(graph[current] - {previous})[0]
            previous, current = current, following
        loops.append(np.asarray(path))
    return loops, actual


def encloses_axis(points):
    """Is the local torso axis (x=0,y=0) inside the planar cycle?"""
    inside = False
    for a, b in zip(points, np.roll(points, -1, axis=0)):
        if (a[1] > 0) != (b[1] > 0) and 0 < a[0] + (b[0] - a[0]) * (-a[1]) / (b[1] - a[1]):
            inside = not inside
    return inside


def local_report(body, context, include_paths=False, only=None):
    markers = landmarks(body, context)
    scale = context.scene.unit_settings.scale_length
    result = {"landmarks": {key: {"vertex": value["vertex"], "status": value["status"], "world_position_m": list(value["point"] * scale)}
                             for key, value in markers.items()}, "distances": {}, "sections": {}}
    for key, (_, a, b, _) in DISTANCES.items():
        if only is not None and only != key:
            continue
        if a in markers and b in markers:
            if markers[a]["vertex"] == markers[b]["vertex"]:
                result["distances"][key] = {"error": "Les deux repères occupent le même sommet."}
            else:
                result["distances"][key] = {"distance_m": (markers[a]["point"] - markers[b]["point"]).length * scale,
                                            "endpoints": [a, b], "method": "Euclidean distance between manually placed surface landmarks"}
    if not any(key in markers and (only is None or only == key) for key in SECTION_IDS):
        return result
    evaluated = body.evaluated_get(context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    try:
        matrix = evaluated.matrix_world
        inverse = matrix.inverted()
        coords = np.empty(len(mesh.vertices) * 3)
        mesh.vertices.foreach_get("co", coords)
        coords = coords.reshape((-1, 3))
        if not np.isfinite(coords).all():
            raise ValueError("Coordonnées du corps invalides.")
        mesh.calc_loop_triangles()
        triangles = np.empty(len(mesh.loop_triangles) * 3, dtype=np.int32)
        mesh.loop_triangles.foreach_get("vertices", triangles)
        triangles = triangles.reshape((-1, 3))
        transform = np.array(matrix.to_3x3())
        for key in SECTION_IDS:
            if key not in markers or (only is not None and only != key):
                continue
            level = (inverse @ markers[key]["point"]).z
            try:
                loops, actual = section_loops(coords, triangles, level)
                central = [points for points in loops if encloses_axis(points)]
                if len(central) != 1:
                    raise ValueError("Choisissez une coupe unique du buste autour de son axe central.")
                points = central[0]
                perimeter = float(np.linalg.norm((points - np.roll(points, 1, axis=0)) @ transform.T, axis=1).sum()) * scale
                section = {"perimeter_m": perimeter, "local_z": actual, "plane_offset_local": actual - level,
                           "other_contours": len(loops) - 1, "method": "Closed mesh section, local XY plane through manual landmark; unique contour enclosing local torso axis"}
                if include_paths:
                    section["local_path"] = points.tolist()
                result["sections"][key] = section
            except ValueError as error:
                result["sections"][key] = {"error": str(error)}
    finally:
        evaluated.to_mesh_clear()
    return result


def value(body, context, identifier):
    if identifier == "pelvis_ratio":
        from . import measurements
        landmarks(body, context)
        segments = measurements.measure(body, context).get("segments")
        if segments is None or not 0 < segments["lower_fraction"] < 1:
            raise ValueError("Placez le repère bassin entre les pieds et le sommet du crâne.")
        return segments["lower_fraction"]
    data = local_report(body, context, only=identifier)
    entry = data["sections" if identifier in SECTION_IDS else "distances"].get(identifier)
    if not entry or "error" in entry:
        raise ValueError(entry.get("error") if entry else "Placez les repères de cette mesure en mode Édition.")
    return entry["perimeter_m" if identifier in SECTION_IDS else "distance_m"]


def fit(body, context, identifier, target_m):
    """Bounded one-control fit, restoring the original value on every failure."""
    if identifier not in FIT_CONTROLS or not math.isfinite(target_m) or target_m <= 0:
        raise ValueError("Mesure cible invalide.")
    keys = body.data.shape_keys
    if not body.is_editable or not keys.is_editable:
        raise ValueError("Le personnage et ses clés de forme doivent être éditables.")
    control = "hm_" + FIT_CONTROLS[identifier]
    original = keys[control]

    def sample(amount):
        keys[control] = amount
        keys.update_tag()
        context.view_layer.update()
        return value(body, context, identifier)

    try:
        samples = [(amount, sample(amount)) for amount in (-1, -.5, 0, .5, 1)]
        differences = np.diff([entry[1] for entry in samples])
        if not (np.all(differences > 1e-8) or np.all(differences < -1e-8)):
            raise ValueError("La mesure ne varie pas régulièrement avec ce réglage et ces repères.")
        lower, upper = samples[0][1], samples[-1][1]
        if not min(lower, upper) <= target_m <= max(lower, upper):
            unit = "%" if identifier == "pelvis_ratio" else "cm"
            raise ValueError(f"Cible hors de la plage du réglage : {min(lower, upper) * 100:.2f} à {max(lower, upper) * 100:.2f} {unit}.")
        lo, hi = -1., 1.
        for _ in range(24):
            mid = (lo + hi) / 2
            current = sample(mid)
            if abs(current - target_m) <= 1e-5:
                return current
            if (current < target_m) == (upper > lower):
                lo = mid
            else:
                hi = mid
        raise ValueError("La convergence vers la mesure cible a échoué.")
    except Exception:
        keys[control] = original
        keys.update_tag()
        context.view_layer.update()
        raise
