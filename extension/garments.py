"""Vêtements procéduraux d'origine (lot V1) : pièces construites SANS aucun asset tiers, accrochées à la surface du corps.

Principe (voir CONCEPTION_V0.md) : une pièce est un SOUS-MAILLAGE de la topologie du corps (faces dont tous les sommets sont dans un masque de région), décalé le long de la normale du corps de `offset_mm`. Le masque
vient de l'os dominant des poids stockés du rig (colonne, bras, jambes, pieds…) avec des coupes le long des membres (manches, jambes) et en hauteur (ourlets) exprimées en fraction de la stature. La pièce reçoit les
POIDS du corps (mêmes os) et un modificateur Armature sur le même squelette ; un modificateur « Solidify » donne l'épaisseur et un « Shrinkwrap » (extérieur) sert de passe de dégagement sous pose. Au repos la pièce est
à `offset_mm` de la peau par construction, quelle que soit la morphologie : `update` ne fait que recalculer les positions (topologie fixe).
Pièces amples (robe, manteau long) : non couvertes sans simulation de tissu (V4). Aucune coupe n'est un patron de couture : formes schématiques mais propres."""
import json
import math

import bmesh
import bpy
import numpy as np

from . import human
from .animation import skeleton

MARKER = "hl_garment"
PARAMS = "hl_garment_params"
COLLECTION_NAME = "Vêtements HumanLoom"
LAYERS = {"dessous": 0, "haut": 1, "veste": 2, "manteau": 3, "bas": 1, "chaussures": 2, "chaussettes": 0, "couvre-chef": 3, "cou": 2, "mains": 1}

# Règles de masque : os dominant (préfixe) -> plage le long du membre (0 = articulation proximale, 1 = distale) ; `z` : fenêtre de hauteur en fraction de la stature (0 pieds, 1 sommet du crâne).
# Les valeurs sont des CHOIX de modélisation (non issus d'une publication).
GARMENTS = {
    "t_shirt": {"label": "T-shirt", "categorie": "Hauts", "couche": "dessous", "decalage_mm": 5.0, "epaisseur_mm": 1.5, "couleur": (0.80, 0.80, 0.82), "rugosite": 0.85, "matiere": "coton",
                "regles": {"spine": None, "clavicle": None, "arm_upper": (0.0, 0.45), "pelvis": None, "leg_upper": None}, "z": (0.50, 0.88)},
    "chemise": {"label": "Chemise à manches longues", "categorie": "Hauts", "couche": "haut", "decalage_mm": 8.0, "epaisseur_mm": 1.5, "couleur": (0.55, 0.70, 0.85), "rugosite": 0.8, "matiere": "coton",
                "regles": {"spine": None, "clavicle": None, "arm_upper": None, "arm_lower": (0.0, 0.92), "pelvis": None, "leg_upper": None}, "z": (0.48, 0.88)},
    "pull": {"label": "Pull", "categorie": "Hauts", "couche": "haut", "decalage_mm": 10.0, "epaisseur_mm": 3.0, "couleur": (0.55, 0.20, 0.22), "rugosite": 0.95, "matiere": "laine",
             "regles": {"spine": None, "clavicle": None, "neck": (0.0, 0.5), "arm_upper": None, "arm_lower": (0.0, 0.95), "pelvis": None, "leg_upper": None}, "z": (0.47, 0.91)},
    "veste": {"label": "Veste", "categorie": "Vestes", "couche": "veste", "decalage_mm": 14.0, "epaisseur_mm": 3.0, "couleur": (0.18, 0.20, 0.26), "rugosite": 0.7, "matiere": "toile",
              "regles": {"spine": None, "clavicle": None, "arm_upper": None, "arm_lower": (0.0, 0.97), "pelvis": None, "leg_upper": None}, "z": (0.44, 0.88)},
    "manteau": {"label": "Manteau court", "categorie": "Vestes", "couche": "manteau", "decalage_mm": 22.0, "epaisseur_mm": 4.0, "couleur": (0.30, 0.25, 0.20), "rugosite": 0.9, "matiere": "laine",
                "regles": {"spine": None, "clavicle": None, "arm_upper": None, "arm_lower": (0.0, 0.97), "pelvis": None, "leg_upper": (0.0, 0.5)}, "z": (0.34, 0.89)},
    "pantalon": {"label": "Pantalon", "categorie": "Bas", "couche": "bas", "decalage_mm": 8.0, "epaisseur_mm": 2.0, "couleur": (0.20, 0.22, 0.25), "rugosite": 0.8, "matiere": "toile",
                 "regles": {"spine": None, "pelvis": None, "leg_upper": None, "leg_lower": (0.0, 0.97)}, "z": (0.04, 0.58)},
    "jean": {"label": "Jean", "categorie": "Bas", "couche": "bas", "decalage_mm": 6.0, "epaisseur_mm": 2.0, "couleur": (0.14, 0.22, 0.38), "rugosite": 0.7, "matiere": "denim",
             "regles": {"spine": None, "pelvis": None, "leg_upper": None, "leg_lower": (0.0, 0.97)}, "z": (0.04, 0.58)},
    "short": {"label": "Short", "categorie": "Bas", "couche": "bas", "decalage_mm": 7.0, "epaisseur_mm": 2.0, "couleur": (0.55, 0.50, 0.35), "rugosite": 0.8, "matiere": "coton",
              "regles": {"spine": None, "pelvis": None, "leg_upper": (0.0, 0.55)}, "z": (0.30, 0.58)},
    "chaussures": {"label": "Chaussures", "categorie": "Chaussures", "couche": "chaussures", "decalage_mm": 6.0, "epaisseur_mm": 3.0, "couleur": (0.10, 0.08, 0.07), "rugosite": 0.5, "matiere": "cuir",
                   "regles": {"foot": None, "toe": None, "ball": None}, "z": (0.0, 0.07)},
    "bottes": {"label": "Bottes", "categorie": "Chaussures", "couche": "chaussures", "decalage_mm": 7.0, "epaisseur_mm": 3.5, "couleur": (0.22, 0.14, 0.08), "rugosite": 0.55, "matiere": "cuir",
               "regles": {"foot": None, "toe": None, "ball": None, "leg_lower": (0.55, 1.0)}, "z": (0.0, 0.26)},
    "chaussettes": {"label": "Chaussettes", "categorie": "Chaussures", "couche": "chaussettes", "decalage_mm": 3.0, "epaisseur_mm": 1.0, "couleur": (0.85, 0.85, 0.85), "rugosite": 0.9, "matiere": "coton",
                    "regles": {"foot": None, "toe": None, "ball": None, "leg_lower": (0.75, 1.0)}, "z": (0.0, 0.14)},
    "bonnet": {"label": "Bonnet", "categorie": "Couvre-chefs", "couche": "couvre-chef", "decalage_mm": 7.0, "epaisseur_mm": 3.0, "couleur": (0.20, 0.35, 0.55), "rugosite": 0.95, "matiere": "laine",
               "regles": {"head": None}, "z": (0.945, 1.0)},
    "casquette": {"label": "Casquette (calotte)", "categorie": "Couvre-chefs", "couche": "couvre-chef", "decalage_mm": 9.0, "epaisseur_mm": 2.5, "couleur": (0.70, 0.12, 0.10), "rugosite": 0.7, "matiere": "toile",
                  "regles": {"head": None}, "z": (0.962, 1.0)},
    "echarpe": {"label": "Écharpe", "categorie": "Accessoires", "couche": "cou", "decalage_mm": 16.0, "epaisseur_mm": 4.0, "couleur": (0.75, 0.55, 0.15), "rugosite": 0.95, "matiere": "laine",
                "regles": {"neck": None, "spine": None, "clavicle": None, "head": None}, "z": (0.855, 0.915)},
    "gants": {"label": "Gants", "categorie": "Accessoires", "couche": "mains", "decalage_mm": 4.0, "epaisseur_mm": 1.5, "couleur": (0.10, 0.10, 0.12), "rugosite": 0.6, "matiere": "cuir",
              "regles": {"hand": None, "thumb": None, "index": None, "middle": None, "ring": None, "pinky": None}},
}
GARMENTS.update({
    "robe_courte": {"label": "Robe courte", "categorie": "Robes", "couche": "haut", "decalage_mm": 8.0, "epaisseur_mm": 1.5, "couleur": (0.70, 0.18, 0.28), "rugosite": 0.8, "matiere": "coton",
                    "robe": {"ourlet": 0.40, "evasement_m": 0.10, "corsage": True}, "regles": {"spine": None, "clavicle": None, "pelvis": None, "leg_upper": None}},
    "robe_mi_longue": {"label": "Robe mi-longue", "categorie": "Robes", "couche": "haut", "decalage_mm": 8.0, "epaisseur_mm": 1.5, "couleur": (0.20, 0.45, 0.35), "rugosite": 0.8, "matiere": "coton",
                       "robe": {"ourlet": 0.24, "evasement_m": 0.16, "corsage": True}, "regles": {"spine": None, "clavicle": None, "pelvis": None, "leg_upper": None}},
    "robe_longue": {"label": "Robe longue", "categorie": "Robes", "couche": "haut", "decalage_mm": 8.0, "epaisseur_mm": 1.5, "couleur": (0.25, 0.20, 0.50), "rugosite": 0.8, "matiere": "coton",
                    "robe": {"ourlet": 0.08, "evasement_m": 0.22, "corsage": True}, "regles": {"spine": None, "clavicle": None, "pelvis": None, "leg_upper": None}},
    "jupe": {"label": "Jupe", "categorie": "Robes", "couche": "bas", "decalage_mm": 8.0, "epaisseur_mm": 1.5, "couleur": (0.55, 0.35, 0.20), "rugosite": 0.85, "matiere": "coton",
             "robe": {"ourlet": 0.30, "evasement_m": 0.12, "corsage": False}, "regles": {}},
})
DRESS_RINGS, DRESS_SEGMENTS = 22, 48  # anneaux de la jupe (de la taille à l'ourlet) et sommets par anneau
BODICE_BONES = ("arm_upper", "arm_lower", "hand", "thumb", "index", "middle", "ring", "pinky")
LIMB_MAIN = {"arm_upper": ("arm_upper", "arm_lower"), "arm_lower": ("arm_lower", "hand"), "leg_upper": ("leg_upper", "leg_lower"), "leg_lower": ("leg_lower", "foot")}


def categories():
    out = {}
    for key, g in GARMENTS.items():
        out.setdefault(g["categorie"], []).append(key)
    return out


# --- données du corps ---------------------------------------------------------------------------------------------------------------------------------
def _vertex_normals(points, triangles):
    cross = np.cross(points[triangles[:, 1]] - points[triangles[:, 0]], points[triangles[:, 2]] - points[triangles[:, 0]])
    normals = np.zeros_like(points)
    for k in range(3):
        np.add.at(normals, triangles[:, k], cross)
    return normals / np.maximum(np.linalg.norm(normals, axis=1), 1e-18)[:, None]


def _weights():
    data = np.load(skeleton.WEIGHTS_FILE, allow_pickle=False)
    return [str(n) for n in data["names"]], data["idx"], data["w"]


def _base_name(name):
    """`arm_upper_twist.01.L` -> `arm_upper` ; `thumb.02.L` -> `thumb` ; `spine.03` -> `spine`."""
    token = name.split(".")[0]
    for suffix in ("_twist",):
        if suffix in token:
            token = token.split(suffix)[0]
    return token


def body_state(body):
    """Cage, normales, triangles, os dominants et table d'os du corps (positions et paramètres le long des membres)."""
    points = skeleton.cage_points(body)
    mesh = body.data
    mesh.calc_loop_triangles()
    triangles = np.array([t.vertices[:] for t in mesh.loop_triangles])
    names, idx, w = _weights()
    dominant = [names[int(idx[v, int(np.argmax(w[v]))])] for v in range(len(points))]
    table = {b["name"]: b for b in skeleton.bone_table(skeleton.joints(points, skeleton.load_anchors()))}
    return {"points": points, "normals": _vertex_normals(points, triangles), "triangles": triangles, "dominant": dominant, "table": table, "names": names, "idx": idx, "w": w}


def build_mask(state, definition, side_of_vertex):
    """Masque (N,) des sommets du corps couverts par la pièce."""
    points, table = state["points"], state["table"]
    height = points[:, 2].max() - points[:, 2].min()
    zmin = points[:, 2].min()
    frac = (points[:, 2] - zmin) / height
    mask = np.zeros(len(points), bool)
    for v, name in enumerate(state["dominant"]):
        base = _base_name(name)
        rule = definition["regles"].get(base, False)
        if rule is False:
            continue
        if rule is None:
            mask[v] = True
            continue
        # plage le long du membre : projection sur le segment (tête de l'os principal -> tête de l'os suivant du membre)
        side = name[-2:] if name[-2:] in (".L", ".R") else ""
        a, b = LIMB_MAIN[base]
        head = np.array(table[a + side]["head"])
        tail = np.array(table[b + side]["head"])
        axis = tail - head
        t = float(np.clip((points[v] - head) @ axis / float(axis @ axis), 0.0, 1.0))
        mask[v] = rule[0] <= t <= rule[1]
    window = definition.get("z")
    if window is not None:
        mask &= (frac >= window[0]) & (frac <= window[1])
    return mask


# --- construction -------------------------------------------------------------------------------------------------------------------------------------
def _material(definition, name):
    material = bpy.data.materials.get("HL " + name) or bpy.data.materials.new("HL " + name)
    material.use_nodes = True
    shader = material.node_tree.nodes.get("Principled BSDF")
    if shader is not None:
        shader.inputs["Base Color"].default_value = (*definition["couleur"], 1.0)
        shader.inputs["Roughness"].default_value = definition["rugosite"]
    material.diffuse_color = (*definition["couleur"], 1.0)
    return material


def _collection(scene):
    collection = bpy.data.collections.get(COLLECTION_NAME)
    if collection is None:
        collection = bpy.data.collections.new(COLLECTION_NAME)
        scene.collection.children.link(collection)
    return collection


def garments_of(body):
    return [c for c in body.children if c.get(MARKER)]


def add_garment(body, key, color=None, offset_mm=None):
    """Crée la pièce `key` sur `body` (rig installé requis) : retourne l'objet. Une pièce déjà présente est refusée."""
    if key not in GARMENTS:
        raise ValueError("Pièce inconnue : %r" % (key,))
    if not skeleton.rigs_of(body):
        raise ValueError("Le corps n'a pas de squelette : posez-le d'abord (les vêtements héritent des poids).")
    if any(g[MARKER] == key for g in garments_of(body)):
        raise ValueError("Cette pièce est déjà sur le corps : %s" % key)
    definition = dict(GARMENTS[key])
    if color is not None:
        definition["couleur"] = tuple(color)
    if offset_mm is not None:
        definition["decalage_mm"] = float(offset_mm)
    state = body_state(body)
    if definition.get("robe"):
        return _add_dress(body, key, definition, state)
    mask = build_mask(state, definition, None)
    triangles_all = state["triangles"]
    mesh_body = body.data
    polygons = [list(p.vertices) for p in mesh_body.polygons]
    kept = [p for p in polygons if all(mask[v] for v in p)]
    if not kept:
        raise ValueError("La pièce %s ne couvre aucun sommet de ce corps." % key)
    used = sorted({v for p in kept for v in p})
    remap = {v: i for i, v in enumerate(used)}
    coordinates = state["points"][used] + state["normals"][used] * (definition["decalage_mm"] / 1000.0)
    mesh = bpy.data.meshes.new("HL " + key)
    mesh.from_pydata([tuple(c) for c in coordinates], [], [[remap[v] for v in p] for p in kept])
    mesh.update()
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    obj = bpy.data.objects.new(f"{definition['label']}", mesh)
    for collection in body.users_collection:
        collection.objects.link(obj)
    obj.parent = body
    obj[MARKER] = key
    obj[PARAMS] = json.dumps({"couleur": list(definition["couleur"]), "decalage_mm": definition["decalage_mm"], "sommets_du_corps": used}, ensure_ascii=False)
    obj.data.materials.append(_material(definition, key))
    # poids hérités du corps (mêmes os, 4 influences au plus)
    names, idx, w = state["names"], state["idx"], state["w"]
    group_index = {}
    for local, v in enumerate(used):
        for slot in range(idx.shape[1]):
            bone = names[int(idx[v, slot])]
            if w[v, slot] > 0 and bone not in skeleton.NON_DEFORMING and bone not in group_index:
                group_index[bone] = obj.vertex_groups.new(name=bone).index
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    deform = bm.verts.layers.deform.verify()
    bm.verts.ensure_lookup_table()
    for local, v in enumerate(used):  # poids écrits directement dans la couche de déformation (rapide)
        vertex = bm.verts[local]
        for slot in range(idx.shape[1]):
            bone = names[int(idx[v, slot])]
            if w[v, slot] > 0 and bone in group_index:
                vertex[deform][group_index[bone]] = float(w[v, slot])
    bm.to_mesh(obj.data)
    bm.free()
    armature = obj.modifiers.new("Armature", "ARMATURE")
    armature.object = skeleton.rigs_of(body)[0]
    solid = obj.modifiers.new("Epaisseur", "SOLIDIFY")
    solid.thickness = definition["epaisseur_mm"] / 1000.0
    solid.offset = 1.0
    wrap = obj.modifiers.new("Degagement", "SHRINKWRAP")
    wrap.target = body
    wrap.wrap_method = "NEAREST_SURFACEPOINT"
    wrap.wrap_mode = "OUTSIDE_SURFACE"
    wrap.offset = definition["decalage_mm"] / 1000.0 * 0.6
    wrap.show_viewport = False  # passe de dégagement (sous pose : repousse les sommets qui pénètrent le corps) : ~15 ms par pièce et par image (reconstruction de l'arbre du corps), donc coupée par défaut ; `set_clearance(obj, True)` l'active
    return obj


def _dress_slice(points, arms, z, half=0.014):
    """Ellipse qui enveloppe le corps (sans les bras) à la hauteur `z` : centre et demi-axes en x et en y."""
    mask = (np.abs(points[:, 2] - z) < half) & ~arms
    if not mask.any():
        mask = (np.abs(points[:, 2] - z) < 3 * half) & ~arms
    x, y = points[mask, 0], points[mask, 1]
    return (x.min() + x.max()) / 2, (y.min() + y.max()) / 2, (x.max() - x.min()) / 2, (y.max() - y.min()) / 2


def _add_dress(body, key, definition, state):
    """Robe ou jupe : CORSAGE = sous-maillage du corps (comme les autres pièces, sans manches), JUPE = anneaux évasés construits autour du corps depuis la taille jusqu'à l'ourlet (ellipse enveloppant les deux
    jambes à chaque hauteur + aisance qui grandit vers l'ourlet). Poids de peau : ceux du sommet du corps le plus proche (la jupe suit les jambes comme un pantalon si elle n'est pas simulée). Groupe d'épinglage :
    corsage entier, première rangée de la jupe (poids 1), deuxième et troisième (poids dégressifs) : seul le bas de la jupe est libre pour la simulation de tissu."""
    params_dress = definition["robe"]
    points = state["points"]
    zmin, zmax = float(points[:, 2].min()), float(points[:, 2].max())
    height = zmax - zmin
    arms = np.array([_base_name(n) in BODICE_BONES for n in state["dominant"]])
    # taille : plus petite largeur du tronc entre 58 % et 74 % de la stature
    candidates = zmin + np.linspace(0.58, 0.74, 17) * height
    widths = [(_dress_slice(points, arms, z)[2]) for z in candidates]
    z_waist = float(candidates[int(np.argmin(widths))])
    z_hem = zmin + params_dress["ourlet"] * height
    coordinates, faces, weights_from, pin = [], [], [], []
    used = []
    offset = definition["decalage_mm"] / 1000.0
    if params_dress["corsage"]:
        window = ((z_waist - 0.03 - zmin) / height, 0.85)
        bodice = dict(definition, regles={"spine": None, "clavicle": None, "pelvis": None, "leg_upper": None}, z=window)
        mask = build_mask(state, bodice, None)
        polygons = [list(p.vertices) for p in body.data.polygons]
        kept = [p for p in polygons if all(mask[v] for v in p)]
        used = sorted({v for p in kept for v in p})
        remap = {v: i for i, v in enumerate(used)}
        coordinates.extend((points[used] + state["normals"][used] * offset).tolist())
        faces.extend([[remap[v] for v in p] for p in kept])
        weights_from.extend(used)
        pin.extend([1.0] * len(used))
    rings, segments = DRESS_RINGS, DRESS_SEGMENTS
    stats = []
    for j in range(rings + 1):
        stats.append(_dress_slice(points, arms, z_waist + (z_hem - z_waist) * j / rings))
    stats = np.array(stats)
    for column in range(4):  # lissage de l'enveloppe le long de la hauteur (3 passes)
        for _ in range(3):
            smooth = stats[:, column].copy()
            smooth[1:-1] = (stats[:-2, column] + 2 * stats[1:-1, column] + stats[2:, column]) / 4
            stats[:, column] = smooth
    first = len(coordinates)
    for j in range(rings + 1):
        t = j / rings
        ease = 0.030 + params_dress["evasement_m"] * t ** 0.9  # aisance dès la taille : les cuisses qui avancent doivent trouver de la place (sans elle, la simulation laisse les jambes traverser le tissu)
        cx, cy, rx, ry = stats[j]
        z = z_waist + (z_hem - z_waist) * t
        for k in range(segments):
            angle = 2 * math.pi * k / segments
            coordinates.append([cx + (rx + ease) * math.cos(angle), cy + (ry + ease) * math.sin(angle), z])
            pin.append(1.0 if j == 0 else 0.6 if j == 1 else 0.2 if j == 2 else 0.0)
    for j in range(rings):
        for k in range(segments):
            a, b = first + j * segments + k, first + j * segments + (k + 1) % segments
            c, d = first + (j + 1) * segments + (k + 1) % segments, first + (j + 1) * segments + k
            faces.append([a, d, c, b])  # normale vers l'extérieur
    # garde-fou : aucun sommet de la jupe à moins de 4 mm de la surface du corps au repos (poussée radiale par pas de 2 mm)
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    mesh_body = body.data
    mesh_body.calc_loop_triangles()
    tree = BVHTree.FromPolygons([Vector(pt) for pt in points], [t.vertices[:] for t in mesh_body.loop_triangles])
    for j in range(rings + 1):
        cx, cy = stats[j][0], stats[j][1]
        for k in range(segments):
            index = first + j * segments + k
            direction = np.array([coordinates[index][0] - cx, coordinates[index][1] - cy, 0.0])
            direction /= max(np.linalg.norm(direction), 1e-9)
            for _ in range(30):
                location, normal, _, distance = tree.find_nearest(Vector(coordinates[index]))
                inside = location is not None and (Vector(coordinates[index]) - location).dot(normal) < 0
                if not inside and distance >= 0.004:
                    break
                coordinates[index] = (np.array(coordinates[index]) + direction * 0.002).tolist()
    # poids : sommet du corps le plus proche (hors bras) pour la jupe
    candidates_body = np.where(~arms)[0]
    for index in range(first, len(coordinates)):
        d2 = np.sum((points[candidates_body] - np.array(coordinates[index])) ** 2, axis=1)
        weights_from.append(int(candidates_body[int(np.argmin(d2))]))
    mesh = bpy.data.meshes.new("HL " + key)
    mesh.from_pydata([tuple(c) for c in coordinates], [], faces)
    mesh.update()
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    obj = bpy.data.objects.new(definition["label"], mesh)
    for collection in body.users_collection:
        collection.objects.link(obj)
    obj.parent = body
    obj[MARKER] = key
    obj[PARAMS] = json.dumps({"couleur": list(definition["couleur"]), "decalage_mm": definition["decalage_mm"], "sommets_du_corps": used, "robe": {"ourlet": params_dress["ourlet"], "evasement_m": params_dress["evasement_m"], "z_taille": z_waist,
                                                                                                                                               "sommets_jupe": [first, len(coordinates)]}}, ensure_ascii=False)
    obj.data.materials.append(_material(definition, key))
    names, idx, w = state["names"], state["idx"], state["w"]
    group_index = {}
    for v in set(weights_from):
        for slot in range(idx.shape[1]):
            bone = names[int(idx[v, slot])]
            if w[v, slot] > 0 and bone not in skeleton.NON_DEFORMING and bone not in group_index:
                group_index[bone] = obj.vertex_groups.new(name=bone).index
    pin_group = obj.vertex_groups.new(name="Epinglage")
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    deform = bm.verts.layers.deform.verify()
    bm.verts.ensure_lookup_table()
    for local, v in enumerate(weights_from):
        vertex = bm.verts[local]
        for slot in range(idx.shape[1]):
            bone = names[int(idx[v, slot])]
            if w[v, slot] > 0 and bone in group_index:
                vertex[deform][group_index[bone]] = float(w[v, slot])
        if pin[local] > 0:
            vertex[deform][pin_group.index] = float(pin[local])
    bm.to_mesh(obj.data)
    bm.free()
    armature = obj.modifiers.new("Armature", "ARMATURE")
    armature.object = skeleton.rigs_of(body)[0]
    return obj


def remove_garment(obj):
    mesh = obj.data
    bpy.data.objects.remove(obj, do_unlink=True)
    if mesh.users == 0:
        bpy.data.meshes.remove(mesh)


def update_garment(obj):
    """Recalcule les positions de la pièce d'après la morphologie ACTUELLE (topologie fixe, sommets du corps mémorisés). Retourne le nombre de sommets."""
    body = obj.parent
    params = json.loads(obj[PARAMS])
    if "robe" in params:  # la jupe n'est pas un sous-maillage du corps : on reconstruit la pièce (même clé, même couleur et même décalage)
        key, color, offset = obj[MARKER], params["couleur"], params["decalage_mm"]
        simulated = bool(obj.get("hl_cloth"))
        remove_garment(obj)
        rebuilt = add_garment(body, key, color, offset)
        if simulated:
            from . import cloth_sim
            cloth_sim.enable(rebuilt)
        return len(rebuilt.data.vertices)
    used = np.array(params["sommets_du_corps"])
    points = skeleton.cage_points(body)
    mesh = body.data
    mesh.calc_loop_triangles()
    triangles = np.array([t.vertices[:] for t in mesh.loop_triangles])
    normals = _vertex_normals(points, triangles)
    coordinates = points[used] + normals[used] * (params["decalage_mm"] / 1000.0)
    obj.data.vertices.foreach_set("co", coordinates.astype(np.float32).ravel())
    obj.data.update()
    return len(used)


def set_clearance(obj, enabled=True):
    modifier = obj.modifiers.get("Degagement")
    if modifier is not None:
        modifier.show_viewport = modifier.show_render = bool(enabled)


def set_color(obj, color):
    params = json.loads(obj[PARAMS])
    params["couleur"] = list(color)
    obj[PARAMS] = json.dumps(params, ensure_ascii=False)
    material = obj.data.materials[0]
    material.diffuse_color = (*color, 1.0)
    shader = material.node_tree.nodes.get("Principled BSDF") if material.use_nodes else None
    if shader is not None:
        shader.inputs["Base Color"].default_value = (*color, 1.0)


# --- tenues -------------------------------------------------------------------------------------------------------------------------------------------
def outfit_of(body):
    """Tenue actuelle : liste ordonnée par couche de {pièce, couleur, décalage} (rechargeable à l'identique)."""
    pieces = []
    for g in sorted(garments_of(body), key=lambda o: LAYERS[GARMENTS[o[MARKER]]["couche"]]):
        params = json.loads(g[PARAMS])
        pieces.append({"piece": g[MARKER], "couleur": params["couleur"], "decalage_mm": params["decalage_mm"]})
    return pieces


def apply_outfit(body, pieces):
    for g in garments_of(body):
        remove_garment(g)
    return [add_garment(body, p["piece"], p.get("couleur"), p.get("decalage_mm")) for p in pieces]


# --- import d'un vêtement de l'utilisateur (lot V2) -----------------------------------------------------------------------------------------------------
IMPORT_MARKER = "hl_garment_import"
IMPORT_FORMATS = (".obj", ".fbx", ".blend")
FIT_LIMITS = {"distance_moyenne_m": 0.10, "part_a_l_interieur": 0.20}  # au-delà : « échec » signalé (échelle, position ou pièce qui n'est pas pour ce corps)


def _read_objects(filepath):
    """Importe le fichier ; retourne les objets MESH créés (aucune donnée n'est copiée dans le dépôt : le fichier reste chez l'utilisateur)."""
    from pathlib import Path
    path = Path(filepath)
    suffix = path.suffix.lower()
    if suffix not in IMPORT_FORMATS:
        raise ValueError("Format non pris en charge : %s (formats : %s)" % (suffix or "?", ", ".join(IMPORT_FORMATS)))
    if not path.is_file():
        raise ValueError("Fichier introuvable : %s" % path)
    before = set(bpy.data.objects)
    if suffix == ".obj":
        bpy.ops.wm.obj_import(filepath=str(path))
    elif suffix == ".fbx":
        bpy.ops.import_scene.fbx(filepath=str(path))
    else:
        with bpy.data.libraries.load(str(path), link=False) as (source, target):
            target.objects = [n for n in source.objects]
        for obj in target.objects:
            if obj is not None:
                bpy.context.scene.collection.objects.link(obj)
    return [o for o in bpy.data.objects if o not in before and o.type == "MESH"]


def fit_report(body, obj, push_out_mm=2.0, apply=True):
    """Ajustement automatique au repos : mesure (distance moyenne à la peau, part des sommets à l'intérieur, profondeur maximale) puis, si `apply`, repousse les sommets intérieurs jusqu'à `push_out_mm` au-dessus de la peau.
    Retourne un rapport chiffré ; `statut` vaut « ok » ou « échec : … » (jamais masqué)."""
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    points = skeleton.cage_points(body)
    mesh = body.data
    mesh.calc_loop_triangles()
    tree = BVHTree.FromPolygons([Vector(p) for p in points], [t.vertices[:] for t in mesh.loop_triangles])
    to_body = body.matrix_world.inverted() @ obj.matrix_world
    coordinates = [to_body @ v.co for v in obj.data.vertices]
    inside, depths, distances, moved = [], [], [], 0
    for i, c in enumerate(coordinates):
        location, normal, _, distance = tree.find_nearest(c)
        distances.append(distance)
        if location is not None and (c - location).dot(normal) < 0:
            inside.append(i)
            depths.append(distance)
    report = {"sommets": len(coordinates), "distance_moyenne_m": round(float(np.mean(distances)), 4) if distances else None, "part_a_l_interieur_avant": round(len(inside) / max(len(coordinates), 1), 4),
              "profondeur_max_avant_mm": round(max(depths, default=0.0) * 1000, 1)}
    if apply and inside:
        inverse = obj.matrix_world.inverted() @ body.matrix_world
        for i in inside:
            location, normal, _, _ = tree.find_nearest(coordinates[i])
            obj.data.vertices[i].co = inverse @ (location + normal * (push_out_mm / 1000.0))
            moved += 1
        obj.data.update()
    report["sommets_repousses"] = moved
    if not distances:
        report["statut"] = "échec : maillage vide"
    elif report["distance_moyenne_m"] > FIT_LIMITS["distance_moyenne_m"]:
        report["statut"] = "échec : la pièce est trop éloignée du corps (distance moyenne %.0f cm) : échelle ou position ?" % (report["distance_moyenne_m"] * 100)
    elif report["part_a_l_interieur_avant"] > FIT_LIMITS["part_a_l_interieur"]:
        report["statut"] = "échec : %.0f %% des sommets sont à l'intérieur du corps : pièce trop petite ou mal placée" % (report["part_a_l_interieur_avant"] * 100)
    else:
        report["statut"] = "ok"
    return report


def import_garment(body, filepath, mode="pose", push_out_mm=2.0):
    """Importe un vêtement de l'utilisateur et l'ajuste au corps. `mode` : « pose » (poids de peau transférés du corps + Armature : suit les animations) ou « morphologie » (Surface Deform lié au corps :
    suit la morphologie et la pose, pas d'Armature). Une pièce en échec d'ajustement est supprimée et l'erreur levée (rien n'est laissé à moitié). Retourne [(objet, rapport), …]."""
    if mode not in ("pose", "morphologie"):
        raise ValueError("Mode inconnu : %r" % (mode,))
    rigs = skeleton.rigs_of(body)
    if mode == "pose" and not rigs:
        raise ValueError("Le corps n'a pas de squelette : posez-le d'abord (mode « pose »).")
    produced = []
    for obj in _read_objects(filepath):
        report = fit_report(body, obj, push_out_mm)
        if report["statut"] != "ok":
            data = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            if data.users == 0:
                bpy.data.meshes.remove(data)
            raise ValueError(report["statut"] + " — " + json.dumps(report, ensure_ascii=False))
        obj.parent = body
        obj.matrix_parent_inverse = body.matrix_world.inverted()
        key = "import_" + obj.name.split(".")[0]
        obj[MARKER] = key
        obj[IMPORT_MARKER] = True
        obj[PARAMS] = json.dumps({"couleur": [0.6, 0.6, 0.6], "decalage_mm": push_out_mm, "sommets_du_corps": [], "mode": mode, "rapport_ajustement": report}, ensure_ascii=False)
        if mode == "pose":
            transfer = obj.modifiers.new("Poids du corps", "DATA_TRANSFER")
            transfer.object = body
            transfer.use_vert_data = True
            transfer.data_types_verts = {"VGROUP_WEIGHTS"}
            transfer.vert_mapping = "POLYINTERP_NEAREST"
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.datalayout_transfer(modifier=transfer.name)
            bpy.ops.object.modifier_apply(modifier=transfer.name)
            armature = obj.modifiers.new("Armature", "ARMATURE")
            armature.object = rigs[0]
        else:
            deform = obj.modifiers.new("Suivi de surface", "SURFACE_DEFORM")
            deform.target = body
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.surfacedeform_bind(modifier=deform.name)
        produced.append((obj, report))
    if not produced:
        raise ValueError("Aucun maillage dans le fichier.")
    return produced


SKIN_GROUP = "Peau couverte"
SKIN_MODIFIER = "Masque peau couverte"


def hide_covered_skin(body, enabled=True):
    """Masque (rendu et vue) la peau sous les vêtements : groupe de sommets du corps = union des sommets couverts + modificateur Masque (inversé) placé juste après le groupe de nœuds. Retourne le nombre de sommets masqués."""
    modifier = body.modifiers.get(SKIN_MODIFIER)
    if not enabled:
        if modifier is not None:
            body.modifiers.remove(modifier)
        return 0
    covered = sorted({v for g in garments_of(body) for v in json.loads(g[PARAMS])["sommets_du_corps"]})
    group = body.vertex_groups.get(SKIN_GROUP) or body.vertex_groups.new(name=SKIN_GROUP)
    group.remove(list(range(len(body.data.vertices))))
    if covered:
        group.add(covered, 1.0, "REPLACE")
    if modifier is None:
        modifier = body.modifiers.new(SKIN_MODIFIER, "MASK")
        index = list(body.modifiers).index(body.modifiers[human.MODIFIER_NAME])
        body.modifiers.move(len(body.modifiers) - 1, index + 1)
    modifier.vertex_group = SKIN_GROUP
    modifier.invert_vertex_group = True
    return len(covered)


def fingerprint(obj):
    """Empreinte d'une pièce : clé, couleur, décalage, nombre de sommets et de faces (pour vérifier un rechargement)."""
    params = json.loads(obj[PARAMS])
    return [obj[MARKER], [round(c, 4) for c in params["couleur"]], round(params["decalage_mm"], 3), len(obj.data.vertices), len(obj.data.polygons)]
