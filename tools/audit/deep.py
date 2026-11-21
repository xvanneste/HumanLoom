"""Deep per-control characterisation (throwaway)."""
import sys, json, time
from pathlib import Path
import bpy, numpy as np
from extension.proportions import CONTROLS, property_name
from extension import geometry_quality
out = Path(sys.argv[sys.argv.index("--") + 1]); out.mkdir(parents=True, exist_ok=True)
bpy.ops.human_modeling.create(); body = bpy.context.object; keys = body.data.shape_keys
eyes = [c for c in body.children if c.type == "MESH"]
def refresh(): keys.update_tag(); bpy.context.view_layer.update()
def ev_coords(obj, world=False):
    ev = obj.evaluated_get(bpy.context.evaluated_depsgraph_get()); me = ev.to_mesh()
    a = np.empty(len(me.vertices) * 3); me.vertices.foreach_get("co", a); ev.to_mesh_clear(); a = a.reshape(-1, 3)
    if world:
        M = np.array(obj.matrix_world); a = a @ M[:3, :3].T + M[:3, 3]
    return a
def state(mods):
    for m in body.modifiers: m.show_viewport = mods
    refresh(); return ev_coords(body), [ev_coords(e, True).mean(axis=0) for e in eyes]
def crossings():
    t = time.perf_counter()
    r = geometry_quality.report(body, bpy.context, include_eyes=True)
    i = r["geometry"]["intersections"]
    return {"pairs": i.get("crossing_triangle_pairs"), "regions": i.get("approximate_regions"), "ms": round((time.perf_counter() - t) * 1000)}

base, base_eyes = state(False)
z0, H = base[:, 2].min(), np.ptp(base[:, 2])
BANDS = {"head": .93, "neck": .86, "shoulder": .81, "chest": .72, "waist": .62, "hip": .52, "thigh": .40, "knee": .28, "calf": .18}
def band(co, f):
    z = z0 + f * H; m = np.abs(co[:, 2] - z) < .01 * H
    if f <= .52 and f < .5 or f in (.40, .28, .18):
        m &= (co[:, 0] > .03) & (co[:, 0] < .30)
    elif f in (.72, .62, .52):
        m &= np.abs(co[:, 0]) < .23
    if m.sum() < 3: return (0.0, 0.0)
    return float(np.ptp(co[m, 0])), float(np.ptp(co[m, 1]))
base_b = {k: band(base, f) for k, f in BANDS.items()}
def bands_delta(co):
    return {k: [round((band(co, f)[0] - base_b[k][0]) * 1000, 1), round((band(co, f)[1] - base_b[k][1]) * 1000, 1)] for k, f in BANDS.items()}
ie0 = float(np.linalg.norm(base_eyes[0] - base_eyes[1]))
res = {"H": float(H), "z0": float(z0), "base_bands_mm": {k: [round(v[0] * 1000, 1), round(v[1] * 1000, 1)] for k, v in base_b.items()},
       "base_cross": None, "controls": []}
state(True); res["base_cross"] = crossings(); state(False)
for ident, label in CONTROLS:
    p = property_name(ident); r = {"id": ident, "label": label}
    for v in (-1.0, 1.0):
        keys[p] = v; co, eyec = state(False)
        d = np.linalg.norm(co - base, axis=1); mx = d.max()
        sel = d > .5 * mx if mx > 1e-9 else np.zeros(len(d), bool)
        cen = co[sel].mean(axis=0) if sel.any() else base.mean(axis=0)
        ie = float(np.linalg.norm(eyec[0] - eyec[1]))
        e_move = [round(float(np.linalg.norm(eyec[i] - base_eyes[i])) * 1000, 2) for i in (0, 1)]
        state(True); cr = crossings()
        r[f"{v:+.0f}"] = {"max_mm": round(float(mx) * 1000, 2), "where_z_frac": round(float((cen[2] - z0) / H), 3), "where_x_mm": round(float(cen[0]) * 1000, 0),
                          "where_y_mm": round(float(cen[1]) * 1000, 0), "bands_mm": bands_delta(co), "eye_move_mm": e_move,
                          "interocular_delta_mm": round((ie - ie0) * 1000, 2), "cross_pairs": cr["pairs"], "cross_regions": cr["regions"]}
        state(False)
    keys[p] = 1.0
    for tag, setup in (("sex0", lambda: keys.key_blocks["Morphologie"].__setattr__("value", 0.0)), ("age0", lambda: keys.__setitem__("human_modeling_age", 0.0)),
                       ("age1", lambda: keys.__setitem__("human_modeling_age", 1.0)), ("age3", lambda: keys.__setitem__("human_modeling_age", 3.0))):
        keys[p] = 0.0; setup(); b2, _ = state(False); keys[p] = 1.0; c2, _ = state(False)
        r["+1_" + tag] = round(float(np.linalg.norm(c2 - b2, axis=1).max()) * 1000, 2)
        keys.key_blocks["Morphologie"].value = 1.0; keys["human_modeling_age"] = 2.0
    keys[p] = 0.0; state(False)
    res["controls"].append(r)
(out / "deep.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8"); print("DEEP_DONE")
