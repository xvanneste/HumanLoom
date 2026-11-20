"""Reversible maintenance layer for the indexed Studio base's inner eyelids."""

import bpy
import numpy as np

KEY = "Surface · Paupières internes"
REVISION = 1


def bind(key, body, control=None, pole=None):
    curve = key.driver_add("value")
    driver = curve.driver
    driver.type = "SCRIPTED"
    variable = driver.variables.new()
    variable.name = "morph"
    variable.type = "SINGLE_PROP"
    variable.targets[0].id_type = "KEY"
    variable.targets[0].id = body.data.shape_keys
    variable.targets[0].data_path = 'key_blocks["Morphologie"].value'
    driver.expression = "1-morph"
    if control:
        amount = driver.variables.new()
        amount.name = "amount"
        amount.type = "SINGLE_PROP"
        amount.targets[0].id_type = "KEY"
        amount.targets[0].id = body.data.shape_keys
        amount.targets[0].data_path = '["hm_' + control + '"]'
        expression = "max(amount,0)" if pole == "gain" else "max(-amount,0)" if pole == "perte" else "amount"
        driver.expression = "(1-morph)*(" + expression + ")"
    return curve


def apply(body, asset_path):
    from . import landmark_sets
    keys = body.data.shape_keys
    if keys is None or not body.is_editable or not keys.is_editable:
        raise ValueError("Le corps et ses clés de forme doivent être éditables.")
    if KEY in keys.key_blocks:
        if body.data.get("human_modeling_surface_revision", 0) >= REVISION:
            return False
        raise ValueError("Une clé du même nom existe déjà. Elle a été conservée.")
    collection, created = None, []
    try:
        with bpy.data.libraries.load(str(asset_path), link=False) as (_, target):
            target.collections = ["Realistic Human Base"]
        collection = target.collections[0]
        source = next(obj for obj in collection.objects if obj.get("human_modeling_body"))
        if landmark_sets.topology(body) != landmark_sets.topology(source):
            raise ValueError("La correction nécessite la topologie d’origine du corps.")
        corrections = [key for key in source.data.shape_keys.key_blocks if key.name == KEY or key.name.startswith(KEY + " · ")]
        if not any(key.name == KEY for key in corrections):
            raise ValueError("La base installée ne contient pas cette correction.")
        count = len(body.data.vertices) * 3
        base, source_base = np.empty(count), np.empty(count)
        keys.key_blocks[0].data.foreach_get("co", base)
        source.data.shape_keys.key_blocks[0].data.foreach_get("co", source_base)
        for correction in corrections:
            if correction.name in keys.key_blocks:
                raise ValueError("Une clé de correction du même nom existe déjà.")
            delta = np.empty(count)
            correction.data.foreach_get("co", delta)
            points = base + delta - source_base
            if not np.isfinite(points).all():
                raise ValueError("Coordonnées de correction invalides.")
            key = body.shape_key_add(name=correction.name)
            created.append(key)
            key.data.foreach_set("co", points)
            key.slider_min = -1 if correction.name != KEY else 0
            parts = correction.name.split(" · ")
            curve = bind(key, body, parts[2] if len(parts) > 2 else None, parts[3] if len(parts) > 3 else None)
            keys.update_tag()
            bpy.context.view_layer.update()
            if not curve.is_valid:
                raise ValueError("Le pilote de correction n’a pas pu être activé.")
        body.data["human_modeling_surface_revision"] = REVISION
        return True
    except Exception:
        for key in reversed(created):
            body.shape_key_remove(key)
        raise
    finally:
        if collection:
            for obj in tuple(collection.objects):
                mesh = obj.data
                bpy.data.objects.remove(obj, do_unlink=True)
                if mesh.users <= int(mesh.use_fake_user):
                    bpy.data.meshes.remove(mesh)
            bpy.data.collections.remove(collection)
