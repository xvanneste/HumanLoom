"""Schéma 10 (lot 2) : humain natif piloté par le groupe de nœuds « HL Human ».

Ajouté À CÔTÉ de l'ancien moteur (clés de forme + pilotes) : rien n'est modifié ni retiré dans les autres modules.
Un humain schéma 10 est un objet MESH ordinaire portant `Object.humanloom` (façade D, D-07) ; ses paramètres sont les
entrées du modificateur « HL Human », jamais des clés de forme.
"""

from pathlib import Path
import re
import uuid as uuid_module

import bpy

NODES_PATH = Path(__file__).parent / "data" / "human_nodes.blend"
ASSET_PATH = Path(__file__).parent / "data" / "realistic.blend"
GROUP_NAME = "HL Human"
MESH_NAME = "HL Human Base"
MODIFIER_NAME = "HL Human"
SCHEMA_VERSION = 10
GENERATOR_VERSION = 1
FACADE_SKIP = {"Geometry"}

# Les entrées du groupe et leur identifiant de socket sont lus dans le groupe (jamais devinés).
_SOCKETS = {}


def sockets():
    """{nom: (identifiant de socket, défaut, min, max)} lu dans le groupe de nœuds livré."""
    if not _SOCKETS:
        with bpy.data.libraries.load(str(NODES_PATH), link=False) as (_, target):
            target.node_groups = [GROUP_NAME]
        group = target.node_groups[0]
        for item in group.interface.items_tree:
            if item.item_type == "SOCKET" and item.in_out == "INPUT" and item.socket_type == "NodeSocketFloat":
                _SOCKETS[item.name] = (item.identifier, item.default_value, item.min_value, item.max_value)
        bpy.data.node_groups.remove(group)
    return _SOCKETS


def modifier_of(obj):
    return obj.modifiers.get(MODIFIER_NAME) if obj is not None and obj.type == "MESH" else None


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
        for variable in fcurve.driver.variables:
            target = variable.targets[0]
            path = target.data_path
            match = re.search(r'hm_([a-z_]+)', path)
            if match:
                name = match.group(1)
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
    return count


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
    with bpy.data.libraries.load(str(ASSET_PATH), link=False) as (_, target):
        target.objects = ["Œil gauche", "Œil droit"]
    stray = [obj for obj in bpy.data.objects if obj.get("human_modeling_body") and obj is not body and obj.users == 0]
    for attribute, eye in zip(("eye_left", "eye_right"), target.objects):
        collection.objects.link(eye)
        eye.parent = body
        _retarget_eye_drivers(eye, body)
        setattr(properties, attribute, eye)
    for obj in stray:
        bpy.data.objects.remove(obj)
    if location is not None:
        body.location = location
    return body


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


CLASSES = (HumanLoomProperties, HUMANLOOM_OT_create, HUMANLOOM_OT_assign_uuid)


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
