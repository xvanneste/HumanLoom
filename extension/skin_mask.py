"""Masquage de peau par personnage, indépendant des données du Mesh source."""

import json
import math

import bpy
import numpy as np

from . import human

OFF, RENDER, GEOMETRY, LEGACY = "OFF", "RENDER", "GEOMETRY", "LEGACY"
MODE_KEY = "hl_skin_mask_mode"
BINDINGS_KEY = "hl_skin_mask_materials"
OWNER_KEY = "hl_skin_mask_generated"
GEOMETRY_KIND = "GEOMETRY"
RENDER_KIND = "RENDER"
LEGACY_NAME = "Masque peau couverte"
LEGACY_GROUP = "Peau couverte"
FACE_ID = ".hl_skin_mask_cage_face"
FACE_CHECK = ".hl_skin_mask_cage_check"
COVERAGE = ".hl_skin_mask_coverage"


def _legacy_name(name):
    if name == LEGACY_NAME:
        return True
    stem, _, suffix = name.rpartition(".")
    if stem != LEGACY_NAME or not suffix.isascii() or not suffix.isdecimal():
        return False
    number = int(suffix)
    return number > 0 and suffix == str(number).zfill(3)


def _mask_inventory(body):
    """Classe les modificateurs possédés sans se fier au mode sauvegardé."""
    inventory = {RENDER_KIND: [], GEOMETRY_KIND: [], LEGACY: []}
    for modifier in body.modifiers:
        if modifier.type == "NODES" and modifier.node_group is not None:
            kind = modifier.node_group.get(OWNER_KEY)
            if kind in (RENDER_KIND, GEOMETRY_KIND):
                inventory[kind].append(modifier)
        elif (modifier.type == "MASK" and modifier.mode == "VERTEX_GROUP"
              and modifier.vertex_group == LEGACY_GROUP and modifier.invert_vertex_group
              and _legacy_name(modifier.name)):
            inventory[LEGACY].append(modifier)
    return inventory


def mode_of(body):
    mode = body.get(MODE_KEY)
    if mode in (OFF, RENDER, GEOMETRY):
        return mode
    return LEGACY if _mask_inventory(body)[LEGACY] else OFF


def _managed_modifier(body, kind=None):
    inventory = _mask_inventory(body)
    candidates = inventory[kind] if kind is not None else [
        *inventory[RENDER_KIND], *inventory[GEOMETRY_KIND]
    ]
    return next(iter(candidates), None)


def needs_repair(body, mode):
    inventory = _mask_inventory(body)
    expected = {GEOMETRY: GEOMETRY_KIND, RENDER: RENDER_KIND}.get(mode)
    return any(len(modifiers) > int(kind == expected) for kind, modifiers in inventory.items())


def manages_geometry(body):
    inventory = _mask_inventory(body)
    return bool(inventory[GEOMETRY_KIND] or inventory[LEGACY])


def _covered_faces(body, pieces):
    mesh = body.data
    vertex_count = len(mesh.vertices)
    covered_faces = np.zeros(len(mesh.polygons), dtype=bool)
    for garment in pieces:
        try:
            vertices = json.loads(garment["hl_garment_params"])["sommets_du_corps"]
            if not isinstance(vertices, list):
                raise ValueError("liste attendue")
            if any(type(index) is not int or not 0 <= index < vertex_count for index in vertices):
                raise ValueError("indice hors du maillage")
        except (KeyError, TypeError, ValueError):
            # Une pièce sans couverture exploitable ne doit jamais creuser la peau.
            print(f"HumanLoom : couverture de peau ignorée pour {garment.name!r}.")
            continue
        if vertices:
            covered = set(vertices)
            # Une face doit être entièrement couverte par une même pièce.
            covered_faces |= np.fromiter((all(v in covered for v in p.vertices) for p in mesh.polygons),
                                          dtype=bool, count=len(mesh.polygons))
    return covered_faces


def _atlas(body, faces, allocated):
    side = math.isqrt(len(faces)) + 1
    image = bpy.data.images.new(body.name + " · Couverture peau", side, side, alpha=True)
    allocated.append(image)
    image[OWNER_KEY] = True
    image.colorspace_settings.name = "Non-Color"
    pixels = np.ones((side * side, 4), dtype=np.float32)
    pixels[:, :3] = 0
    pixels[1:len(faces) + 1, :3] = faces[:, None]
    image.pixels.foreach_set(pixels.ravel())
    image.update()
    image.pack()
    return image


def _scalar(tree, operation, left, right=0):
    node = tree.nodes.new("ShaderNodeMath")
    node.operation = operation
    for socket, value in zip(node.inputs, (left, right)):
        if isinstance(value, bpy.types.NodeSocket):
            tree.links.new(value, socket)
        else:
            socket.default_value = value
    if operation == "COMPARE":
        node.inputs[2].default_value = 1.e-4
    return node.outputs[0]


def _lookup(tree, index, image):
    """Échantillonne au centre du texel. Zéro est réservé aux faces sans attribut."""
    scalar = lambda op, left, right=0: _scalar(tree, op, left, right)
    side = image.size[0]
    uv = tree.nodes.new("ShaderNodeCombineXYZ")
    x = scalar("DIVIDE", scalar("ADD", scalar("MODULO", index, side), 0.5), side)
    y = scalar("DIVIDE", scalar("ADD", scalar("FLOOR", scalar("DIVIDE", index, side)), 0.5), side)
    tree.links.new(x, uv.inputs["X"])
    tree.links.new(y, uv.inputs["Y"])
    sample = tree.nodes.new("GeometryNodeImageTexture")
    sample.inputs["Image"].default_value = image
    sample.interpolation = "Closest"
    sample.extension = "CLIP"
    tree.links.new(uv.outputs[0], sample.inputs["Vector"])
    return sample.outputs["Color"]


def _material(base, body, allocated):
    material = base.copy() if base else bpy.data.materials.new("Peau")
    allocated.append(material)
    material.use_fake_user = False
    material.name = body.name + " · Peau couverte"
    material[OWNER_KEY] = True
    material.use_nodes = True
    tree = material.node_tree
    if not base or not base.use_nodes:
        principled = next((node for node in tree.nodes if node.type == "BSDF_PRINCIPLED"), None)
        if principled is not None:
            principled.inputs["Base Color"].default_value = material.diffuse_color
    surface_outputs = [node.inputs["Surface"] for node in tree.nodes
                       if node.type == "OUTPUT_MATERIAL" and node.is_active_output
                       and node.inputs["Surface"].is_linked]
    if surface_outputs:
        attr = tree.nodes.new("ShaderNodeAttribute")
        attr.attribute_name = COVERAGE
        coverage = _scalar(tree, "GREATER_THAN", attr.outputs["Fac"], 0.5)
        transparent = tree.nodes.new("ShaderNodeBsdfTransparent")
        for surface in surface_outputs:
            shader = surface.links[0].from_socket
            mix = tree.nodes.new("ShaderNodeMixShader")
            tree.links.new(coverage, mix.inputs[0])
            tree.links.new(shader, mix.inputs[1])
            tree.links.new(transparent.outputs[0], mix.inputs[2])
            tree.links.new(mix.outputs[0], surface)
    return material


def _ensure_origin(mesh, created):
    """Les identifiants voyagent avec les faces depuis le maillage source."""
    attributes = [mesh.attributes.get(name) for name in (FACE_ID, FACE_CHECK)]
    count = len(mesh.polygons)
    indices = np.arange(1, count + 1, dtype=np.float32)
    fields = (indices, count + 1 - indices)
    if any(attribute is not None for attribute in attributes):
        for attribute, expected in zip(attributes, fields):
            if attribute is None or attribute.domain != "FACE" or attribute.data_type != "FLOAT":
                raise ValueError("Provenance des faces HumanLoom incomplète ou invalide.")
            values = np.empty(count, dtype=np.float32)
            attribute.data.foreach_get("value", values)
            if not np.array_equal(values, expected):
                raise ValueError("La provenance des faces HumanLoom a été modifiée.")
        return
    if not mesh.is_editable:
        raise ValueError("Le maillage source doit être éditable pour enregistrer la provenance.")
    for name, values in zip((FACE_ID, FACE_CHECK), fields):
        attribute = mesh.attributes.new(name, "FLOAT", "FACE")
        # Les handles d'attribut peuvent changer lors d'un ajout RNA.
        created.append(name)
        attribute.data.foreach_set("value", values)
    mesh.update()


def _coverage_sample(tree, image, count):
    def field(name):
        attr = tree.nodes.new("GeometryNodeInputNamedAttribute")
        attr.data_type = "FLOAT"
        attr.inputs["Name"].default_value = name
        return attr.outputs["Attribute"]

    index = field(FACE_ID)
    witness = field(FACE_CHECK)
    scalar = lambda op, left, right=0: _scalar(tree, op, left, right)
    # Les couches absentes valent zéro. Les ID hors plage, fractionnaires ou
    # incohérents avec leur témoin gardent la peau visible dans les deux moteurs.
    minimum = scalar("GREATER_THAN", index, 0.5)
    maximum = scalar("LESS_THAN", index, count + 0.5)
    rounded = scalar("ROUND", index)
    integral = scalar("COMPARE", index, rounded)
    check = scalar("COMPARE", scalar("ADD", index, witness), count + 1)
    valid = scalar("MULTIPLY", scalar("MULTIPLY", minimum, maximum),
                   scalar("MULTIPLY", integral, check))
    safe_index = scalar("MULTIPLY", rounded, valid)
    return _lookup(tree, safe_index, image)


def _group_for(body, kind, image, count, fallback, allocated):
    tree = bpy.data.node_groups.new(body.name + " · Masque de peau", "GeometryNodeTree")
    allocated.append(tree)
    tree[OWNER_KEY] = kind
    tree.interface.new_socket(name="Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    tree.interface.new_socket(name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    source = tree.nodes.new("NodeGroupInput").outputs["Geometry"]
    destination = tree.nodes.new("NodeGroupOutput").inputs["Geometry"]
    coverage = _coverage_sample(tree, image, count)
    threshold = _scalar(tree, "GREATER_THAN", coverage, 0.5)
    if kind == GEOMETRY_KIND:
        delete = tree.nodes.new("GeometryNodeDeleteGeometry")
        delete.domain = "FACE"
        tree.links.new(source, delete.inputs["Geometry"])
        tree.links.new(threshold, delete.inputs["Selection"])
        result = delete.outputs["Geometry"]
    else:
        store = tree.nodes.new("GeometryNodeStoreNamedAttribute")
        store.data_type = "FLOAT"
        store.domain = "FACE"
        store.inputs["Name"].default_value = COVERAGE
        tree.links.new(source, store.inputs["Geometry"])
        tree.links.new(threshold, store.inputs["Value"])
        result = store.outputs["Geometry"]
        if fallback is not None:
            assign = tree.nodes.new("GeometryNodeSetMaterial")
            assign.inputs["Material"].default_value = fallback
            tree.links.new(result, assign.inputs["Geometry"])
            result = assign.outputs["Geometry"]
    tree.links.new(result, destination)
    return tree


def _source_slots(body):
    """Retrouve les liaisons d'origine, même si une surcharge a été remplacée."""
    bindings = body.get(BINDINGS_KEY, {})
    # L'indice seul ne suffit pas après un déplacement d'emplacement.
    previous = {entry["masked"]: entry for entry in bindings.values()
                if entry.get("masked") is not None}
    sources = []
    for index, slot in enumerate(body.material_slots):
        entry = previous.get(slot.material) if slot.link == "OBJECT" else None
        link = entry["link"] if entry is not None else slot.link
        if link == "DATA":
            material = body.data.materials[index]
        else:
            material = entry.get("source") if entry is not None else slot.material
        sources.append((link, material))
    return sources


def _restore_slots(body, sources):
    previous = body.get(BINDINGS_KEY)
    if previous is None:
        return []
    old = [entry.get("masked") for entry in previous.values()]
    for slot, (link, material) in zip(body.material_slots, sources):
        if link == "DATA" and slot.link == "OBJECT":
            slot.material = None
        slot.link = link
        if link == "OBJECT":
            slot.material = material
    del body[BINDINGS_KEY]
    return old


def _discard(group, materials):
    # Ne retire que les données générées devenues orphelines. Des copies d'objet
    # et des matériaux réutilisés peuvent encore partager l'ancien atlas.
    images = set()
    if group and group.get(OWNER_KEY) and group.users == 0:
        for node in group.nodes:
            if node.bl_idname == "GeometryNodeSetMaterial":
                materials.append(node.inputs["Material"].default_value)
            elif node.bl_idname == "GeometryNodeImageTexture":
                images.add(node.inputs["Image"].default_value)
        bpy.data.node_groups.remove(group)
    for material in set(materials):
        if material and material.get(OWNER_KEY) and material.users == 0:
            images.update(node.image for node in material.node_tree.nodes if node.type == "TEX_IMAGE")
            bpy.data.materials.remove(material)
    for image in images:
        if image and image.get(OWNER_KEY) and image.users == 0:
            bpy.data.images.remove(image)


def _cloth_nodes(obj):
    from . import cloth_sim

    for modifier in obj.modifiers:
        if modifier.type != "NODES" or modifier.node_group is None:
            continue
        if modifier.node_group.name.startswith(cloth_sim.CLOTH_GROUP):
            return modifier
        if obj.get("hl_cloth") and modifier.name == cloth_sim.CLOTH_MODIFIER:
            return modifier
    return None


def _point_cache(obj):
    return any(cache.is_baked or cache.is_baking or cache.use_external for modifier in obj.modifiers
               if (cache := getattr(modifier, "point_cache", None)) is not None)


def guard_garments(garments):
    from . import cloth_sim

    # Blender 5.2 ne distingue pas une zone GN cuite via RNA, même embarquée.
    # Une simulation de tissu HumanLoom active est donc protégée.
    if any(g.get(cloth_sim.BAKE_KEY) or _cloth_nodes(g) or _point_cache(g) for g in garments):
        raise ValueError("Une pièce est simulée ou possède un cache protégé. "
                         "Gérez explicitement sa simulation avant de la remplacer, l’ajuster ou la retirer.")


def guard(body):
    from . import cloth_sim

    if _point_cache(body):
        raise ValueError("Un cache de simulation protégé dépend de ce corps.")
    guard_garments(body.children)
    for garment in bpy.data.objects:
        modifier = _cloth_nodes(garment)
        if modifier is None:
            continue
        effectors = next((socket for socket in modifier.node_group.interface.items_tree
                          if socket.item_type == "SOCKET" and socket.in_out == "INPUT"
                          and socket.name == "Effectors Collection"), None)
        if effectors is not None:
            collection = getattr(modifier.properties.inputs, effectors.identifier).value
            if collection and collection.all_objects.get(body.name) is not None:
                raise ValueError("Une simulation active utilise ce corps comme collider. "
                                 "Son masque géométrique reste inchangé.")


def require_editable(body):
    if body.mode != "OBJECT" or not body.is_editable:
        raise ValueError("Sélectionnez un corps éditable en mode Objet.")


def _prepare(body, mode, faces, sources, allocated, created_attributes):
    groups = {}
    masked = []
    if faces.any():
        _ensure_origin(body.data, created_attributes)
        size = len(faces)
        image = _atlas(body, faces, allocated)
        if mode == GEOMETRY:
            groups[GEOMETRY_KIND] = _group_for(body, GEOMETRY_KIND, image, size, None, allocated)
        else:
            fallback = None
            if sources:
                masked = [_material(material, body, allocated) for _, material in sources]
            else:
                fallback = _material(None, body, allocated)
            groups[RENDER_KIND] = _group_for(body, RENDER_KIND, image, size, fallback, allocated)
    return groups, masked


def _publish(body, mode, old, sources, groups, masked, legacy):
    old_materials = _restore_slots(body, sources)
    obsolete = list(legacy)
    for kind, candidates in old.items():
        group = groups.get(kind)
        if group is None:
            obsolete.extend(candidates)
            continue
        modifier = candidates[0] if candidates else None
        obsolete.extend(candidates[1:])
        if modifier is None:
            name = "HL Couverture de peau" if kind == RENDER_KIND else "HL Masque de peau"
            modifier = body.modifiers.new(name, "NODES")
            if kind == GEOMETRY_KIND:
                human_modifier = body.modifiers.get(human.MODIFIER_NAME)
                if human_modifier:
                    after_human = list(body.modifiers).index(human_modifier) + 1
                    body.modifiers.move(len(body.modifiers) - 1, after_human)
        modifier.node_group = group
        modifier.show_viewport = True
        modifier.show_render = True

    if masked:
        bindings = {}
        for index, (slot, (link, source), material) in enumerate(zip(body.material_slots, sources, masked)):
            bindings[str(index)] = {"masked": material, "link": link}
            if link == "OBJECT" and source is not None:
                bindings[str(index)]["source"] = source
            slot.link = "OBJECT"
            slot.material = material
        body[BINDINGS_KEY] = bindings
    for modifier in obsolete:
        modifier.show_viewport = modifier.show_render = False
    body[MODE_KEY] = mode
    return old_materials, obsolete


def _restore_publication(body, modifiers, slots, properties):
    for modifier in list(body.modifiers):
        if modifier not in modifiers:
            body.modifiers.remove(modifier)
    for modifier, (show_viewport, show_render, group) in modifiers.items():
        if modifier.type == "NODES" and modifier.node_group != group:
            modifier.node_group = group
        if modifier.show_viewport != show_viewport:
            modifier.show_viewport = show_viewport
        if modifier.show_render != show_render:
            modifier.show_render = show_render
    for slot, (link, material) in zip(body.material_slots, slots):
        if slot.link == "OBJECT" and link == "DATA":
            slot.material = None
        slot.link = link
        if link == "OBJECT":
            slot.material = material
    for key, value in properties.items():
        if value is not None:
            body[key] = value
        elif key in body:
            del body[key]


def _discard_prepared(allocated):
    for item in reversed(allocated):
        if item.users:
            continue
        if isinstance(item, bpy.types.NodeTree):
            bpy.data.node_groups.remove(item)
        elif isinstance(item, bpy.types.Material):
            bpy.data.materials.remove(item)
        elif isinstance(item, bpy.types.Image):
            bpy.data.images.remove(item)


def set_mode(body, mode, pieces):
    """Prépare puis publie le masque, en gardant les anciens éléments jusqu'au succès."""
    if mode not in (OFF, RENDER, GEOMETRY):
        raise ValueError("Mode de masque de peau inconnu.")
    require_editable(body)
    previous = mode_of(body)
    inventory = _mask_inventory(body)
    legacy = inventory[LEGACY]
    old = {kind: inventory[kind] for kind in (RENDER_KIND, GEOMETRY_KIND)}
    if legacy or previous == GEOMETRY or mode == GEOMETRY or old[GEOMETRY_KIND]:
        guard(body)
    old_groups = dict.fromkeys(modifier.node_group for candidates in old.values() for modifier in candidates)
    faces = _covered_faces(body, pieces) if mode != OFF else np.zeros(0, dtype=bool)
    sources = _source_slots(body)
    modifiers = {modifier: (modifier.show_viewport, modifier.show_render,
                            modifier.node_group if modifier.type == "NODES" else None)
                 for modifier in body.modifiers}
    slots = [(slot.link, slot.material) for slot in body.material_slots]
    bindings = body.get(BINDINGS_KEY)
    properties = {
        MODE_KEY: body.get(MODE_KEY),
        BINDINGS_KEY: {key: dict(entry.items()) for key, entry in bindings.items()}
        if bindings is not None else None,
    }
    allocated, created_attributes = [], []
    try:
        groups, masked = _prepare(body, mode, faces, sources, allocated, created_attributes)
        try:
            old_materials, obsolete = _publish(body, mode, old, sources, groups, masked, legacy)
        except Exception:
            _restore_publication(body, modifiers, slots, properties)
            raise
    except Exception:
        _discard_prepared(allocated)
        for name in created_attributes:
            body.data.attributes.remove(body.data.attributes[name])
        if created_attributes:
            body.data.update()
        raise

    for modifier in obsolete:
        body.modifiers.remove(modifier)
    for group in old_groups:
        _discard(group, [])
    _discard(None, old_materials)
    return int(faces.sum())
