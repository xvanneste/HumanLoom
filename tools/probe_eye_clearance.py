"""Measure eye/orbit intersections under small reversible eye fit changes."""
import json
from pathlib import Path
import sys
import bpy
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_age_dimensions import surface
from validate_age_eye_fit import crossings

asset, output = [Path(p).resolve() for p in sys.argv[sys.argv.index("--")+1:]]
with bpy.data.libraries.load(str(asset), link=False) as (_, target):
    target.collections = ["Realistic Human Base"]
collection = target.collections[0]
bpy.context.scene.collection.children.link(collection)
body = next(obj for obj in collection.objects if obj.get("human_modeling_body"))
body.modifiers.new("QA", "SUBSURF").levels = 1
eye = list(body.children)[0]
records = []
for sex in (0., 1.):
    body.data.shape_keys.key_blocks["Morphologie"].value = sex
    body.data.shape_keys.update_tag()
    bpy.context.view_layer.update()
    bp, bf = surface(body)
    ep, ef = surface(eye)
    center = (ep.min(axis=0)+ep.max(axis=0))/2
    print("EYE", sex, "center", center, "extent", np.ptp(ep, axis=0), flush=True)
    for scale in (1., .99, .97, .95, .92, .88):
        for offset in (0., -.001, .001, .002):
            points = (ep-center)*scale+center+np.array((0,offset,0))
            data = crossings(bp,bf,points,ef)
            records.append({"sex":sex,"scale":scale,"offset_y_m":offset,**data})
            print("FIT",sex,scale,offset,data["crossing_pairs"],flush=True)
output.parent.mkdir(parents=True,exist_ok=True)
output.write_text(json.dumps(records,indent=2),encoding="utf-8")
