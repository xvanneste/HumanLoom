"""Simulation de tissu NATIVE de Blender 5.2 pour les vêtements amples (lot V4) : groupe de nœuds « Cloth Dynamics (Experimental) » (solveur XPBD) et modificateur « Collider » du fichier d'assets fourni avec Blender.

Sources : notes de version 5.2, page Physics (« The new experimental Cloth Dynamics modifier and node group can just be added to any mesh to give it cloth-like behavior. », « A collider object is created by adding a Collider
modifier to it. This uses the geometry at that point in the modifier stack as collision mesh. ») ; le comportement de nos réglages est MESURÉ ici (CONCEPTION_V4.md), pas tiré d'une documentation (le manuel 5.2 n'a pas de page sur
Cloth Dynamics : « non vérifié »). Fonctionnalité EXPÉRIMENTALE de Blender : son design peut changer.

Montage mesuré : le vêtement porte (dans cet ordre) Armature → « Tissu » (Cloth Dynamics) ; le groupe de sommets « Epinglage » donne la force d'épinglage (poids 1 : suit l'armature ; 0 : libre) ; le corps porte un modificateur
« Collider » PLACÉ APRÈS son Armature, et il appartient à une collection « HL Colliders » propre au personnage reliée à l'entrée « Effectors Collection » du tissu. Le cache est « emballé » (PACKED, dans le .blend) avec une plage d'images FIXÉE :
sans cela le bake natif ne produit rien de rejouable (mesuré). Jamais pour la foule (41–62 ms par vêtement et par image)."""
import time

import bpy
import numpy as np

from .animation import skeleton

ASSET = "assets/nodes/geometry_nodes_dynamics_assets.blend"
CLOTH_GROUP, COLLIDER_GROUP = "Cloth Dynamics (Experimental)", "Collider"
CLOTH_MODIFIER, COLLIDER_MODIFIER, COLLECTION = "Tissu", "Collider", "HL Colliders"
DEFAULTS = {"Substeps": 5, "Constraint Steps": 15, "Collision Radius": 0.01}  # valeurs mesurées (CONCEPTION_V4.md)
BAKE_KEY = "hl_cloth_bake"
ACTIVE_KEY = "hl_cloth"
CLOTH_UID_KEY = "hl_cloth_modifier_uid"
SESSION_KEY = "hl_cloth_session"


CLOTH_INPUTS = ("Substeps", "Constraint Steps", "Collision Radius", "Effectors Collection", "Pin Group")
COLLIDER_INPUTS = ("Deforming",)


def _valid_group(group, required):
    """Un nom n'est pas une preuve d'origine : le groupe doit être local et exposer les entrées utilisées."""
    if group.library is not None or group.bl_idname != "GeometryNodeTree":
        return False
    names = {item.name for item in group.interface.items_tree if item.item_type == "SOCKET" and item.in_out == "INPUT"}
    return all(name in names for name in required)


def _find_group(name, required):
    return next((g for g in bpy.data.node_groups if (g.name == name or (g.name.startswith(name + ".") and g.name[len(name) + 1:].isdigit()))
                 and _valid_group(g, required)), None)


def _localize(tree, memo):
    """Rend locale toute la fermeture transitive : les sous-groupes (Edge Length, Curve Segment) restent sinon liés au fichier d'assets de l'installation Blender (GRM-018)."""
    key = tree.as_pointer()
    if key in memo:
        return memo[key]
    result = tree.copy() if tree.library is not None else tree
    memo[key] = result
    for node in result.nodes:
        if node.type == "GROUP" and node.node_tree is not None:
            node.node_tree = _localize(node.node_tree, memo)
    return result


def _groups():
    """Groupes de nœuds du fichier d'assets de Blender (chargés si absents, locaux sur toute leur fermeture)."""
    wanted = {CLOTH_GROUP: CLOTH_INPUTS, COLLIDER_GROUP: COLLIDER_INPUTS}
    found = {name: _find_group(name, required) for name, required in wanted.items()}
    missing = [name for name, group in found.items() if group is None]
    if missing:
        path = bpy.utils.system_resource("DATAFILES") + "/" + ASSET
        with bpy.data.libraries.load(path, link=False) as (source, target):
            for name in missing:
                if name not in source.node_groups:
                    raise ValueError("Groupe Blender 5.2 absent : " + name)
            target.node_groups = list(missing)  # Blender remplace les noms par les blocs dans la liste donnée
        loaded = list(target.node_groups)
        for name in missing:
            found[name] = next((g for g in loaded if g is not None and g.name.startswith(name) and _valid_group(g, wanted[name])), None)
            if found[name] is None:
                raise ValueError("Groupe Blender 5.2 incompatible : " + name)
    memo = {}
    return tuple(_localize(found[name], memo) for name in (CLOTH_GROUP, COLLIDER_GROUP))


def _input(group, name):
    socket = next((i for i in group.interface.items_tree
                   if i.item_type == "SOCKET" and i.in_out == "INPUT" and i.name == name), None)
    if socket is None:
        raise ValueError(f"Entrée Blender 5.2 absente dans {group.name} : {name}")
    return socket


def _cloth_modifier(garment):
    uid = garment.get(CLOTH_UID_KEY)
    if uid is not None:
        return next((modifier for modifier in garment.modifiers if modifier.persistent_uid == uid), None)
    modifier = garment.modifiers.get(CLOTH_MODIFIER)
    if (modifier is not None and modifier.type == "NODES" and modifier.node_group
            and modifier.node_group.name.startswith(CLOTH_GROUP)):
        return modifier
    return None


def is_enabled(garment):
    return _cloth_modifier(garment) is not None


def _effectors(modifier):
    socket = _input(modifier.node_group, "Effectors Collection")
    return getattr(modifier.properties.inputs, socket.identifier).value


def _active_sibling(body, garment):
    return next((modifier for child in body.children if child != garment and child.get(ACTIVE_KEY)
                 and (modifier := _cloth_modifier(child)) is not None), None)


def _corrective_states(body):
    """Photographie par datablock, partagée par toutes les pièces simulées du corps."""
    from .animation import correctives

    objects = [body] + [child for child in body.children if child.type == "MESH"]
    states = {}
    for obj in objects:
        keys = correctives.keys_of(obj.data)
        if keys:
            states[obj.data.shape_keys] = {key.name: key.mute for key in keys}
    # Le mute appartient au datablock : refuser la mutation d'un autre personnage
    # ou d'un objet lié au même maillage.
    for obj in bpy.data.objects:
        if obj not in objects and obj.type == "MESH" and obj.data.shape_keys in states:
            raise ValueError("Des correctifs sont partagés avec un autre objet. Rendez le maillage indépendant avant la simulation.")
    return {str(i): {"keys": keys, "mutes": mutes} for i, (keys, mutes) in enumerate(states.items())}


def _apply_corrective_states(states, mute=False):
    for state in states.values():
        keys = state["keys"]
        if keys is None:
            continue
        for name, initial in state["mutes"].items():
            key = keys.key_blocks.get(name)
            if key is not None:
                key.mute = mute or initial


def _remove_effectors(body, collection):
    if collection.objects.get(body.name) == body:
        collection.objects.unlink(body)
    if collection.objects or collection.children or collection.use_fake_user:
        return
    # Le compteur RNA peut encore inclure une entrée GN retirée ; la carte
    # des références indique les utilisateurs réels après le retrait.
    users = bpy.data.user_map(subset=[collection])[collection]
    if not users or (len(users) == 1 and any(isinstance(user, bpy.types.Scene)
                                             and user.collection.children.get(collection.name) == collection
                                             for user in users)):
        bpy.data.collections.remove(collection)


def enable(garment, settings=None):
    """Active la simulation sur une robe ou une jupe épinglée et retourne son modificateur."""
    body = garment.parent
    if body is None or not skeleton.rigs_of(body):
        raise ValueError("Le corps n'a pas de squelette : posez-le d'abord.")
    if "Epinglage" not in garment.vertex_groups:
        raise ValueError("Cette pièce n'a pas de groupe d'épinglage : seules les robes et les jupes se simulent.")
    current = _cloth_modifier(garment)
    if current is not None:
        return current

    cloth_group, collider_group = _groups()
    session = body.get(SESSION_KEY)
    sibling = _active_sibling(body, garment)
    starting = session is None and sibling is None
    if starting:
        states = _corrective_states(body)
        collection = None
    else:
        collection = session["collection"] if session is not None else _effectors(sibling)
        if collection is None:
            raise ValueError("Collection de collision absente : désactivez les pièces simulées avant de réessayer.")

    collider = modifier = None
    try:
        if starting:
            existing = any(m.type == "NODES" and m.node_group == collider_group for m in body.modifiers)
            if not existing:
                collider = body.modifiers.new(COLLIDER_MODIFIER, "NODES")
                collider.node_group = collider_group
                getattr(collider.properties.inputs, _input(collider_group, "Deforming").identifier).value = True
                armature_index = max((i for i, m in enumerate(body.modifiers) if m.type == "ARMATURE"), default=-1)
                body.modifiers.move(len(body.modifiers) - 1, armature_index + 1)

            # Les deux robes d'un même corps partagent leurs effecteurs. Deux corps
            # distincts ont chacun leur collection, même dans une scène commune.
            collection = bpy.data.collections.new(COLLECTION)
            owners = list(body.users_scene)
            scene = bpy.context.scene if bpy.context.scene in owners or not owners else owners[0]
            scene.collection.children.link(collection)
            collection.hide_render = True
            collection.objects.link(body)

        modifier = garment.modifiers.new(CLOTH_MODIFIER, "NODES")
        modifier.node_group = cloth_group
        values = dict(DEFAULTS, **(settings or {}))
        for name, value in values.items():
            getattr(modifier.properties.inputs, _input(cloth_group, name).identifier).value = value
        getattr(modifier.properties.inputs, _input(cloth_group, "Effectors Collection").identifier).value = collection
        getattr(modifier.properties.inputs, _input(cloth_group, "Pin Group").identifier).attribute_name = "Epinglage"

        if starting:
            body[SESSION_KEY] = {"collection": collection,
                                 "collider_uid": collider.persistent_uid if collider is not None else 0,
                                 "correctives": states}
            # Le contournement du conflit entre le Collider et les correctifs de
            # flexion reste nécessaire dans le montage mesuré (CONCEPTION_V4.md).
            _apply_corrective_states(states, mute=True)
        garment[CLOTH_UID_KEY] = modifier.persistent_uid
        garment[ACTIVE_KEY] = True
        return modifier
    except Exception:
        if modifier is not None:
            garment.modifiers.remove(modifier)
        if CLOTH_UID_KEY in garment:
            del garment[CLOTH_UID_KEY]
        if starting:
            if SESSION_KEY in body:
                _apply_corrective_states(states)
                del body[SESSION_KEY]
            if collider is not None:
                body.modifiers.remove(collider)
            if collection is not None:
                _remove_effectors(body, collection)
        raise


def disable(garment):
    """Retire la simulation, puis libère les ressources au départ de la dernière pièce."""
    body = garment.parent
    modifier = _cloth_modifier(garment)
    managed = garment.get(ACTIVE_KEY) or CLOTH_UID_KEY in garment
    session = body.get(SESSION_KEY) if body is not None else None
    legacy_collection = None
    if managed and session is None and modifier is not None and modifier.type == "NODES" and modifier.node_group:
        try:
            legacy_collection = _effectors(modifier)
        except ValueError:
            pass
    if modifier is not None:
        garment.modifiers.remove(modifier)
    for key in (ACTIVE_KEY, CLOTH_UID_KEY, BAKE_KEY):
        if key in garment:
            del garment[key]
    if body is None or not managed or _active_sibling(body, garment) is not None:
        return

    if session is not None:
        collection = session["collection"]
        uid = session["collider_uid"]
        collider = next((m for m in body.modifiers if m.persistent_uid == uid), None) if uid else None
        if collider is not None:
            body.modifiers.remove(collider)
        _apply_corrective_states(session["correctives"])
        del body[SESSION_KEY]
        if collection is not None:
            _remove_effectors(body, collection)
    else:
        # L'ancien format ne conservait ni le mute initial ni le propriétaire
        # de la collection. Garder sa collection et le rétablissement historique.
        from .animation import correctives

        collider = body.modifiers.get(COLLIDER_MODIFIER)
        if collider is not None and collider.type == "NODES" and collider.node_group and collider.node_group.name.startswith(COLLIDER_GROUP):
            body.modifiers.remove(collider)
        if legacy_collection is not None and legacy_collection.objects.get(body.name) == body:
            legacy_collection.objects.unlink(body)
        for obj in [body] + [child for child in body.children if child.type == "MESH"]:
            for key in correctives.keys_of(obj.data):
                key.mute = False


def bake(garment, frame_start=None, frame_end=None):
    """Cuit la simulation sur la plage (par défaut : celle de la scène) : cache EMBALLÉ dans le .blend avec plage fixée. Retourne {« images », « duree_s »}."""
    modifier = _cloth_modifier(garment)
    if modifier is None:
        raise ValueError("La simulation n'est pas activée sur cette pièce.")
    scene = bpy.context.scene
    start = scene.frame_start if frame_start is None else int(frame_start)
    end = scene.frame_end if frame_end is None else int(frame_end)
    if end <= start:
        raise ValueError("Plage d'images invalide : %d à %d" % (start, end))
    for item in modifier.bakes:
        item.bake_mode = "ANIMATION"
        item.bake_target = "PACKED"
        item.use_custom_simulation_frame_range = True
        item.frame_start, item.frame_end = start, end
    for obj in bpy.context.view_layer.objects:
        obj.select_set(False)
    garment.select_set(True)
    bpy.context.view_layer.objects.active = garment
    started = time.perf_counter()
    bpy.ops.object.simulation_nodes_cache_bake(selected=True)
    garment[BAKE_KEY] = [start, end]
    return {"images": end - start + 1, "duree_s": round(time.perf_counter() - started, 2)}


def clear_bake(garment):
    for obj in bpy.context.view_layer.objects:
        obj.select_set(False)
    garment.select_set(True)
    bpy.context.view_layer.objects.active = garment
    bpy.ops.object.simulation_nodes_cache_delete(selected=True)
    if BAKE_KEY in garment:
        del garment[BAKE_KEY]


def baked_range(garment):
    value = garment.get(BAKE_KEY)
    return tuple(value) if value else None


def positions(garment):
    evaluated = garment.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    out = np.array([(garment.matrix_world @ v.co)[:] for v in mesh.vertices])
    evaluated.to_mesh_clear()
    return out


def cost_ms(garment, frames=8):
    """Coût moyen d'évaluation par image (ms) sur `frames` images consécutives à partir de la plage de la scène."""
    scene = bpy.context.scene
    scene.frame_set(scene.frame_start)
    times = []
    for f in range(scene.frame_start + 1, scene.frame_start + 1 + frames):
        started = time.perf_counter()
        scene.frame_set(f)
        bpy.context.view_layer.update()
        times.append((time.perf_counter() - started) * 1000.0)
    return float(np.mean(times))
