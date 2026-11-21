"""I-37 / D-10 : l'écart de forme au neutre entre l'asset actuel et extension-13 vient-il uniquement de la clé « Atlas14 · reference » ?
Sonde en lecture seule : charge les deux assets (bibliothèque Blender), compare la cage évaluée (modificateurs coupés)
sur 5 sexes x 7 stades, puis recompare en coupant (mute) les clés présentes seulement dans l'actuel.
Usage : blender --background --factory-startup --python atlas14_probe.py -- <asset_actuel> <asset_ancien> <sortie.json>"""
import sys, json
from pathlib import Path
import bpy, numpy as np

cur_path, old_path, out = [Path(p).resolve() for p in sys.argv[sys.argv.index("--") + 1:]]
bodies = []
for path in (cur_path, old_path):
    with bpy.data.libraries.load(str(path), link=False) as (_, t):
        t.collections = ["Realistic Human Base"]
    col = t.collections[0]; bpy.context.scene.collection.children.link(col)
    obj = next(o for o in col.objects if o.get("human_modeling_body"))
    for m in obj.modifiers:
        m.show_viewport = False  # cage seule (clés de forme + drivers)
    bodies.append(obj)
cur, old = bodies
kc, ko = cur.data.shape_keys, old.data.shape_keys
only_cur = [k.name for k in kc.key_blocks if k.name not in ko.key_blocks]
only_old = [k.name for k in ko.key_blocks if k.name not in kc.key_blocks]


def cage(obj):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    mesh = ev.to_mesh()
    pts = np.array([v.co[:] for v in mesh.vertices])
    ev.to_mesh_clear()
    return pts


def refresh(obj):
    obj.data.shape_keys.update_tag(); bpy.context.view_layer.update()


rows = []
for sex in (0., .25, .5, .75, 1.):
    for stage in (0., .5, 1., 1.5, 2., 2.5, 3.):
        for obj in bodies:
            obj.data.shape_keys.key_blocks["Morphologie"].value = sex
            obj.data.shape_keys["human_modeling_age"] = stage
            refresh(obj)
        a, b = cage(cur), cage(old)
        d_all = float(np.linalg.norm(a - b, axis=1).max() * 1000) if a.shape == b.shape else None
        active = {n: round(kc.key_blocks[n].value, 4) for n in only_cur if abs(kc.key_blocks[n].value) > 1e-9}
        for n in only_cur:
            kc.key_blocks[n].mute = True
        refresh(cur)
        a2 = cage(cur)
        d_muted = float(np.linalg.norm(a2 - b, axis=1).max() * 1000)
        for n in only_cur:
            kc.key_blocks[n].mute = False
        refresh(cur)
        rows.append({"sex": sex, "stage": stage, "ecart_max_mm": None if d_all is None else round(d_all, 4),
                     "ecart_sans_cles_nouvelles_mm": round(d_muted, 4), "cles_nouvelles_actives": active})
        print("ROW", rows[-1], flush=True)
res = {"cles_seulement_actuel": only_cur, "cles_seulement_ancien": only_old, "n_cles": [len(kc.key_blocks), len(ko.key_blocks)], "cas": rows}
out.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
print("ATLAS14_PROBE_DONE", flush=True)
