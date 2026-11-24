"""Dents, gencives et langue du corps natif (lot F0-f) : objets PROCÉDURAUX (aucun asset tiers), placés dans la cavité buccale mesurée de la cage et rattachés aux os du rig.

- dents et gencives supérieures : parent = os `head` ; dents et gencives inférieures, langue : parent = os `jaw` (elles suivent l'ouverture de la bouche) ;
- dimensions : les largeurs et longueurs de couronne des incisives centrales, latérales et canines maxillaires viennent de `data/dental_reference.json` (Alsahli et al. 2025, Tables 2 et 3,
  selon le sexe) ; TOUT le reste (prémolaires, molaires, arcade inférieure, épaisseurs, gencive, langue, dentition lactéale, usure du senior) est un paramètre PROVISOIRE du bloc
  « provisoires » du même fichier, marqué « non vérifié » : choix de modélisation de ce projet, pas une donnée publiée (D-35) ;
- âge (curseur 0 à 3) : jusqu'à `age_max` la dentition est lactéale (5 dents par côté, taille réduite) ; au-delà, permanente (7 dents par côté, sans dents de sagesse) ; usure des incisives
  et canines croissante au-dessus de l'âge 2 ;
- la forme de chaque dent est une super-ellipsoïde étagée (rien d'anatomique au sens clinique) ; les gencives sont un ruban le long de l'arcade ; la langue est un loft de sections posées sur le plancher
  de la cavité (hauteur mesurée par tir de rayons sur la cage).
Ce module ne lit aucun .blend ; le .json est lu à l'installation."""
import json
import math
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

try:
    from .. import human
    from . import skeleton
except ImportError:  # importé à plat par certains scripts de test
    import human
    import skeleton

DATA = Path(__file__).resolve().parent.parent / "data" / "dental_reference.json"
MARKER = "hl_dental"
FINGERPRINT = "hl_dental_fingerprint"
KINDS = {"upper": ("HL Dents hautes", "head"), "lower": ("HL Dents basses", skeleton.JAW), "tongue": ("HL Langue", skeleton.JAW)}
MM = 0.001


def load_reference():
    return json.loads(DATA.read_text(encoding="utf-8"))


# --- paramètres -----------------------------------------------------------------------------------------------------------------------------------

def tooth_table(reference, sex, age):
    """Dents d'une hémi-arcade : listes (nom, largeur, hauteur de couronne, épaisseur) en mm, supérieure puis inférieure, + indicateurs de provenance. `sex` : 0 = homme, 1 = femme."""
    published = reference["valeurs"]["dents_maxillaires_anterieures_adultes"]
    prov = reference["provisoires"]
    primary = age <= prov["dentition_lacteale"]["age_max"]
    names = prov["dentition_lacteale"]["dents_par_cote"] if primary else prov["dentition_adulte_dents_par_cote"]
    size = prov["dentition_lacteale"]["facteur_taille"] if primary else 1.0
    wear_cfg = prov["usure_senior_mm"]
    wear = float(np.clip((age - 2.0) / max(wear_cfg["age"] - 2.0, 1e-6), 0.0, 1.0)) * wear_cfg["perte_de_hauteur_incisives_canines"] if not primary else 0.0
    upper, lower = [], []
    for name in names:
        base = name.replace("molaire_1", "molaire_1")
        sourced = base in published["hommes"]
        if sourced:
            men, women = published["hommes"][base], published["femmes"][base]
            width_u = (men["largeur_moyenne"] * (1 - sex) + women["largeur_moyenne"] * sex)
            height_u = (men["longueur_moyenne"] * (1 - sex) + women["longueur_moyenne"] * sex)
        else:
            width_u = prov["largeurs_superieures_mm"].get(name, prov["largeurs_superieures_mm"]["molaire_1"] if "molaire" in name else prov["largeurs_superieures_mm"]["premolaire_1"])
            height_u = prov["hauteurs_couronne_mm"]["molaire" if "molaire" in name else "premolaire"]
        width_l = prov["largeurs_inferieures_mm"].get(base if not primary else "molaire_1" if "molaire" in name else base, width_u)
        height_l = height_u * prov["hauteurs_couronne_mm"]["facteur_inferieures"]
        thickness = prov["epaisseur_vestibulo_linguale_mm"].get(base, 9.0)
        anterior = base in ("incisive_centrale", "incisive_laterale", "canine")
        cut = wear if anterior else 0.0
        upper.append({"nom": base, "largeur": width_u * size, "hauteur": max(height_u * size - cut, 2.0), "epaisseur": thickness * size, "source": "publié (Alsahli 2025)" if sourced else "provisoire", "usure": cut})
        lower.append({"nom": base, "largeur": width_l * size, "hauteur": max(height_l * size - cut, 2.0), "epaisseur": thickness * size * 0.9, "source": "provisoire", "usure": cut})
    return upper, lower, primary


# --- géométrie de l'arcade ---------------------------------------------------------------------------------------------------------------------

def solve_arch(total_length, half_width):
    """Paramètre k de la parabole y = k x² (m⁻¹) dont la longueur d'arc de x = 0 à x = half_width vaut `total_length`."""
    straight = half_width
    if total_length <= straight * 1.0001:
        return 1e-6

    def length(k):
        x = np.linspace(0.0, half_width, 400)
        return float(np.sum(np.sqrt(1 + (2 * k * x[:-1]) ** 2) * np.diff(x)))

    lo, hi = 1e-6, 400.0
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if length(mid) < total_length else (lo, mid)
    return (lo + hi) / 2


def arch_positions(widths, k):
    """Centres des dents d'une hémi-arcade, par abscisse curviligne depuis la ligne médiane : (x, y_relatif, tangente (2), normale externe (2)). Parabole y = k x²."""
    xs = np.linspace(0.0, 0.2, 4000)
    ds = np.sqrt(1 + (2 * k * xs[:-1]) ** 2) * np.diff(xs)
    cumulative = np.concatenate([[0.0], np.cumsum(ds)])
    out, start = [], 0.0
    for width in widths:
        s = start + width / 2
        x = float(np.interp(s, cumulative, xs))
        tangent = np.array([1.0, 2 * k * x])
        tangent /= np.linalg.norm(tangent)
        normal = np.array([2 * k * x, -1.0])
        normal /= np.linalg.norm(normal)
        out.append((x, k * x * x, tangent, normal))
        start += width
    return out


AROUND, RINGS = 18, 9
_templates = {}


def _tooth_template(taper):
    """Modèle unitaire d'une dent (largeur, épaisseur, hauteur = 1) : sommets (A, 3) et polygones ; super-ellipsoïde étagée, x = largeur, y = épaisseur, z de 0 (bord libre) à 1 (collet).
    Les deux derniers sommets sont les calottes (leur z est fixé à l'échelle). Calculé une fois par `taper`."""
    if taper in _templates:
        return _templates[taper]
    n = 2.6
    angles = np.linspace(0, 2 * math.pi, AROUND, endpoint=False)
    c, sn = np.cos(angles), np.sin(angles)
    ex = np.sign(c) * np.abs(c) ** (2 / n) * 0.5
    ey = np.sign(sn) * np.abs(sn) ** (2 / n) * 0.5
    rows = []
    for ring in range(RINGS):
        t = ring / (RINGS - 1)
        scale_x = 1.0 - 0.18 * t
        scale_y = taper + (1.0 - taper) * t
        rows.append(np.stack([ex * scale_x, ey * scale_y, np.full(AROUND, t)], 1))
    vertices = np.vstack(rows + [np.array([[0.0, 0.0, 0.0], [0.0, 0.0, 1.0]])])
    polygons = []
    for ring in range(RINGS - 1):
        for i in range(AROUND):
            a, b = ring * AROUND + i, ring * AROUND + (i + 1) % AROUND
            polygons.append((a, b, b + AROUND, a + AROUND))
    bottom, top = len(vertices) - 2, len(vertices) - 1
    for i in range(AROUND):
        j = (i + 1) % AROUND
        polygons.append((bottom, j, i))
        polygons.append((top, (RINGS - 1) * AROUND + i, (RINGS - 1) * AROUND + j))
    _templates[taper] = (vertices, polygons)
    return _templates[taper]


def _frame(k, x):
    tangent = np.array([1.0, 2 * k * x])
    tangent /= np.linalg.norm(tangent)
    normal = np.array([2 * k * x, -1.0])
    normal /= np.linalg.norm(normal)
    return tangent, normal


def build_arch(teeth, k, jaw_up, z_edge, front_y, shift=0.0, gum_height=0.008, gum_margin=0.001, faces=True):
    """Dents (dictionnaires, mm) -> (sommets, polygones, indices de matériau) dans le repère du corps. `jaw_up` : +1 si les couronnes montent (arcade haute), -1 si elles descendent.
    `faces=False` : sommets seulement (ajustement rapide), polygones et matériaux valent None."""
    widths = [t["largeur"] * MM for t in teeth]
    placed = arch_positions(widths, k)
    blocks, polygons, material, offset = [], [], [], 0
    for side in (1.0, -1.0):
        for tooth, (x, y, tangent, normal) in zip(teeth, placed):
            w, h, e = tooth["largeur"] * MM, tooth["hauteur"] * MM, tooth["epaisseur"] * MM
            template, tpolys = _tooth_template(0.45 if tooth["nom"] in ("incisive_centrale", "incisive_laterale", "canine") else 0.85)
            v = template * np.array([w, e, h])
            v[-2, 2], v[-1, 2] = -0.1 * min(w, h), h + 0.1 * min(w, h)
            tx, ty, nx, ny = tangent[0] * side, tangent[1], normal[0] * side, normal[1]
            blocks.append(np.stack([side * x + tx * v[:, 0] + nx * v[:, 1], front_y + y + ty * v[:, 0] + ny * v[:, 1] + shift, z_edge + jaw_up * v[:, 2]], 1))
            if faces:
                for poly in tpolys:
                    polygons.append(tuple(offset + i for i in poly) if jaw_up > 0 else tuple(reversed([offset + i for i in poly])))
                    material.append(0)
            offset += len(template)
    # gencive : ruban fermé le long de l'arcade, d'une dent de fond à l'autre
    samples = 60
    xs = np.linspace(0.0, 0.2, 4000)
    cumulative = np.concatenate([[0.0], np.cumsum(np.sqrt(1 + (2 * k * xs[:-1]) ** 2) * np.diff(xs))])
    total = float(sum(widths))
    centers = np.cumsum([0.0] + widths[:-1]) + np.array(widths) / 2
    heights = np.array([t["hauteur"] * MM for t in teeth])
    thicknesses = np.array([t["epaisseur"] * MM for t in teeth])
    order = [(-1.0, i) for i in range(samples, -1, -1)] + [(1.0, i) for i in range(1, samples + 1)]  # la ligne médiane n'est comptée qu'une fois
    ring = []
    for side, i in order:
        s_arc = total * i / samples
        x = float(np.interp(s_arc, cumulative, xs))
        _tangent, normal = _frame(k, x)
        h = float(np.interp(s_arc, centers, heights))
        e = float(np.interp(s_arc, centers, thicknesses))
        for level, off in ((0, e / 2 + gum_margin), (1, e / 2 + gum_margin), (1, -(e / 2 + gum_margin)), (0, -(e / 2 + gum_margin))):
            z = z_edge + jaw_up * (h - gum_margin if level == 0 else h + gum_height)
            ring.append((side * x + normal[0] * side * off, front_y + k * x * x + normal[1] * off + shift, z))
    blocks.append(np.array(ring))
    if faces:
        count = len(order)
        for i in range(count - 1):
            for corner in range(4):
                a = offset + i * 4 + corner
                b = offset + i * 4 + (corner + 1) % 4
                quad = (a, b, b + 4, a + 4)
                polygons.append(quad if jaw_up > 0 else tuple(reversed(quad)))
                material.append(1)
    return np.vstack(blocks), (polygons if faces else None), (material if faces else None)


# --- objets ----------------------------------------------------------------------------------------------------------------------------------------

def ensure_material(name, color, roughness, subsurface=0.0):
    material = bpy.data.materials.get(name)
    if material is None:
        material = bpy.data.materials.new(name)
        material.use_nodes = True
        material.diffuse_color = color  # couleur d'aperçu (rendu Workbench)
        node = material.node_tree.nodes.get("Principled BSDF")
        if node is not None:
            node.inputs["Base Color"].default_value = color
            node.inputs["Roughness"].default_value = roughness
            if "Subsurface Weight" in node.inputs:
                node.inputs["Subsurface Weight"].default_value = subsurface
    return material


def _bvh(points, body):
    polygons = [tuple(p.vertices) for p in body.data.polygons]
    return BVHTree.FromPolygons([tuple(map(float, p)) for p in points], polygons, all_triangles=False)


def collision_flags(points, tree):
    """Sommets dans la masse du corps (parité des croisements d'un rayon vertical : impair = dans la masse, donc la pièce traverse la peau ou la muqueuse)."""
    flags = np.zeros(len(points), bool)
    for i, p in enumerate(points):
        origin, count = Vector((float(p[0]), float(p[1]), float(p[2]))), 0
        for _ in range(12):
            hit = tree.ray_cast(origin, Vector((0, 0, 1)), 1.0)
            if hit[0] is None:
                break
            count += 1
            origin = hit[0] + Vector((0, 0, 1e-5))
        flags[i] = count % 2 == 1
    return flags


def jaw_pose(body, armature, points, angle_degrees=20.0):
    """Cage ouverte par rotation de `jaw` seul (déformation linéaire par os, les autres os au repos : exact pour ce cas) : (arbre BVH de la cage ouverte, fonction qui fait tourner des points
    rigides avec la mâchoire). Le sens de rotation est celui qui descend le menton."""
    group = body.vertex_groups.get(skeleton.JAW)
    weights = np.zeros(len(points))
    if group is not None:
        for vertex in np.load(skeleton.JAW_FILE, allow_pickle=False)["idx"].tolist():  # seuls les sommets pondérés par la règle de la mâchoire portent un poids `jaw`
            try:
                weights[vertex] = group.weight(vertex)
            except RuntimeError:
                pass
    bone = armature.data.bones[skeleton.JAW]
    hinge = np.array((body.matrix_world.inverted() @ armature.matrix_world @ bone.head_local)[:])
    best = None
    for sign in (1.0, -1.0):
        rotation = np.array(Matrix.Rotation(sign * math.radians(angle_degrees), 3, "X"))
        moved = points + weights[:, None] * ((points - hinge) @ rotation.T + hinge - points)
        drop = points[skeleton.JAW_CHIN, 2] - moved[skeleton.JAW_CHIN, 2]
        if best is None or drop > best[0]:
            best = (drop, rotation, moved)
    _drop, rotation, moved = best
    return _bvh(moved, body), (lambda v: (np.asarray(v) - hinge) @ rotation.T + hinge)


def collision_count(points, tree, limit):
    """Comme `collision_flags`, mais s'arrête dès que le nombre de sommets dans la masse dépasse `limit` (essais d'ajustement : un échec franc est détecté vite)."""
    count = 0
    for p in points:
        origin, crossings = Vector((float(p[0]), float(p[1]), float(p[2]))), 0
        for _ in range(12):
            hit = tree.ray_cast(origin, Vector((0, 0, 1)), 1.0)
            if hit[0] is None:
                break
            crossings += 1
            origin = hit[0] + Vector((0, 0, 1e-5))
        if crossings % 2 == 1:
            count += 1
            if count > limit:
                break
    return count


def cavity_geometry(points, body):
    """Plan d'occlusion et repères de la cavité d'après la cage : (z_fente, y_fente, ecart_de_fente, BVH)."""
    a, b = skeleton.JAW_SLIT
    z = float((points[a, 2] + points[b, 2]) / 2)
    return z, float((points[a, 1] + points[b, 1]) / 2), float(abs(points[a, 2] - points[b, 2])), _bvh(points, body)


def tongue_mesh(points, body, tree, z_slit, y_slit, stature, prov, opening=None):
    """Langue : loft de sections ; plancher mesuré par rayons vers le bas sur la ligne médiane, demi-largeur limitée par des rayons latéraux."""
    cfg = prov["langue"]
    scale = stature / prov["arcade"]["stature_de_reference_m"]
    length = cfg["longueur_mm_adulte"] * MM * scale
    thickness_max = cfg["epaisseur_mm_adulte"] * MM * scale
    y0 = y_slit + cfg["retrait_depuis_la_fente_mm"] * MM * scale
    sections, vertices, polygons, anchors = 24, [], [], []
    around = 16
    for i in range(sections):
        t = i / (sections - 1)
        y = y0 + t * length
        hit = tree.ray_cast(Vector((0.0, y, z_slit - 2 * MM)), Vector((0, 0, -1)), 0.2)
        floor = hit[0].z if hit[0] is not None else z_slit - 0.03
        top = min(z_slit - cfg["jeu_sous_le_plan_d_occlusion_mm"] * MM * scale, floor + thickness_max)
        top = max(top, floor + 4 * MM)
        level = (floor + top) / 2
        side = []
        for direction in (1.0, -1.0):
            h = tree.ray_cast(Vector((0.0, y, level)), Vector((direction, 0, 0)), 0.2)
            side.append(h[3] if h[0] is not None else 0.03)
        half = max(min(side) - 2.0 * MM, 4 * MM)
        half *= (0.35 + 0.65 * math.sin(min(1.0, t * 1.15 + 0.1) * math.pi / 2)) * (1.0 - 0.7 * max(0.0, t - 0.85) / 0.15)  # pointe plus étroite, base large
        floor_clear = floor + 7.0 * MM  # marge : le plancher de la cavité suit la mâchoire à 70-90 % (le reste du poids est resté à la tête et au cou), la langue (rigide sur l'os) à 100 % : jusqu'à ~6 mm d'écart à 20°
        center_z = (floor_clear + top) / 2
        radius_z = max((top - floor_clear) / 2, 2 * MM)
        for j in range(around):
            phi = 2 * math.pi * j / around
            vertices.append([half * math.cos(phi), y, center_z + radius_z * math.sin(phi)])
        anchors.extend([(0.0, y, center_z)] * around)
    stride = around
    for i in range(sections - 1):
        for j in range(around):
            a, b = i * stride + j, i * stride + (j + 1) % around
            polygons.append((a, b, b + stride, a + stride))
    polygons.append(tuple(reversed(range(stride))))  # extrémités : une face à chaque bout
    polygons.append(tuple((sections - 1) * stride + j for j in range(stride)))
    vertices = np.array(vertices)
    # le plancher de la cavité est en V : tout sommet dans la masse est ramené vers l'axe de sa section jusqu'à en sortir
    anchors = np.array(anchors)
    for step in range(1, 40):  # bouche fermée, puis ouverte (`opening` = (arbre de la cage ouverte, fonction de la rotation de la mâchoire)) : sortie de la masse dans les deux poses
        flags = collision_flags(vertices, tree)
        if opening is not None:
            flags |= collision_flags(opening[1](vertices), opening[0])
        if not flags.any():
            break
        vertices[flags] = anchors[flags] + (vertices[flags] - anchors[flags]) * 0.93
    return vertices, polygons


# Formes de la langue (articulation) : amplitudes en mm à valeur 1, adulte ; PROVISOIRES, choix de modélisation (aucune donnée d'amplitude linguale lue ni vérifiée). Axe : y croît vers l'arrière (pointe en t = 0).
TONGUE_SHAPES = {
    "langue_pointe_haut": ("Pointe vers le haut", 9.0),
    "langue_pointe_bas": ("Pointe vers le bas", 7.0),
    "langue_dos_haut": ("Dos relevé", 7.0),
    "langue_sortie": ("Langue sortie", 22.0),
    "langue_gauche": ("Vers la gauche", 8.0),
    "langue_droite": ("Vers la droite", 8.0),
    "langue_etroite": ("Langue étroite", 0.15),
}


def tongue_shape_offsets(vertices, scale=1.0):
    """Décalage (mètres) de chaque sommet pour chaque forme de `TONGUE_SHAPES` à valeur 1."""
    y = vertices[:, 1]
    t = np.clip((y - y.min()) / max(float(y.max() - y.min()), 1e-9), 0.0, 1.0)  # 0 : pointe, 1 : base
    tip, mid = (1.0 - t) ** 2, np.sin(np.pi * np.clip(t * 1.1, 0.0, 1.0)) ** 2
    amp = {k: v[1] for k, v in TONGUE_SHAPES.items()}
    zeros = np.zeros(len(vertices))
    offsets = {
        "langue_pointe_haut": np.stack([zeros, zeros, tip * amp["langue_pointe_haut"] * MM * scale], axis=1),
        "langue_pointe_bas": np.stack([zeros, zeros, -tip * amp["langue_pointe_bas"] * MM * scale], axis=1),
        "langue_dos_haut": np.stack([zeros, zeros, mid * amp["langue_dos_haut"] * MM * scale], axis=1),
        "langue_sortie": np.stack([zeros, -((1.0 - t) ** 1.2) * amp["langue_sortie"] * MM * scale, zeros], axis=1),
        "langue_gauche": np.stack([tip * amp["langue_gauche"] * MM * scale, zeros, zeros], axis=1),
        "langue_droite": np.stack([-tip * amp["langue_droite"] * MM * scale, zeros, zeros], axis=1),
    }
    centre = vertices[:, 0].mean()
    offsets["langue_etroite"] = np.stack([-(vertices[:, 0] - centre) * amp["langue_etroite"], zeros, zeros], axis=1)
    return offsets


def add_tongue_shapes(obj, scale=1.0):
    """Ajoute à l'objet langue une forme de base et une forme par articulation (valeurs 0-1, additives) ; exportables et « cuisables » avec le reste du visage."""
    if obj.data.shape_keys is None:
        obj.shape_key_add(name="Basis", from_mix=False)
    base = np.array([v.co[:] for v in obj.data.vertices])
    for name, offset in tongue_shape_offsets(base, scale).items():
        key = obj.shape_key_add(name=name, from_mix=False)
        key.relative_key = obj.data.shape_keys.key_blocks["Basis"]
        key.data.foreach_set("co", (base + offset).ravel())
        key.slider_min, key.slider_max = 0.0, 1.0
        key.value = 0.0  # `shape_key_add` crée les formes à 1 : la langue doit rester au repos à l'installation
    obj["hl_tongue_shapes"] = json.dumps({k: {"nom": v[0], "amplitude": v[1], "source": "provisoire, non vérifié"} for k, v in TONGUE_SHAPES.items()}, ensure_ascii=False)


def _make_object(name, vertices, polygons, material_ids, materials, parent_bone, body, armature):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([tuple(map(float, v)) for v in vertices], [], [tuple(int(i) for i in p) for p in polygons])
    mesh.update()
    for material in materials:
        mesh.materials.append(material)
    if material_ids is not None:
        for polygon, index in zip(mesh.polygons, material_ids):
            polygon.material_index = index
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    obj = bpy.data.objects.new(name, mesh)
    for collection in body.users_collection:
        collection.objects.link(obj)
    bone = armature.data.bones[parent_bone]
    rest_world = armature.matrix_world @ bone.matrix_local @ Matrix.Translation((0.0, bone.length, 0.0))
    obj.parent = armature
    obj.parent_type = "BONE"
    obj.parent_bone = parent_bone
    obj.matrix_parent_inverse = rest_world.inverted() @ body.matrix_world
    obj[MARKER] = name
    return obj


def parts_of(body):
    rigs = skeleton.rigs_of(body)
    return [child for rig in rigs for child in rig.children if child.get(MARKER)]


def fingerprint(body):
    return skeleton.fingerprint(body)


def install(body, armature, points=None, hint=None):
    """Crée dents hautes, dents basses et langue d'après la cage ACTUELLE et l'âge/sexe du corps. Retourne les trois objets. Appelé par `skeleton.install` ; sans effet si déjà présents."""
    if parts_of(body):
        return parts_of(body)
    reference = load_reference()
    prov = reference["provisoires"]
    points = skeleton.cage_points(body) if points is None else points  # `update` fournit la cage qu'elle vient de calculer
    z_slit, y_slit, gap, tree = cavity_geometry(points, body)
    sex, age = human.get_value(body, "sex"), human.get_value(body, "age", 2.0)
    stature = float(points[:, 2].max() - points[:, 2].min())
    scale = stature / prov["arcade"]["stature_de_reference_m"]
    upper, lower, primary = tooth_table(reference, sex, age)
    half_width = prov["arcade"]["demi_largeur_derniere_dent_mm_adulte"] * MM * scale * (0.8 if primary else 1.0)
    clearance = prov["fente_dents_mm"] * MM
    exposure = prov["exposition_verticale"]["exposition_incisives_hautes_sous_le_bord_labial_mm"] * MM * scale  # les incisives hautes DÉPASSENT sous le bord de la lèvre haute (sinon elles restent cachées)
    overbite = prov["exposition_verticale"]["recouvrement_vertical_mm"] * MM
    front_y = y_slit + prov["arcade"]["retrait_derriere_la_fente_mm"] * MM * scale
    made = []
    enamel = ensure_material("HL Email", (0.86, 0.84, 0.78, 1.0), 0.35, 0.05)
    gum = ensure_material("HL Gencive", (0.62, 0.22, 0.25, 1.0), 0.55, 0.25)
    tongue_material = ensure_material("HL Langue", (0.66, 0.26, 0.28, 1.0), 0.6, 0.2)
    gum_height, gum_margin = prov["gencive"]["hauteur_au_dessus_de_la_couronne_mm"] * MM * scale, prov["gencive"]["marge_mm"] * MM

    def arches(retreat, narrowing, faces=False, exposure=exposure):
        out = []
        for kind, teeth, direction, z_edge, shift in (("upper", upper, 1.0, z_slit - exposure, 0.0),
                                                       ("lower", lower, -1.0, z_slit - exposure + overbite, prov["arcade"]["decalage_inferieures_vers_l_arriere_mm"] * MM * scale)):
            arch_half = half_width - narrowing - (prov["arcade"]["recul_arcade_inferieure_mm"] * MM * scale if kind == "lower" else 0.0)
            k = solve_arch(sum(t["largeur"] for t in teeth) * MM, arch_half)
            out.append((kind, teeth, k, build_arch(teeth, k, direction, z_edge, front_y + retreat, shift, gum_height=gum_height, gum_margin=gum_margin, faces=faces)))
        return out

    open_tree, rotate = jaw_pose(body, armature, points)

    def clear(retreat, narrowing, step=3, exposure=exposure):
        """Moins de 1,5 % des sommets testés dans la masse, par arcade, bouche fermée et ouverte (zéro exact n'existe pas : quelques sommets de la gencive restent contre la muqueuse)."""
        for kind, _t, _k, (v, _p, _m) in arches(retreat, narrowing, exposure=exposure):
            sample = v[::step]
            limit = int(0.015 * len(sample))
            bad = collision_count(sample, tree, limit)
            if bad <= limit and kind == "lower":  # la mâchoire haute ne bouge pas : seule l'arcade basse est testée bouche ouverte
                bad += collision_count(rotate(sample), open_tree, limit - bad)
            if bad > limit:
                return False
        return True

    # ajustement : pour chaque rétrécissement (0, 3, 6, 9 mm), plus petite reculée (0 à 30 mm, par 3 mm) pour laquelle moins de 1,5 % des sommets traversent la masse du corps, bouche fermée ET
    # ouverte (20°) : échantillon puis tous les sommets. Le critère n'est pas monotone en la reculée (trop loin, l'arcade touche le fond de la cavité) : balayage, pas de bissection.
    chosen, fit_report = None, {}
    start = max(0, int(hint) - 6) if hint is not None else 0  # `update` : on repart près de la reculée précédente
    for exposure_try in (exposure, exposure * 0.5, 0.0):  # l'exposition des incisives (sous le bord labial) est réduite si la lèvre basse épaisse empêche de la tenir
        for narrowing in (0.0, 3.0 * MM, 6.0 * MM, 9.0 * MM):
            for retreat in range(start, 31, 3):
                if clear(retreat * MM, narrowing, step=12, exposure=exposure_try) and clear(retreat * MM, narrowing, step=1, exposure=exposure_try):
                    chosen = arches(retreat * MM, narrowing, faces=True, exposure=exposure_try)
                    fit_report = {"reculee_mm": float(retreat), "retrecissement_mm": round(narrowing / MM, 1), "exposition_mm": round(exposure_try / MM, 2)}
                    break
            if chosen:
                break
        if chosen:
            break
    if chosen is None:  # dernier recours : le validateur le signalera
        chosen, fit_report = arches(30 * MM, 9.0 * MM, faces=True, exposure=0.0), {"reculee_mm": 30.0, "retrecissement_mm": 9.0, "echec": True}
    for kind, teeth, k, (vertices, polygons, material_ids) in chosen:
        obj = _make_object(KINDS[kind][0], vertices, polygons, material_ids, [enamel, gum], KINDS[kind][1], body, armature)
        obj["hl_dental_fit"] = json.dumps(fit_report)
        obj["hl_dental_teeth"] = json.dumps(teeth)
        obj["hl_dental_arch_k"] = float(k)
        obj["hl_dental_primary"] = bool(primary)
        obj[FINGERPRINT] = fingerprint(body)
        made.append(obj)
    vertices, polygons = tongue_mesh(points, body, tree, z_slit, y_slit, stature, prov, opening=(open_tree, rotate))
    obj = _make_object(KINDS["tongue"][0], vertices, polygons, None, [tongue_material], KINDS["tongue"][1], body, armature)
    add_tongue_shapes(obj, stature / prov["arcade"]["stature_de_reference_m"])
    obj[FINGERPRINT] = fingerprint(body)
    made.append(obj)
    return made


def remove(body):
    """Retire dents, gencives et langue (objets et maillages). Retourne le nombre d'objets retirés."""
    count = 0
    for obj in parts_of(body):
        mesh = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        if mesh is not None and mesh.users == 0:
            bpy.data.meshes.remove(mesh)
        count += 1
    return count


def update(body, armature, points=None):
    """Régénère après un changement de morphologie (tailles, âge, position dans la cavité)."""
    hint = None
    for obj in parts_of(body):
        if obj.get("hl_dental_fit"):
            hint = json.loads(obj["hl_dental_fit"]).get("reculee_mm")
            break
    remove(body)
    return install(body, armature, points, hint)
