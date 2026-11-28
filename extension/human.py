"""Schéma 10 (lot 2) : humain natif piloté par le groupe de nœuds « HL Human ».

Cohabite avec l'ancien moteur (clés de forme + pilotes, `human_modeling.create`), conservé jusqu'au lot 5 : les modules
partagés (mesures, repères, préréglages, anatomie, groom, interface) passent par les accesseurs ci-dessous
(`is_native`, `get_value`, `set_value`, `draw_control`, …) et fonctionnent pour les deux.
Un humain schéma 10 est un objet MESH ordinaire portant `Object.humanloom` (façade D, D-07) ; ses paramètres sont les
entrées du modificateur « HL Human », jamais des clés de forme.
"""

from pathlib import Path
import re
import uuid as uuid_module

import bpy

try:
    from .proportions import AMPLITUDE_FACTORS, MERGED_IN_SCHEMA_10
except ImportError:  # importé à plat par certains scripts de test
    from proportions import AMPLITUDE_FACTORS, MERGED_IN_SCHEMA_10

NODES_PATH = Path(__file__).parent / "data" / "human_nodes.blend"
EYES_PATH = Path(__file__).parent / "data" / "human_eyes.blend"  # yeux + porteur de relief (tools/build_human_eyes.py)
GROUP_NAME = "HL Human"
MESH_NAME = "HL Human Base"
MODIFIER_NAME = "HL Human"
SCHEMA_VERSION = 10
GENERATOR_VERSION = 1
FACADE_SKIP = {"Geometry"}

# Les entrées du groupe et leur identifiant de socket sont lus dans le groupe (jamais devinés).
_SOCKETS = {}


SOCKETS_PATH = Path(__file__).parent / "data" / "human_sockets.json"


def read_sockets_from_group():
    """Lit les entrées dans le groupe de nœuds livré (impossible pendant l'enregistrement : `bpy.data` est alors restreint)."""
    found = {}
    with bpy.data.libraries.load(str(NODES_PATH), link=False) as (_, target):
        target.node_groups = [GROUP_NAME]
    group = target.node_groups[0]
    for item in group.interface.items_tree:
        if item.item_type == "SOCKET" and item.in_out == "INPUT" and item.socket_type == "NodeSocketFloat":
            found[item.name] = (item.identifier, item.default_value, item.min_value, item.max_value)
    bpy.data.node_groups.remove(group)
    return found


def sockets():
    """{nom: (identifiant de socket, défaut, min, max)}.

    Lu dans `data/human_sockets.json`, écrit par `tools/build_human_nodes.py` depuis le groupe et vérifié contre lui par
    `validate_human_nodes.py` : l'enregistrement de l'extension ne peut pas ouvrir de .blend (`bpy.data` restreint au démarrage)."""
    if not _SOCKETS:
        import json
        for name, values in json.loads(SOCKETS_PATH.read_text(encoding="utf-8")).items():
            _SOCKETS[name] = tuple(values)
    return _SOCKETS


class HumanStateError(ValueError):
    """Le corps natif est dans un état que l'extension ne peut pas piloter (modificateur absent, dupliqué ou remplacé)."""


_COMPATIBLE = {}  # session_uid du groupe -> le groupe porte toutes les entrées attendues


def _compatible(group):
    """Le groupe de nœuds expose-t-il toutes les entrées de « HL Human » (par identifiant de socket, pas par nom de groupe) ?"""
    key = group.session_uid
    if key not in _COMPATIBLE:
        have = {item.identifier for item in group.interface.items_tree if item.item_type == "SOCKET" and item.in_out == "INPUT"}
        _COMPATIBLE[key] = all(values[0] in have for values in sockets().values())
    return _COMPATIBLE[key]


def modifier_status(obj):
    """(état, modificateur) du pilote de l'humain natif. États : « ok » (nom canonique), « renamed » (renommé par l'utilisateur, retrouvé par son groupe), « missing », « duplicate » (deux modificateurs portent le groupe), « incompatible » (le modificateur « HL Human » existe mais son groupe n'a pas les entrées attendues)."""
    if obj is None or obj.type != "MESH":
        return "missing", None
    candidates = [m for m in obj.modifiers if m.type == "NODES" and m.node_group is not None and _compatible(m.node_group)]
    if len(candidates) > 1:
        return "duplicate", None
    if candidates:
        return ("ok" if candidates[0].name == MODIFIER_NAME else "renamed"), candidates[0]
    named = obj.modifiers.get(MODIFIER_NAME)
    return ("incompatible" if named is not None else "missing"), None


_STATE_MESSAGES = {
    "missing": "le modificateur « HL Human » est absent",
    "duplicate": "plusieurs modificateurs portent le groupe « HL Human » (supprimez la copie)",
    "incompatible": "le modificateur « HL Human » utilise un groupe de nœuds qui n'a pas les entrées attendues",
}


def modifier_of(obj):
    """Le modificateur pilote, ou None s'il est absent, dupliqué ou remplacé (voir `modifier_status`). Un renommage ordinaire est toléré."""
    return modifier_status(obj)[1]


def require_modifier(obj):
    """Comme `modifier_of`, mais lève `HumanStateError` avec la cause : aucune commande ne doit échouer en silence."""
    state, modifier = modifier_status(obj)
    if modifier is None:
        raise HumanStateError(f"{getattr(obj, 'name', obj)} : {_STATE_MESSAGES.get(state, state)}.")
    return modifier


def repair_modifier(obj):
    """Remet le nom canonique au modificateur renommé (les pilotes des yeux et du relief le désignent par son nom) ; renvoie l'état final. Les valeurs ne changent pas."""
    state, modifier = modifier_status(obj)
    if state == "renamed":
        occupant = obj.modifiers.get(MODIFIER_NAME)
        if occupant is not None and occupant != modifier:
            raise HumanStateError(f"{obj.name} : le nom « {MODIFIER_NAME} » est pris par un autre modificateur.")
        modifier.name = MODIFIER_NAME
    elif state != "ok":
        raise HumanStateError(f"{obj.name} : {_STATE_MESSAGES[state]} ; réparation impossible automatiquement.")
    return modifier_status(obj)[0]


def is_native(obj):
    """Vrai pour un humain schéma 10 (façade `humanloom`), faux pour un corps de l'ancien moteur ou un autre objet."""
    properties = getattr(obj, "humanloom", None) if obj is not None else None
    return bool(properties is not None and properties.is_human and obj.type == "MESH")


def is_legacy(obj):
    return obj is not None and obj.type == "MESH" and bool(obj.get("human_modeling_body")) and not is_native(obj)


def is_body(obj):
    return is_native(obj) or is_legacy(obj)


def body_of(obj):
    """Le corps (natif ou ancien moteur) de l'objet actif ou de son parent, sinon None."""
    if is_body(obj):
        return obj
    if obj is not None and obj.parent is not None and is_body(obj.parent):
        return obj.parent
    parent = obj.parent if obj is not None else None
    if parent is not None and parent.type == "ARMATURE" and parent.parent is not None and is_body(parent.parent):  # œil rattaché à l'os head du squelette du corps
        return parent.parent
    return None


def _legacy_name(name):
    return {"sex": None, "age": "human_modeling_age"}.get(name, "hm_" + name)


def has_control(obj, name):
    """Le personnage porte-t-il cette commande (sexe, âge, ou l'un des 48 contrôles) ?"""
    if is_native(obj):
        return name in sockets()
    keys = obj.data.shape_keys
    if keys is None:
        return False
    if name == "sex":
        return "Morphologie" in keys.key_blocks
    return _legacy_name(name) in keys


def get_value(obj, name, default=0.0):
    if is_native(obj):
        if name not in sockets():
            return default
        require_modifier(obj)
        return float(getattr(obj.humanloom, name))
    keys = obj.data.shape_keys
    if name == "sex":
        return float(keys.key_blocks["Morphologie"].value)
    return float(keys.get(_legacy_name(name), default))


def set_value(obj, name, value):
    if is_native(obj):
        require_modifier(obj)
        setattr(obj.humanloom, name, float(value))
        return
    keys = obj.data.shape_keys
    if name == "sex":
        keys.key_blocks["Morphologie"].value = float(value)
    else:
        keys[_legacy_name(name)] = float(value)
    keys.update_tag()


def native_path(name):
    """Chemin de données natif d'une commande : l'entrée du modificateur (existe SANS l'extension, contrairement au chemin de la façade `humanloom.<nom>`)."""
    return f'modifiers["{MODIFIER_NAME}"].properties.inputs.{sockets()[name][0]}.value'


def _facade_actions(obj):
    """(action, fente) de l'action active et des bandes NLA de l'objet."""
    animation = obj.animation_data
    if animation is None:
        return
    if animation.action is not None:
        yield animation.action, animation.action_slot
    for track in animation.nla_tracks:
        for strip in track.strips:
            if strip.action is not None:
                yield strip.action, strip.action_slot


def bake_facade_animation(obj):
    """Convertit les courbes et drivers dont le chemin passe par la façade (`humanloom.<nom>`) en chemins natifs des entrées du modificateur, pour que l'animation reste lisible sans l'extension (INT-003).
    Ne crée jamais de doublon : si une courbe native existe déjà pour la même entrée, la courbe de façade est signalée (« conflits ») et laissée telle quelle. Retourne {converted, conflits, drivers}."""
    from bpy_extras.anim_utils import action_get_channelbag_for_slot
    report = {"converted": 0, "conflits": [], "drivers": 0}
    if not is_native(obj):
        return report
    prefix = "humanloom."
    mapping = {prefix + name: native_path(name) for name in sockets()}
    seen = set()
    for action, slot in _facade_actions(obj):
        if (action.as_pointer(), slot.handle if slot is not None else None) in seen:
            continue
        seen.add((action.as_pointer(), slot.handle if slot is not None else None))
        bag = action_get_channelbag_for_slot(action, slot)
        if bag is None:
            continue
        existing = {(c.data_path, c.array_index) for c in bag.fcurves}
        for curve in list(bag.fcurves):
            target = mapping.get(curve.data_path)
            if target is None:
                continue
            if (target, curve.array_index) in existing:
                report["conflits"].append(curve.data_path)
                continue
            existing.discard((curve.data_path, curve.array_index))
            curve.data_path = target
            existing.add((target, curve.array_index))
            report["converted"] += 1
    animation = obj.animation_data
    if animation is not None:
        for driver in animation.drivers:
            target = mapping.get(driver.data_path)
            if target is not None and not any(d.data_path == target and d.array_index == driver.array_index for d in animation.drivers):
                driver.data_path = target
                report["drivers"] += 1
    obj.update_tag()
    return report


def touch(obj):
    """Force la réévaluation après un réglage fait par script."""
    obj.update_tag()
    if not is_native(obj) and obj.data.shape_keys is not None:
        obj.data.shape_keys.update_tag()


def is_editable(obj):
    if is_native(obj):
        return obj.is_editable and obj.data.is_editable and modifier_of(obj) is not None
    return obj.is_editable and obj.data.shape_keys is not None and obj.data.shape_keys.is_editable


def draw_control(layout, obj, name, text, slider=True):
    """Dessine un curseur de commande, pour les deux moteurs (même code d'interface)."""
    if is_native(obj):
        layout.prop(obj.humanloom, name, text=text, slider=slider)
    elif name == "sex":
        layout.prop(obj.data.shape_keys.key_blocks["Morphologie"], "value", text=text, slider=slider)
    else:
        layout.prop(obj.data.shape_keys, f'["{_legacy_name(name)}"]', text=text, slider=slider)


def base_coordinates(obj):
    """Sommets de la forme neutre (Basis pour l'ancien moteur ; maillage de base du groupe pour un humain natif)."""
    import numpy as np
    if is_native(obj):
        values = np.empty(len(obj.data.vertices) * 3)
        obj.data.vertices.foreach_get("co", values)
    else:
        vertices = obj.data.shape_keys.key_blocks[0].data
        values = np.empty(len(vertices) * 3)
        vertices.foreach_get("co", values)
    return values.reshape((-1, 3))


def _getter(name):
    def get(self):
        obj = self.id_data
        modifier = modifier_of(obj)
        if modifier is None:
            return 0.0
        return float(getattr(modifier.properties.inputs, sockets()[name][0]).value)
    return get


def _setter(name):
    def set_value(self, value):
        modifier = require_modifier(self.id_data)  # lève HumanStateError : pas d'écriture muette
        getattr(modifier.properties.inputs, sockets()[name][0]).value = float(value)
        self.id_data.update_tag()
    return set_value


def _new_uuid(self=None):
    return str(uuid_module.uuid4())


class HumanLoomProperties(bpy.types.PropertyGroup):
    is_human: bpy.props.BoolProperty(name="Est un humain", default=False)
    uuid: bpy.props.StringProperty(name="Identifiant", default="")
    schema_version: bpy.props.IntProperty(name="Schéma", default=0)
    generator_version: bpy.props.IntProperty(name="Version du générateur", default=0)
    eye_left: bpy.props.PointerProperty(name="Œil gauche", type=bpy.types.Object)
    eye_right: bpy.props.PointerProperty(name="Œil droit", type=bpy.types.Object)


def _facade_names():
    """Noms des paramètres : lus dans le groupe livré au moment de l'enregistrement."""
    return list(sockets().keys())


def build_facade():
    """Ajoute une propriété flottante par entrée du groupe (sex, age, 48 contrôles) à la façade."""
    for name, (_, default, low, high) in sockets().items():
        HumanLoomProperties.__annotations__[name] = bpy.props.FloatProperty(
            name=name, default=default, min=low, max=high, get=_getter(name), set=_setter(name), options={"ANIMATABLE"})


def load_nodes():
    with bpy.data.libraries.load(str(NODES_PATH), link=False) as (_, target):
        target.node_groups = [GROUP_NAME]
        target.meshes = [MESH_NAME]
    group, mesh = target.node_groups[0], target.meshes[0]
    return group, mesh


def _retarget_eye_drivers(eye, body):
    """Les pilotes des yeux lisaient les clés du corps ; ils lisent maintenant les entrées du modificateur."""
    names = sockets()
    keys = eye.data.shape_keys
    if keys is None or keys.animation_data is None:
        return 0
    count = 0
    for fcurve in keys.animation_data.drivers:
        owner = None
        for variable in fcurve.driver.variables:
            target = variable.targets[0]
            path = target.data_path
            match = re.search(r'hm_([a-z_]+)', path)
            if match:
                name = MERGED_IN_SCHEMA_10.get(match.group(1), match.group(1))
            elif "human_modeling_age" in path:
                name = "age"
            elif "Morphologie" in path:
                name = "sex"
            else:
                raise ValueError(f"Variable de pilote d'œil non reconnue : {path}")
            target.id_type = "OBJECT"
            target.id = body
            target.data_path = f'modifiers["{MODIFIER_NAME}"].properties.inputs.{names[name][0]}.value'
            count += 1
            if variable.name in ("amount", "local"):
                owner = name
        if owner in AMPLITUDE_FACTORS:
            _amplify_eye_key(fcurve, keys, owner, body, names)
    return count


def _amplify_eye_key(fcurve, keys, control, body, names):
    """Le crâne est amplifié par le groupe de nœuds (lot 4) : l'œil reçoit le même facteur d'âge, sinon il ne suit plus son orbite."""
    factors = AMPLITUDE_FACTORS[control]
    driver = fcurve.driver
    age_path = f".{names['age'][0]}.value"
    age_name = next((v.name for v in driver.variables if v.targets[0].data_path.endswith(age_path)), None)
    if age_name is None:
        variable = driver.variables.new()
        variable.name = age_name = "hl_age"
        variable.type = "SINGLE_PROP"
        variable.targets[0].id_type = "OBJECT"
        variable.targets[0].id = body
        variable.targets[0].data_path = f'modifiers["{MODIFIER_NAME}"].properties.inputs{age_path}'
    factor = "+".join(f"{value}*max(0,1-abs({age_name}-{stage}))" for stage, value in enumerate(factors))
    driver.expression = f"({driver.expression})*({factor})"
    key = keys.key_blocks[fcurve.data_path.split('"')[1]]
    top = float(max(factors))
    if key.slider_min < 0:
        key.slider_min *= top
    key.slider_max = max(key.slider_max, 1.0) * top


_TRACKED = ("objects", "meshes", "shape_keys", "node_groups", "materials", "textures", "images", "actions", "armatures", "curves")  # ordre de retrait (les objets d'abord)


def _inventory():
    return {name: {item.session_uid for item in getattr(bpy.data, name)} for name in _TRACKED}


def _rollback(before):
    """Retire uniquement les blocs créés depuis `before` (jamais de purge globale) : une création échouée ne laisse aucun reste."""
    for name in _TRACKED:
        collection = getattr(bpy.data, name)
        for item in [i for i in collection if i.session_uid not in before[name]]:
            try:
                if name == "objects":
                    collection.remove(item, do_unlink=True)
                else:
                    collection.remove(item)
            except (ReferenceError, RuntimeError, ValueError):  # déjà retiré avec son propriétaire
                pass


def _preflight():
    """Vérifie les ressources AVANT de toucher à `bpy.data` : fichiers présents et blocs attendus listés dedans."""
    for path, kind, names in ((NODES_PATH, "node_groups", [GROUP_NAME]), (NODES_PATH, "meshes", [MESH_NAME]), (EYES_PATH, "objects", list(_EYE_OBJECTS))):
        if not Path(path).is_file():
            raise OSError(f"Ressource manquante : {path}")
        with bpy.data.libraries.load(str(path), link=False) as (source, _):
            missing = [n for n in names if n not in getattr(source, kind)]
        if missing:
            raise KeyError(f"{Path(path).name} ne contient pas {missing}")
    sockets()


_EYE_OBJECTS = ("HL Relief Source", "Œil gauche", "Œil droit")


def create_human(context, location=None):
    """Crée un humain natif complet (corps, deux yeux, relief de peau) ou n'en crée aucun : en cas d'échec les blocs créés sont retirés et l'erreur est relancée. Le marqueur `is_human` n'est publié qu'à la fin."""
    _preflight()
    before = _inventory()
    try:
        return _build_human(context, location)
    except Exception:
        _rollback(before)
        mark_objects_current()
        raise


def _build_human(context, location):
    group, mesh = load_nodes()
    body = bpy.data.objects.new("Humain", mesh)
    collection = context.collection
    collection.objects.link(body)
    modifier = body.modifiers.new(MODIFIER_NAME, "NODES")
    modifier.node_group = group
    for name, (identifier, default, _, _) in sockets().items():
        getattr(modifier.properties.inputs, identifier).value = default
    surface = body.modifiers.new("Human Modeling · Surface", "SUBSURF")
    surface.levels, surface.render_levels = 1, 2
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    properties = body.humanloom
    with bpy.data.libraries.load(str(EYES_PATH), link=False) as (_, target):
        target.objects = list(_EYE_OBJECTS)
    source, *eyes = target.objects
    for attribute, eye in zip(("eye_left", "eye_right"), eyes):
        collection.objects.link(eye)
        eye.parent = body
        _retarget_eye_drivers(eye, body)
        setattr(properties, attribute, eye)
    from . import skin_relief
    skin_relief.attach_native(body, source)  # groupe de sommets + Displace piloté par les entrées du modificateur
    source_mesh = source.data
    bpy.data.objects.remove(source)
    bpy.data.meshes.remove(source_mesh)  # retire aussi ses clés de forme (bloc Key) devenues orphelines
    for stale in ("human_modeling_schema",):  # le schéma d'un humain natif est `humanloom.schema_version`
        if stale in mesh:
            del mesh[stale]
    if location is not None:
        body.location = location
    properties.uuid = _new_uuid()
    properties.schema_version = SCHEMA_VERSION
    properties.generator_version = GENERATOR_VERSION
    properties.is_human = True  # publié en dernier : corps + yeux + relief entièrement construits
    return body


def duplicate_human(context, body, share_mesh=False, *, select=False):
    """Copie un personnage. Le partage du Mesh est réservé au template de foule."""
    from .human_duplicate import duplicate

    global _duplicating
    _duplicating += 1
    try:
        return duplicate(context, body, share_mesh, select)
    finally:
        mark_objects_current()
        _duplicating -= 1


class HUMANLOOM_OT_create(bpy.types.Operator):
    bl_idname = "humanloom.create"
    bl_label = "Créer un humain (schéma 10)"
    bl_description = "Ajoute un humain natif piloté par le groupe de nœuds « HL Human »"
    bl_options = {"REGISTER", "UNDO"}

    sex: bpy.props.FloatProperty(name="Morphologie", default=0.5, min=0.0, max=1.0, options={"SKIP_SAVE"})
    age: bpy.props.FloatProperty(name="Âge", default=2.0, min=0.0, max=3.0, options={"SKIP_SAVE"})

    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT"

    def execute(self, context):
        try:
            body = create_human(context, context.scene.cursor.location)
        except Exception as error:  # noqa: BLE001 : toute panne est rapportée, le rollback a déjà nettoyé
            self.report({"ERROR"}, f"Impossible de créer l'humain ({error}).")
            return {"CANCELLED"}
        body.humanloom.sex = self.sex
        body.humanloom.age = self.age
        for obj in tuple(context.selected_objects):
            obj.select_set(False)
        body.select_set(True)
        context.view_layer.objects.active = body
        return {"FINISHED"}


class HUMANLOOM_OT_repair_modifier(bpy.types.Operator):
    """Remet le nom « HL Human » au modificateur pilote renommé (les pilotes des yeux et du relief le désignent par son nom)."""
    bl_idname = "humanloom.repair_modifier"
    bl_label = "Réparer le modificateur pilote"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return is_native(context.object) and modifier_status(context.object)[0] == "renamed"

    def execute(self, context):
        try:
            repair_modifier(context.object)
        except HumanStateError as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        return {"FINISHED"}


class HUMANLOOM_OT_assign_uuid(bpy.types.Operator):
    """Donne un nouvel identifiant à un humain dupliqué (copie d'objet : l'UUID est copié, il doit être unique)."""
    bl_idname = "humanloom.renew_uuid"
    bl_label = "Renouveler l'identifiant"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.object.humanloom.is_human

    def execute(self, context):
        context.object.humanloom.uuid = _new_uuid()
        return {"FINISHED"}


class HUMANLOOM_OT_duplicate(bpy.types.Operator):
    bl_idname = "humanloom.duplicate"
    bl_label = "Dupliquer le personnage"
    bl_description = "Copie le corps, les yeux, les repères et les cheveux en un personnage indépendant avec un nouvel identifiant"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return is_native(body_of(context.object))

    def execute(self, context):
        try:
            duplicate_human(context, body_of(context.object), select=True)
        except (AttributeError, ReferenceError, RuntimeError, TypeError, ValueError) as error:
            self.report({'WARNING'}, f'Duplication annulée : {error}')
            return {'CANCELLED'}
        return {"FINISHED"}


def ensure_unique_uuid(scene=None, depsgraph=None):
    """Après une duplication, deux objets portent le même UUID : le second reçoit un nouvel identifiant."""
    seen = set()
    for obj in bpy.data.objects:
        properties = getattr(obj, "humanloom", None)
        if properties is None or not properties.is_human:
            continue
        if properties.uuid in seen or not properties.uuid:
            properties.uuid = _new_uuid()
        seen.add(properties.uuid)


_count = [0]
_signature = [0]  # INT-002 : empreinte des objets (xor des session_uid) : un REMPLACEMENT d'objet à nombre constant (supprimer + copier) est détecté, ce que le seul nombre d'objets manquait
_duplicating = 0


def _objects_signature():
    value = 0
    for obj in bpy.data.objects:
        value ^= obj.session_uid
    return value


def mark_objects_current():
    """Enregistre l'état courant des objets comme « déjà traité » (appelé après les opérations internes qui créent ou retirent des objets : foule, duplication)."""
    _count[0] = len(bpy.data.objects)
    _signature[0] = _objects_signature()


@bpy.app.handlers.persistent
def _on_depsgraph(scene, depsgraph=None):
    """Détecte une duplication (le nombre d'objets change) et rend les UUID uniques."""
    if not _duplicating:
        signature = _objects_signature()
        if len(bpy.data.objects) != _count[0] or signature != _signature[0]:
            _count[0], _signature[0] = len(bpy.data.objects), signature
            ensure_unique_uuid()


class HUMANLOOM_OT_facade_animation_to_native(bpy.types.Operator):
    """Convertit l'animation des réglages (chemins de la façade `humanloom.*`) en chemins natifs du modificateur : elle reste lisible si l'extension est désactivée ou absente."""
    bl_idname = "humanloom.facade_animation_to_native"
    bl_label = "Rendre l'animation indépendante de l'extension"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return is_native(context.object) and context.object.animation_data is not None

    def execute(self, context):
        report = bake_facade_animation(context.object)
        if report["conflits"]:
            self.report({"WARNING"}, f"{report['converted']} courbes converties ; conflit (courbe native existante) : {', '.join(report['conflits'][:3])}")
        else:
            self.report({"INFO"}, f"{report['converted']} courbes et {report['drivers']} pilotes convertis.")
        return {"FINISHED"}


CLASSES = (HumanLoomProperties, HUMANLOOM_OT_create, HUMANLOOM_OT_repair_modifier, HUMANLOOM_OT_facade_animation_to_native, HUMANLOOM_OT_assign_uuid, HUMANLOOM_OT_duplicate)


def register():
    build_facade()
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Object.humanloom = bpy.props.PointerProperty(type=HumanLoomProperties)
    if _on_depsgraph not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(_on_depsgraph)


def unregister():
    if _on_depsgraph in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(_on_depsgraph)
    del bpy.types.Object.humanloom
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
