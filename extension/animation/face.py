"""Visage complet (lot L1) : poses et expressions (galerie, mélange), visèmes, correspondance ARKit, formes « cuites » pour l'export, animation faciale en NLA indépendante du corps.

Une POSE est un dictionnaire : noms de commandes de `proportions.FACE_COMMANDS` (valeurs 0-1), plus des clés réservées :
  `_jaw`     angle d'ouverture de la mâchoire en degrés (os `jaw`) ;
  `_tongue`  {nom de forme de `dental.TONGUE_SHAPES`: valeur 0-1} ;
  `_gaze`    [horizontal, vertical] en degrés (os `eye.L/.R`).
D-34 : toutes les poses sont ÉCRITES PAR NOUS ; aucune donnée de visage tierce. D-35 : ce qui n'a pas été lu dans une publication est déclaré « non vérifié »."""
import json
import math

import bpy
import numpy as np

from .. import human
from mathutils import Vector
from mathutils.bvhtree import BVHTree

from ..proportions import FACE_COMMANDS, FACE_PRESETS
from . import dental, skeleton

NON_VERIFIE = "non vérifié : choix de modélisation de HumanLoom, aucune publication lue pour ces valeurs"
SCENE_POSES = "humanloom_face_poses"  # poses de l'utilisateur (JSON dans la scène)
SCENE_FAVORITES = "humanloom_face_favorites"  # identifiants favoris (JSON dans la scène)
PILOTS = tuple(c for c in FACE_COMMANDS if c != "mouth_open")

# --- visèmes ------------------------------------------------------------------------------------------------------------------------------------------
# Liste de 14 visèmes + silence : les noms de groupes suivent la liste des visèmes de la norme MPEG-4 (parties « face animation ») TELLE QUE RETENUE DE MÉMOIRE ; la table de la norme n'a PAS été lue ici,
# et les valeurs de chaque pose (ouverture, arrondi, langue) sont des choix de modélisation de HumanLoom. Tout est donc « non vérifié ».
VISEMES = {
    "sil": ("Silence", {}),
    "pbm": ("p, b, m", {"lips_press": 1.0}),
    "fv": ("f, v", {"upper_lip_raise": 0.5, "_jaw": 3.0}),
    "th": ("th", {"_jaw": 5.0, "_tongue": {"langue_sortie": 0.4}}),
    "td": ("t, d", {"_jaw": 5.0, "_tongue": {"langue_pointe_haut": 1.0}}),
    "kg": ("k, g", {"_jaw": 6.0, "_tongue": {"langue_dos_haut": 1.0}}),
    "chj": ("ch, j, sh", {"lip_pucker": 0.5, "_jaw": 4.0}),
    "sz": ("s, z", {"lip_stretch": 0.4, "_jaw": 3.0, "_tongue": {"langue_pointe_haut": 0.5}}),
    "nl": ("n, l", {"_jaw": 6.0, "_tongue": {"langue_pointe_haut": 1.0}}),
    "r": ("r", {"lip_pucker": 0.3, "_jaw": 5.0, "_tongue": {"langue_dos_haut": 0.6}}),
    "aa": ("a", {"_jaw": 18.0}),
    "e": ("e", {"_jaw": 10.0, "lip_stretch": 0.5}),
    "ih": ("i", {"_jaw": 6.0, "lip_stretch": 0.8}),
    "oh": ("o", {"_jaw": 12.0, "lip_pucker": 0.8}),
    "ou": ("ou", {"_jaw": 5.0, "lip_pucker": 1.0}),
}

# --- ARKit 52 -----------------------------------------------------------------------------------------------------------------------------------------
# Les 52 noms de coefficients sont ceux du jeu de formes ARKit (documentation d'Apple, relue de mémoire : la page n'a pas été relue ici). Aucun coefficient n'est inventé : chaque ligne dit si notre visage
# le couvre (« direct » : même geste, « approx » : geste voisin, « os » : porté par un os, « forme » : forme de langue, « non couvert » : rien). Le sens gauche/droite (côté du sujet ou de l'observateur)
# n'est pas vérifié : nos commandes `.L` sont du côté +x du personnage. Poids = valeur de commande pour un coefficient à 1.
ARKIT = {
    "eyeBlinkLeft": ("direct", [("blink_L", 1.0)]), "eyeBlinkRight": ("direct", [("blink_R", 1.0)]),
    "eyeLookDownLeft": ("os", [("_gaze", 1.0)]), "eyeLookDownRight": ("os", [("_gaze", 1.0)]),
    "eyeLookInLeft": ("os", [("_gaze", 1.0)]), "eyeLookInRight": ("os", [("_gaze", 1.0)]),
    "eyeLookOutLeft": ("os", [("_gaze", 1.0)]), "eyeLookOutRight": ("os", [("_gaze", 1.0)]),
    "eyeLookUpLeft": ("os", [("_gaze", 1.0)]), "eyeLookUpRight": ("os", [("_gaze", 1.0)]),
    "eyeSquintLeft": ("approx", [("eye_squint", 1.0)]), "eyeSquintRight": ("approx", [("eye_squint", 1.0)]),
    "eyeWideLeft": ("approx", [("eye_wide", 1.0)]), "eyeWideRight": ("approx", [("eye_wide", 1.0)]),
    "jawForward": ("non couvert", []), "jawLeft": ("non couvert", []), "jawRight": ("non couvert", []),
    "jawOpen": ("os", [("_jaw", 1.0)]),
    "mouthClose": ("non couvert", []),
    "mouthFunnel": ("approx", [("lip_pucker", 0.5)]), "mouthPucker": ("direct", [("lip_pucker", 1.0)]),
    "mouthLeft": ("non couvert", []), "mouthRight": ("non couvert", []),
    "mouthSmileLeft": ("direct", [("smile_L", 1.0)]), "mouthSmileRight": ("direct", [("smile_R", 1.0)]),
    "mouthFrownLeft": ("approx", [("mouth_down", 1.0)]), "mouthFrownRight": ("approx", [("mouth_down", 1.0)]),
    "mouthDimpleLeft": ("non couvert", []), "mouthDimpleRight": ("non couvert", []),
    "mouthStretchLeft": ("approx", [("lip_stretch", 1.0)]), "mouthStretchRight": ("approx", [("lip_stretch", 1.0)]),
    "mouthRollLower": ("non couvert", []), "mouthRollUpper": ("non couvert", []),
    "mouthShrugLower": ("approx", [("chin_raise", 1.0)]), "mouthShrugUpper": ("approx", [("upper_lip_raise", 0.5)]),
    "mouthPressLeft": ("approx", [("lips_press", 1.0)]), "mouthPressRight": ("approx", [("lips_press", 1.0)]),
    "mouthLowerDownLeft": ("non couvert", []), "mouthLowerDownRight": ("non couvert", []),
    "mouthUpperUpLeft": ("approx", [("upper_lip_raise", 1.0)]), "mouthUpperUpRight": ("approx", [("upper_lip_raise", 1.0)]),
    "browDownLeft": ("approx", [("brow_down", 1.0)]), "browDownRight": ("approx", [("brow_down", 1.0)]),
    "browInnerUp": ("direct", [("brow_inner_up", 1.0)]),
    "browOuterUpLeft": ("approx", [("brow_up", 1.0)]), "browOuterUpRight": ("approx", [("brow_up", 1.0)]),
    "cheekPuff": ("direct", [("cheek_puff", 1.0)]),
    "cheekSquintLeft": ("approx", [("cheek_raise", 1.0)]), "cheekSquintRight": ("approx", [("cheek_raise", 1.0)]),
    "noseSneerLeft": ("approx", [("nose_wrinkle", 1.0)]), "noseSneerRight": ("approx", [("nose_wrinkle", 1.0)]),
    "tongueOut": ("forme", [("_tongue:langue_sortie", 1.0)]),
}
COVERAGE_WEIGHT = {"direct": 1.0, "os": 1.0, "forme": 1.0, "approx": 0.5, "non couvert": 0.0}
JAW_FULL_DEGREES = skeleton.MOUTH_OPEN_DEGREES


def arkit_report():
    """Couverture numérique des 52 coefficients : effectifs par catégorie, couverture pondérée (direct/os/forme 1, approx 0,5, non couvert 0), liste des non couverts, table commande -> coefficients."""
    kinds = {}
    for name, (kind, _) in ARKIT.items():
        kinds.setdefault(kind, []).append(name)
    total = len(ARKIT)
    inverse = {}
    for name, (kind, targets) in ARKIT.items():
        for command, weight in targets:
            inverse.setdefault(command, []).append({"coefficient": name, "poids": weight, "categorie": kind})
    return {"total": total, "par_categorie": {k: len(v) for k, v in kinds.items()},
            "couverture_ponderee": round(sum(COVERAGE_WEIGHT[k] * len(v) for k, v in kinds.items()) / total, 4),
            "non_couverts": sorted(kinds.get("non couvert", [])), "commande_vers_coefficients": inverse,
            "source": "noms : documentation ARKit d'Apple, de mémoire (non relue) ; correspondances : choix de HumanLoom, non vérifiés"}


def arkit_to_pose(coefficients):
    """Convertit un dictionnaire {coefficient ARKit: valeur 0-1} en pose HumanLoom. Plusieurs coefficients sur la même commande : le maximum. Coefficients inconnus : ValueError."""
    pose, gaze = {}, {"up": [], "down": [], "in": [], "out": []}
    for name, value in coefficients.items():
        if name not in ARKIT:
            raise ValueError("Coefficient ARKit inconnu : " + name)
        value = float(np.clip(value, 0.0, 1.0))
        for command, weight in ARKIT[name][1]:
            if command == "_jaw":
                pose["_jaw"] = max(pose.get("_jaw", 0.0), value * weight * JAW_FULL_DEGREES)
            elif command.startswith("_tongue:"):
                tongue = pose.setdefault("_tongue", {})
                tongue[command.split(":")[1]] = max(tongue.get(command.split(":")[1], 0.0), value * weight)
            elif command == "_gaze":
                for key in ("Up", "Down", "In", "Out"):
                    if "Look" + key in name:
                        gaze[key.lower()].append((name.endswith("Left"), value))
            else:
                pose[command] = max(pose.get(command, 0.0), value * weight)
    if any(gaze.values()):
        def mean(items):
            return sum(v for _, v in items) / 2.0  # deux yeux

        yaw_left = sum(v for left, v in gaze["out"] if left) - sum(v for left, v in gaze["in"] if left)
        yaw_right = sum(v for left, v in gaze["in"] if not left) - sum(v for left, v in gaze["out"] if not left)
        pose["_gaze"] = [(yaw_left + yaw_right) / 2.0 * skeleton.GAZE_LIMITS["horizontal_deg"], (mean(gaze["up"]) - mean(gaze["down"])) * skeleton.GAZE_LIMITS["vertical_deg"]]
    return pose


# --- poses : application, mélange, bibliothèque --------------------------------------------------------------------------------------------------------
def builtin_poses():
    """{identifiant: {"label", "categorie", "pose", "source"}} : expressions (FACE_PRESETS) et visèmes ; écrits par nous (D-34)."""
    library = {}
    for key, pose in FACE_PRESETS.items():
        library["expression:" + key] = {"label": key.capitalize(), "categorie": "expression", "pose": dict(pose), "source": "combinaison d'unités d'action écrite par HumanLoom, intensités artistiques"}
    for key, (label, pose) in VISEMES.items():
        library["visème:" + key] = {"label": label, "categorie": "visème", "pose": json.loads(json.dumps(pose)), "source": NON_VERIFIE}
    return library


def user_poses(scene):
    try:
        return json.loads(scene.get(SCENE_POSES, "{}"))
    except ValueError:
        return {}


def favorites(scene):
    try:
        return list(json.loads(scene.get(SCENE_FAVORITES, "[]")))
    except ValueError:
        return []


def gallery(scene):
    """Index complet : poses prédéfinies + poses de l'utilisateur, avec drapeau favori. Liste de dictionnaires triée par catégorie puis libellé."""
    library = builtin_poses()
    for key, pose in user_poses(scene).items():
        library["utilisateur:" + key] = {"label": key, "categorie": "utilisateur", "pose": pose, "source": "enregistrée par l'utilisateur"}
    fav = set(favorites(scene))
    rows = [dict(id=k, favori=k in fav, **v) for k, v in library.items()]
    return sorted(rows, key=lambda r: (not r["favori"], r["categorie"], r["label"]))


def save_pose(scene, name, pose):
    poses = user_poses(scene)
    poses[name] = pose
    scene[SCENE_POSES] = json.dumps(poses, ensure_ascii=False)


def toggle_favorite(scene, pose_id):
    fav = favorites(scene)
    if pose_id in fav:
        fav.remove(pose_id)
    else:
        fav.append(pose_id)
    scene[SCENE_FAVORITES] = json.dumps(fav)
    return pose_id in fav


def read_pose(body):
    """Pose actuelle du visage (commandes, mâchoire, langue, regard)."""
    pose = {name: round(human.get_value(body, name), 4) for name in PILOTS if human.has_control(body, name) and abs(human.get_value(body, name)) > 1e-6}
    rigs = skeleton.rigs_of(body)
    if rigs and skeleton.JAW in rigs[0].pose.bones:
        pose_bone = rigs[0].pose.bones[skeleton.JAW]
        degrees = abs(math.degrees(pose_bone.rotation_euler[0]))
        if degrees > 0.01:
            pose["_jaw"] = round(degrees, 3)
    tongue = _tongue_object(body)
    if tongue is not None and tongue.data.shape_keys is not None:
        values = {k.name: round(k.value, 4) for k in tongue.data.shape_keys.key_blocks if k.name in dental.TONGUE_SHAPES and k.value > 1e-6}
        if values:
            pose["_tongue"] = values
    return pose


def mix_poses(first, second, factor):
    """Mélange linéaire de deux poses (`factor` 0 : première, 1 : seconde) ; clé absente = 0."""
    factor = float(np.clip(factor, 0.0, 1.0))
    mixed = {}
    for name in set(first) | set(second):
        if name == "_tongue":
            keys = set(first.get(name, {})) | set(second.get(name, {}))
            mixed[name] = {k: (1 - factor) * first.get(name, {}).get(k, 0.0) + factor * second.get(name, {}).get(k, 0.0) for k in keys}
        elif name == "_gaze":
            a, b = first.get(name, [0.0, 0.0]), second.get(name, [0.0, 0.0])
            mixed[name] = [(1 - factor) * a[i] + factor * b[i] for i in range(2)]
        else:
            mixed[name] = (1 - factor) * first.get(name, 0.0) + factor * second.get(name, 0.0)
    return mixed


def _tongue_object(body):
    return dental.part_of(body, "tongue")


def apply_pose(body, pose):
    """Applique la pose : commandes absentes remises à 0, mâchoire (si le squelette est installé), langue (si présente), regard (si `_gaze`). Retourne un rapport de ce qui a été appliqué."""
    report = {"commandes": 0, "machoire": False, "langue": False, "regard": False}
    for name in PILOTS:
        if human.has_control(body, name):
            human.set_value(body, name, float(np.clip(pose.get(name, 0.0), 0.0, 1.0)))
            report["commandes"] += 1
    report["machoire"] = skeleton.open_jaw(body, float(pose.get("_jaw", 0.0)))
    tongue = _tongue_object(body)
    if tongue is not None and tongue.data.shape_keys is not None:
        for key in tongue.data.shape_keys.key_blocks:
            if key.name in dental.TONGUE_SHAPES:
                key.value = float(np.clip(pose.get("_tongue", {}).get(key.name, 0.0), 0.0, 1.0))
        report["langue"] = True
    if "_gaze" in pose:
        report["regard"] = skeleton.set_gaze(body, float(pose["_gaze"][0]), float(pose["_gaze"][1]))
    bpy.context.view_layer.update()
    return report


# --- formes cuites pour l'export --------------------------------------------------------------------------------------------------------------------
def _evaluated_points(body):
    """Cage morphée (modificateur `HL Human` seul : même topologie que le maillage du corps, donc poids de peau copiables)."""
    return skeleton.cage_points(body)


def bake_shapes(body, arkit=True, name=None):
    """Crée un objet « export » : copie de la CAGE du corps (modificateur `HL Human` seul, sans armature ni autres modificateurs ; à lisser/subdiviser à l'export si besoin) avec une forme par commande de visage (noms HumanLoom) et, si `arkit`, une forme par coefficient ARKit couvert par
    des commandes (les coefficients portés par un os ou la langue ne sont pas cuits : ils n'ont pas de forme de peau). Les commandes pilotées par un driver sont ignorées. Les valeurs de commandes de
    `body` sont restaurées. Retourne (objet, rapport)."""
    armature_modifiers = [m for m in body.modifiers if m.type == "ARMATURE"]
    states = [(m, m.show_viewport) for m in armature_modifiers]
    saved = {n: human.get_value(body, n) for n in FACE_COMMANDS if human.has_control(body, n)}
    driven = {n for n in saved if skeleton._driven(body, n)}
    for m in armature_modifiers:
        m.show_viewport = False
    try:
        for n in saved:
            if n not in driven:
                human.set_value(body, n, 0.0)
        base = _evaluated_points(body)
        mesh = bpy.data.meshes.new((name or body.name) + " export")
        mesh.from_pydata([tuple(p) for p in base], [], [])
        source_mesh = body.data
        if len(source_mesh.vertices) == len(base):  # topologie conservée : on copie les polygones du maillage source
            mesh.clear_geometry()
            mesh.from_pydata([tuple(p) for p in base], [], [tuple(p.vertices) for p in source_mesh.polygons])
        mesh.update()
        obj = bpy.data.objects.new((name or body.name) + " export", mesh)
        bpy.context.scene.collection.objects.link(obj)
        obj.matrix_world = body.matrix_world.copy()
        obj.shape_key_add(name="Basis", from_mix=False)
        report = {"formes": {}, "ignorees_pilotees": sorted(driven), "sommets": int(len(base))}

        def add(shape_name, values):
            for n in saved:
                if n not in driven:
                    human.set_value(body, n, float(values.get(n, 0.0)))
            points = _evaluated_points(body)
            key = obj.shape_key_add(name=shape_name, from_mix=False)
            key.relative_key = mesh.shape_keys.key_blocks["Basis"]
            key.data.foreach_set("co", points.ravel())
            key.slider_min, key.slider_max = 0.0, 1.0
            report["formes"][shape_name] = round(float(np.linalg.norm(points - base, axis=1).max()) * 1000, 3)

        for command in saved:
            if command not in driven:
                add(command, {command: 1.0})
        if arkit:
            for coefficient, (kind, targets) in ARKIT.items():
                commands = {c: w for c, w in targets if not c.startswith("_")}
                if commands and not (set(commands) & driven):
                    add(coefficient, commands)
        report["arkit_cuits"] = sum(1 for n in report["formes"] if n in ARKIT)
        report["arkit_non_cuits_os_langue_ou_non_couverts"] = sorted(n for n in ARKIT if n not in report["formes"])
    finally:
        for n, v in saved.items():
            if n not in driven:
                human.set_value(body, n, v)
        for m, state in states:
            m.show_viewport = state
    if source_mesh.vertices and len(source_mesh.vertices) == len(base):
        for group in body.vertex_groups:
            obj.vertex_groups.new(name=group.name)
        for v in source_mesh.vertices:
            for g in v.groups:
                obj.vertex_groups[body.vertex_groups[g.group].name].add([v.index], g.weight, "REPLACE")
    return obj, report


# --- animation faciale en NLA (indépendante du corps) ---------------------------------------------------------------------------------------------------
FACE_TRACK = "Visage"


def _command_paths(body):
    return {n: f'modifiers["{human.MODIFIER_NAME}"].properties.inputs.{human.sockets()[n][0]}.value' for n in PILOTS if human.has_control(body, n)}


def _push_strip(owner_id, name, start):
    """Pousse l'action courante de `owner_id` dans une piste NLA « Visage » (nouvelle bande), retire l'action active. Retourne la bande."""
    animation = owner_id.animation_data
    action = animation.action
    track = animation.nla_tracks.get(FACE_TRACK) or animation.nla_tracks.new()
    track.name = FACE_TRACK
    end = max(action.frame_range[1], start + 1)
    strip = track.strips.new(name, int(start), action)
    strip.name = name
    strip.frame_end = max(strip.frame_end, end)
    animation.action = None
    return strip


def build_clip(body, name, keys, start=1):
    """Crée un clip facial à partir de `keys` = [(image, pose), ...] : commandes sur le CORPS (modificateur), mâchoire et regard sur l'ARMATURE, langue sur sa clé de forme ; chaque jeu va dans sa propre
    bande de la piste NLA « Visage » (les actions du corps ne sont pas touchées : l'action active du corps/de l'armature est mise de côté puis restaurée). Retourne la liste des bandes créées."""
    rigs = skeleton.rigs_of(body)
    armature = rigs[0] if rigs else None
    tongue = _tongue_object(body)
    paths = _command_paths(body)
    strips = []
    saved_pose = read_pose(body)
    holders = [(body, "corps")]
    if armature is not None:
        holders.append((armature, "armature"))
    if tongue is not None and tongue.data.shape_keys is not None:
        holders.append((tongue.data.shape_keys, "langue"))
    previous = {}
    for holder, label in holders:
        holder.animation_data_create()
        previous[label] = holder.animation_data.action
        holder.animation_data.action = None
    try:
        for frame, pose in keys:
            apply_pose(body, pose)
            for command, path in paths.items():
                if not skeleton._driven(body, command):
                    body.keyframe_insert(path, frame=frame)
            if armature is not None:
                for bone_name in (skeleton.JAW, "eye.L", "eye.R"):
                    pb = armature.pose.bones.get(bone_name)
                    if pb is not None:
                        pb.keyframe_insert("rotation_euler", frame=frame)
            if tongue is not None and tongue.data.shape_keys is not None:
                for key in tongue.data.shape_keys.key_blocks:
                    if key.name in dental.TONGUE_SHAPES:
                        key.keyframe_insert("value", frame=frame)
        for holder, label in holders:
            if holder.animation_data.action is not None:
                holder.animation_data.action.name = f"{name} ({label})"
                strips.append(_push_strip(holder, f"{name} ({label})", start))
    finally:
        for holder, label in holders:
            holder.animation_data.action = previous[label]
        apply_pose(body, saved_pose)
    return strips


def clip_strips(body):
    """Bandes de la piste « Visage » de chaque porteur (corps, armature, clé de forme de langue)."""
    rigs = skeleton.rigs_of(body)
    tongue = _tongue_object(body)
    holders = [body] + ([rigs[0]] if rigs else []) + ([tongue.data.shape_keys] if tongue is not None and tongue.data.shape_keys is not None else [])
    found = []
    for holder in holders:
        animation = holder.animation_data
        track = animation.nla_tracks.get(FACE_TRACK) if animation is not None else None
        if track is not None:
            found.extend((holder, s) for s in track.strips)
    return found


def set_clips_enabled(body, enabled):
    for holder, _ in clip_strips(body):
        holder.animation_data.nla_tracks[FACE_TRACK].mute = not enabled


def remove_clips(body):
    """Retire la piste « Visage » de chaque porteur et remet le visage au neutre (les valeurs animées restent sinon figées sur la dernière image évaluée)."""
    count = 0
    for holder, _ in clip_strips(body):
        track = holder.animation_data.nla_tracks.get(FACE_TRACK)
        if track is not None:
            holder.animation_data.nla_tracks.remove(track)
            count += 1
    if count:
        apply_pose(body, {})
    return count


# --- mesures ----------------------------------------------------------------------------------------------------------------------------------------
def teeth_visible_fraction(body, kind="lower"):
    """Part (0-1) des sommets des dents `kind` ("lower" ou "upper") VISIBLES de face : le rayon horizontal parti de l'avant atteint la dent avant la peau du corps évalué (pose actuelle comprise). Les
    sommets cachés par construction (face postérieure, sous la dent) comptent dans le total : c'est une mesure relative, à comparer d'une expression à l'autre."""
    teeth = dental.part_of(body, kind)
    if teeth is None:
        return None
    bpy.context.view_layer.update()
    evaluated = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    tree = BVHTree.FromPolygons([v.co.copy() for v in mesh.vertices], [p.vertices[:] for p in mesh.polygons])
    inverse = body.matrix_world.inverted()
    evaluated.to_mesh_clear()
    visible = 0
    vertices = teeth.data.vertices
    for v in vertices:
        point = inverse @ (teeth.matrix_world @ v.co)
        hit = tree.ray_cast(Vector((point.x, point.y - 0.3, point.z)), Vector((0, 1, 0)), 0.3005)
        if hit[0] is None or hit[0].y >= point.y - 0.0004:
            visible += 1
    return visible / max(len(vertices), 1)


SMILE_LID_UP, SMILE_LID_DOWN, SMILE_CHEEK = 7000, 6790, 7380  # sommets de la cage (côté +x) : peau de la paupière supérieure (8 mm au-dessus du centre de l'œil), de l'inférieure (8 mm au-dessous), pommette


def smile_metrics(body, levels=(0.25, 0.5, 0.75, 1.0)):
    """Mesures du sourire de Duchenne (commande `smile_duchenne`, les autres commandes à 0) sur la CAGE : pour chaque intensité, déplacement de la commissure (angle au-dessus de l'horizontale, vers l'extérieur et le haut),
    VOLUME local des joues (flux du déplacement à travers la surface, Σ (d·n) A sur un disque de 35 mm centré sur le sommet de pommette `SMILE_CHEEK` : variation nette, brute, rapport net/brut), réduction de l'ouverture palpébrale
    (écart vertical, en mm, entre deux points de peau de la paupière supérieure et de l'inférieure, côté +x ; négatif = l'ouverture diminue) et faces retournées (aire > 1 mm²). Les valeurs des commandes sont restaurées."""
    mesh = body.data
    mesh.calc_loop_triangles()
    triangles = np.array([t.vertices[:] for t in mesh.loop_triangles])
    saved = {n: human.get_value(body, n) for n in FACE_COMMANDS if human.has_control(body, n)}
    jaw = np.load(skeleton.JAW_FILE, allow_pickle=False)
    slit = np.concatenate([jaw["slit_upper"], jaw["slit_lower"]])
    try:
        for n in saved:
            human.set_value(body, n, 0.0)
        rest = skeleton.cage_points(body)
        corner = int(slit[np.argmax(rest[slit, 0])])
        lid_up, lid_down, cheek_id = SMILE_LID_UP, SMILE_LID_DOWN, SMILE_CHEEK  # sommets de la cage (topologie commune à toutes les morphologies)
        cross = np.cross(rest[triangles[:, 1]] - rest[triangles[:, 0]], rest[triangles[:, 2]] - rest[triangles[:, 0]])
        area = np.linalg.norm(cross, axis=1) / 2.0
        normals = cross / np.maximum(2 * area, 1e-18)[:, None]
        vertex_n, vertex_a = np.zeros_like(rest), np.zeros(len(rest))
        for k in range(3):
            np.add.at(vertex_n, triangles[:, k], normals * area[:, None] / 3.0)
            np.add.at(vertex_a, triangles[:, k], area / 3.0)
        vertex_n /= np.maximum(np.linalg.norm(vertex_n, axis=1), 1e-18)[:, None]
        region = (np.linalg.norm(rest - rest[cheek_id], axis=1) < 0.035) & (rest[:, 1] < rest[cheek_id, 1] + 0.012)
        n0 = np.cross(rest[triangles[:, 1]] - rest[triangles[:, 0]], rest[triangles[:, 2]] - rest[triangles[:, 0]])
        rows = {}
        for level in levels:
            human.set_value(body, "smile_duchenne", float(level))
            posed = skeleton.cage_points(body)
            d = posed - rest
            flux = np.einsum("ij,ij->i", d, vertex_n) * vertex_a
            n1 = np.cross(posed[triangles[:, 1]] - posed[triangles[:, 0]], posed[triangles[:, 2]] - posed[triangles[:, 0]])
            flips = int(((np.einsum("ij,ij->i", n0, n1) < 0) & (np.linalg.norm(n0, axis=1) > 4e-6)).sum())
            cd = d[corner]
            rows[float(level)] = {
                "commissure_mm": round(float(np.linalg.norm(cd)) * 1000, 2), "commissure_angle_deg": round(float(np.degrees(np.arctan2(cd[2], cd[0]))), 1),
                "joue_volume_net_cm3": round(float(flux[region].sum()) * 1e6, 4), "joue_volume_brut_cm3": round(float(np.abs(flux[region]).sum()) * 1e6, 4),
                "joue_net_sur_brut": round(float(abs(flux[region].sum()) / max(np.abs(flux[region]).sum(), 1e-18)), 3),
                "ouverture_palpebrale_mm": round(float((posed[lid_up, 2] - posed[lid_down, 2]) - (rest[lid_up, 2] - rest[lid_down, 2])) * 1000, 2),
                "faces_retournees": flips}
        return rows
    finally:
        for n, v in saved.items():
            human.set_value(body, n, v)
