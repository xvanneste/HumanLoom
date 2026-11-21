"""Functional exploration of HumanLoom controls (throwaway, not part of the repo)."""
import sys, json, time, math, statistics
from pathlib import Path
import bpy, numpy as np
from mathutils.kdtree import KDTree
from extension.proportions import CONTROLS, property_name

out = Path(sys.argv[sys.argv.index("--") + 1]); out.mkdir(parents=True, exist_ok=True)
rep = {}

def evaluated_coords(body, mods=True):
    body.data.shape_keys.update_tag(); bpy.context.view_layer.update()
    ev = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = ev.to_mesh()
    a = np.empty(len(me.vertices) * 3); me.vertices.foreach_get("co", a)
    ev.to_mesh_clear()
    return a.reshape(-1, 3)

t0 = time.perf_counter()
assert bpy.ops.human_modeling.create() == {"FINISHED"}
rep["create_seconds"] = round(time.perf_counter() - t0, 3)
body = bpy.context.object
keys = body.data.shape_keys
for m in body.modifiers:
    m.show_viewport = False   # control cage = shape keys only (for geometry comparison)
neutral = evaluated_coords(body)
# mirror map on neutral
kd = KDTree(len(neutral))
for i, c in enumerate(neutral): kd.insert(c, i)
kd.balance()
mirror = np.array([kd.find((-c[0], c[1], c[2]))[1] for c in neutral])
def asym(co): return float(np.mean(np.linalg.norm(co - (co[mirror] * np.array([-1, 1, 1])), axis=1)))
rep["neutral"] = {"verts": len(neutral), "height": float(np.ptp(neutral[:, 2])), "asym_mm": asym(neutral) * 1000,
                  "bbox": [float(x) for x in np.ptp(neutral, axis=0)]}

# A. every control at -1 and +1
rows = []
for ident, label in CONTROLS:
    prop = property_name(ident)
    if prop not in keys:
        rows.append({"id": ident, "label": label, "missing": True}); continue
    r = {"id": ident, "label": label}
    for v in (-1.0, 1.0):
        keys[prop] = v
        t = time.perf_counter(); co = evaluated_coords(body); dt = time.perf_counter() - t
        d = np.linalg.norm(co - neutral, axis=1)
        r[f"{v:+.0f}"] = {"finite": bool(np.isfinite(co).all()), "max_mm": round(float(d.max()) * 1000, 2),
                          "mean_mm": round(float(d.mean()) * 1000, 3), "verts_moved_pct": round(float((d > 1e-5).mean()) * 100, 1),
                          "dheight_mm": round(float(np.ptp(co[:, 2]) - np.ptp(neutral[:, 2])) * 1000, 2),
                          "asym_mm": round(asym(co) * 1000, 3), "ms": round(dt * 1000, 1)}
    keys[prop] = 0.0
    rows.append(r)
rep["controls"] = rows
back = evaluated_coords(body)
rep["reset_residual_mm"] = round(float(np.linalg.norm(back - neutral, axis=1).max()) * 1000, 4)

# B. slider timing with modifiers on
for m in body.modifiers: m.show_viewport = True
times = []
for i in range(40):
    keys[property_name("shoulders")] = (i % 10) / 10 - .5
    t = time.perf_counter(); evaluated_coords(body); times.append((time.perf_counter() - t) * 1000)
keys[property_name("shoulders")] = 0.0
rep["slider_eval_ms_with_modifiers"] = {"median": round(statistics.median(times), 1), "max": round(max(times), 1)}
for m in body.modifiers: m.show_viewport = False
times = []
for i in range(40):
    keys[property_name("shoulders")] = (i % 10) / 10 - .5
    t = time.perf_counter(); evaluated_coords(body); times.append((time.perf_counter() - t) * 1000)
keys[property_name("shoulders")] = 0.0
rep["slider_eval_ms_cage_only"] = {"median": round(statistics.median(times), 1), "max": round(max(times), 1)}
rep["shape_key_count"] = len(keys.key_blocks); rep["driver_count"] = len(keys.animation_data.drivers)

# C. sex and age
for m in body.modifiers: m.show_viewport = False
rows = []
for sex in (0.0, .25, .5, .75, 1.0):
    keys.key_blocks["Morphologie"].value = sex
    co = evaluated_coords(body)
    rows.append({"sex": sex, "height_m": round(float(np.ptp(co[:, 2])), 4), "width_m": round(float(np.ptp(co[:, 0])), 4), "finite": bool(np.isfinite(co).all())})
keys.key_blocks["Morphologie"].value = 0.0
rep["sex_sweep"] = rows
rows = []
for age in (0, .5, 1, 1.5, 2, 2.5, 3):
    keys["human_modeling_age"] = float(age)
    co = evaluated_coords(body)
    rows.append({"age_stage": age, "height_m": round(float(np.ptp(co[:, 2])), 4), "finite": bool(np.isfinite(co).all()),
                 "max_mm_vs_neutral": round(float(np.linalg.norm(co - neutral, axis=1).max()) * 1000, 1)})
keys["human_modeling_age"] = 2.0
rep["age_sweep"] = rows

# D. body profiles via operator
from extension.body_profiles import PROFILES
rows = []
for pid in PROFILES:
    r = bpy.ops.human_modeling.body_profile(profile=pid)
    co = evaluated_coords(body)
    rows.append({"profile": pid, "result": list(r)[0], "height_m": round(float(np.ptp(co[:, 2])), 4), "depth_m": round(float(np.ptp(co[:, 1])), 4),
                 "width_m": round(float(np.ptp(co[:, 0])), 4), "max_mm_vs_neutral": round(float(np.linalg.norm(co - neutral, axis=1).max()) * 1000, 1)})
bpy.ops.human_modeling.reset_proportions()
rep["profiles"] = rows

# E. randomize
rows = []
for scope in ("FACE", "BODY", "ALL"):
    for seed in (1, 2):
        bpy.ops.human_modeling.randomize(seed=seed, strength=1.0, scope=scope)
        co = evaluated_coords(body)
        rows.append({"scope": scope, "seed": seed, "finite": bool(np.isfinite(co).all()), "max_mm": round(float(np.linalg.norm(co - neutral, axis=1).max()) * 1000, 1)})
bpy.ops.human_modeling.reset_proportions()
rep["randomize"] = rows

# F. all extremes at once (stress)
for ident, _ in CONTROLS:
    p = property_name(ident)
    if p in keys: keys[p] = 1.0
co = evaluated_coords(body)
rep["all_controls_plus1"] = {"finite": bool(np.isfinite(co).all()), "max_mm": round(float(np.linalg.norm(co - neutral, axis=1).max()) * 1000, 1),
                             "height": round(float(np.ptp(co[:, 2])), 3)}
bpy.ops.human_modeling.reset_proportions()
(out / "ft.json").write_text(json.dumps(rep, indent=1, ensure_ascii=False), encoding="utf-8")
print("FT_DONE")
