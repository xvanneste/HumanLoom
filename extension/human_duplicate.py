"""Copie d'un personnage et remappage limité aux IDs alloués par l'opération."""

from collections import defaultdict

import bpy
from idprop.types import IDPropertyGroup

from . import cloth_sim, crowd, garments, human, skin_mask


PRIVATE_ACTION_KEY = 'hl_character_private_action'


class DuplicateError(ValueError):
    """Personnage ou dépendance hors du périmètre de copie."""


class DuplicateRollbackError(RuntimeError):
    """Les effets de l'échec ne peuvent pas tous être annulés."""


def _objects(body):
    result = [body]
    for obj in result:
        result.extend(child for child in obj.children if not human.is_body(child))
    return result


def _local(resource):
    return resource is not None and resource.library is None and resource.override_library is None


def _mask_resources(body):
    inventory = skin_mask._mask_inventory(body)
    bindings = body.get(skin_mask.BINDINGS_KEY, {})
    masked_slots = {entry.get('masked') for entry in bindings.values()}
    for slot in body.material_slots:
        material = slot.material
        if slot.link == 'OBJECT' and material in masked_slots and _local(material) and material.get(skin_mask.OWNER_KEY):
            yield material
    for kind in (skin_mask.RENDER_KIND, skin_mask.GEOMETRY_KIND):
        for modifier in inventory[kind]:
            group = modifier.node_group
            if not _local(group):
                continue
            yield group
            for node in group.nodes:
                if node.bl_idname == 'GeometryNodeImageTexture':
                    resource = node.inputs['Image'].default_value
                elif node.bl_idname == 'GeometryNodeSetMaterial':
                    resource = node.inputs['Material'].default_value
                else:
                    continue
                if _local(resource) and resource.get(skin_mask.OWNER_KEY):
                    yield resource


def _material_resources(objects):
    data_materials = set()
    overrides = set()
    for obj in objects:
        if obj.get(garments.MARKER):
            marker = garments.MATERIAL_OWNER
        elif obj.type == 'CURVES' and obj.get('hl_groom_region'):
            marker = 'hl_owned'
        else:
            continue
        data_materials.update(material for material in getattr(obj.data, 'materials', ())
                              if _local(material) and material.get(marker))
        overrides.update(slot.material for slot in obj.material_slots if slot.link == 'OBJECT'
                         and _local(slot.material) and slot.material.get(marker))

    # Un matériau marqué peut être emprunté comme surcharge à un autre objet.
    # Les liaisons DATA de la pièce restent visibles ici, même sous la surcharge.
    if overrides:
        owned = set(objects)
        for obj in bpy.data.objects:
            if obj not in owned:
                overrides.difference_update(getattr(obj.data, 'materials', ()))
                overrides.difference_update(slot.material for slot in obj.material_slots if slot.link == 'OBJECT')
                if not overrides:
                    break
    return data_materials | overrides


def _attached_resources(body, objects, detach_crowd):
    """Les marqueurs attestent une ressource seulement à une attache métier reconnue."""
    yield from _mask_resources(body)
    yield from _material_resources(objects)
    external_actions = {action for obj in objects for action in obj.get(crowd.LIBRARY_CLIPS_KEY, {}).values()}
    external_actions.update(action for obj in objects for action in crowd._clip_history(obj))
    for obj in objects:
        is_groom = obj.type == 'CURVES' and obj.get('hl_groom_region')
        if is_groom:
            for modifier in obj.modifiers:
                if modifier.type == 'NODES' and _local(modifier.node_group) and modifier.node_group.get('hl_owned'):
                    yield modifier.node_group
        animation = obj.animation_data
        if animation is None:
            continue
        for slot_owner in _animation_slots(animation):
            action = slot_owner.action
            if not _local(action) or action in external_actions:
                continue
            owner = action.get(PRIVATE_ACTION_KEY)
            if owner == body.humanloom.uuid or (owner is None and detach_crowd and action.get(crowd.OWNED_KEY)):
                yield action


def _dependencies(users):
    dependencies = defaultdict(set)
    for target, owners in users.items():
        for owner in owners:
            dependencies[owner].add(target)
    return dependencies


def _embedded(resource):
    if isinstance(resource, bpy.types.Material):
        return resource.node_tree
    return getattr(resource, 'shape_keys', None)


def _nodes_properties(modifier):
    if modifier.type != 'NODES' or modifier.node_group is None:
        return
    for item in modifier.node_group.interface.items_tree:
        if item.item_type == 'SOCKET' and item.in_out == 'INPUT':
            owner = getattr(modifier.properties.inputs, item.identifier, None)
            if owner is not None:
                yield owner


def _gn_mode(modifier):
    for item in modifier.node_group.interface.items_tree:
        if item.item_type == 'SOCKET' and item.in_out == 'INPUT' and item.name == 'Mode':
            value = getattr(modifier.properties.inputs, item.identifier, None)
            return getattr(value, 'value', None)
    return None


def _guard_simulation(objects):
    colliders = bpy.data.collections.get(cloth_sim.COLLECTION)
    for obj in objects:
        if colliders is not None and colliders.all_objects.get(obj.name) == obj:
            raise DuplicateError(f'{obj.name} appartient à la collection de collision {colliders.name}.')
        if obj.get('hl_cloth') or obj.get(cloth_sim.BAKE_KEY) or skin_mask._cloth_nodes(obj):
            raise DuplicateError(f'{obj.name} possède une simulation de tissu active ou un cache.')
        if obj.particle_systems or obj.rigid_body or obj.rigid_body_constraint:
            raise DuplicateError(f'{obj.name} possède une simulation physique à isoler avant la copie.')
        for modifier in obj.modifiers:
            cache = getattr(modifier, 'point_cache', None)
            if cache is not None or modifier.type in {'FLUID', 'DYNAMIC_PAINT', 'PARTICLE_SYSTEM'}:
                raise DuplicateError(f'{obj.name} possède une simulation ou un cache ({modifier.name}).')
            if modifier.type == 'SURFACE_DEFORM' and modifier.is_bound and modifier.target in objects:
                raise DuplicateError(f'{obj.name} est lié à une surface interne ({modifier.name}). Déliez la pièce avant sa copie.')
            if modifier.type == 'NODES' and modifier.bakes:
                passive_groom = (obj.get('hl_groom_region') and modifier.name == 'HumanLoom · suivi 5.2'
                                 and modifier.node_group is not None and _gn_mode(modifier) == 'Animation'
                                 and all(not bake.directory for bake in modifier.bakes))
                if not passive_groom:
                    raise DuplicateError(f'{obj.name} contient une zone Geometry Nodes simulée ou mise en cache ({modifier.name}).')

    # Une pièce hors de la hiérarchie peut utiliser ce personnage comme collider.
    # Le socket identifie la collection réelle, même après renommage.
    for garment in bpy.data.objects:
        if skin_mask._cloth_nodes(garment) is None:
            continue
        for modifier in garment.modifiers:
            if modifier.type != 'NODES' or modifier.node_group is None:
                continue
            for socket in modifier.node_group.interface.items_tree:
                if socket.item_type != 'SOCKET' or socket.in_out != 'INPUT' or socket.name != 'Effectors Collection':
                    continue
                input_value = getattr(modifier.properties.inputs, socket.identifier, None)
                collection = getattr(input_value, 'value', None)
                if isinstance(collection, bpy.types.Collection) and any(
                        collection.all_objects.get(obj.name) == obj for obj in objects):
                    raise DuplicateError(f'Une simulation de {garment.name} utilise la collection de collision {collection.name}.')


def _guard_expression(resource):
    animation = getattr(resource, 'animation_data', None)
    if animation is None:
        return
    for curve in animation.drivers:
        driver = curve.driver
        if driver.type == 'SCRIPTED' and driver.expression and not driver.is_simple_expression:
            raise DuplicateError(f'{resource.name} possède un pilote Python dont les dépendances ne sont pas vérifiables : {curve.data_path}.')


def _idprops(owner):
    try:
        keys = owner.keys()
    except (AttributeError, TypeError):
        # Certaines structures RNA exposent keys() sans gérer les propriétés ID.
        return
    for key in keys:
        value = owner[key]
        if isinstance(value, IDPropertyGroup):
            yield from _idprops(value)
        elif isinstance(value, bpy.types.ID):
            yield owner, key, value


def _remap_values(owner, mapping, skip=()):
    for struct, key, value in _idprops(owner):
        if value in mapping:
            struct[key] = mapping[value]
    for prop in owner.bl_rna.properties:
        name = prop.identifier
        if prop.type != 'POINTER' or prop.is_readonly or name in skip:
            continue
        value = getattr(owner, name)
        if isinstance(value, bpy.types.ID) and value in mapping:
            setattr(owner, name, mapping[value])
            if getattr(owner, name) != mapping[value]:
                raise DuplicateError(f'Blender n’a pas accepté la cible de {owner.bl_rna.identifier}.{name}.')


def _remap_constraint(constraint, mapping):
    _remap_values(constraint, mapping)
    for target in getattr(constraint, 'targets', ()):
        _remap_values(target, mapping)


def _remap_object(original, clone, mapping):
    clone.parent = mapping.get(original.parent, original.parent)
    clone.parent_type = original.parent_type
    clone.parent_bone = original.parent_bone
    clone.matrix_parent_inverse = original.matrix_parent_inverse
    if human.is_native(clone):
        _remap_values(clone.humanloom, mapping)
    for constraint in clone.constraints:
        _remap_constraint(constraint, mapping)
    if clone.pose is not None:
        for bone in clone.pose.bones:
            _remap_values(bone, mapping)
            for constraint in bone.constraints:
                _remap_constraint(constraint, mapping)
    for modifier in clone.modifiers:
        _remap_values(modifier, mapping)
        for owner in _nodes_properties(modifier):
            _remap_values(owner, mapping)
        if modifier.type == 'UV_PROJECT':
            for projector in modifier.projectors:
                _remap_values(projector, mapping)
    for slot in clone.material_slots:
        if slot.link == 'OBJECT' and slot.material in mapping:
            slot.material = mapping[slot.material]


def _animation_slots(animation):
    yield animation
    pending = [strip for track in animation.nla_tracks for strip in track.strips]
    for strip in pending:
        yield strip
        pending.extend(getattr(strip, 'strips', ()))


def _remap_animation(original, clone, mapping):
    if getattr(clone, 'animation_data', None) is None:
        return
    for curve in clone.animation_data.drivers:
        for variable in curve.driver.variables:
            for target in variable.targets:
                if target.id in mapping:
                    target.id = mapping[target.id]
    sources = _animation_slots(original.animation_data)
    for source, target in zip(sources, _animation_slots(clone.animation_data), strict=True):
        action = source.action
        if action is None:
            continue
        destination = mapping.get(action, action)
        source_slot = source.action_slot
        handle = source_slot.handle if source_slot else None
        if target.action != destination:
            target.action = destination
        if handle is not None:
            slot = next((slot for slot in destination.slots if slot.handle == handle), None)
            if slot is None:
                raise DuplicateError(f'Slot {handle} absent dans l’action {destination.name}.')
            if target.action_slot != slot:
                target.action_slot = slot
        elif target.action_slot is not None:
            target.action_slot = None
        if target.action != destination or target.action_slot != (slot if handle is not None else None):
            raise DuplicateError(f'Blender n’a pas conservé le slot d’animation de {original.name}.')


def _remap_id(original, clone, mapping):
    if isinstance(clone, bpy.types.Object):
        _remap_values(clone, mapping, {'parent', 'data', 'active_material'})
        _remap_object(original, clone, mapping)
    else:
        _remap_values(clone, mapping)
    if isinstance(clone, bpy.types.Armature):
        for bone in clone.bones:
            _remap_values(bone, mapping)
    if isinstance(clone, bpy.types.NodeTree):
        for item in clone.interface.items_tree:
            _remap_values(item, mapping)
        for node in clone.nodes:
            _remap_values(node, mapping)
            for socket in (*node.inputs, *node.outputs):
                _remap_values(socket, mapping)
    if not isinstance(clone, bpy.types.Object):
        materials = getattr(clone, 'materials', ())
        for index, material in enumerate(materials):
            if material in mapping:
                materials[index] = mapping[material]
    _remap_animation(original, clone, mapping)


def _borrowed_dependencies(dependencies, owned):
    borrowed = {target for owner in owned for target in dependencies[owner] if target not in owned}
    pending = list(borrowed)
    for resource in pending:
        # Les relations d'un objet extérieur restent sous le contrôle de cet objet.
        if isinstance(resource, (bpy.types.Object, bpy.types.Library)):
            continue
        for target in dependencies[resource]:
            if target in owned:
                raise DuplicateError(f'La ressource partagée {resource.name} référence {target.name} dans le personnage.')
            if target not in borrowed:
                borrowed.add(target)
                pending.append(target)
    return borrowed


def _collections(context, objects, detach_crowd):
    destinations = {}
    available = {context.scene.collection, *context.scene.collection.children_recursive}
    for obj in objects:
        links = tuple(c for c in obj.users_collection if not detach_crowd or not crowd._is_crowd_collection(c))
        if not links or (detach_crowd and not available.intersection(links)):
            fallback = context.collection
            if detach_crowd and crowd._is_crowd_collection(fallback):
                fallback = context.scene.collection
            links = (*links, fallback)
        if any(not c.is_editable for c in links):
            raise DuplicateError(f'Une collection de {obj.name} est liée et ne peut pas recevoir la copie.')
        destinations[obj] = links
    return destinations


class _Duplicate:
    def __init__(self, context, body, share_mesh):
        if context.mode != 'OBJECT' or not human.is_native(body):
            raise DuplicateError('Sélectionnez un personnage HumanLoom en mode Objet.')
        self.context = context
        self.body = body
        self.share_mesh = share_mesh
        self.mapping = {}
        self.allocated = []
        self.links = []
        self.selection = None
        self.objects = _objects(body)
        self.detach_crowd = not share_mesh and body.get(crowd.OBJECT_KEY) is not None
        self.destinations = _collections(context, self.objects, self.detach_crowd)

    def plan(self):
        if self.share_mesh and (len(self.objects) != 3 or self.body.get(crowd.OBJECT_KEY) is not None
                                or set(self.objects[1:]) != {self.body.humanloom.eye_left, self.body.humanloom.eye_right}):
            raise DuplicateError('Le maillage partagé est réservé au template de foule avec ses deux yeux.')
        if any(obj.library is not None or obj.override_library is not None for obj in self.objects):
            raise DuplicateError('Une partie du personnage est liée à une bibliothèque ou possède une surcharge.')
        _guard_simulation(self.objects)
        root_data = self.body.data
        data = {obj.data for obj in self.objects if obj.data is not None}
        if self.share_mesh:
            data.remove(root_data)
            if any(obj.data == root_data for obj in self.objects[1:]):
                raise DuplicateError('Un enfant utilise déjà le maillage partagé du corps.')
        attached = set(_attached_resources(self.body, self.objects, self.detach_crowd))
        self.sources = [*self.objects, *sorted(data | attached, key=lambda item: item.name_full)]
        owned = set(self.sources)
        owned.update(embedded for resource in self.sources if (embedded := _embedded(resource)) is not None)
        deps = _dependencies(bpy.data.user_map())
        _borrowed_dependencies(deps, owned)
        self.dependencies = {resource: deps[resource] for resource in owned}
        for resource in owned:
            _guard_expression(resource)

    def allocate(self):
        for source in self.sources:
            clone = source.copy()
            self.allocated.append(clone)
            self.mapping[source] = clone
            clone.use_fake_user = False
            if isinstance(clone, bpy.types.Action):
                clone[PRIVATE_ACTION_KEY] = self.mapping[self.body].humanloom.uuid
            embedded = _embedded(source)
            if embedded is not None:
                embedded_clone = _embedded(clone)
                if embedded_clone is None or embedded_clone == embedded:
                    raise DuplicateError(f'Impossible d’isoler les données intégrées de {source.name}.')
                self.mapping[embedded] = embedded_clone
                if not embedded_clone.is_embedded_data:
                    self.allocated.append(embedded_clone)
            if isinstance(source, bpy.types.Object) and human.is_native(source):
                clone.humanloom.uuid = human._new_uuid()

    def remap(self):
        for source in self.objects:
            self.mapping[source].data = self.mapping.get(source.data, source.data)
        for source, clone in self.mapping.items():
            _remap_id(source, clone, self.mapping)

    def _detach_crowd(self):
        for clone in self.allocated:
            for key in (crowd.OBJECT_KEY, crowd.OWNED_KEY, crowd.CLIP_ANCHOR_KEY):
                if key in clone:
                    del clone[key]

    def validate(self):
        deps = _dependencies(bpy.data.user_map())
        for source, clone in self.mapping.items():
            expected = {self.mapping.get(target, target) for target in self.dependencies[source]}
            difference = deps[clone].symmetric_difference(expected)
            if difference:
                targets = ', '.join(sorted(item.name for item in difference))
                raise DuplicateError(f'Liens de {source.name} non conservés ou non remappés : {targets}.')

    def publish(self, select):
        for source, destinations in self.destinations.items():
            clone = self.mapping[source]
            for collection in destinations:
                self.links.append((collection, clone))
                collection.objects.link(clone)
        clone = self.mapping[self.body]
        if select:
            layer = self.context.view_layer
            self.selection = (layer.objects.active, tuple(self.context.selected_objects))
            layer.update()
            for obj in self.selection[1]:
                obj.select_set(False, view_layer=layer)
            clone.select_set(True, view_layer=layer)
            layer.objects.active = clone
            if layer.objects.active != clone or not clone.select_get(view_layer=layer):
                raise DuplicateError('La copie n’est pas sélectionnable dans ce calque de vue.')
        return clone

    def _unlink(self):
        for collection, clone in reversed(self.links):
            if collection.objects.get(clone.name) == clone:
                collection.objects.unlink(clone)

    def _remove(self):
        allocated = set(self.allocated)
        users = bpy.data.user_map()
        removable = allocated.copy()
        for resource in removable.copy():
            if users.get(resource, set()) - allocated:
                removable.remove(resource)
        while True:
            held = {resource for resource in removable if users.get(resource, set()) - removable}
            if not held:
                break
            removable.difference_update(held)
        if removable:
            bpy.data.batch_remove(ids=removable)
        if allocated - removable:
            names = ', '.join(sorted(resource.name for resource in allocated - removable))
            raise DuplicateRollbackError(f'Allocations conservées car un autre ID les utilise : {names}.')

    def _restore_selection(self):
        if self.selection is None:
            return
        active, selected = self.selection
        layer = self.context.view_layer
        layer.objects.active = active
        layer.update()
        for obj in set(self.context.selected_objects).union(selected):
            if layer.objects.get(obj.name) == obj:
                obj.select_set(obj in selected, view_layer=layer)
        layer.objects.active = active

    def execute(self, select):
        self.plan()
        try:
            self.allocate()
            self.remap()
            self.validate()
            if self.detach_crowd:
                self._detach_crowd()
            return self.publish(select)
        except Exception as error:
            failures = []
            for restore in (self._unlink, self._restore_selection, self._remove):
                try:
                    restore()
                except Exception as rollback_error:
                    failures.append(str(rollback_error))
            if failures:
                raise DuplicateRollbackError(f'{error}. Restauration incomplète : {" / ".join(failures)}') from error
            raise


def duplicate(context, body, share_mesh, select):
    return _Duplicate(context, body, share_mesh).execute(select)
