"""Analyse de redondance des 48 contrôles : champs de déplacement à +1 et -1 (cage seule), similarité cosinus et recouvrement.
Lancer via shim : blender --background --factory-startup --python tools/audit/shim.py -- --shim-root <repo> --shim-test tools/audit/control_similarity.py -- <sortie>
Rien n'est sauvegardé ; corps créé dans une session éphémère."""
import sys, json
from pathlib import Path
import bpy, numpy as np
from extension.proportions import CONTROLS, property_name

out = Path(sys.argv[sys.argv.index("--") + 1]); out.mkdir(parents=True, exist_ok=True)
assert bpy.ops.human_modeling.create() == {"FINISHED"}
body = bpy.context.object; keys = body.data.shape_keys
for m in body.modifiers:
    m.show_viewport = False


def coords():
    keys.update_tag(); bpy.context.view_layer.update()
    ev = body.evaluated_get(bpy.context.evaluated_depsgraph_get()); me = ev.to_mesh()
    a = np.empty(len(me.vertices) * 3); me.vertices.foreach_get("co", a); ev.to_mesh_clear(); return a


neutral = coords()
D = {}
for ident, label in CONTROLS:
    p = property_name(ident)
    if p not in keys:
        continue
    for s in (1.0, -1.0):
        keys[p] = s; D[(ident, s)] = coords() - neutral
    keys[p] = 0.0
ids = [i for i, _ in CONTROLS if (i, 1.0) in D]
labels = dict(CONTROLS)


def cos(a, b):
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    return float(a @ b / (na * nb)) if na > 1e-9 and nb > 1e-9 else 0.0


res = {"controles": {}, "paires_cos_abs_sup_0_6": [], "amplitude_faible": []}
for i in ids:
    d = D[(i, 1.0)]; d2 = D[(i, -1.0)]
    mag = np.linalg.norm(d.reshape(-1, 3), axis=1)
    res["controles"][i] = {"label": labels[i], "max_mm_plus": round(float(mag.max()) * 1000, 2), "symetrie_cos_plus_moins": round(cos(d, -d2), 3),
                           "sommets_deplaces_pct": round(float((mag > 1e-5).mean()) * 100, 1)}
    if mag.max() * 1000 < 2.0:
        res["amplitude_faible"].append([i, round(float(mag.max()) * 1000, 2)])
for a in range(len(ids)):
    for b in range(a + 1, len(ids)):
        c = cos(D[(ids[a], 1.0)], D[(ids[b], 1.0)])
        if abs(c) > 0.6:
            # recouvrement des sommets déplacés
            ma = np.linalg.norm(D[(ids[a], 1.0)].reshape(-1, 3), axis=1) > 1e-5
            mb = np.linalg.norm(D[(ids[b], 1.0)].reshape(-1, 3), axis=1) > 1e-5
            res["paires_cos_abs_sup_0_6"].append({"a": ids[a], "b": ids[b], "cos": round(c, 3), "recouvrement_pct_de_a": round(float((ma & mb).sum() / max(ma.sum(), 1)) * 100, 1)})
res["paires_cos_abs_sup_0_6"].sort(key=lambda x: -abs(x["cos"]))
(out / "control_similarity.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
print("SIM_DONE")
