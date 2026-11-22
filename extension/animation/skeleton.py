"""Squelette du corps HumanLoom (lot A2) : os, noms et hiérarchie PROPRES à HumanLoom (convention Blender, suffixes .L / .R).

Principes (D-31) :
- aucun nom, position, repère ni poids d'un squelette tiers : les os sont placés d'après la cage évaluée du corps natif (ancres = ensembles de sommets
  de la topologie fixe, `data/human_rig_anchors.json`) et pondérés par `data/human_rig_weights.npz` (diffusion de chaleur sur la même topologie,
  voir `tools/build_human_rig.py`). Un squelette tiers est relié à celui-ci par la couche de mapping (lot A2b), jamais par des noms copiés ;
- les os suivent la convention Blender : l'axe Y d'un os va de sa tête à sa queue (vers l'enfant principal), Z est aligné vers l'avant du personnage
  (vers le haut pour le pied) : la correction entre repères de repos de sources différentes est faite par le mapping, pas ici ;
- l'armature est un enfant du corps (Armature modifier « HL Rig » juste après « HL Human ») : déplacer le corps déplace le rig, sans dépendance circulaire.

Ce module ne lit aucun .blend au chargement (règle d'enregistrement) ; les données sont lues à l'installation du rig.
"""
import hashlib
import json
from pathlib import Path

import bpy
import numpy as np

try:
    from .. import human
except ImportError:  # importé à plat par certains scripts de test
    import human

VERSION = 1
DATA = Path(__file__).resolve().parent.parent / "data"
ANCHORS_FILE = DATA / "human_rig_anchors.json"
WEIGHTS_FILE = DATA / "human_rig_weights.npz"
NON_DEFORMING = ("root",)  # os de contrôle sans poids : `root` (origine au sol, porte le déplacement global ; gestionnaire de root motion, lot A3)
MODIFIER_NAME = "HL Rig"
ARMATURE_NAME = "HL Rig"
MARKER = "hl_rig"
FINGERPRINT = "hl_rig_fingerprint"

# Statuts
NOT_INSTALLED, INSTALLED, OUTDATED, NEEDS_CONFIGURATION = "NOT_INSTALLED", "INSTALLED", "OUTDATED", "NEEDS_CONFIGURATION"
LABELS = {NOT_INSTALLED: "Non installé", INSTALLED: "Installé", OUTDATED: "Obsolète (la morphologie a changé)", NEEDS_CONFIGURATION: "À configurer"}

FINGERS = (("index", -0.30, 0.95), ("middle", -0.10, 1.00), ("ring", 0.10, 0.95), ("pinky", 0.30, 0.85))  # (nom, position latérale, longueur relative)
THUMB_BASE = (0.06, -0.35)  # (fraction le long de la main, latéral) : base du pouce ; son bout est une ancre mesurée sur le maillage, les articulations sont interpolées
THUMB_STOPS = (0.0, 0.40, 0.75, 1.0)
KNUCKLE = 0.42  # fraction de la main où commencent les phalanges
FORWARD, UP = (0.0, -1.0, 0.0), (0.0, 0.0, 1.0)  # avant du personnage (-Y de Blender), haut


def load_anchors():
    return json.loads(ANCHORS_FILE.read_text(encoding="utf-8"))


def anchor_positions(points, data):
    """Position de chaque ancre d'après la cage évaluée `points` (N, 3)."""
    result = {}
    for name, anchor in data["anchors"].items():
        chosen = points[anchor["vertices"]]
        kind = anchor["kind"]
        if kind == "centroid":
            result[name] = chosen.mean(0)
        elif kind == "mid":  # sur le plan de symétrie : x = 0
            center = chosen.mean(0)
            result[name] = np.array([0.0, center[1], center[2]])
        elif kind == "back":  # colonne vertébrale : plus près du dos que le centre de la coupe
            result[name] = np.array([0.0, chosen[:, 1].min() + anchor["fraction"] * (chosen[:, 1].max() - chosen[:, 1].min()), chosen[:, 2].mean()])
        else:
            raise ValueError(f"Type d'ancre inconnu : {kind}")
    return result


def _lerp(a, b, t):
    return a + (b - a) * t


def joints(points, data):
    """Points d'articulation nommés, calculés d'après les ancres ; H = stature de la cage."""
    a = anchor_positions(points, data)
    c = data["constants"]
    zmin, zmax = float(points[:, 2].min()), float(points[:, 2].max())
    stature = zmax - zmin
    j = {"H": np.array([stature, 0, 0])}
    for i in range(7):
        j[f"P{i}"] = _lerp(a["spine_0"], a["neck_base"], i / 6.0)
    j["root_head"] = np.array([0.0, j["P0"][1], zmin])  # au sol, sous le bassin
    j["root_tail"] = j["root_head"] + np.array([0.0, -0.06 * stature, 0.0])
    j["head_base"], j["head_top"] = a["head_base"], a["head_top"]
    j["neck_mid"] = _lerp(a["neck_base"], a["head_base"], 0.5)
    for side, sign in (("L", 1.0), ("R", -1.0)):
        s = f".{side}"
        j["clav_head" + s] = j["P6"] + np.array([sign * c["clavicle_x"] * stature, -c["clavicle_y"] * stature, -c["clavicle_z"] * stature])
        j["elbow" + s] = a["elbow" + s]
        # centre de l'articulation de l'épaule : proportions de la stature (latéral, hauteur) et position antéro-postérieure de la base du cou ;
        # le bras est coudé en A-pose, une extrapolation depuis le coude donnerait une position fausse (mesuré)
        j["shoulder" + s] = np.array([sign * c["shoulder_x"] * stature, j["P6"][1] + c["shoulder_y"] * stature, zmin + c["shoulder_z"] * stature])
        j["wrist" + s] = a["wrist" + s]
        for name, start, end in (("arm_up", "shoulder", "elbow"), ("arm_lo", "elbow", "wrist")):
            j[f"{name}_1{s}"], j[f"{name}_2{s}"] = _lerp(j[start + s], j[end + s], 1 / 3), _lerp(j[start + s], j[end + s], 2 / 3)
        hi, lo = a["thigh_hi" + s], a["thigh_lo" + s]
        j["hip" + s] = np.array([hi[0], hi[1], hi[2] + (hi[2] - lo[2]) * c["hip_k"]])  # prolongement vertical : l'axe de la cuisse converge vers le plan médian, pas la hanche
        j["knee" + s] = a["knee" + s]
        ankle = a["ankle" + s]
        j["ankle" + s] = np.array([ankle[0], ankle[1], zmin + c["ankle_z"] * stature])
        j["ball" + s], j["toe_tip" + s] = a["ball" + s], a["toe_tip" + s]
        for name, start, end in (("leg_up", "hip", "knee"), ("leg_lo", "knee", "ankle")):
            j[f"{name}_1{s}"], j[f"{name}_2{s}"] = _lerp(j[start + s], j[end + s], 1 / 3), _lerp(j[start + s], j[end + s], 2 / 3)
        # repère de la main : axe du poignet au bout du majeur, largeur entre les deux côtés des articulations des doigts
        wrist, tip, side_a, side_b = a["wrist" + s], a["hand_tip" + s], a["hand_side_a" + s], a["hand_side_b" + s]
        axis = tip - wrist
        length = float(np.linalg.norm(axis))
        axis_unit = axis / length
        lateral = side_b - side_a
        lateral = lateral - axis_unit * float(lateral @ axis_unit)
        width = float(np.linalg.norm(lateral))
        lateral_unit = lateral / width

        def hand_point(f, g, wrist=wrist, axis=axis, lateral_unit=lateral_unit, width=width):
            return wrist + axis * f + lateral_unit * (g * width)

        j["hand_end" + s] = hand_point(KNUCKLE, 0.0)
        for finger, g, extent in FINGERS:
            stops = [KNUCKLE + (extent - KNUCKLE) * t for t in (0.0, 0.38, 0.70, 1.0)]
            j[f"{finger}_0{s}"] = hand_point(0.0, 0.35 * g)
            for index, stop in enumerate(stops, start=1):
                j[f"{finger}_{index}{s}"] = hand_point(stop, g)
        thumb_base, thumb_tip = hand_point(*THUMB_BASE), a["thumb_tip" + s]
        for index, stop in enumerate(THUMB_STOPS, start=1):
            j[f"thumb_{index}{s}"] = _lerp(thumb_base, thumb_tip, stop)
    mirror = np.array([-1.0, 1.0, 1.0])
    for key in [k for k in j if k.endswith(".L") and k[:-2] + ".R" in j]:  # symétrie imposée : moyenne du côté gauche et du miroir du côté droit
        mean = (j[key] + mirror * j[key[:-2] + ".R"]) / 2
        j[key], j[key[:-2] + ".R"] = mean, mean * mirror
    return j


def bone_table(j):
    """Liste ordonnée (parents avant enfants) de dictionnaires {name, parent, head, tail, reference} d'après les points d'articulation."""
    table = []

    def bone(name, parent, head, tail, reference=FORWARD):
        table.append({"name": name, "parent": parent, "head": j[head] if isinstance(head, str) else head, "tail": j[tail] if isinstance(tail, str) else tail, "reference": reference})

    bone("root", None, "root_head", "root_tail", UP)
    bone("pelvis", "root", "P0", "P1")
    for i in range(1, 6):
        bone(f"spine.{i:02d}", "pelvis" if i == 1 else f"spine.{i - 1:02d}", f"P{i}", f"P{i + 1}")
    bone("neck.01", "spine.05", "P6", "neck_mid")
    bone("neck.02", "neck.01", "neck_mid", "head_base")
    bone("head", "neck.02", "head_base", "head_top")
    for side in ("L", "R"):
        s = f".{side}"
        bone("clavicle" + s, "spine.05", "clav_head" + s, "shoulder" + s)
        bone("arm_upper" + s, "clavicle" + s, "shoulder" + s, "elbow" + s)
        bone("arm_lower" + s, "arm_upper" + s, "elbow" + s, "wrist" + s)
        bone("hand" + s, "arm_lower" + s, "wrist" + s, "hand_end" + s)
        bone("arm_upper_twist.01" + s, "arm_upper" + s, "arm_up_1" + s, "arm_up_2" + s)
        bone("arm_upper_twist.02" + s, "arm_upper" + s, "arm_up_2" + s, "elbow" + s)
        bone("arm_lower_twist.01" + s, "arm_lower" + s, "arm_lo_1" + s, "arm_lo_2" + s)
        bone("arm_lower_twist.02" + s, "arm_lower" + s, "arm_lo_2" + s, "wrist" + s)
        for finger, _, _ in FINGERS:
            previous = "hand" + s
            for index in range(0, 4):
                name = f"{finger}.{index:02d}{s}"
                bone(name, previous, f"{finger}_{index}{s}", f"{finger}_{index + 1}{s}")
                previous = name
        previous = "hand" + s
        for index in range(1, 4):
            name = f"thumb.{index:02d}{s}"
            bone(name, previous, f"thumb_{index}{s}", f"thumb_{index + 1}{s}" if index < 3 else f"thumb_4{s}")
            previous = name
        bone("leg_upper" + s, "pelvis", "hip" + s, "knee" + s)
        bone("leg_lower" + s, "leg_upper" + s, "knee" + s, "ankle" + s)
        bone("foot" + s, "leg_lower" + s, "ankle" + s, "ball" + s, UP)
        bone("toe" + s, "foot" + s, "ball" + s, "toe_tip" + s, UP)
        bone("leg_upper_twist.01" + s, "leg_upper" + s, "leg_up_1" + s, "leg_up_2" + s)
        bone("leg_upper_twist.02" + s, "leg_upper" + s, "leg_up_2" + s, "knee" + s)
        bone("leg_lower_twist.01" + s, "leg_lower" + s, "leg_lo_1" + s, "leg_lo_2" + s)
        bone("leg_lower_twist.02" + s, "leg_lower" + s, "leg_lo_2" + s, "ankle" + s)
    return table


def _roll_reference(direction, reference):
    """Vecteur de roulis : la référence, ou le haut si l'os lui est quasi parallèle."""
    unit = direction / (np.linalg.norm(direction) + 1e-12)
    if abs(float(unit @ np.array(reference))) > 0.95:
        return UP if abs(float(unit @ np.array(UP))) < 0.95 else FORWARD
    return reference


def deform_names():
    return [n for n in bone_names() if n not in NON_DEFORMING]


def bone_names():
    """Noms des os, sans géométrie (table construite sur des points fictifs) : utile pour les tests et l'interface."""
    dummy = {}

    class Any(dict):
        def __missing__(self, key):
            return np.array([0.0, 0.0, 1.0])

    return [b["name"] for b in bone_table(Any(dummy))]


# --- cage et empreinte --------------------------------------------------------------------------------------------------------------------------

def cage_points(body):
    """Positions de la cage morphée (modificateur `HL Human` seul) dans le repère du corps. Les autres modificateurs sont désactivés le temps du calcul."""
    saved = [(m, m.show_viewport) for m in body.modifiers]
    try:
        for modifier in body.modifiers:
            modifier.show_viewport = modifier.name == human.MODIFIER_NAME
        human.touch(body)
        bpy.context.view_layer.update()
        evaluated = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
        mesh = evaluated.to_mesh()
        buffer = np.empty(len(mesh.vertices) * 3, np.float32)
        mesh.vertices.foreach_get("co", buffer)
        evaluated.to_mesh_clear()
    finally:
        for modifier, state in saved:
            modifier.show_viewport = state
        human.touch(body)
    return buffer.reshape(-1, 3).astype(np.float64)


def fingerprint(body):
    """Empreinte des réglages qui déterminent la morphologie (sexe, âge, contrôles) : change quand les os doivent être reposés."""
    values = {name: round(float(human.get_value(body, name)), 6) for name in sorted(human.sockets())}
    return hashlib.sha1(json.dumps(values, sort_keys=True).encode()).hexdigest()[:16]


# --- état du rig ----------------------------------------------------------------------------------------------------------------------------------

def rigs_of(body):
    return [child for child in body.children if child.type == "ARMATURE" and child.get(MARKER)]


def status(body):
    """(statut, liste de problèmes). Non installé ; Installé ; Obsolète (empreinte différente) ; À configurer (rig incomplet, double, corps non natif…)."""
    if not human.is_native(body):
        return NEEDS_CONFIGURATION, ["Le corps n'est pas un humain natif (schéma 10)."]
    rigs = rigs_of(body)
    if not rigs:
        return NOT_INSTALLED, []
    problems = []
    if len(rigs) > 1:
        problems.append(f"{len(rigs)} rigs installés (un seul est permis).")
    rig = rigs[0]
    names = set(bone_names())
    missing = names - {bone.name for bone in rig.data.bones}
    if missing:
        problems.append(f"{len(missing)} os manquants (ex. {sorted(missing)[0]}).")
    groups = {group.name for group in body.vertex_groups}
    if set(deform_names()) - groups:
        problems.append(f"{len(set(deform_names()) - groups)} groupes de poids manquants.")
    modifier = body.modifiers.get(MODIFIER_NAME)
    if modifier is None or modifier.type != "ARMATURE" or modifier.object != rig:
        problems.append("Le modificateur « HL Rig » est absent ou ne vise pas ce rig.")
    elif list(body.modifiers).index(modifier) != list(body.modifiers).index(body.modifiers[human.MODIFIER_NAME]) + 1:
        problems.append("Le modificateur « HL Rig » n'est pas juste après « HL Human ».")
    if rig.get(MARKER) != VERSION:
        problems.append("Version du rig différente de celle de l'extension.")
    if problems:
        return NEEDS_CONFIGURATION, problems
    if rig.get(FINGERPRINT) != fingerprint(body):
        return OUTDATED, ["Les réglages de morphologie ont changé depuis la pose des os."]
    return INSTALLED, []


# --- création, mise à jour, retrait --------------------------------------------------------------------------------------------------------------

class _Context:
    """Conserve et restaure l'objet actif, la sélection et le mode pendant une opération qui passe par le mode édition."""

    def __enter__(self):
        view = bpy.context.view_layer
        self.active, self.selected = view.objects.active, [o for o in view.objects if o.select_get()]
        self.mode = bpy.context.mode
        return self

    def __exit__(self, *exc):
        view = bpy.context.view_layer
        if bpy.context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        for obj in view.objects:
            obj.select_set(obj in self.selected)
        view.objects.active = self.active


def _set_bones(armature, table):
    """Pose (ou repose) head/tail/roulis de chaque os ; création si absent. L'armature doit être en mode édition."""
    edit = armature.data.edit_bones
    for entry in table:
        bone = edit.get(entry["name"]) or edit.new(entry["name"])
        bone.head = tuple(float(v) for v in entry["head"])
        tail = np.array(entry["tail"], dtype=float)
        if np.linalg.norm(tail - entry["head"]) < 1e-5:
            tail = entry["head"] + np.array([0.0, 0.0, 0.01])
        bone.tail = tuple(float(v) for v in tail)
        bone.align_roll(_roll_reference(tail - np.array(entry["head"]), entry["reference"]))
        bone.use_connect = False
        bone.use_deform = entry["name"] not in NON_DEFORMING
    for entry in table:
        edit[entry["name"]].parent = edit[entry["parent"]] if entry["parent"] else None


def install(body):
    """Crée l'armature enfant du corps, les groupes de poids et le modificateur. Lève ValueError si le corps n'est pas natif ou si un rig existe déjà."""
    state, problems = status(body)
    if state == NEEDS_CONFIGURATION and not rigs_of(body):
        raise ValueError(problems[0])
    if rigs_of(body):
        raise ValueError("Un rig est déjà installé sur ce corps (mettez-le à jour ou retirez-le).")
    data = load_anchors()
    points = cage_points(body)
    table = bone_table(joints(points, data))
    with _Context():
        armature_data = bpy.data.armatures.new(ARMATURE_NAME)
        armature_data.display_type = "STICK"
        armature = bpy.data.objects.new(ARMATURE_NAME, armature_data)
        for collection in body.users_collection:
            collection.objects.link(armature)
        armature.parent = body
        armature.show_in_front = True
        armature[MARKER] = VERSION
        bpy.context.view_layer.objects.active = armature
        armature.select_set(True)
        bpy.ops.object.mode_set(mode="EDIT")
        _set_bones(armature, table)
        bpy.ops.object.mode_set(mode="OBJECT")
        armature[FINGERPRINT] = fingerprint(body)
        _apply_weights(body, [entry["name"] for entry in table])
        modifier = body.modifiers.new(MODIFIER_NAME, "ARMATURE")
        modifier.object = armature
        body_index = list(body.modifiers).index(body.modifiers[human.MODIFIER_NAME])
        body.modifiers.move(len(body.modifiers) - 1, body_index + 1)
    return armature


def _apply_weights(body, names):
    weights = np.load(WEIGHTS_FILE, allow_pickle=False)
    stored = [str(n) for n in weights["names"]]
    if stored != names:
        raise ValueError("Les poids stockés ne correspondent pas à la table d'os (régénérer avec tools/build_human_rig.py).")
    groups = [None if name in NON_DEFORMING else (body.vertex_groups.get(name) or body.vertex_groups.new(name=name)) for name in names]
    indices, values = weights["idx"], weights["w"]
    for vertex in range(len(indices)):
        for slot in range(indices.shape[1]):
            weight = float(values[vertex, slot])
            if weight > 0.0:
                groups[int(indices[vertex, slot])].add([vertex], weight, "REPLACE")


def update(body):
    """Repose les os d'après la morphologie actuelle : poids et actions conservés (les repères sont définis par règle)."""
    rigs = rigs_of(body)
    if len(rigs) != 1:
        raise ValueError("Aucun rig (ou plusieurs) : rien à mettre à jour.")
    armature = rigs[0]
    table = bone_table(joints(cage_points(body), load_anchors()))
    with _Context():
        bpy.context.view_layer.objects.active = armature
        armature.select_set(True)
        bpy.ops.object.mode_set(mode="EDIT")
        _set_bones(armature, table)
        bpy.ops.object.mode_set(mode="OBJECT")
    armature[FINGERPRINT] = fingerprint(body)
    return armature


def remove(body):
    """Retire armature, groupes de poids de nos os et modificateur ; ne touche à aucun autre groupe ni modificateur. Retourne le nombre d'éléments retirés."""
    removed = 0
    modifier = body.modifiers.get(MODIFIER_NAME)
    if modifier is not None and modifier.type == "ARMATURE":
        body.modifiers.remove(modifier)
        removed += 1
    names = set(deform_names())
    for group in [g for g in body.vertex_groups if g.name in names]:
        body.vertex_groups.remove(group)
        removed += 1
    for armature in rigs_of(body):
        data = armature.data
        bpy.data.objects.remove(armature, do_unlink=True)
        if data.users == 0:
            bpy.data.armatures.remove(data)
        removed += 1
    return removed
