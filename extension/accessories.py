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
MATERIAL_OWNER = "hl_accessory_material"  # matériau créé pour UN accessoire (retiré avec lui)
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
        self.vertices, self.faces, self.tags = [], [], []
        self.tag = 0  # indice de matériau des faces ajoutées ensuite

    def add(self, vertices, faces):
        base = len(self.vertices)
        self.vertices.extend(np.asarray(vertices, float).tolist())
        self.faces.extend([[base + i for i in face] for face in faces])
        self.tags.extend([self.tag] * len(faces))

    def rounded_prism(self, center, width, length, thickness, radius, segments=6):
        """Plaque à coins arrondis (téléphone) : `width` en x, `length` en y, `thickness` en z, centrée en `center`."""
        cx, cy, cz = center
        corners = []
        for sx, sy in ((1, 1), (-1, 1), (-1, -1), (1, -1)):  # sens trigonométrique
            ox, oy = sx * (width / 2 - radius), sy * (length / 2 - radius)
            start = {(1, 1): 0.0, (-1, 1): 90.0, (-1, -1): 180.0, (1, -1): 270.0}[(sx, sy)]
            for k in range(segments + 1):
                angle = math.radians(start + 90.0 * k / segments)
                corners.append((ox + radius * math.cos(angle), oy + radius * math.sin(angle)))
        n = len(corners)
        vertices = [(cx + x, cy + y, cz - thickness / 2) for x, y in corners] + [(cx + x, cy + y, cz + thickness / 2) for x, y in corners]
        faces = [tuple(reversed(range(n))), tuple(range(n, 2 * n))] + [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
        self.add(vertices, faces)

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
def _hand_frame(armature, side, *, world=True):
    """Repère orthonormé de la paume, en espace monde ou armature."""
    transform = armature.matrix_world if world else Matrix.Identity(4)
    bones = armature.pose.bones
    hand = bones["hand." + side]
    head, tail = np.array(transform @ hand.head), np.array(transform @ hand.tail)
    y = tail - head
    y /= np.linalg.norm(y)
    thumb = np.array(transform @ bones["thumb.01." + side].head)
    middle = np.array(transform @ bones["middle.01." + side].head)
    # La normale sortante vient du côté radial de la main (le pouce).
    radial = thumb - middle
    radial -= y * (radial @ y)
    radial /= np.linalg.norm(radial)
    z = np.cross(y, radial) * (1.0 if side == "L" else -1.0)
    z /= np.linalg.norm(z)
    x = np.cross(y, z)
    return (head + tail) * 0.5, x, y, z


def _cage_rig(body, armature):
    cage = skeleton.cage_points(body)
    body_to_rig = np.array(armature.matrix_world.inverted() @ body.matrix_world)
    return cage @ body_to_rig[:3, :3].T + body_to_rig[:3, 3]


def _rest_to_pose(bone):
    return bone.matrix @ bone.bone.matrix_local.inverted()


def _face_band(cage, eye_height):
    return cage[(np.abs(cage[:, 0]) < 0.01) & (np.abs(cage[:, 2] - eye_height) < 0.012)]


def _eye_centre_rig(body, armature, cage):
    """Centre des yeux au repos, recalé sur les globes morphés si le rig sort de la cage."""
    anchors = [armature.data.bones["eye." + side].head_local[:] for side in ("L", "R")]
    centre = np.mean(anchors, axis=0)
    if len(_face_band(cage, centre[2])):
        return centre

    depsgraph = bpy.context.evaluated_depsgraph_get()
    world_to_rig = armature.matrix_world.inverted()
    centres = []
    for eye in skeleton.eyes_of(body):
        evaluated = eye.evaluated_get(depsgraph)
        vertices = evaluated.data.vertices
        eye_centre = Vector(np.mean([v.co[:] for v in vertices], axis=0))
        point = world_to_rig @ evaluated.matrix_world @ eye_centre
        if eye.parent == armature and eye.parent_type == 'BONE':
            bone = armature.pose.bones[eye.parent_bone]
            point = _rest_to_pose(bone).inverted() @ point
        centres.append(point[:])
    return np.mean(centres, axis=0) if centres else centre


def _frame_matrix(origin, x, y, z):
    return Matrix((*np.column_stack((x, y, z, origin)).tolist(), (0, 0, 0, 1)))


def _socket_frame_rig(body, armature, name):
    """Matrice du point d'attache posé dans le repère de l'armature."""
    bone_name = SOCKETS[name][0]
    if name.startswith("main."):
        return _frame_matrix(*_hand_frame(armature, name[-1], world=False))

    # La cage est au repos. Mesurer avec l'os au repos, puis transporter l'attache par sa pose.
    bone = armature.data.bones[bone_name]
    cage = _cage_rig(body, armature)
    up = (0.0, 0.0, 1.0)
    if name == "dos":
        z0 = bone.head_local.z
        band = cage[(np.abs(cage[:, 2] - z0) < 0.04) & (np.abs(cage[:, 0]) < 0.03)]
        point = band[np.argmax(band[:, 1])]
        frame = _frame_matrix(point, (1.0, 0.0, 0.0), up, (0.0, 1.0, 0.0))
    elif name.startswith("epaule."):
        sign = 1.0 if name.endswith(".L") else -1.0
        cx, cy, cz = bone.tail_local
        band = cage[(np.abs(cage[:, 0] - cx) < 0.04) & (np.abs(cage[:, 1] - cy) < 0.06) & (cage[:, 2] > cz - 0.02)]
        point = band[np.argmax(band[:, 2])]
        frame = _frame_matrix(point, (sign, 0.0, 0.0), (0.0, 1.0, 0.0), up)
    elif name == "taille":
        z0 = bone.head_local.z
        band = cage[(np.abs(cage[:, 2] - z0) < 0.03) & (np.abs(cage[:, 1]) < 0.04)]
        point = band[np.argmax(band[:, 0])]
        frame = _frame_matrix(point, (0.0, -1.0, 0.0), up, (1.0, 0.0, 0.0))
    elif name == "tete":
        point = cage[np.argmax(cage[:, 2])]
        frame = _frame_matrix(point, (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), up)
    elif name == "visage":
        eye_height = _eye_centre_rig(body, armature, cage)[2]
        front = _face_band(cage, eye_height)
        point = (0.0, float(front[:, 1].min()) - 0.016, eye_height)
        frame = _frame_matrix(point, (1.0, 0.0, 0.0), up, (0.0, -1.0, 0.0))
    return _rest_to_pose(armature.pose.bones[bone_name]) @ frame


def socket_frame(body, name):
    """Origine et axes du point d'attache en espace monde (échelle incluse)."""
    if name not in SOCKETS:
        raise ValueError("Point d'attache inconnu : %r" % (name,))
    armature = skeleton.rigs_of(body)[0]
    frame = armature.matrix_world @ _socket_frame_rig(body, armature, name)
    return tuple(np.array(frame.col[i][:3]) for i in (3, 0, 1, 2))


# --- construction des accessoires ---------------------------------------------------------------------------------------------------------------------
def _grip(body, side, pose="poignee"):
    """Centre et rayon de la poignée dans le repère orthonormé de la paume."""
    armature = skeleton.rigs_of(body)[0]
    origin, x, y, z = _hand_frame(armature, side, world=False)
    apply_grasp(body, side, pose)
    joints = []
    for f in FINGERS:  # articulations et bouts des doigts autour de la poignée
        joints.extend([armature.pose.bones[f"{f}.02.{side}"].head[:],
                       armature.pose.bones[f"{f}.03.{side}"].head[:],
                       armature.pose.bones[f"{f}.03.{side}"].tail[:]])
    release_grasp(body, side)
    centre_rig = np.mean(joints, axis=0)
    centre = (centre_rig - origin) @ np.stack((x, y, z), axis=1)
    radius = float(np.linalg.norm(joints - centre_rig, axis=1).mean())
    return centre, radius * 0.6


def build_mesh(body, key):
    """Maillage (sommets, faces) de l'accessoire `key` dans le repère de son point d'attache (x travers, y longueur, z normale), à l'échelle de la stature du corps."""
    armature = skeleton.rigs_of(body)[0]
    stature = float(_cage_rig(body, armature)[:, 2].max())
    s = stature / 1.70
    soup = Soup()
    definition = ACCESSORIES[key]
    if key in ("sac_a_main", "sac_de_courses", "parapluie_ferme", "parapluie_ouvert"):
        side = definition["socket"][-1]
        if key.startswith("parapluie"):
            grip_roll(body, side)  # la tige est verticale et traverse le poing : le poignet tourne pour que l'axe de fermeture des doigts devienne vertical
        origin, hx, hy, hz = _hand_frame(armature, side, world=False)
        frame = np.stack([hx, hy, hz], axis=1)
        centre, height = _grip(body, side)
        grip = origin + frame @ centre  # centre de la poignée (armature)
        r = max(height, 0.010)  # rayon de la poignée : 60 % de la distance moyenne des articulations des doigts refermés
        down = np.array([0.0, 0.0, -1.0])
        if key.startswith("parapluie"):
            a = down.copy()  # tige verticale = axe de fermeture des doigts (poignet tourné) ; elle passe par le centre des articulations des doigts
            b = np.cross(a, np.array([1.0, 0.0, 0.0]))
        else:
            a = np.array([hx[0], hx[1], 0.0])  # axe de la poignée : travers de la main, ramené à l'horizontale (les sacs pendent à la verticale)
            a /= np.linalg.norm(a)
            b = np.cross(a, down)
        up = -down
        soup.cylinder(grip - a * 0.045 * s, grip + a * 0.045 * s, r)  # poignée
        if key in ("sac_a_main", "sac_de_courses"):
            width, depth, tall = (0.28, 0.10, 0.20) if key == "sac_a_main" else (0.30, 0.16, 0.34)
            top = 0.10 * s  # la poignée est à 10 cm du haut du sac (sangles)
            soup.obox(grip + down * (top + tall * s / 2), (a, b, down), (width * s, depth * s, tall * s))
            for sign in (-1.0, 1.0):
                soup.cylinder(grip + a * sign * 0.040 * s, grip + a * sign * 0.040 * s + down * top, 0.004 * s, 8)  # sangles
        elif key == "parapluie_ferme":
            soup.cylinder(grip + up * 0.045 * s, grip + down * 0.80 * s, 0.008 * s)  # tige tenue dans le poing, pointe vers le bas
            soup.cone(grip + down * 0.88 * s, grip + down * 0.30 * s, 0.03 * s, 12)  # toile roulée
        else:
            soup.cylinder(grip + down * 0.045 * s, grip + up * 0.70 * s, 0.008 * s)
            soup.dome(grip + up * 0.62 * s, up, 0.50 * s, 0.22 * s)
        soup.vertices = ((np.array(soup.vertices) - origin) @ frame).tolist()  # armature -> repère de la paume
    elif key == "telephone":
        # téléphone : dos (z local 0 = contre la paume), cadre, écran (matériau 1, brillant sombre), bosse d'objectif ; l'écran regarde +z (vers le visage quand le téléphone est à l'oreille)
        width, length, thick = 0.072 * s, 0.150 * s, 0.0085 * s
        centre = (0.0, 0.020 * s, thick / 2 + 0.018 * s)  # posé sur la surface de la paume (l'origine du repère est sur l'axe de l'os, ~1,8 cm sous la peau), décalé vers les doigts
        soup.tag = 0
        soup.rounded_prism(centre, width, length, thick, 0.010 * s)
        soup.tag = 1
        soup.rounded_prism((centre[0], centre[1], centre[2] + thick / 2 + 0.0002 * s), width - 0.006 * s, length - 0.014 * s, 0.0004 * s, 0.008 * s)  # écran
        soup.tag = 0
        soup.cylinder((centre[0] + 0.018 * s, centre[1] + 0.058 * s, centre[2] - thick / 2 - 0.002 * s), (centre[0] + 0.018 * s, centre[1] + 0.058 * s, centre[2] - thick / 2), 0.009 * s, 16)  # objectif au dos
    elif key == "sac_a_dos":
        soup.box((0.0, 0.0, 0.108 * s), (0.30 * s, 0.42 * s, 0.14 * s))  # repère du dos : x droite, y haut, z vers l'arrière ; le sac est derrière le dos, bretelles contre le dos
        soup.box((-0.09 * s, 0.0, 0.032 * s), (0.05 * s, 0.38 * s, 0.008 * s))
        soup.box((0.09 * s, 0.0, 0.032 * s), (0.05 * s, 0.38 * s, 0.008 * s))
    elif key == "lunettes":
        for sign in (1.0, -1.0):
            soup.ring((sign * 0.031 * s, 0.0, 0.0), 0.021 * s, 0.0015 * s, axis=(0.0, 0.0, 1.0))
            soup.box((sign * 0.075 * s, 0.0, -0.045 * s), (0.003 * s, 0.003 * s, 0.09 * s))  # branche (vers l'arrière)
        soup.box((0.0, 0.0, 0.0), (0.016 * s, 0.003 * s, 0.003 * s))  # pont
    build_mesh.tags = list(soup.tags)
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
    frame_rig = _socket_frame_rig(body, armature, definition["socket"])
    mesh = bpy.data.meshes.new("HL " + key)
    tags = getattr(build_mesh, "tags", None)
    mesh.from_pydata([tuple(v) for v in vertices], [], [list(f) for f in faces])
    mesh.update()
    obj = bpy.data.objects.new(definition["label"], mesh)
    for collection in body.users_collection:
        collection.objects.link(obj)
    material = bpy.data.materials.new("HL " + key)  # un matériau PROPRE à l'accessoire (GRM-002) : réutiliser « HL <clé> » recolorait l'accessoire de tous les personnages
    material[MATERIAL_OWNER] = True
    colour = tuple(color) if color is not None else definition["couleur"]
    material.diffuse_color = (*colour, 1.0)
    material.use_nodes = True
    shader = material.node_tree.nodes.get("Principled BSDF")
    if shader is not None:
        shader.inputs["Base Color"].default_value = (*colour, 1.0)
        shader.inputs["Roughness"].default_value = 0.6
    mesh.materials.append(material)
    if tags and any(tags):  # second matériau (écran du téléphone) : bleu nuit brillant
        screen = bpy.data.materials.new("HL ecran")
        screen[MATERIAL_OWNER] = True
        screen.diffuse_color = (0.02, 0.05, 0.12, 1.0)
        screen.use_nodes = True
        shader = screen.node_tree.nodes.get("Principled BSDF")
        if shader is not None:
            shader.inputs["Base Color"].default_value = (0.02, 0.05, 0.12, 1.0)
            shader.inputs["Roughness"].default_value = 0.08
        mesh.materials.append(screen)
        for polygon, tag in zip(mesh.polygons, tags):
            polygon.material_index = int(tag)
    obj.parent = armature
    obj.parent_type = "BONE"
    obj.parent_bone = SOCKETS[definition["socket"]][0]
    # Avec les matrices locales à l'identité, Blender évalue ici le vrai parent os.
    # Cela inclut l'origine de parentage de l'os et l'éventuel parentage relatif.
    bpy.context.view_layer.update()
    obj.matrix_parent_inverse = obj.matrix_world.inverted() @ armature.matrix_world @ frame_rig
    obj[MARKER] = key
    obj[PARAMS] = json.dumps({"socket": definition["socket"], "couleur": list(colour), "prehension": definition["grasp"], "parapluie": key.startswith("parapluie")}, ensure_ascii=False)
    if definition["grasp"]:
        apply_grasp(body, definition["socket"][-1], definition["grasp"])
    return obj


def obj_key_is_umbrella(params):
    return bool(params.get("parapluie"))


def remove_accessory(obj):
    body = obj.parent.parent if obj.parent is not None else None
    params = json.loads(obj[PARAMS])
    mesh = obj.data
    materials = {slot.material for slot in obj.material_slots if slot.material is not None}
    bpy.data.objects.remove(obj, do_unlink=True)
    if mesh.users == 0:
        bpy.data.meshes.remove(mesh)
    for material in materials:
        if material.get(MATERIAL_OWNER) and material.users == 0:
            bpy.data.materials.remove(material)
    if body is not None and params.get("prehension") and not any(json.loads(a[PARAMS]).get("socket") == params["socket"] for a in accessories_of(body)):
        release_grasp(body, params["socket"][-1])
        if params["socket"].startswith("main.") and obj_key_is_umbrella(params):
            reset_hand(body, params["socket"][-1])


# --- sauvegarde / restauration de la pose de l'utilisateur (GRM-010) ---------------------------------------------------------------------------------------
POSE_BACKUP = "hl_accessory_pose_backup"


def _pose_state(pose_bone):
    return {"mode": pose_bone.rotation_mode, "quat": list(pose_bone.rotation_quaternion), "euler": list(pose_bone.rotation_euler), "axis_angle": list(pose_bone.rotation_axis_angle), "loc": list(pose_bone.location)}


def _save_pose(armature, names, group):
    """Mémorise (une seule fois par groupe) la pose COURANTE des os que l'accessoire va modifier : mode de rotation, quaternion, Euler, axe-angle, position. Restaurée par `_restore_pose` au retrait de l'accessoire."""
    store = json.loads(armature.get(POSE_BACKUP, "{}"))
    if group in store:
        return
    store[group] = {n: _pose_state(armature.pose.bones[n]) for n in names if n in armature.pose.bones}
    armature[POSE_BACKUP] = json.dumps(store)


def _restore_pose(armature, group):
    """Remet les os du groupe dans l'état mémorisé ; retourne False s'il n'y a rien à restaurer (l'appelant remet alors à zéro, comme avant)."""
    store = json.loads(armature.get(POSE_BACKUP, "{}"))
    saved = store.pop(group, None)
    if saved is None:
        return False
    for name, state in saved.items():
        bone = armature.pose.bones.get(name)
        if bone is None:
            continue
        bone.rotation_mode = state["mode"]
        bone.rotation_quaternion = state["quat"]
        bone.rotation_euler = state["euler"]
        bone.rotation_axis_angle = state["axis_angle"]
        bone.location = state["loc"]
    if store:
        armature[POSE_BACKUP] = json.dumps(store)
    elif POSE_BACKUP in armature:
        del armature[POSE_BACKUP]
    return True


def _hand_bones(side):
    return [f"{finger}.0{n}.{side}" for finger in ("thumb",) + FINGERS for n in (1, 2, 3)]


def _arm_bones(side):
    return [f"arm_upper.{side}", f"arm_lower.{side}", f"hand.{side}"]


# --- préhension de la main ------------------------------------------------------------------------------------------------------------------------------
def _flexion_sign(armature, side, finger):
    """Signe de rotation locale X qui REFERME le doigt vers la paume : le bout se déplace du côté de la normale de la paume (mesuré)."""
    first = armature.pose.bones[f"{finger}.01.{side}"]
    saved_state = _pose_state(first)  # mesure sans trace : le mode de rotation et les valeurs de l'utilisateur sont rétablis à la fin (GRM-010)
    first.rotation_mode = "XYZ"
    _, _, _, z = _hand_frame(armature, side, world=False)
    saved = tuple(first.rotation_euler)
    first.rotation_euler = (0.0, 0.0, 0.0)
    bpy.context.view_layer.update()
    rest = np.array(armature.pose.bones[f"{finger}.03.{side}"].tail)
    first.rotation_euler = (math.radians(40.0), 0.0, 0.0)
    bpy.context.view_layer.update()
    bent = np.array(armature.pose.bones[f"{finger}.03.{side}"].tail)
    first.rotation_euler = saved
    first.rotation_mode = saved_state["mode"]
    first.rotation_quaternion = saved_state["quat"]
    first.rotation_euler = saved_state["euler"]
    first.rotation_axis_angle = saved_state["axis_angle"]
    first.location = saved_state["loc"]
    bpy.context.view_layer.update()
    return 1.0 if float((bent - rest) @ z) > 0 else -1.0


def apply_grasp(body, side, pose="poignee", amount=1.0):
    """Ferme la main `side` (« L » ou « R ») selon la préhension `pose`, à `amount` (0 : main ouverte, 1 : préhension complète). Retourne True."""
    if pose not in GRASPS:
        raise ValueError("Préhension inconnue : %r" % (pose,))
    armature = skeleton.rigs_of(body)[0]
    _save_pose(armature, _hand_bones(side), "main." + side)
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
    if _restore_pose(armature, "main." + side):  # la pose des doigts d'avant l'accessoire revient (GRM-010) ; sans sauvegarde : retour à zéro comme avant
        bpy.context.view_layer.update()
        return
    for finger in ("thumb",) + FINGERS:
        for n in (1, 2, 3):
            pose_bone = armature.pose.bones.get(f"{finger}.0{n}.{side}")
            if pose_bone is not None:
                pose_bone.rotation_euler = (0.0, 0.0, 0.0)
    bpy.context.view_layer.update()


def grip_roll(body, side):
    """Pose du bras pour tenir une tige verticale dans le poing : l'avant-bras se plie vers l'avant (coude) et le poignet tourne pour que l'axe de fermeture des doigts devienne vertical.
    Recherche par grille sur la flexion du coude (un axe à la fois) et le roulis du poignet ; garde la combinaison qui rend l'axe le plus vertical avec la main devant le buste.
    Retourne {coude_axe, coude_deg, roulis_deg, verticalite}."""
    armature = skeleton.rigs_of(body)[0]
    elbow = armature.pose.bones["arm_lower." + side]
    hand = armature.pose.bones["hand." + side]
    shoulder = np.array(armature.pose.bones["arm_upper." + side].head)
    _save_pose(armature, _arm_bones(side), "bras." + side)
    for bone in (elbow, hand):
        bone.rotation_mode = "XYZ"
    best = (-1.0, None)
    for axis in range(3):
        for bend in (-100.0, -80.0, -60.0, 60.0, 80.0, 100.0):
            for roll in (-90.0, -60.0, -30.0, 0.0, 30.0, 60.0, 90.0):
                angles = [0.0, 0.0, 0.0]
                angles[axis] = math.radians(bend)
                elbow.rotation_euler = tuple(angles)
                hand.rotation_euler = (0.0, math.radians(roll), 0.0)
                bpy.context.view_layer.update()
                origin, x, y, _ = _hand_frame(armature, side, world=False)
                in_front = shoulder[1] - origin[1]  # le visage regarde vers -y : la main doit être devant le buste
                score = abs(float(x[2])) - 0.5 * abs(float(y[2])) + (0.0 if in_front > 0.12 else -1.0)
                if score > best[0]:
                    best = (score, (axis, bend, roll, abs(float(x[2]))))
    axis, bend, roll, vertical = best[1]
    angles = [0.0, 0.0, 0.0]
    angles[axis] = math.radians(bend)
    elbow.rotation_euler = tuple(angles)
    hand.rotation_euler = (0.0, math.radians(roll), 0.0)
    bpy.context.view_layer.update()
    return {"coude_axe": "XYZ"[axis], "coude_deg": bend, "roulis_deg": roll, "verticalite": round(vertical, 3)}


def reset_hand(body, side):
    """Remet à zéro la pose du poignet, du coude et de l'épaule de ce côté (annule `grip_roll` et `pose_phone_ear`)."""
    armature = skeleton.rigs_of(body)[0]
    if _restore_pose(armature, "bras." + side):  # pose du bras d'avant l'accessoire (GRM-010)
        bpy.context.view_layer.update()
        return
    for name in ("hand", "arm_lower", "arm_upper"):
        pose_bone = armature.pose.bones.get(f"{name}.{side}")
        if pose_bone is not None:
            pose_bone.rotation_mode = "XYZ"
            pose_bone.rotation_euler = (0.0, 0.0, 0.0)
    bpy.context.view_layer.update()


def _ear_target_rig(body, armature, side):
    cage = _cage_rig(body, armature)
    _, eye_y, eye_height = _eye_centre_rig(body, armature, cage)
    sign = 1.0 if side == "L" else -1.0
    zone = cage[(np.abs(cage[:, 2] - (eye_height - 0.025)) < 0.02) & (cage[:, 0] * sign > 0.04) & (cage[:, 1] > -0.02)]
    ear_x = float(zone[:, 0].max() if sign > 0 else zone[:, 0].min()) if len(zone) else sign * 0.09
    head_centre = (0.0, eye_y + 0.07, eye_height)
    # Le téléphone occupe l'espace entre la paume et l'oreille.
    target = (ear_x + sign * 0.036, head_centre[1] - 0.01, eye_height - 0.025)
    head_pose = _rest_to_pose(armature.pose.bones["head"])
    return tuple(np.array(head_pose @ Vector(p)) for p in (target, head_centre))


def ear_target(body, side):
    """Point visé de la paume et centre de la tête posés dans le repère du corps."""
    armature = skeleton.rigs_of(body)[0]
    rig_to_body = body.matrix_world.inverted() @ armature.matrix_world
    return tuple(np.array(rig_to_body @ Vector(p)) for p in _ear_target_rig(body, armature, side))


def pose_phone_ear(body, side="R", iterations=500, seed=3):
    """Pose « téléphone à l'oreille » : trouve les rotations de l'épaule, du coude et du poignet qui amènent le centre de la paume à l'oreille, la normale de la paume (donc l'écran du téléphone) tournée vers la tête.
    Recherche aléatoire avec pas décroissant (aucune donnée publiée : posture de modélisation). Retourne le rapport {écart_mm, angle_normale_deg}."""
    armature = skeleton.rigs_of(body)[0]
    target, head_centre = _ear_target_rig(body, armature, side)
    names = [f"arm_upper.{side}", f"arm_lower.{side}", f"hand.{side}"]
    _save_pose(armature, names, "bras." + side)
    bones = [armature.pose.bones[n] for n in names]
    for bone in bones:
        bone.rotation_mode = "XYZ"

    sign = 1.0 if side == "L" else -1.0
    elbow_bone = armature.pose.bones[f"arm_lower.{side}"]

    def evaluate(angles):
        for bone, a in zip(bones, angles.reshape(3, 3)):
            bone.rotation_euler = tuple(a)
        bpy.context.view_layer.update()
        origin, _, y, z = _hand_frame(armature, side, world=False)
        to_head = head_centre - origin
        to_head /= np.linalg.norm(to_head)
        gap = float(np.linalg.norm(origin - target))
        elbow = np.array(elbow_bone.head)
        # postures plausibles : coude écarté du buste et plus bas que le poignet, doigts vers le haut, pas de torsion extrême
        penalty = 1.0 * max(0.0, 0.16 - sign * elbow[0]) + 1.0 * max(0.0, elbow[2] - (origin[2] - 0.12)) + 0.2 * max(0.0, 0.3 - float(y[2])) + 0.003 * float(np.sum(angles ** 2))
        return gap + 0.05 * (1.0 - float(z @ to_head)) + penalty

    best_all = None
    for trial in range(4):
        rng = np.random.default_rng(seed + trial)
        best = np.zeros(9)
        best_value = evaluate(best)
        step = 0.7
        for it in range(iterations):
            candidate = np.clip(best + rng.normal(0.0, step, 9), -2.4, 2.4)
            value = evaluate(candidate)
            if value < best_value:
                best, best_value = candidate, value
            if it % 100 == 99:
                step *= 0.6
        if best_all is None or best_value < best_all[1]:
            best_all = (best, best_value)
    best, _ = best_all
    evaluate(best)
    # La recherche est anatomique. Le compte rendu mesure l'écart et l'orientation dans la scène.
    origin, _, _, normal = _hand_frame(armature, side)
    target_world, head_world = (np.array(armature.matrix_world @ Vector(p)) for p in (target, head_centre))
    to_head = head_world - origin
    to_head /= np.linalg.norm(to_head)
    gap = float(np.linalg.norm(origin - target_world))
    angle = float(np.degrees(np.arccos(np.clip(normal @ to_head, -1, 1))))
    return {"ecart_mm": round(gap * 1000, 1), "angle_normale_deg": round(angle, 1), "angles_deg": [round(float(np.degrees(a)), 1) for a in best]}


def fingertip_distances(body, side):
    """Distance (m) des bouts des quatre doigts au centre de la paume."""
    armature = skeleton.rigs_of(body)[0]
    origin, x, y, z = _hand_frame(armature, side)
    return [float(np.linalg.norm(np.array((armature.matrix_world @ armature.pose.bones[f"{f}.03.{side}"].tail)[:]) - origin)) for f in FINGERS]
