"""T-A1 bis — qualité géométrique à ×3 et ×6 pour chaque contrôle timide, par sexe (Morphologie 0/1) et par âge (stades 0 à 3).
Via shim ; cage seule ; rien n'est sauvegardé. Sortie : JSON."""
import sys, json
from pathlib import Path
import bpy, numpy as np
from extension.proportions import CONTROLS, property_name

out = Path(sys.argv[sys.argv.index("--") + 1]).resolve(); out.mkdir(parents=True, exist_ok=True)
assert bpy.ops.human_modeling.create() == {"FINISHED"}
body = bpy.context.object; keys = body.data.shape_keys; me = body.data
for m in body.modifiers:
    m.show_viewport = False
polys = [tuple(p.vertices) for p in me.polygons]
tri = np.array([p[:3] for p in polys]); edges = np.array([e.vertices[:] for e in me.edges])


def coords():
    keys.update_tag(); bpy.context.view_layer.update()
    ev = body.evaluated_get(bpy.context.evaluated_depsgraph_get()); m = ev.to_mesh()
    a = np.empty(len(m.vertices) * 3); m.vertices.foreach_get("co", a); ev.to_mesh_clear(); return a.reshape(-1, 3)


def geom(co):
    p0, p1, p2 = co[tri[:, 0]], co[tri[:, 1]], co[tri[:, 2]]
    n = np.cross(p1 - p0, p2 - p0); a = np.linalg.norm(n, axis=1) / 2
    el = np.linalg.norm(co[edges[:, 0]] - co[edges[:, 1]], axis=1)
    return n, a, el


GROUPS = ["eyelid_aperture", "lip_thickness", "lips", "muscle_definition", "nose_width", "mouth_corner", "mouth", "facial_asymmetry", "eye_height",
          "eye_spacing", "cheeks", "nose_bridge", "jaw_angle", "chin", "ears_angle", "ears_size", "nose_length", "forehead", "head_width", "jaw", "head_height"]
ids = [i for i, _ in CONTROLS if i in GROUPS and property_name(i) in keys]
blocks = {i: [b for b in keys.key_blocks if b.name == "HM · " + i or b.name.startswith("HM · " + i + " · ")] for i in ids}
for i in ids:
    for b in blocks[i]:
        b.slider_min, b.slider_max = -10.0, 10.0
rows = []
for sex in (0.0, 1.0):
    for age in (0.0, 1.0, 2.0, 3.0):
        keys.key_blocks["Morphologie"].value = sex
        keys["human_modeling_age"] = age
        neutral = coords(); n0, a0, e0 = geom(neutral); ok0 = a0 > 1e-10
        for i in ids:
            p = property_name(i)
            for f in (1.0, 3.0, 6.0):
                for sg in (1.0, -1.0):
                    keys[p] = sg * f
                    co = coords(); n, a, el = geom(co)
                    flip = int(((np.einsum("ij,ij->i", n, n0) < 0) & ok0).sum())
                    small = int(((a < 0.1 * a0) & ok0).sum())
                    stretch = int((el > 2.5 * np.maximum(e0, 1e-9)).sum())
                    mm = float(np.linalg.norm(co - neutral, axis=1).max()) * 1000
                    rows.append({"control": i, "sexe": sex, "age": age, "facteur": sg * f, "faces_retournees": flip, "faces_petites": small, "aretes_etirees": stretch, "max_mm": round(mm, 2)})
            keys[p] = 0.0
(out / "amplitude_matrix.json").write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
print("MATRIX_DONE", len(rows))
