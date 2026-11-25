"""Simulation de tissu NATIVE de Blender 5.2 pour les vêtements amples (lot V4) : groupe de nœuds « Cloth Dynamics (Experimental) » (solveur XPBD) et modificateur « Collider » du fichier d'assets fourni avec Blender.

Sources : notes de version 5.2, page Physics (« The new experimental Cloth Dynamics modifier and node group can just be added to any mesh to give it cloth-like behavior. », « A collider object is created by adding a Collider
modifier to it. This uses the geometry at that point in the modifier stack as collision mesh. ») ; le comportement de nos réglages est MESURÉ ici (CONCEPTION_V4.md), pas tiré d'une documentation (le manuel 5.2 n'a pas de page sur
Cloth Dynamics : « non vérifié »). Fonctionnalité EXPÉRIMENTALE de Blender : son design peut changer.

Montage mesuré : le vêtement porte (dans cet ordre) Armature → « Tissu » (Cloth Dynamics) ; le groupe de sommets « Epinglage » donne la force d'épinglage (poids 1 : suit l'armature ; 0 : libre) ; le corps porte un modificateur
« Collider » PLACÉ APRÈS son Armature, et il appartient à une collection « HL Colliders » reliée à l'entrée « Effectors Collection » du tissu. Le cache est « emballé » (PACKED, dans le .blend) avec une plage d'images FIXÉE :
sans cela le bake natif ne produit rien de rejouable (mesuré). Jamais pour la foule (41–62 ms par vêtement et par image)."""
import time

import bpy
import numpy as np

from . import human
from .animation import skeleton

ASSET = "assets/nodes/geometry_nodes_dynamics_assets.blend"
CLOTH_GROUP, COLLIDER_GROUP = "Cloth Dynamics (Experimental)", "Collider"
CLOTH_MODIFIER, COLLIDER_MODIFIER, COLLECTION = "Tissu", "Collider", "HL Colliders"
DEFAULTS = {"Substeps": 5, "Constraint Steps": 15, "Collision Radius": 0.01}  # valeurs mesurées (CONCEPTION_V4.md)
BAKE_KEY = "hl_cloth_bake"


def _groups():
    """Groupes de nœuds du fichier d'assets de Blender (chargés une fois, locaux)."""
    for name in (CLOTH_GROUP, COLLIDER_GROUP):
        if name not in bpy.data.node_groups or bpy.data.node_groups[name].library is not None:
            break
    else:
        return bpy.data.node_groups[CLOTH_GROUP], bpy.data.node_groups[COLLIDER_GROUP]
    path = bpy.utils.system_resource("DATAFILES") + "/" + ASSET
    with bpy.data.libraries.load(path, link=False) as (source, target):
        for name in (CLOTH_GROUP, COLLIDER_GROUP):
            if name not in source.node_groups:
                raise ValueError("Groupe Blender 5.2 absent : " + name)
        target.node_groups = [CLOTH_GROUP, COLLIDER_GROUP]
    return target.node_groups[0], target.node_groups[1]


def _input(group, name):
    return next(i for i in group.interface.items_tree if i.item_type == "SOCKET" and i.in_out == "INPUT" and i.name == name)


def _collider_collection(scene):
    collection = bpy.data.collections.get(COLLECTION)
    if collection is None:
        collection = bpy.data.collections.new(COLLECTION)
        scene.collection.children.link(collection)
    collection.hide_render = True
    return collection


def is_enabled(garment):
    return garment.modifiers.get(CLOTH_MODIFIER) is not None


def _mute_correctives(body, muted):
    """Coupe (ou remet) les clés de forme de correctifs de flexion du corps et de ses pièces tant qu'une pièce est SIMULÉE : mesuré, avec les correctifs actifs la jupe pénètre le corps de 138 à 197 mm à la marche (seuil 15 mm), sans eux 9,5 mm ;
    cause non élucidée (le collider voit une surface qui change à chaque image par les pilotes de clés de forme). Le corps garde donc la peau sans correctifs en simulation de tissu (limite documentée)."""
    from .animation import correctives
    for obj in [body] + [c for c in body.children if c.type == "MESH"]:
        for key in correctives.keys_of(obj.data):
            key.mute = muted


def enable(garment, settings=None):
    """Active la simulation sur la pièce (robe ou jupe) : modificateur Collider sur le corps (après son Armature), collection d'effecteurs, modificateur « Tissu ». Retourne le modificateur. Refuse une pièce sans
    groupe d'épinglage ou sans squelette."""
    body = garment.parent
    if body is None or not skeleton.rigs_of(body):
        raise ValueError("Le corps n'a pas de squelette : posez-le d'abord.")
    if "Epinglage" not in garment.vertex_groups:
        raise ValueError("Cette pièce n'a pas de groupe d'épinglage : seules les robes et les jupes se simulent.")
    if is_enabled(garment):
        return garment.modifiers[CLOTH_MODIFIER]
    _mute_correctives(garment.parent, True)
    cloth_group, collider_group = _groups()
    scene = bpy.context.scene
    if body.modifiers.get(COLLIDER_MODIFIER) is None:
        collider = body.modifiers.new(COLLIDER_MODIFIER, "NODES")
        collider.node_group = collider_group
        getattr(collider.properties.inputs, _input(collider_group, "Deforming").identifier).value = True  # le corps est animé : « Whether the collider geometry is changing » (description du socket)
        armature_index = max((i for i, m in enumerate(body.modifiers) if m.type == "ARMATURE"), default=-1)
        body.modifiers.move(len(body.modifiers) - 1, armature_index + 1)  # APRÈS l'Armature (géométrie utilisée = celle présente à ce point de la pile)
    collection = _collider_collection(scene)
    if body.name not in collection.objects:
        collection.objects.link(body)
    modifier = garment.modifiers.new(CLOTH_MODIFIER, "NODES")
    modifier.node_group = cloth_group
    values = dict(DEFAULTS, **(settings or {}))
    for name, value in values.items():
        getattr(modifier.properties.inputs, _input(cloth_group, name).identifier).value = value
    getattr(modifier.properties.inputs, _input(cloth_group, "Effectors Collection").identifier).value = collection
    getattr(modifier.properties.inputs, _input(cloth_group, "Pin Group").identifier).attribute_name = "Epinglage"
    garment["hl_cloth"] = True
    return modifier


def disable(garment):
    """Retire la simulation de la pièce ; le Collider du corps est retiré s'il ne reste aucune pièce simulée."""
    modifier = garment.modifiers.get(CLOTH_MODIFIER)
    if modifier is not None:
        garment.modifiers.remove(modifier)
    for key in ("hl_cloth", BAKE_KEY):
        if key in garment:
            del garment[key]
    body = garment.parent
    if body is not None and not any(c.get("hl_cloth") for c in body.children):
        collider = body.modifiers.get(COLLIDER_MODIFIER)
        if collider is not None:
            body.modifiers.remove(collider)
        _mute_correctives(body, False)


def bake(garment, frame_start=None, frame_end=None):
    """Cuit la simulation sur la plage (par défaut : celle de la scène) : cache EMBALLÉ dans le .blend avec plage fixée. Retourne {« images », « duree_s »}."""
    modifier = garment.modifiers.get(CLOTH_MODIFIER)
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
