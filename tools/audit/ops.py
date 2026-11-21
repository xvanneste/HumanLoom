"""Exhaustive operator / property exercise (throwaway)."""
import sys, json, time, math, traceback
from pathlib import Path
import bpy, bmesh, numpy as np
from extension import anatomy, measurements, groom, geometry_quality
from extension.proportions import CONTROLS, property_name
out = Path(sys.argv[sys.argv.index("--") + 1]); out.mkdir(parents=True, exist_ok=True)
R = {}; LOG = []
def step(name, fn):
    t = time.perf_counter()
    try:
        v = fn(); R[name] = {"ok": True, "value": v, "ms": round((time.perf_counter() - t) * 1000)}
    except Exception as e:
        R[name] = {"ok": False, "error": f"{type(e).__name__}: {str(e)[:160]}", "ms": round((time.perf_counter() - t) * 1000)}
def fin(r): return list(r)[0]
def clear():
    if bpy.context.mode != "OBJECT": bpy.ops.object.mode_set(mode="OBJECT")
    for o in tuple(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
def new_body():
    clear(); bpy.ops.human_modeling.create(); b = bpy.context.object; return b
def poll_table():
    ops = [o for o in dir(bpy.ops.human_modeling) if not o.startswith("_")] + ["humanloom." + o for o in dir(bpy.ops.humanloom) if not o.startswith("_")]
    res = {}
    for o in ops:
        mod, name = (o.split(".") if "." in o else ("human_modeling", o))
        res[o] = bool(getattr(getattr(bpy.ops, mod), name).poll())
    return res

# A. polls by context
def polls():
    out_ = {}
    clear(); out_["empty_scene"] = poll_table()
    b = new_body(); out_["body_selected"] = poll_table()
    eye = [c for c in b.children if c.type == "MESH"][0]
    bpy.ops.object.select_all(action="DESELECT"); eye.select_set(True); bpy.context.view_layer.objects.active = eye
    out_["eye_active"] = poll_table()
    bpy.context.view_layer.objects.active = b; b.select_set(True); bpy.ops.object.mode_set(mode="EDIT")
    out_["edit_mode"] = poll_table(); bpy.ops.object.mode_set(mode="OBJECT")
    return out_
step("polls", polls)
body = new_body(); keys = body.data.shape_keys
def refresh(): keys.update_tag(); bpy.context.view_layer.update()

# B. measurements, landmarks, fit
def measure_all():
    refresh(); return {k: v for k, v in measurements.measure(body, bpy.context).items() if k != "segments"}
step("measure", measure_all)
def lm_flow():
    res = {}
    bpy.context.view_layer.objects.active = body; body.select_set(True)
    co = np.array([v.co[:] for v in body.data.vertices]); H = np.ptp(co[:, 2]); z0 = co[:, 2].min()
    def vert_near(x, zf, yf=-1):  # nearest vertex to a point (x, front)
        target = np.array([x, -0.08 * (yf == -1), z0 + zf * H]); d = np.linalg.norm(co - target, axis=1); d[co[:, 0] * x < 0] = 9; return int(d.argmin())
    picks = {"pelvis": vert_near(0, .52), "waist_level": vert_near(0, .62), "hips_level": vert_near(0, .52), "chest_level": vert_near(0, .72),
             "al_l": vert_near(.016, .915), "al_r": vert_near(-.016, .915), "ch_l": vert_near(.025, .893), "ch_r": vert_near(-.025, .893),
             "en_l": vert_near(.016, .935), "en_r": vert_near(-.016, .935)}
    for ident, vi in picks.items():
        bpy.ops.object.mode_set(mode="EDIT"); bm = bmesh.from_edit_mesh(body.data); bm.verts.ensure_lookup_table()
        for v in bm.verts: v.select = False
        bm.verts[vi].select = True; bmesh.update_edit_mesh(body.data)
        body.hm_landmark = ident
        r = bpy.ops.human_modeling.mark_pelvis() if ident == "pelvis" else bpy.ops.human_modeling.mark_anatomy()
        bpy.ops.object.mode_set(mode="OBJECT"); res["mark_" + ident] = fin(r)
    refresh()
    res["landmarks_markers"] = len([c for c in body.children if c.get(anatomy.LANDMARK_KEY)])
    return res
step("landmark_flow", lm_flow)
def fit_flow():
    res = {}
    for key, label, _ in anatomy.MEASURES:
        try:
            v0 = anatomy.value(body, bpy.context, key)
            tgt = v0 * 1.05 if key != "pelvis_ratio" else v0 * 1.02
            r = bpy.ops.human_modeling.fit_measurement(measurement=key, target_cm=tgt * 100 if key != "pelvis_ratio" else tgt * 100)
            refresh(); v1 = anatomy.value(body, bpy.context, key)
            res[key] = {"result": fin(r), "before": round(v0, 4), "target": round(tgt, 4), "after": round(v1, 4)}
            # far out of range
            try:
                r2 = bpy.ops.human_modeling.fit_measurement(measurement=key, target_cm=v0 * 100 * 3 if key != "pelvis_ratio" else 500)
                refresh(); res[key]["extreme"] = {"result": fin(r2), "value": round(anatomy.value(body, bpy.context, key), 4)}
            except Exception as e: res[key]["extreme"] = "ERR " + str(e)[:80]
            bpy.ops.human_modeling.reset_proportions()
        except Exception as e: res[key] = "ERR " + str(e)[:120]
    return res
step("fit_measurements", fit_flow)
def lm_io():
    p = out / "lm.json"; res = {}
    res["save"] = fin(bpy.ops.human_modeling.save_landmarks(filepath=str(p)))
    res["mirror_none_missing"] = fin(bpy.ops.human_modeling.mirror_landmarks())
    for c in [c for c in body.children if c.get(anatomy.LANDMARK_KEY) in ("al_r", "ch_r")]: bpy.data.objects.remove(c, do_unlink=True)
    res["mirror_two_missing"] = fin(bpy.ops.human_modeling.mirror_landmarks())
    res["load"] = fin(bpy.ops.human_modeling.load_landmarks(filepath=str(p)))
    return res
step("landmark_io", lm_io)
def reference():
    res = {}; n = 0; bad = 0
    for g, _, _ in measurements.GROUPS:
        for s in ("M", "F"):
            for pc in ("P05", "P50", "P95"):
                body.hm_reference_group = g; body.hm_reference_sex = s; body.hm_reference_percentile = pc
                try:
                    r = measurements.report(body, bpy.context); n += 1
                    if "reference" not in r and "stature_reference" not in r: pass
                except Exception as e: bad += 1; res.setdefault("errors", []).append(f"{g}/{s}/{pc}: {str(e)[:60]}")
    res["combos"] = n; res["bad"] = bad
    body.hm_reference_group = "30_39"; body.hm_reference_sex = "M"; body.hm_reference_percentile = "P50"
    res["reference_height"] = fin(bpy.ops.human_modeling.reference_height())
    refresh(); res["height_after_cm"] = round(measurements.measure(body, bpy.context)["height_m"] * 100, 2)
    res["report_export"] = fin(bpy.ops.human_modeling.measurement_report(filepath=str(out / "m.json")))
    res["geometry_export"] = fin(bpy.ops.human_modeling.export_geometry_report(filepath=str(out / "g.json")))
    return res
step("reference_and_reports", reference)

# C. misc operators
body = new_body(); keys = body.data.shape_keys
step("smooth_op", lambda: {"result": fin(bpy.ops.human_modeling.smooth()), "mods": [(m.name, m.type) for m in body.modifiers]})
step("add_proportions_on_current", lambda: fin(bpy.ops.human_modeling.add_proportions()))
step("repair_surface", lambda: fin(bpy.ops.human_modeling.repair_surface()))
step("reset_proportions", lambda: fin(bpy.ops.human_modeling.reset_proportions()))
def create_variants():
    res = []
    for loc in ((0, 0, 0), (5, 0, 0), (-5, 3, 0)):
        bpy.context.scene.cursor.location = loc; bpy.ops.human_modeling.create(); b = bpy.context.object
        res.append({"name": b.name, "loc": [round(x, 2) for x in b.location], "verts": len(b.data.vertices), "shape_data": b.data.name, "keys": b.data.shape_keys.name})
    return res
step("create_multiple", create_variants)

# D. transforms and duplicates
def transforms():
    b = new_body(); res = {}
    b.rotation_euler = (math.radians(90), 0, 0); bpy.context.view_layer.update()
    try: res["rot90_x_set_height"] = fin(bpy.ops.human_modeling.set_height(height=1.8)); bpy.context.view_layer.update(); res["rot_measure_h"] = round(measurements.measure(b, bpy.context)["height_m"], 4)
    except Exception as e: res["rot90"] = "ERR " + str(e)[:100]
    b.rotation_euler = (0, 0, 0); b.scale = (1, 2, 1); bpy.context.view_layer.update()
    try: res["nonuniform_set_height"] = fin(bpy.ops.human_modeling.set_height(height=1.8)); res["nonuniform_scale_after"] = [round(x, 3) for x in b.scale]
    except Exception as e: res["nonuniform"] = "ERR " + str(e)[:100]
    b.scale = (1, 1, 1)
    # duplicate
    bpy.ops.object.select_all(action="DESELECT"); b.select_set(True); bpy.context.view_layer.objects.active = b
    bpy.ops.object.duplicate(); d = bpy.context.object
    res["dup_shares_mesh"] = d.data == b.data; res["dup_shares_keys"] = d.data.shape_keys == b.data.shape_keys
    d.data.shape_keys["hm_shoulders"] = 1.0; d.data.shape_keys.update_tag(); bpy.context.view_layer.update()
    ev = lambda o: np.array([v.co[:] for v in o.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices])
    res["dup_independent_edit"] = float(np.abs(ev(d) - ev(b)).max()) > 1e-4
    res["dup_children"] = len(d.children)
    ch = [c for c in d.children if c.type == "MESH"]
    if ch:
        k = ch[0].data.shape_keys
        res["dup_eye_driver_target"] = [v.targets[0].id.name if v.targets[0].id else None for dr in (k.animation_data.drivers if k and k.animation_data else [])[:1] for v in dr.driver.variables]
    return res
step("transforms_duplicates", transforms)

# E. groom exhaustive
def groom_all():
    b = new_body(); res = {}; bpy.context.view_layer.objects.active = b
    for region, label, _ in groom.REGIONS:
        b.hl_groom_region = region; t = time.perf_counter()
        try:
            r = bpy.ops.humanloom.groom_build(); h = groom.find(b, region)
            res[region] = {"res": fin(r), "s": round(time.perf_counter() - t, 2), "guides": len(h.data.curves) if h else None, "mods": [m.name for m in h.modifiers] if h else None}
        except Exception as e: res[region] = "ERR " + str(e)[:120]
    return res
step("groom_build_each_region", groom_all)
def groom_params():
    res = {}; b = [o for o in bpy.data.objects if o.get("human_modeling_body")][0]; bpy.context.view_layer.objects.active = b
    b.hl_groom_region = "SCALP"; hair = groom.find(b, "SCALP"); s = hair.hl_groom
    def eval_count():
        bpy.context.view_layer.update(); return len(hair.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.curves)
    base = eval_count(); res["base_eval_curves"] = base
    tests = {"nature": (0, 1), "variation": (0, .8), "frizz": (0, 1), "viewport": (0, 1), "density": (0, 8000000), "radius": (.000005, .00015), "grey": (0, 1), "roughness": (.05, 1),
             "bendiness": (0, 1), "root_bendiness": (0, 1)}
    for k, (lo, hi) in tests.items():
        for v in (lo, hi):
            try:
                setattr(s, k, v); r = bpy.ops.humanloom.groom_apply(); res[f"{k}={v}"] = {"res": fin(r), "eval": eval_count()}
            except Exception as e: res[f"{k}={v}"] = "ERR " + str(e)[:100]
        setattr(s, k, groom.defaults("SCALP").get(k, getattr(s, k)))
    for k, vals in (("length", (.001, .45)), ("guides", (20, 3000)), ("seed", (0, 2147483647))):
        for v in vals:
            try:
                setattr(s, k, v); r = bpy.ops.humanloom.groom_build(); hair = groom.find(b, "SCALP"); s = hair.hl_groom; res[f"{k}={v}"] = {"res": fin(r), "guides": len(hair.data.curves), "eval": eval_count()}
            except Exception as e: res[f"{k}={v}"] = "ERR " + str(e)[:100]
    for st in ("SWEPT", "PARTED", "UPRIGHT"):
        try: s.style = st; r = bpy.ops.humanloom.groom_build(); hair = groom.find(b, "SCALP"); s = hair.hl_groom; res["style=" + st] = fin(r)
        except Exception as e: res["style=" + st] = "ERR " + str(e)[:100]
    for q in ("LIGHT", "BALANCED", "FULL", "CUSTOM"):
        try: res["quality=" + q] = {"res": fin(bpy.ops.humanloom.groom_quality(preset=q, all_layers=True)), "eval": eval_count()}
        except Exception as e: res["quality=" + q] = "ERR " + str(e)[:100]
    for d in ("SPARSE", "NORMAL", "DENSE"):
        try: res["density_preset=" + d] = {"res": fin(bpy.ops.humanloom.groom_density(preset=d)), "density": groom.find(b, "SCALP").hl_groom.density}
        except Exception as e: res["density_preset=" + d] = "ERR " + str(e)[:100]
    res["select"] = fin(bpy.ops.humanloom.groom_select()); bpy.context.view_layer.objects.active = b
    try: res["paint"] = fin(bpy.ops.humanloom.groom_paint()); res["mode_after_paint"] = bpy.context.mode; bpy.ops.object.mode_set(mode="OBJECT")
    except Exception as e: res["paint"] = "ERR " + str(e)[:100]
    return res
step("groom_parameters", groom_params)
def groom_phys():
    b = [o for o in bpy.data.objects if o.get("human_modeling_body")][0]; b.hl_groom_region = "SCALP"; hair = groom.find(b, "SCALP"); s = hair.hl_groom
    s.physics = "XPBD"; s.guides = 128; bpy.ops.humanloom.groom_build(); hair = groom.find(b, "SCALP"); s = hair.hl_groom
    res = {}
    t = time.perf_counter(); bpy.context.scene.frame_set(1)
    for f in (2, 6, 12):
        bpy.context.scene.frame_set(f)
    res["xpbd_frames_s"] = round(time.perf_counter() - t, 2); bpy.context.scene.frame_set(1)
    return res
step("groom_xpbd", groom_phys)
def groom_io():
    b = [o for o in bpy.data.objects if o.get("human_modeling_body")][0]; bpy.context.view_layer.objects.active = b; res = {}
    p = out / "groom.json"; res["export"] = fin(bpy.ops.humanloom.groom_export(filepath=str(p))); data = json.loads(p.read_text(encoding="utf-8")); res["layers"] = list(data.get("layers", {}))
    res["import_over_existing"] = "refused" if True else ""
    try: res["import_over_existing"] = fin(bpy.ops.humanloom.groom_import(filepath=str(p)))
    except Exception as e: res["import_over_existing"] = "ERR " + str(e)[:80]
    bad = out / "bad.json"; bad.write_text("{\"format\": 1}", encoding="utf-8")
    try: res["import_invalid"] = fin(bpy.ops.humanloom.groom_import(filepath=str(bad)))
    except Exception as e: res["import_invalid"] = "ERR " + str(e)[:80]
    for r in [h.get("hl_groom_region") for h in b.children if h.type == "CURVES"]:
        b.hl_groom_region = r; bpy.ops.humanloom.groom_remove()
    res["after_remove_curves"] = len([h for h in b.children if h.type == "CURVES"])
    res["import_clean"] = fin(bpy.ops.humanloom.groom_import(filepath=str(p))); res["after_import_curves"] = len([h for h in b.children if h.type == "CURVES"])
    return res
step("groom_io", groom_io)

# F. stress: all controls, random seeds with geometry
def stress():
    b = new_body(); k = b.data.shape_keys; res = {}
    for ident, _ in CONTROLS:
        if property_name(ident) in k: k[property_name(ident)] = 1.0
    k.update_tag(); bpy.context.view_layer.update()
    r = geometry_quality.report(b, bpy.context, include_eyes=True)["geometry"]["intersections"]
    res["all_plus1_modifiers_on"] = {"pairs": r.get("crossing_triangle_pairs"), "regions": r.get("approximate_regions")}
    for ident, _ in CONTROLS:
        if property_name(ident) in k: k[property_name(ident)] = -1.0
    k.update_tag(); bpy.context.view_layer.update()
    r = geometry_quality.report(b, bpy.context, include_eyes=True)["geometry"]["intersections"]
    res["all_minus1_modifiers_on"] = {"pairs": r.get("crossing_triangle_pairs"), "regions": r.get("approximate_regions")}
    bpy.ops.human_modeling.reset_proportions()
    pairs = []
    for seed in range(0, 30):
        bpy.ops.human_modeling.randomize(seed=seed, strength=1.0, scope="ALL"); k.update_tag(); bpy.context.view_layer.update()
        gi = geometry_quality.report(b, bpy.context, include_eyes=True)["geometry"]["intersections"]; pairs.append(gi.get("crossing_triangle_pairs"))
    res["random_all_strength1_30_seeds_pairs"] = pairs
    return res
step("stress", stress)
(out / "ops.json").write_text(json.dumps(R, indent=1, ensure_ascii=False, default=str), encoding="utf-8"); print("OPS_DONE")
