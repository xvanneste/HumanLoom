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
import math
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

try:
    from .. import human
except ImportError:  # importé à plat par certains scripts de test
    import human

VERSION = 1
DATA = Path(__file__).resolve().parent.parent / "data"
ANCHORS_FILE = DATA / "human_rig_anchors.json"
WEIGHTS_FILE = DATA / "human_rig_weights.npz"
JAW = "jaw"  # os de la mâchoire (enfant de `head`) : poids propres dans `human_jaw_weights.npz` (règle géométrique, `tools/build_human_jaw.py`), appliqués par-dessus les poids stockés
JAW_FILE = DATA / "human_jaw_weights.npz"
JAW_SLIT = (7986, 8004)  # sommets (lèvre basse, lèvre haute) de la fente labiale sur la ligne médiane : la topologie est fixe, donc les indices valent pour toute morphologie
JAW_CHIN = 7977  # pointe du menton (gnathion) sur la ligne médiane
JAW_HINGE = (0.55, 0.30)  # PROVISOIRE (non vérifié, pas de donnée publiée lue) : profondeur de l'axe de la mâchoire (fraction de la profondeur de la tête) et hauteur au-dessus de la fente (fraction de la distance fente-sommet du crâne)
EYE_BONES = ("eye.L", "eye.R")  # os du regard (enfants de `head`) : portent les yeux (objets), sans poids de peau
NON_DEFORMING = ("root",) + EYE_BONES  # os de contrôle sans poids : `root` (origine au sol, porte le déplacement global ; gestionnaire de root motion, lot A3)
MODIFIER_NAME = "HL Rig"
DQS_MODIFIER = "HL Rig DQS"  # second modificateur Armature (quaternions duals, « Preserve Volume ») limité aux membres distaux par un groupe de sommets ; MODIFIER_NAME reste la liaison linéaire (épaules, tronc, cou, tête)
GROUP_LBS, GROUP_DQS = "HL LBS", "HL DQS"  # masques binaires COMPLÉMENTAIRES : chaque sommet est déformé par un seul des deux modificateurs (la frontière est placée là où les deux méthodes coïncident : poids sur un seul os)
TWIST_CONSTRAINT = "HL Torsion"
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
    for sign, side in ((1.0, "L"), (-1.0, "R")):  # centres des yeux : estimation anthropométrique de la cage (remplacée par les vrais yeux à l'installation, voir `real_eye_joints`)
        centre = np.array([sign * 0.0198 * stature, -0.073 * stature, a["head_base"][2] + 0.437 * (a["head_top"][2] - a["head_base"][2])])
        j["eye_head." + side], j["eye_tail." + side] = centre, centre + np.array([0.0, -0.012, 0.0])
    if len(points) > max(JAW_SLIT + (JAW_CHIN,)):  # (la table fictive de `bone_names` n'a pas de géométrie)
        slit_z = float((points[JAW_SLIT[0], 2] + points[JAW_SLIT[1], 2]) / 2)
        head_zone = points[:, 2] > zmax - 0.15 * stature
        y_min, y_max = float(points[head_zone, 1].min()), float(points[head_zone, 1].max())
        j["jaw_hinge"] = np.array([0.0, y_min + JAW_HINGE[0] * (y_max - y_min), slit_z + JAW_HINGE[1] * (zmax - slit_z)])
        j["jaw_tip"] = np.array([0.0, points[JAW_CHIN, 1], points[JAW_CHIN, 2]])
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
    bone(JAW, "head", "jaw_hinge", "jaw_tip")
    for side in ("L", "R"):
        bone("eye." + side, "head", "eye_head." + side, "eye_tail." + side, UP)
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


def eyes_of(body):
    return [eye for eye in (body.humanloom.eye_left, body.humanloom.eye_right) if eye is not None]


def _eye_centre(body, eye):
    """Centre d'un œil dans le repère du corps (moyenne de ses sommets : l'origine de l'objet est à 0)."""
    inverse = body.matrix_world.inverted()
    return np.mean([np.array((inverse @ (eye.matrix_world @ v.co))[:]) for v in eye.data.vertices], axis=0)


def eye_side(body, eye):
    """"L" si l'œil est du côté +x (comme les os `.L`), "R" sinon."""
    return "L" if _eye_centre(body, eye)[0] > 0 else "R"


def real_eye_joints(body, j):
    """Remplace les centres d'yeux estimés de `j` par ceux des vrais yeux du corps (si présents) : les os `eye.L/.R` sont posés AU CENTRE de chaque globe."""
    for eye in eyes_of(body):
        side = eye_side(body, eye)
        centre = _eye_centre(body, eye)
        j["eye_head." + side], j["eye_tail." + side] = centre, centre + np.array([0.0, -0.012, 0.0])
    return j


def attach_eyes(body, armature):
    """Rattache chaque œil à son os de regard `eye.L` / `eye.R` (à défaut, à `head`), parent = os, en conservant sa position monde : au repos, monde = corps @ base de l'œil. À rappeler après toute repose des os."""
    count = 0
    for eye in eyes_of(body):
        name = "eye." + eye_side(body, eye)
        bone = armature.data.bones.get(name) or armature.data.bones.get("head")
        if bone is None:
            continue
        rest_world = armature.matrix_world @ bone.matrix_local @ Matrix.Translation((0.0, bone.length, 0.0))  # un parent « os » a son origine à la QUEUE de l'os
        eye.parent = armature
        eye.parent_type = "BONE"
        eye.parent_bone = bone.name
        eye.matrix_parent_inverse = rest_world.inverted() @ body.matrix_world
        count += 1
    return count


def detach_eyes(body):
    """Remet les yeux sous le corps (état d'avant l'installation du rig)."""
    for eye in eyes_of(body):
        if eye.parent is not None and eye.parent != body:
            eye.parent_type = "OBJECT"
            eye.parent = body
            eye.matrix_parent_inverse = body.matrix_world.inverted() @ body.matrix_world


STORED, RECOMPUTED = "stockes", "recalcules"
BARE_LIMIT = 0.001  # part maximale de sommets sans poids après la liaison automatique ; au-delà : refus net (les tests la baissent pour provoquer l'échec)
WEIGHT_METHODS = ((STORED, "Poids stockés", "Poids calculés une fois sur le corps neutre (reproductibles, instantanés)"),
                  (RECOMPUTED, "Recalculer sur la morphologie", "Liaison automatique par chaleur de Blender sur la morphologie actuelle (quelques secondes)"))


def recompute_weights(body, table):
    """Poids par la liaison automatique de Blender (chaleur) sur la cage ACTUELLE et les os de `table` (torsions exclues puis réparties par une rampe en chapeau), 4 influences au plus.
    Retourne (noms, idx (N, 4), w (N, 4))."""
    points = cage_points(body)
    table = [entry for entry in table if entry["name"] not in (JAW,) + EYE_BONES]  # la mâchoire n'entre pas dans la liaison automatique : ses poids viennent de `human_jaw_weights.npz`
    names = [entry["name"] for entry in table]
    index = {n: i for i, n in enumerate(names)}
    mesh = body.data
    scene = bpy.context.scene
    with _Context():
        data = bpy.data.armatures.new("hl_tmp_rig")
        rig = bpy.data.objects.new("hl_tmp_rig", data)
        scene.collection.objects.link(rig)
        bench_mesh = bpy.data.meshes.new("hl_tmp_bench")
        bench_mesh.from_pydata([tuple(p) for p in points], [tuple(e.vertices) for e in mesh.edges], [tuple(p.vertices) for p in mesh.polygons])
        bench_mesh.update()
        bench = bpy.data.objects.new("hl_tmp_bench", bench_mesh)
        scene.collection.objects.link(bench)
        try:
            bpy.context.view_layer.objects.active = rig
            for other in bpy.context.view_layer.objects:
                other.select_set(False)
            rig.select_set(True)
            bpy.ops.object.mode_set(mode="EDIT")
            _set_bones(rig, table)
            for edit_bone in data.edit_bones:
                edit_bone.use_deform = "_twist" not in edit_bone.name and edit_bone.name not in NON_DEFORMING
            bpy.ops.object.mode_set(mode="OBJECT")
            bench.select_set(True)
            rig.select_set(True)
            bpy.context.view_layer.objects.active = rig
            bpy.ops.object.parent_set(type="ARMATURE_AUTO")
            groups = {g.index: g.name for g in bench.vertex_groups}
            full = np.zeros((len(points), len(names)), dtype=np.float32)
            for vertex in bench_mesh.vertices:
                for group in vertex.groups:
                    full[vertex.index, index[groups[group.group]]] = group.weight
        finally:
            bpy.data.objects.remove(bench, do_unlink=True)
            bpy.data.objects.remove(rig, do_unlink=True)
            bpy.data.meshes.remove(bench_mesh)
            bpy.data.armatures.remove(data)
    sums = full.sum(1, keepdims=True)
    bare = float((sums[:, 0] == 0).mean())
    if bare > BARE_LIMIT:  # la chaleur de Blender échoue sur certaines morphologies (maillage qui se recoupe : I-49) : refus net, pas de poids vides
        raise ValueError(f"La liaison automatique de Blender a échoué sur cette morphologie ({bare * 100:.0f} % des sommets sans poids) : utilisez les poids stockés.")
    full /= np.where(sums > 0, sums, 1)
    for limb in ("arm_upper", "arm_lower", "leg_upper", "leg_lower"):
        for side in ("L", "R"):
            base = index[f"{limb}.{side}"]
            head, tail = np.array(table[base]["head"]), np.array(table[base]["tail"])
            t = np.clip(((points - head) @ (tail - head)) / ((tail - head) @ (tail - head)), 0.0, 1.0)
            hat1, hat2 = np.maximum(0, 1 - np.abs(t - 1 / 3) * 3), np.maximum(0, 1 - np.abs(t - 2 / 3) * 3)
            original = full[:, base].copy()
            full[:, index[f"{limb}_twist.01.{side}"]] = original * hat1
            full[:, index[f"{limb}_twist.02.{side}"]] = original * hat2
            full[:, base] = original * np.clip(1 - hat1 - hat2, 0, 1)
    order = np.argsort(-full, axis=1)[:, :4]
    chosen = np.take_along_axis(full, order, axis=1)
    chosen /= chosen.sum(1, keepdims=True)
    return names, order.astype(np.int16), chosen.astype(np.float32)


def install(body, method=STORED, weights=True):
    """Crée l'armature enfant du corps, les groupes de poids et le modificateur. Lève ValueError si le corps n'est pas natif ou si un rig existe déjà. `method` : poids stockés (défaut) ou recalculés."""
    state, problems = status(body)
    if state == NEEDS_CONFIGURATION and not rigs_of(body):
        raise ValueError(problems[0])
    if rigs_of(body):
        raise ValueError("Un rig est déjà installé sur ce corps (mettez-le à jour ou retirez-le).")
    data = load_anchors()
    points = cage_points(body)
    table = bone_table(real_eye_joints(body, joints(points, data)))
    computed = recompute_weights(body, table) if method == RECOMPUTED else None  # avant tout effet de bord : un échec ne laisse rien derrière lui
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
        attach_eyes(body, armature)
        if weights:  # `weights=False` : le maillage partagé (foule) porte déjà les groupes et les poids
            _apply_weights(body, [entry["name"] for entry in table], computed)
        from . import dental  # dents, gencives, langue : rattachés à head et jaw (lot F0-f)
        dental.install(body, armature)
        attach_mouth_driver(body, armature)
        armature["hl_rig_weights"] = method
        attach_twist(armature)
        modifier = body.modifiers.new(MODIFIER_NAME, "ARMATURE")
        modifier.object = armature
        modifier.vertex_group = GROUP_LBS
        dqs = body.modifiers.new(DQS_MODIFIER, "ARMATURE")
        dqs.object = armature
        dqs.use_deform_preserve_volume = True
        dqs.vertex_group = GROUP_DQS
        body_index = list(body.modifiers).index(body.modifiers[human.MODIFIER_NAME])
        body.modifiers.move(len(body.modifiers) - 2, body_index + 1)
        body.modifiers.move(len(body.modifiers) - 1, body_index + 2)
    return armature


def attach_twist(armature):
    """Torsion de l'avant-bras : le roulis de la main (pronation / supination) est réparti sur les deux os de torsion de 0 (coude) à 1 (poignet), fractions 1/3 et 2/3 (centres des chapeaux de poids) : copie de la rotation
    autour de l'axe de l'os (Y), repère local, ordre d'Euler YXZ (torsion d'abord ; l'axe médian X reste dans ±90° pour les flexions du poignet). Règle de modélisation, non issue de données publiées.
    Pas de contrainte de torsion sur le bras, la cuisse et la jambe : la copie du roulis propre d'un segment qui fléchit de plus de 90° (épaule, hanche, genou) tombe sur l'ambiguïté des angles d'Euler (mesuré : faces
    retournées par centaines) ; ces segments sont traités par les quaternions duals (voir DQS_MODIFIER)."""
    for side in ("L", "R"):
        for number, share in ((1, 1 / 3), (2, 2 / 3)):
            pose_bone = armature.pose.bones.get(f"arm_lower_twist.0{number}.{side}")
            if pose_bone is None:
                continue
            pose_bone.rotation_mode = "XYZ"
            for old in [c for c in pose_bone.constraints if c.name == TWIST_CONSTRAINT]:
                pose_bone.constraints.remove(old)
            constraint = pose_bone.constraints.new("COPY_ROTATION")
            constraint.name = TWIST_CONSTRAINT
            constraint.target, constraint.subtarget = armature, f"hand.{side}"
            constraint.use_x = constraint.use_z = False
            constraint.use_y = True
            constraint.euler_order = "YXZ"
            constraint.mix_mode = "REPLACE"
            constraint.target_space = constraint.owner_space = "LOCAL"
            constraint.influence = share


DQS_BASES = ("arm_lower", "hand", "leg_upper", "leg_lower", "foot", "toe", "index", "middle", "ring", "pinky", "thumb")


DQS_MIN = 0.0  # part minimale du poids sur les os distaux pour qu'un sommet passe aux quaternions duals (0 : au moins une influence)
DQS_HIP = True  # la hanche (cuisse) est-elle en quaternions duals ?


def in_dqs_zone(name):
    base = name.split(".")[0]
    if base == "leg_upper" and not DQS_HIP:
        return False
    return base in DQS_BASES or base in ("arm_lower_twist", "leg_upper_twist", "leg_lower_twist")  # PAS le bras : les poids du bras portent une fuite du tronc (spine.03/04 ~7 %), que les quaternions duals gonflent en bosse à l'épaule levée (mesuré, planche)


def redistribute_distal(names, idx, w, points, table):
    """Avant-bras et jambe : à partir de la moitié du segment, la part du poids de l'os de base passe à la torsion 02 (le roulis de la main arrive de l'extrémité distale : un retour du poids sur l'os de base au poignet,
    qui ne tourne pas, pince la peau). Retourne de nouveaux (idx, w)."""
    index = {n: i for i, n in enumerate(names)}
    idx, w = idx.copy(), w.copy()
    lookup = {entry["name"]: entry for entry in table}
    for limb in ("arm_lower", "leg_lower"):
        for side in ("L", "R"):
            base, tw2 = index.get(f"{limb}.{side}"), index.get(f"{limb}_twist.02.{side}")
            if base is None or tw2 is None:
                continue
            head, tail = np.array(lookup[f"{limb}.{side}"]["head"]), np.array(lookup[f"{limb}.{side}"]["tail"])
            axis = tail - head
            t = ((points - head) @ axis) / float(axis @ axis)
            rows = np.where((t > 0.5) & (t < 1.1) & (idx == base).any(1))[0]
            for v in rows:
                slot = int(np.where(idx[v] == base)[0][0])
                where = np.where(idx[v] == tw2)[0]
                if len(where):
                    w[v, where[0]] += w[v, slot]
                    w[v, slot] = 0.0
                else:
                    idx[v, slot] = tw2
    return idx, w


def _apply_weights(body, names, computed=None):
    weights = {"names": computed[0], "idx": computed[1], "w": computed[2]} if computed else np.load(WEIGHTS_FILE, allow_pickle=False)
    stored = [str(n) for n in weights["names"]]
    if stored != [n for n in names if n != JAW and n not in EYE_BONES]:
        raise ValueError("Les poids stockés ne correspondent pas à la table d'os (régénérer avec tools/build_human_rig.py).")
    groups = [None if name in NON_DEFORMING else (body.vertex_groups.get(name) or body.vertex_groups.new(name=name)) for name in stored]
    indices, values = weights["idx"], weights["w"]
    points = cage_points(body)
    indices, values = redistribute_distal(stored, indices, values, points, bone_table(real_eye_joints(body, joints(points, load_anchors()))))
    dqs_slots = np.array([in_dqs_zone(n) for n in stored])
    member = (np.where(dqs_slots[indices], values, 0.0).sum(1) > max(DQS_MIN, 1e-4))  # sommet déformé par les quaternions duals : au moins une influence distale
    lbs_group, dqs_group = body.vertex_groups.new(name=GROUP_LBS), body.vertex_groups.new(name=GROUP_DQS)
    dqs_group.add([int(v) for v in np.where(member)[0]], 1.0, "REPLACE")
    lbs_group.add([int(v) for v in np.where(~member)[0]], 1.0, "REPLACE")
    for vertex in range(len(indices)):
        for slot in range(indices.shape[1]):
            weight = float(values[vertex, slot])
            if weight > 0.0:
                groups[int(indices[vertex, slot])].add([vertex], weight, "REPLACE")
    if JAW in names:
        _apply_jaw_weights(body)


MOUTH_OPEN_DEGREES = 30.0  # ouverture pour laquelle le correctif `mouth_open` vaut 1 (voir tools/build_face_layers.py)


def _driven(body, command):
    """Vrai si la commande de visage `command` est pilotée par un driver (mâchoire, suivi des paupières)."""
    if not human.is_native(body) or command not in human.sockets() or body.animation_data is None:
        return False
    path = f'modifiers["{human.MODIFIER_NAME}"].properties.inputs.{human.sockets()[command][0]}.value'
    return any(f.data_path == path for f in body.animation_data.drivers)


def mouth_driver_path(body):
    """Chemin de la propriété du modificateur `HL Human` qui porte `mouth_open`, ou None si le groupe n'a pas cette entrée."""
    if not human.is_native(body) or "mouth_open" not in human.sockets():
        return None
    return f'modifiers["{human.MODIFIER_NAME}"].properties.inputs.{human.sockets()["mouth_open"][0]}.value'


def attach_mouth_driver(body, armature):
    """Pilote `mouth_open` par la rotation locale de l'os `jaw` : |rotation X| / 30°, borné à 1. Le correctif suit ainsi toute animation de la mâchoire (pose, action, NLA)."""
    path = mouth_driver_path(body)
    if path is None:
        return False
    body.driver_remove(path)
    fcurve = body.driver_add(path)
    driver = fcurve.driver
    driver.type = "SCRIPTED"
    variable = driver.variables.new()
    variable.name = "rx"
    variable.type = "TRANSFORMS"
    target = variable.targets[0]
    target.id = armature
    target.bone_target = JAW
    target.transform_type = "ROT_X"
    target.transform_space = "LOCAL_SPACE"
    driver.expression = f"min(1.0, abs(rx) / {math.radians(MOUTH_OPEN_DEGREES):.6f})"
    return True


def open_jaw(body, degrees):
    """Ouvre (ou ferme avec 0) la mâchoire de `degrees` degrés par la pose de l'os `jaw` ; le sens de rotation est celui qui descend la pointe de l'os. Retourne False sans squelette."""
    rigs = rigs_of(body)
    if not rigs:
        return False
    pose = rigs[0].pose.bones.get(JAW)
    if pose is None:
        return False
    pose.rotation_mode = "XYZ"
    if degrees == 0:
        pose.rotation_euler = (0.0, 0.0, 0.0)
        return True
    pose.rotation_euler = (math.radians(degrees), 0.0, 0.0)
    bpy.context.view_layer.update()
    low_plus = (rigs[0].matrix_world @ pose.tail).z
    pose.rotation_euler = (0.0, 0.0, 0.0)
    bpy.context.view_layer.update()
    rest = (rigs[0].matrix_world @ pose.tail).z
    sign = 1.0 if low_plus < rest else -1.0
    pose.rotation_euler = (sign * math.radians(degrees), 0.0, 0.0)
    return True


# --- regard ----------------------------------------------------------------------------------------------------------------------------------------
GAZE_CONSTRAINT = "HL Regard"
GAZE_LIMITS = {"horizontal_deg": 45.0, "vertical_deg": 35.0}  # PROVISOIRE, non vérifié : amplitudes maximales de rotation de chaque œil (aucune donnée publiée lue)


def gaze_direction(armature, side):
    """Direction monde (vecteur unitaire, numpy) dans laquelle regarde l'œil `side` ("L" ou "R") : l'axe Y de son os."""
    pose = armature.pose.bones["eye." + side]
    return np.array(((armature.matrix_world @ pose.matrix).to_3x3() @ Vector((0.0, 1.0, 0.0))).normalized()[:])


def _gaze_axes(armature):
    """(signe de yaw, signe de pitch) tels que yaw > 0 regarde vers +x (côté .L) et pitch > 0 vers le haut ; mesuré une fois par essai de rotation."""
    pose = armature.pose.bones["eye.L"]
    pose.rotation_mode = "XYZ"
    saved = tuple(pose.rotation_euler)
    result = []
    for axis, key in ((2, 0), (0, 2)):
        pose.rotation_euler = (0.0, 0.0, 0.0)
        bpy.context.view_layer.update()
        before = gaze_direction(armature, "L")
        trial = [0.0, 0.0, 0.0]
        trial[axis] = math.radians(10)
        pose.rotation_euler = tuple(trial)
        bpy.context.view_layer.update()
        move = gaze_direction(armature, "L") - before
        result.append(1.0 if move[key] > 0 else -1.0)
    pose.rotation_euler = saved
    bpy.context.view_layer.update()
    return tuple(result)


def set_gaze(body, yaw_degrees=0.0, pitch_degrees=0.0, convergence_degrees=0.0):
    """Oriente les yeux par la pose des os `eye.L/.R` : `yaw` > 0 vers +x (gauche du personnage), `pitch` > 0 vers le haut, `convergence` = angle total entre les deux axes (chaque œil
    tourne de moitié vers l'intérieur). Retourne False sans squelette."""
    rigs = rigs_of(body)
    if not rigs or "eye.L" not in rigs[0].pose.bones:
        return False
    armature = rigs[0]
    sign_yaw, sign_pitch = _gaze_axes(armature)
    for side, inward in (("L", -1.0), ("R", 1.0)):  # à +x l'œil gauche tourne vers -x pour converger
        pose = armature.pose.bones["eye." + side]
        pose.rotation_mode = "XYZ"
        angles = [0.0, 0.0, 0.0]
        angles[2] = sign_yaw * math.radians(yaw_degrees + inward * convergence_degrees / 2.0)
        angles[0] = sign_pitch * math.radians(pitch_degrees)
        pose.rotation_euler = tuple(angles)
    bpy.context.view_layer.update()
    return True


def track_gaze(body, target):
    """Les deux yeux suivent l'objet `target` (contrainte « Damped Track » sur l'axe Y de chaque os, bornée par une contrainte de rotation limitée) : la convergence vient de la distance de
    la cible. Retourne False sans squelette."""
    rigs = rigs_of(body)
    if not rigs or "eye.L" not in rigs[0].pose.bones:
        return False
    for side in ("L", "R"):
        pose = rigs[0].pose.bones["eye." + side]
        clear_constraints(pose)
        track = pose.constraints.new("DAMPED_TRACK")
        track.name = GAZE_CONSTRAINT
        track.target = target
        track.track_axis = "TRACK_Y"
        limit = pose.constraints.new("LIMIT_ROTATION")
        limit.name = GAZE_CONSTRAINT + " limite"
        limit.owner_space = "LOCAL"
        limit.use_limit_x = limit.use_limit_z = True
        limit.min_x, limit.max_x = -math.radians(GAZE_LIMITS["vertical_deg"]), math.radians(GAZE_LIMITS["vertical_deg"])
        limit.min_z, limit.max_z = -math.radians(GAZE_LIMITS["horizontal_deg"]), math.radians(GAZE_LIMITS["horizontal_deg"])
    bpy.context.view_layer.update()
    return True


LID_FOLLOW = {"down_closure": 0.30, "up_opening": 0.30}  # PROVISOIRE, non vérifié : fermeture de la paupière supérieure à regard maximal vers le bas / ouverture à regard maximal vers le haut (fraction des commandes blink et eye_wide)


def _lid_paths(body):
    if not human.is_native(body):
        return {}
    return {name: f'modifiers["{human.MODIFIER_NAME}"].properties.inputs.{human.sockets()[name][0]}.value' for name in ("blink_L", "blink_R", "eye_wide") if name in human.sockets()}


def lid_follow_enabled(body):
    paths = _lid_paths(body)
    return bool(paths) and body.animation_data is not None and all(any(f.data_path == p for f in body.animation_data.drivers) for p in paths.values())


def attach_lid_follow(body):
    """Les paupières suivent le regard : `blink_L`, `blink_R` (regard vers le bas : la paupière supérieure descend) et `eye_wide` (regard vers le haut : elle monte) sont PILOTÉS par la rotation
    verticale de l'os `eye.L` ; tant que le suivi est actif, ces trois commandes ne sont plus réglables à la main (retirer avec `detach_lid_follow`). Retourne False sans squelette."""
    rigs = rigs_of(body)
    paths = _lid_paths(body)
    if not rigs or "eye.L" not in rigs[0].pose.bones or len(paths) < 3:
        return False
    sign_pitch = _gaze_axes(rigs[0])[1]
    limit = math.radians(GAZE_LIMITS["vertical_deg"])
    for name, path in paths.items():
        body.driver_remove(path)
        driver = body.driver_add(path).driver
        driver.type = "SCRIPTED"
        variable = driver.variables.new()
        variable.name = "rx"
        variable.type = "TRANSFORMS"
        target = variable.targets[0]
        target.id = rigs[0]
        target.bone_target = "eye.L"
        target.transform_type = "ROT_X"
        target.transform_space = "LOCAL_SPACE"
        up = f"({sign_pitch:+.0f} * rx)"
        if name == "eye_wide":
            driver.expression = f"min(1.0, max(0.0, {up}) / {limit:.6f} * {LID_FOLLOW['up_opening']})"
        else:
            driver.expression = f"min(1.0, max(0.0, -{up}) / {limit:.6f} * {LID_FOLLOW['down_closure']})"
    return True


def detach_lid_follow(body):
    for name, path in _lid_paths(body).items():
        if body.animation_data is not None and any(f.data_path == path for f in body.animation_data.drivers):
            body.driver_remove(path)
            human.set_value(body, name, 0.0)


def clear_constraints(pose):
    for constraint in [c for c in pose.constraints if c.name.startswith(GAZE_CONSTRAINT)]:
        pose.constraints.remove(constraint)


def clear_gaze(body):
    """Retire le suivi de cible et remet les yeux droit devant."""
    rigs = rigs_of(body)
    if not rigs:
        return False
    for side in ("L", "R"):
        pose = rigs[0].pose.bones.get("eye." + side)
        if pose is not None:
            clear_constraints(pose)
            pose.rotation_mode = "XYZ"
            pose.rotation_euler = (0.0, 0.0, 0.0)
    bpy.context.view_layer.update()
    return True


def detach_mouth_driver(body):
    path = mouth_driver_path(body)
    if path is not None and body.animation_data is not None and any(f.data_path == path for f in body.animation_data.drivers):
        body.driver_remove(path)
        human.set_value(body, "mouth_open", 0.0)


def _apply_jaw_weights(body):
    """Mâchoire : chaque sommet de la zone donne au groupe `jaw` la part `w` de son poids sur `head` (jamais plus : ce qui suit le cou reste sur le cou, la torsion du cou
    n'est pas changée). Au plus 4 influences : si le sommet en aurait 5, la plus faible (hors tête et mâchoire) est reversée sur la tête."""
    data = np.load(JAW_FILE, allow_pickle=False)
    group = body.vertex_groups.get(JAW) or body.vertex_groups.new(name=JAW)
    head = body.vertex_groups["head"]
    mesh = body.data
    for vertex, weight in zip(data["idx"].tolist(), data["w"].tolist()):
        current = {g.group: g.weight for g in mesh.vertices[vertex].groups}
        share = current.get(head.index, 0.0)
        moved = min(weight, share)
        if moved <= 0.0:
            continue
        if len(current) >= 4 and group.index not in current:
            others = [k for k in current if k not in (head.index, group.index)]
            if others:
                weakest = min(others, key=lambda k: current[k])
                head.add([vertex], share + current[weakest], "REPLACE")
                body.vertex_groups[weakest].remove([vertex])
                share += current[weakest]
        head.add([vertex], share - moved, "REPLACE")
        group.add([vertex], moved, "REPLACE")


def update(body, dental=False):
    """Repose les os d'après la morphologie actuelle : poids et actions conservés (les repères sont définis par règle). `dental=True` régénère aussi dents, gencives et langue (l'ajustement
    dans la cavité coûte de 0,2 à 3 s : l'interface le demande, le chemin rapide de la seule repose des os ne le fait pas ; sans régénération les dents gardent leur ancienne place)."""
    rigs = rigs_of(body)
    if len(rigs) != 1:
        raise ValueError("Aucun rig (ou plusieurs) : rien à mettre à jour.")
    armature = rigs[0]
    points = cage_points(body)
    table = bone_table(real_eye_joints(body, joints(points, load_anchors())))
    with _Context():
        bpy.context.view_layer.objects.active = armature
        armature.select_set(True)
        bpy.ops.object.mode_set(mode="EDIT")
        _set_bones(armature, table)
        bpy.ops.object.mode_set(mode="OBJECT")
    armature[FINGERPRINT] = fingerprint(body)
    attach_eyes(body, armature)
    if dental:
        from . import dental as dental_module
        dental_module.update(body, armature, points)
    return armature


def remove(body):
    """Retire armature, groupes de poids de nos os et modificateur ; ne touche à aucun autre groupe ni modificateur. Retourne le nombre d'éléments retirés."""
    removed = 0
    detach_mouth_driver(body)
    detach_eyes(body)
    from . import dental
    removed += dental.remove(body)
    for modifier_name in (MODIFIER_NAME, DQS_MODIFIER):
        modifier = body.modifiers.get(modifier_name)
        if modifier is not None and modifier.type == "ARMATURE":
            body.modifiers.remove(modifier)
            removed += 1
    names = set(deform_names()) | {GROUP_LBS, GROUP_DQS}
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
