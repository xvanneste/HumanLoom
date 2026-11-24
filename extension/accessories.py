"""Accessoires procéduraux, points d'attache et poses de préhension de la main (lot V3) : sacs, téléphone, parapluie, lunettes. Aucun asset tiers : les formes sont construites par le code.

- POINTS D'ATTACHE (`SOCKETS`) : calculés sur le corps ACTUEL (cage) et rattachés à un os du squelette : mains (paume), épaules, dos, taille, tête, visage. L'accessoire est un objet enfant de l'os (suit toutes les animations).
- POSES DE PRÉHENSION (`GRASPS`) : rotations de fléchissement des doigts (angles en degrés, valeurs de modélisation non issues d'une publication) ; le sens de fermeture de chaque os est MESURÉ sur le squelette (le doigt doit
  se rapprocher de la paume), pas supposé. `apply_grasp` / `release_grasp` posent / retirent la préhension de la main d'un côté.
- La poignée d'un sac ou d'un parapluie est calée sur le passage des doigts refermés (la préhension « poignée » donne la position et le rayon) : pas d'interpénétration des doigts avec la poignée, contact mesuré."""
import json
import math

import bpy
import numpy as np
from mathutils import Euler, Matrix, Vector

from . import human
from .animation import skeleton

MARKER = "hl_accessory"
PARAMS = "hl_accessory_params"
FINGERS = ("index", "middle", "ring", "pinky")

# Poses de préhension : angle de flexion (degrés) de chaque phalange (01, 02, 03) par doigt ; valeurs de modélisation.
GRASPS = {
    "poignee": {"index": (45, 50, 30), "middle": (48, 52, 32), "ring": (50, 55, 34), "pinky": (52, 58, 36), "thumb": (15, 25, 20)},
    "plat": {"index": (25, 25, 15), "middle": (22, 22, 12), "ring": (20, 20, 10), "pinky": (18, 18, 10), "thumb": (8, 10, 8)},
}

# Points d'attache : os, description. La position et l'orientation sont calculées sur le corps (`socket_frame`).
SOCKETS = {
    "main.L": ("hand.L", "paume gauche"), "main.R": ("hand.R", "paume droite"),
    "epaule.L": ("clavicle.L", "dessus de l'épaule gauche"), "epaule.R": ("clavicle.R", "dessus de l'épaule droite"),
    "dos": ("spine.03", "milieu du dos"), "taille": ("pelvis", "côté gauche de la taille"),
    "tete": ("head", "dessus de la tête"), "visage": ("head", "devant des yeux"),
}

ACCESSORIES = {
    "sac_a_main": {"label": "Sac à main", "categorie": "Sacs", "socket": "main.R", "grasp": "poignee", "couleur": (0.45, 0.20, 0.12)},
    "sac_a_dos": {"label": "Sac à dos", "categorie": "Sacs", "socket": "dos", "grasp": None, "couleur": (0.15, 0.25, 0.35)},
    "sac_de_courses": {"label": "Sac de courses", "categorie": "Sacs", "socket": "main.L", "grasp": "poignee", "couleur": (0.75, 0.65, 0.45)},
    "telephone": {"label": "Téléphone", "categorie": "Objets", "socket": "main.R", "grasp": "plat", "couleur": (0.05, 0.05, 0.07)},
    "parapluie_ferme": {"label": "Parapluie fermé", "categorie": "Parapluies", "socket": "main.R", "grasp": "poignee", "couleur": (0.12, 0.12, 0.30)},
    "parapluie_ouvert": {"label": "Parapluie ouvert", "categorie": "Parapluies", "socket": "main.R", "grasp": "poignee", "couleur": (0.12, 0.12, 0.30)},
    "lunettes": {"label": "Lunettes", "categorie": "Visage", "socket": "visage", "grasp": None, "couleur": (0.05, 0.05, 0.05)},
}


# --- géométrie primitive ------------------------------------------------------------------------------------------------------------------------------
class Soup:
    """Accumulateur de maillage (sommets, faces) en repère local (x : travers, y : longueur, z : normale)."""

    def __init__(self):
        self.vertices, self.faces = [], []

    def add(self, vertices, faces):
        base = len(self.vertices)
        self.vertices.extend(np.asarray(vertices, float).tolist())
        self.faces.extend([[base + i for i in face] for face in faces])

    def box(self, center, size):
        cx, cy, cz = center
        sx, sy, sz = (s / 2 for s in size)
        vertices = [(cx + dx * sx, cy + dy * sy, cz + dz * sz) for dx in (-1, 1) for dy in (-1, 1) for dz in (-1, 1)]
        faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
        self.add(vertices, faces)

    def obox(self, center, axes, size):
        """Boîte orientée : `axes` = trois vecteurs unitaires orthogonaux, `size` = dimensions le long de ces axes."""
        center = np.array(center, float)
        vertices = [center + axes[0] * dx * size[0] / 2 + axes[1] * dy * size[1] / 2 + axes[2] * dz * size[2] / 2 for dx in (-1, 1) for dy in (-1, 1) for dz in (-1, 1)]
        faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
        self.add(vertices, faces)

    def cylinder(self, start, end, radius, segments=16, cap=True):
        start, end = np.array(start, float), np.array(end, float)
        axis = end - start
        length = np.linalg.norm(axis)
        axis /= max(length, 1e-12)
        helper = np.array([0.0, 0.0, 1.0]) if abs(axis[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
        u = np.cross(axis, helper)
        u /= np.linalg.norm(u)
        v = np.cross(axis, u)
        ring = [math.cos(2 * math.pi * k / segments) * u + math.sin(2 * math.pi * k / segments) * v for k in range(segments)]
        vertices = [start + r * radius for r in ring] + [end + r * radius for r in ring]
        faces = [(k, (k + 1) % segments, segments + (k + 1) % segments, segments + k) for k in range(segments)]
        if cap:
            faces.append(tuple(reversed(range(segments))))
            faces.append(tuple(range(segments, 2 * segments)))
        self.add(vertices, faces)

    def cone(self, apex, base_center, radius, segments=16):
        apex, base_center = np.array(apex, float), np.array(base_center, float)
        axis = apex - base_center
        axis /= max(np.linalg.norm(axis), 1e-12)
        helper = np.array([0.0, 0.0, 1.0]) if abs(axis[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
        u = np.cross(axis, helper)
        u /= np.linalg.norm(u)
        v = np.cross(axis, u)
        vertices = [base_center + radius * (math.cos(2 * math.pi * k / segments) * u + math.sin(2 * math.pi * k / segments) * v) for k in range(segments)] + [apex]
        faces = [(k, (k + 1) % segments, segments) for k in range(segments)]
        faces.append(tuple(reversed(range(segments))))
        self.add(vertices, faces)

    def dome(self, center, axis, radius, height, segments=20, rings=6):
        """Calotte (parapluie ouvert) : paraboloïde de rayon `radius` et de hauteur `height` autour de `axis`."""
        axis = np.array(axis, float)
        axis /= np.linalg.norm(axis)
        helper = np.array([0.0, 0.0, 1.0]) if abs(axis[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
        u = np.cross(axis, helper)
        u /= np.linalg.norm(u)
        v = np.cross(axis, u)
        center = np.array(center, float)
        vertices, faces = [], []
        for r in range(rings + 1):
            t = r / rings
            for k in range(segments):
                angle = 2 * math.pi * k / segments
                vertices.append(center + axis * height * (1 - t * t) + (math.cos(angle) * u + math.sin(angle) * v) * radius * t)
        for r in range(rings):
            for k in range(segments):
                a, b = r * segments + k, r * segments + (k + 1) % segments
                faces.append((a, b, b + segments, a + segments))
        self.add(vertices, faces)

    def ring(self, center, radius, tube, axis=(0.0, 1.0, 0.0), segments=20, sides=8):
        """Tore (monture de lunettes) d'axe `axis`."""
        axis = np.array(axis, float)
        axis /= np.linalg.norm(axis)
        helper = np.array([0.0, 0.0, 1.0]) if abs(axis[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
        u = np.cross(axis, helper)
        u /= np.linalg.norm(u)
        v = np.cross(axis, u)
        center = np.array(center, float)
        vertices, faces = [], []
        for i in range(segments):
            a = 2 * math.pi * i / segments
            radial = math.cos(a) * u + math.sin(a) * v
            for j in range(sides):
                b = 2 * math.pi * j / sides
                vertices.append(center + radial * (radius + tube * math.cos(b)) + axis * tube * math.sin(b))
        for i in range(segments):
            for j in range(sides):
                a, b = i * sides + j, i * sides + (j + 1) % sides
                c, d = ((i + 1) % segments) * sides + (j + 1) % sides, ((i + 1) % segments) * sides + j
                faces.append((a, b, c, d))
        self.add(vertices, faces)

    def handle_arc(self, center, radius, tube, span=math.pi, plane_axis=(0.0, 1.0, 0.0), start_axis=(1.0, 0.0, 0.0), segments=14, sides=6):
        """Anse (demi-tore ouvert) : arc de `span` radians dans le plan perpendiculaire à `plane_axis`."""
        plane_axis = np.array(plane_axis, float)
        plane_axis /= np.linalg.norm(plane_axis)
        u = np.array(start_axis, float)
        u -= plane_axis * (u @ plane_axis)
        u /= np.linalg.norm(u)
        v = np.cross(plane_axis, u)
        center = np.array(center, float)
        vertices, faces = [], []
        for i in range(segments + 1):
            a = span * i / segments
            radial = math.cos(a) * u + math.sin(a) * v
            for j in range(sides):
                b = 2 * math.pi * j / sides
                vertices.append(center + radial * radius + (radial * math.cos(b) + plane_axis * math.sin(b)) * tube)
        for i in range(segments):
            for j in range(sides):
                a, b = i * sides + j, i * sides + (j + 1) % sides
                faces.append((a, b, b + sides, a + sides))
        self.add(vertices, faces)


# --- points d'attache -------------------------------------------------------------------------------------------------------------------------------------
def _hand_frame(armature, side):
    """Repère de la paume (monde) : origine au centre de la paume, y le long de la main (vers les doigts), z = normale sortante de la paume (le côté vers lequel les doigts se referment), x = travers de la main.
    La normale vient de l'ANATOMIE (pouce du côté radial) et non d'un essai de rotation : normale = ± (y × direction du pouce), signe selon la main (gauche +, droite −), repère monde Z haut."""
    hand = armature.pose.bones["hand." + side]
    head, tail = np.array((armature.matrix_world @ hand.head)[:]), np.array((armature.matrix_world @ hand.tail)[:])
    y = tail - head
    y /= np.linalg.norm(y)
    thumb = np.array((armature.matrix_world @ armature.pose.bones["thumb.01." + side].head)[:])
    middle = np.array((armature.matrix_world @ armature.pose.bones["middle.01." + side].head)[:])
    radial = thumb - middle
    radial -= y * (radial @ y)
    radial /= np.linalg.norm(radial)
    z = np.cross(y, radial) * (1.0 if side == "L" else -1.0)
    z /= np.linalg.norm(z)
    x = np.cross(y, z)
    return head + (tail - head) * 0.5, x, y, z


def socket_frame(body, name):
    """(origine, x, y, z) monde du point d'attache `name` sur le corps actuel."""
    armature = skeleton.rigs_of(body)[0]
    cage = skeleton.cage_points(body)
    top = cage[:, 2].max()
    if name.startswith("main."):
        return _hand_frame(armature, name[-1])
    up = np.array([0.0, 0.0, 1.0])
    if name == "dos":
        bone = armature.pose.bones["spine.03"]
        z0 = float((armature.matrix_world @ bone.head).z)
        band = np.where((np.abs(cage[:, 2] - z0) < 0.04) & (np.abs(cage[:, 0]) < 0.03))[0]
        point = cage[band[np.argmax(cage[band, 1])]]  # point le plus en arrière
        return point, np.array([1.0, 0.0, 0.0]), up, np.array([0.0, 1.0, 0.0])
    if name.startswith("epaule."):
        sign = 1.0 if name.endswith(".L") else -1.0
        bone = armature.pose.bones["clavicle." + name[-1]]
        centre = np.array((armature.matrix_world @ bone.tail)[:])
        band = np.where((np.abs(cage[:, 0] - centre[0]) < 0.04) & (np.abs(cage[:, 1] - centre[1]) < 0.06) & (cage[:, 2] > centre[2] - 0.02))[0]
        point = cage[band[np.argmax(cage[band, 2])]]
        return point, np.array([sign, 0.0, 0.0]), np.array([0.0, 1.0, 0.0]), up
    if name == "taille":
        bone = armature.pose.bones["pelvis"]
        z0 = float((armature.matrix_world @ bone.head).z)
        band = np.where((np.abs(cage[:, 2] - z0) < 0.03) & (np.abs(cage[:, 1]) < 0.04))[0]
        point = cage[band[np.argmax(cage[band, 0])]]
        return point, np.array([0.0, -1.0, 0.0]), up, np.array([1.0, 0.0, 0.0])
    if name == "tete":
        point = cage[np.argmax(cage[:, 2])]
        return point, np.array([1.0, 0.0, 0.0]), np.array([0.0, 1.0, 0.0]), up
    if name == "visage":
        eyes = [e for e in skeleton.eyes_of(body)]
        centre = np.mean([skeleton._eye_centre(body, e) for e in eyes], axis=0)
        front = cage[np.where((np.abs(cage[:, 0]) < 0.01) & (np.abs(cage[:, 2] - centre[2]) < 0.012))[0]]
        point = np.array([0.0, float(front[:, 1].min()) - 0.016, float(centre[2])])
        return point, np.array([1.0, 0.0, 0.0]), up, np.array([0.0, -1.0, 0.0])
    raise ValueError("Point d'attache inconnu : %r" % (name,))


# --- construction des accessoires ---------------------------------------------------------------------------------------------------------------------
def _grip(body, side, pose="poignee"):
    """Position (repère de la paume : x, y, z) et rayon du passage des doigts refermés en préhension `pose` : centre des articulations des 4 doigts, rayon = 60 % de leur distance moyenne à ce centre."""
    armature = skeleton.rigs_of(body)[0]
    origin, x, y, z = _hand_frame(armature, side)
    apply_grasp(body, side, pose)
    bpy.context.view_layer.update()
    joints = []
    for f in FINGERS:  # articulations des phalanges et bout du doigt : elles enveloppent la poignée
        joints.append(np.array((armature.matrix_world @ armature.pose.bones[f"{f}.02.{side}"].head)[:]))
        joints.append(np.array((armature.matrix_world @ armature.pose.bones[f"{f}.03.{side}"].head)[:]))
        joints.append(np.array((armature.matrix_world @ armature.pose.bones[f"{f}.03.{side}"].tail)[:]))
    release_grasp(body, side)
    centre_world = np.mean(joints, axis=0)
    centre = np.array([(centre_world - origin) @ x, (centre_world - origin) @ y, (centre_world - origin) @ z])
    radius = float(np.mean([np.linalg.norm(j - centre_world) for j in joints]))
    return centre, radius * 0.6  # centre de la poignée (repère paume) et son rayon (60 % de la distance moyenne des articulations)


def build_mesh(body, key):
    """Maillage (sommets, faces) de l'accessoire `key` dans le repère de son point d'attache (x travers, y longueur, z normale), à l'échelle de la stature du corps."""
    stature = float(skeleton.cage_points(body)[:, 2].max())
    s = stature / 1.70
    soup = Soup()
    definition = ACCESSORIES[key]
    if key in ("sac_a_main", "sac_de_courses", "parapluie_ferme", "parapluie_ouvert"):
        side = definition["socket"][-1]
        origin, hx, hy, hz = socket_frame(body, definition["socket"])
        frame = np.stack([hx, hy, hz], axis=1)  # colonnes : axes de la paume dans le monde
        centre, height = _grip(body, side)
        grip = origin + frame @ centre  # centre de la poignée (monde)
        r = max(height, 0.010)  # rayon de la poignée : 60 % de la distance moyenne des articulations des doigts refermés
        a = np.array([hx[0], hx[1], 0.0])  # axe de la poignée : travers de la main, ramené à l'horizontale (le fût et les sacs pendent à la verticale)
        a /= np.linalg.norm(a)
        down = np.array([0.0, 0.0, -1.0])
        b = np.cross(a, down)
        up = -down
        soup.cylinder(grip - a * 0.045 * s, grip + a * 0.045 * s, r)
        if key in ("sac_a_main", "sac_de_courses"):
            width, depth, tall = (0.28, 0.10, 0.20) if key == "sac_a_main" else (0.30, 0.16, 0.34)
            top = 0.10 * s  # la poignée est à 10 cm du haut du sac (sangles)
            soup.obox(grip + down * (top + tall * s / 2), (a, b, down), (width * s, depth * s, tall * s))
            for sign in (-1.0, 1.0):
                soup.cylinder(grip + a * sign * 0.040 * s, grip + a * sign * 0.040 * s + down * top, 0.004 * s, 8)  # sangles
        elif key == "parapluie_ferme":
            soup.cylinder(grip, grip + down * 0.80 * s, 0.008 * s)
            soup.cone(grip + down * 0.88 * s, grip + down * 0.30 * s, 0.03 * s, 12)
        else:
            soup.cylinder(grip, grip + up * 0.70 * s, 0.008 * s)
            soup.dome(grip + up * 0.62 * s, up, 0.50 * s, 0.22 * s)
        soup.vertices = ((np.array(soup.vertices) - origin) @ frame).tolist()  # monde -> repère de la paume
    elif key == "telephone":
        soup.box((0.0, 0.02 * s, 0.010 * s), (0.072 * s, 0.150 * s, 0.009 * s))
    elif key == "sac_a_dos":
        soup.box((0.0, 0.0, 0.108 * s), (0.30 * s, 0.42 * s, 0.14 * s))  # repère du dos : x droite, y haut, z vers l'arrière ; le sac est derrière le dos, bretelles contre le dos
        soup.box((-0.09 * s, 0.0, 0.032 * s), (0.05 * s, 0.38 * s, 0.008 * s))
        soup.box((0.09 * s, 0.0, 0.032 * s), (0.05 * s, 0.38 * s, 0.008 * s))
    elif key == "lunettes":
        for sign in (1.0, -1.0):
            soup.ring((sign * 0.031 * s, 0.0, 0.0), 0.021 * s, 0.0015 * s, axis=(0.0, 0.0, 1.0))
            soup.box((sign * 0.075 * s, 0.0, -0.045 * s), (0.003 * s, 0.003 * s, 0.09 * s))  # branche (vers l'arrière)
        soup.box((0.0, 0.0, 0.0), (0.016 * s, 0.003 * s, 0.003 * s))  # pont
    return np.array(soup.vertices), soup.faces


def accessories_of(body):
    armature = skeleton.rigs_of(body)
    return [c for a in armature for c in a.children if c.get(MARKER)]


def add_accessory(body, key, color=None):
    """Crée l'accessoire `key` au point d'attache prévu, rattaché à l'os correspondant. Retourne l'objet."""
    if key not in ACCESSORIES:
        raise ValueError("Accessoire inconnu : %r" % (key,))
    rigs = skeleton.rigs_of(body)
    if not rigs:
        raise ValueError("Le corps n'a pas de squelette : posez-le d'abord.")
    if any(a[MARKER] == key for a in accessories_of(body)):
        raise ValueError("Cet accessoire est déjà sur le corps : %s" % key)
    definition = ACCESSORIES[key]
    armature = rigs[0]
    vertices, faces = build_mesh(body, key)
    origin, x, y, z = socket_frame(body, definition["socket"])
    frame = Matrix(((x[0], y[0], z[0], origin[0]), (x[1], y[1], z[1], origin[1]), (x[2], y[2], z[2], origin[2]), (0, 0, 0, 1)))
    mesh = bpy.data.meshes.new("HL " + key)
    mesh.from_pydata([tuple(v) for v in vertices], [], [list(f) for f in faces])
    mesh.update()
    obj = bpy.data.objects.new(definition["label"], mesh)
    for collection in body.users_collection:
        collection.objects.link(obj)
    material = bpy.data.materials.get("HL " + key) or bpy.data.materials.new("HL " + key)
    colour = tuple(color) if color is not None else definition["couleur"]
    material.diffuse_color = (*colour, 1.0)
    material.use_nodes = True
    shader = material.node_tree.nodes.get("Principled BSDF")
    if shader is not None:
        shader.inputs["Base Color"].default_value = (*colour, 1.0)
        shader.inputs["Roughness"].default_value = 0.6
    mesh.materials.append(material)
    bone = armature.data.bones[SOCKETS[definition["socket"]][0]]
    obj.parent = armature
    obj.parent_type = "BONE"
    obj.parent_bone = bone.name
    obj.matrix_basis = Matrix.Identity(4)
    parent_world = armature.matrix_world @ bone.matrix_local @ Matrix.Translation((0.0, bone.length, 0.0))  # un parent « os » a son origine à la QUEUE de l'os
    obj.matrix_parent_inverse = parent_world.inverted() @ (body.matrix_world @ frame)
    obj[MARKER] = key
    obj[PARAMS] = json.dumps({"socket": definition["socket"], "couleur": list(colour), "prehension": definition["grasp"]}, ensure_ascii=False)
    if definition["grasp"]:
        apply_grasp(body, definition["socket"][-1], definition["grasp"])
    return obj


def remove_accessory(obj):
    body = obj.parent.parent if obj.parent is not None else None
    params = json.loads(obj[PARAMS])
    mesh = obj.data
    bpy.data.objects.remove(obj, do_unlink=True)
    if mesh.users == 0:
        bpy.data.meshes.remove(mesh)
    if body is not None and params.get("prehension") and not any(json.loads(a[PARAMS]).get("socket") == params["socket"] for a in accessories_of(body)):
        release_grasp(body, params["socket"][-1])


# --- préhension de la main ------------------------------------------------------------------------------------------------------------------------------
def _flexion_sign(armature, side, finger):
    """Signe de rotation locale X qui REFERME le doigt vers la paume : le bout se déplace du côté de la normale de la paume (mesuré)."""
    first = armature.pose.bones[f"{finger}.01.{side}"]
    first.rotation_mode = "XYZ"
    origin, x, y, z = _hand_frame(armature, side)
    saved = tuple(first.rotation_euler)
    first.rotation_euler = (0.0, 0.0, 0.0)
    bpy.context.view_layer.update()
    rest = np.array((armature.matrix_world @ armature.pose.bones[f"{finger}.03.{side}"].tail)[:])
    first.rotation_euler = (math.radians(40.0), 0.0, 0.0)
    bpy.context.view_layer.update()
    bent = np.array((armature.matrix_world @ armature.pose.bones[f"{finger}.03.{side}"].tail)[:])
    first.rotation_euler = saved
    bpy.context.view_layer.update()
    return 1.0 if float((bent - rest) @ z) > 0 else -1.0


def apply_grasp(body, side, pose="poignee", amount=1.0):
    """Ferme la main `side` (« L » ou « R ») selon la préhension `pose`, à `amount` (0 : main ouverte, 1 : préhension complète). Retourne True."""
    if pose not in GRASPS:
        raise ValueError("Préhension inconnue : %r" % (pose,))
    armature = skeleton.rigs_of(body)[0]
    for finger, angles in GRASPS[pose].items():
        if f"{finger}.01.{side}" not in armature.pose.bones:
            continue
        sign = _flexion_sign(armature, side, "index" if finger == "thumb" else finger) if finger != "thumb" else _flexion_sign(armature, side, "index")
        for n, degrees in enumerate(angles, start=1):
            pose_bone = armature.pose.bones.get(f"{finger}.0{n}.{side}")
            if pose_bone is not None:
                pose_bone.rotation_mode = "XYZ"
                pose_bone.rotation_euler = (sign * math.radians(degrees * amount), 0.0, 0.0)
    bpy.context.view_layer.update()
    return True


def release_grasp(body, side):
    armature = skeleton.rigs_of(body)[0]
    for finger in ("thumb",) + FINGERS:
        for n in (1, 2, 3):
            pose_bone = armature.pose.bones.get(f"{finger}.0{n}.{side}")
            if pose_bone is not None:
                pose_bone.rotation_euler = (0.0, 0.0, 0.0)
    bpy.context.view_layer.update()


def fingertip_distances(body, side):
    """Distance (m) des bouts des quatre doigts au centre de la paume."""
    armature = skeleton.rigs_of(body)[0]
    origin, x, y, z = _hand_frame(armature, side)
    return [float(np.linalg.norm(np.array((armature.matrix_world @ armature.pose.bones[f"{f}.03.{side}"].tail)[:]) - origin)) for f in FINGERS]
