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


def modifier_of(obj):
    return obj.modifiers.get(MODIFIER_NAME) if obj is not None and obj.type == "MESH" else None


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
        return float(getattr(obj.humanloom, name)) if name in sockets() else default
    keys = obj.data.shape_keys
    if name == "sex":
        return float(keys.key_blocks["Morphologie"].value)
    return float(keys.get(_legacy_name(name), default))


def set_value(obj, name, value):
    if is_native(obj):
        setattr(obj.humanloom, name, float(value))
        return
    keys = obj.data.shape_keys
    if name == "sex":
        keys.key_blocks["Morphologie"].value = float(value)
    else:
        keys[_legacy_name(name)] = float(value)
    keys.update_tag()


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
        modifier = modifier_of(self.id_data)
        if modifier is None:
            return
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


def create_human(context, location=None):
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
    properties.is_human = True
    properties.uuid = _new_uuid()
    properties.schema_version = SCHEMA_VERSION
    properties.generator_version = GENERATOR_VERSION
    with bpy.data.libraries.load(str(EYES_PATH), link=False) as (_, target):
        target.objects = ["HL Relief Source", "Œil gauche", "Œil droit"]
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
    return body


def _retarget_drivers(owner_id, old, new):
    """Les pilotes copiés lisent encore l'original : ils lisent maintenant la copie."""
    animation = getattr(owner_id, "animation_data", None)
    if animation is None:
        return
    for fcurve in animation.drivers:
        for variable in fcurve.driver.variables:
            for target in variable.targets:
                if target.id == old:
                    target.id = new


def duplicate_human(context, body):
    """Copie complète et indépendante : corps, yeux, repères, cheveux (données, groupes de nœuds et matériaux propres), nouvel UUID."""
    clone = body.copy()
    clone.data = body.data.copy()
    for collection in body.users_collection:
        collection.objects.link(clone)
    _retarget_drivers(clone, body, clone)
    mapping = {body: clone}
    queue = [(child, clone) for child in body.children]
    while queue:  # enfants du corps puis leurs propres enfants (yeux rattachés à l'os head du squelette)
        child, new_parent = queue.pop(0)
        copy = child.copy()
        if child.data is not None:
            copy.data = child.data.copy()
        for collection in child.users_collection:
            collection.objects.link(copy)
        copy.parent = new_parent
        copy.parent_type, copy.parent_bone = child.parent_type, child.parent_bone
        copy.matrix_parent_inverse = child.matrix_parent_inverse.copy()
        queue.extend((grandchild, copy) for grandchild in child.children)
        mapping[child] = copy
        if child.type == "MESH" and copy.data.shape_keys is not None:
            _retarget_drivers(copy.data.shape_keys, body, clone)
        if child.type == "CURVES":
            copy.data.surface = clone
            _unshare_groom(copy)
    for modifier in clone.modifiers:  # le squelette (enfant du corps) est copié avec lui : le modificateur de la copie vise le squelette de la copie
        if modifier.type == "ARMATURE" and modifier.object in mapping:
            modifier.object = mapping[modifier.object]
    properties = clone.humanloom
    properties.uuid = _new_uuid()
    for attribute in ("eye_left", "eye_right"):
        original_eye = getattr(body.humanloom, attribute)
        setattr(properties, attribute, mapping.get(original_eye))
    return clone


def _unshare_groom(hair):
    """Groupes de nœuds et matériaux créés par HumanLoom : propres à la copie (T-A8 : le matériau était partagé)."""
    materials = {}
    for index, material in enumerate(hair.data.materials):
        if material is not None and material.get("hl_owned"):
            materials[material] = material.copy()
            hair.data.materials[index] = materials[material]
    for modifier in hair.modifiers:
        if modifier.type == "NODES" and modifier.node_group is not None and modifier.node_group.get("hl_owned"):
            group = modifier.node_group.copy()
            for node in group.nodes:
                if node.bl_idname == "GeometryNodeSetMaterial" and node.inputs["Material"].default_value in materials:
                    node.inputs["Material"].default_value = materials[node.inputs["Material"].default_value]
            modifier.node_group = group


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
        except (OSError, RuntimeError, KeyError) as error:
            self.report({"ERROR"}, f"Impossible de créer l'humain ({error}).")
            return {"CANCELLED"}
        body.humanloom.sex = self.sex
        body.humanloom.age = self.age
        for obj in tuple(context.selected_objects):
            obj.select_set(False)
        body.select_set(True)
        context.view_layer.objects.active = body
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
        clone = duplicate_human(context, body_of(context.object))
        for obj in tuple(context.selected_objects):
            obj.select_set(False)
        clone.select_set(True)
        context.view_layer.objects.active = clone
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


@bpy.app.handlers.persistent
def _on_depsgraph(scene, depsgraph=None):
    """Détecte une duplication (le nombre d'objets change) et rend les UUID uniques."""
    if len(bpy.data.objects) != _count[0]:
        _count[0] = len(bpy.data.objects)
        ensure_unique_uuid()


CLASSES = (HumanLoomProperties, HUMANLOOM_OT_create, HUMANLOOM_OT_assign_uuid, HUMANLOOM_OT_duplicate)


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
