"""Génère `tools/data/neutral_reference.json` : forme neutre figée de l'asset actuel (D-19).

Usage : blender --background --factory-startup --python tools/make_neutral_reference.py
Régénération VOLONTAIRE uniquement (changement assumé de la forme de l'asset) ; relire le diff avant de la garder."""
import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import neutral_reference as ref

with bpy.data.libraries.load(str(ref.ASSET), link=False) as (_, target):
    target.collections = ["Realistic Human Base"]
collection = target.collections[0]
bpy.context.scene.collection.children.link(collection)
body = next(o for o in collection.objects if o.get("human_modeling_body"))
states = {}
for sex in ref.SEXES:
    for stage in ref.STAGES:
        ref.set_state(body, sex, stage)
        points = ref.cage(body)
        body_points, eye_points = ref.sample(body)
        states[ref.key(sex, stage)] = {"points": [round(float(c), 6) for c in body_points.ravel()],
                                       "eyes": [[round(float(c), 6) for c in eye.ravel()] for eye in eye_points],
                                       "cage_sha256_1e-6": ref.fingerprint(points)}
data = {"purpose": "Forme neutre de l'asset actuel (D-19), cage sans modificateurs, autres commandes à 0",
        "asset_sha256": ref.asset_sha256(), "blender": bpy.app.version_string, "vertices": len(body.data.vertices),
        "stride": ref.STRIDE, "zone_stride": ref.ZONE_STRIDE, "eye_stride": ref.EYE_STRIDE, "eyelid_radius_m": ref.EYELID_RADIUS, "tolerance_m": ref.TOLERANCE, "states": states}
ref.REFERENCE.parent.mkdir(exist_ok=True)
ref.REFERENCE.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
print("NEUTRAL_REFERENCE_OK", ref.REFERENCE, ref.REFERENCE.stat().st_size, "octets", len(states), "états")
