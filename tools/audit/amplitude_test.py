"""T-A1 — qualité géométrique des contrôles à ×1, ×2, ×3 (cage seule, corps neutre par défaut).
Les clés de forme ont un curseur borné à ±1 : on élargit temporairement leur plage (slider_min/max) pour simuler un facteur d'amplitude.
Lancer via shim : blender --background --factory-startup --python tools/audit/shim.py -- --shim-root <repo> --shim-test tools/audit/amplitude_test.py -- <sortie>
Rien n'est sauvegardé."""
import sys, json
from pathlib import Path
import bpy, numpy as np
from extension.proportions import CONTROLS, property_name

out = Path(sys.argv[sys.argv.index("--") + 1]); out.mkdir(parents=True, exist_ok=True)
assert bpy.ops.human_modeling.create() == {"FINISHED"}
body = bpy.context.object; keys = body.data.shape_keys; me = body.data
for m in body.modifiers:
    m.show_viewport = False
nv = len(me.vertices)
polys = [tuple(p.vertices) for p in me.polygons]
tri = np.array([p[:3] for p in polys])           # première fan de chaque face (suffisant pour normales/aires)
edges = np.array([e.vertices[:] for e in me.edges])


def coords():
    keys.update_tag(); bpy.context.view_layer.update()
    ev = body.evaluated_get(bpy.context.evaluated_depsgraph_get()); m = ev.to_mesh()
    a = np.empty(len(m.vertices) * 3); m.vertices.foreach_get("co", a); ev.to_mesh_clear(); return a.reshape(-1, 3)


def geom(co):
    p0, p1, p2 = co[tri[:, 0]], co[tri[:, 1]], co[tri[:, 2]]
    n = np.cross(p1 - p0, p2 - p0); a = np.linalg.norm(n, axis=1) / 2
    el = np.linalg.norm(co[edges[:, 0]] - co[edges[:, 1]], axis=1)
    return n, a, el


neutral = coords(); n0, a0, e0 = geom(neutral)
ok0 = a0 > 1e-10
res = {"controles": {}}
GROUPS = ["eyelid_aperture", "lip_thickness", "lips", "muscle_definition", "nose_width", "mouth_corner", "mouth", "facial_asymmetry", "eye_height",
          "eye_spacing", "cheeks", "nose_bridge", "jaw_angle", "chin", "ears_angle", "ears_size", "nose_length", "forehead", "head_width", "jaw",
          "muscles_abdomen", "fat_face", "head_height"]
ids = [i for i, _ in CONTROLS if i in GROUPS]
for ident in ids:
    prop = property_name(ident)
    if prop not in keys:
        continue
    blocks = [b for b in keys.key_blocks if b.name == "HM · " + ident or b.name.startswith("HM · " + ident + " · ")]
    saved = [(b, b.slider_min, b.slider_max) for b in blocks]
    for b in blocks:
        b.slider_min, b.slider_max = -10.0, 10.0
    r = {}
    for s in (1.0, 2.0, 3.0, 6.0, 10.0, -1.0, -2.0, -3.0, -6.0, -10.0):
        try:
            keys[prop] = s
        except Exception as e:
            r[f"{s:+.0f}"] = "ERR " + str(e)[:80]; continue
        co = coords(); n, a, el = geom(co)
        d = np.linalg.norm(co - neutral, axis=1)
        flip = (np.einsum("ij,ij->i", n, n0) < 0) & ok0
        r[f"{s:+.0f}"] = {"finite": bool(np.isfinite(co).all()), "max_mm": round(float(d.max()) * 1000, 2),
                          "faces_retournees": int(flip.sum()),
                          "faces_aire_inf_10pct": int(((a < 0.1 * a0) & ok0).sum()),
                          "aretes_x2_5": int((el > 2.5 * np.maximum(e0, 1e-9)).sum())}
    keys[prop] = 0.0
    for b, lo, hi in saved:
        b.slider_min, b.slider_max = lo, hi
    if isinstance(r.get("+1"), dict) and isinstance(r.get("+2"), dict) and r["+1"]["max_mm"] > 0:
        r["linearite_x2"] = round(r["+2"]["max_mm"] / r["+1"]["max_mm"], 2)
        if isinstance(r.get("+3"), dict):
            r["linearite_x3"] = round(r["+3"]["max_mm"] / r["+1"]["max_mm"], 2)
    res["controles"][ident] = r
(out / "amplitude_test.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
print("AMP_DONE")
