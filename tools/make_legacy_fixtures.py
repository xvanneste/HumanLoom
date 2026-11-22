"""Génère les fixtures d'anciennes versions manquantes (I-47) à partir de `tools/data/realistic.blend`.

Usage : blender --background --factory-startup --python tools/make_legacy_fixtures.py -- <dossier_sortie>
Produit `adult-original.blend` (corps sans aucun réglage de proportions, schéma absent) et `legacy-03.blend`
(schéma 3 : seuls les réglages `hm_mouth` et `hm_shoulders` existent), plus `fixtures.json` (faits mesurés).

ATTENTION : ces fichiers sont SYNTHÉTIQUES. Ils retirent de l'asset actuel toutes les clés de forme
sauf `Basis` et `Morphologie` (et les réglages gardés), les propriétés `hm_*`, le relief de peau et les marqueurs de schéma. Ils ne sont pas
les fichiers historiques de l'auteur, que le dépôt ne contient pas : un test qui passe sur eux ne prouve pas la compatibilité
avec une vraie ancienne session."""
import json
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
OUT.mkdir(parents=True, exist_ok=True)
ASSET = ROOT / "tools/data/realistic.blend"
COLLECTION = "Realistic Human Base"
BASE_KEYS = ("Basis", "Morphologie")
BODY_PROPS = ("human_modeling_age_targets", "age_source", "hm_anatomy_candidate", "hm_surface_frames", "hm_regional_muscles_version")
DATA_PROPS = ("human_modeling_schema", "human_modeling_base", "human_modeling_surface_revision")


def is_kept(name, kept):
    return any(name == "HM · " + control or name.startswith("HM · " + control + " · ") for control in kept)


def strip(body, kept, schema):
    for obj in (body, *body.children):
        shape_keys = obj.data.shape_keys
        for key in tuple(shape_keys.key_blocks):
            if key.name not in BASE_KEYS and not is_kept(key.name, kept):
                obj.shape_key_remove(key)
        if shape_keys.animation_data:
            for curve in tuple(shape_keys.animation_data.drivers):
                path = curve.data_path
                if path.startswith("key_blocks[") and path.split('"')[1] not in shape_keys.key_blocks:
                    shape_keys.animation_data.drivers.remove(curve)
        for name in tuple(shape_keys.keys()):
            if (name.startswith("hm_") and name not in {"hm_" + c for c in kept}) or name == "human_modeling_age":
                del shape_keys[name]
    for name in BODY_PROPS:
        if name in body:
            del body[name]
    for name in DATA_PROPS:
        if name in body.data:
            del body.data[name]
    if schema:
        body.data["human_modeling_schema"] = schema
    modifier = body.modifiers.get("Human Modeling · Relief de peau")
    if modifier:
        body.modifiers.remove(modifier)
    group = body.vertex_groups.get("HM · Relief visage")
    if group:
        body.vertex_groups.remove(group)


def build(name, kept, schema):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with bpy.data.libraries.load(str(ASSET), link=False) as (_, target):
        target.collections = [COLLECTION]
    collection = target.collections[0]
    bpy.context.scene.collection.children.link(collection)
    body = next(obj for obj in collection.objects if obj.get("human_modeling_body"))
    strip(body, kept, schema)
    keys = body.data.shape_keys
    drivers = keys.animation_data.drivers if keys.animation_data else []
    facts = {
        "schema": body.data.get("human_modeling_schema"), "body_keys": len(keys.key_blocks), "body_drivers": len(drivers),
        "invalid_drivers": sum(1 for d in drivers if not d.driver.is_valid),
        "hm_props": sorted(k for k in keys.keys() if k.startswith("hm_")), "modifiers": [m.name for m in body.modifiers],
        "eye_keys": [len(e.data.shape_keys.key_blocks) for e in body.children],
    }
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / name), compress=True)
    return facts


report = {"synthetique": True, "source": "tools/data/realistic.blend",
          "adult-original.blend": build("adult-original.blend", (), None),
          "legacy-03.blend": build("legacy-03.blend", ("mouth", "shoulders"), 3)}
print("FIXTURES_FACTS", json.dumps(report, ensure_ascii=False))
assert report["adult-original.blend"]["body_keys"] == 2 and report["adult-original.blend"]["schema"] is None
assert report["legacy-03.blend"]["schema"] == 3 and report["legacy-03.blend"]["hm_props"] == ["hm_mouth", "hm_shoulders"]
assert report["legacy-03.blend"]["invalid_drivers"] == 0
(OUT / "fixtures.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
print("FIXTURES_OK", json.dumps(report, ensure_ascii=False))
