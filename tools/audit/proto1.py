import bpy, time, statistics, json, os, sys
import numpy as np
from pathlib import Path
from extension.proportions import CONTROLS
OUT = Path(sys.argv[-1]); OUT.mkdir(parents=True, exist_ok=True)
ids = [c[0] for c in CONTROLS]
ann = {i: bpy.props.FloatProperty(name=i, min=-1.0, max=1.0, default=0.0) for i in ids}
ann["age"] = bpy.props.FloatProperty(name="age", min=0.0, max=3.0, default=2.0)
HLProto = type("HLProto", (bpy.types.PropertyGroup,), {"__annotations__": ann})
bpy.utils.register_class(HLProto)
bpy.types.Object.hlproto = bpy.props.PointerProperty(type=HLProto)
R = {}

def new_body(loc=(0, 0, 0)):
    bpy.context.scene.cursor.location = loc
    bpy.ops.human_modeling.create()
    b = bpy.context.object
    for m in b.modifiers:
        m.show_viewport = False
    return b

def coords(b):
    b.data.shape_keys.update_tag()
    bpy.context.view_layer.update()
    e = b.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = e.to_mesh()
    a = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", a)
    e.to_mesh_clear()
    return a

def rewire(b, mode):
    k = b.data.shape_keys
    n = 0
    skipped = 0
    for i in ids:
        setattr(b.hlproto, i, float(k.get("hm_" + i, 0.0)))
    b.hlproto.age = float(k["human_modeling_age"])
    for d in k.animation_data.drivers:
        for v in d.driver.variables:
            t = v.targets[0]
            if t.id_type != "KEY":
                continue
            p = t.data_path
            if p.startswith('["hm_'):
                name = p[5:-2]
            elif p == '["human_modeling_age"]':
                name = "age"
            else:
                skipped += 1
                continue
            t.id_type = "OBJECT"
            t.id = b
            t.data_path = ("hlproto." + name) if mode == "A" else ('["hlproto"]["' + name + '"]')
            n += 1
    return n, skipped

def setc(b, name, v, new):
    if new:
        setattr(b.hlproto, name, v)
    else:
        b.data.shape_keys["hm_" + name] = v

old = new_body((0, 0, 0))
newA = new_body((3, 0, 0))
newB = new_body((6, 0, 0))
R["P1_rewired_variables_and_skipped"] = {"A": rewire(newA, "A"), "B": rewire(newB, "B")}
rng = np.random.default_rng(5)
maxd = {"A": 0.0, "B": 0.0}
for trial in range(10):
    vals = {i: float(rng.uniform(-1, 1)) for i in ids}
    age = float(rng.uniform(0, 3))
    for i, v in vals.items():
        setc(old, i, v, False)
        setc(newA, i, v, True)
        setc(newB, i, v, True)
    old.data.shape_keys["human_modeling_age"] = age
    newA.hlproto.age = age
    newB.hlproto.age = age
    co = coords(old)
    for tag, nb in (("A", newA), ("B", newB)):
        maxd[tag] = max(maxd[tag], float(np.abs(coords(nb) - co).max()))
R["P1_equality_max_mm_vs_current_system"] = {k: round(v * 1000, 6) for k, v in maxd.items()}
R["P1_invalid_drivers"] = {tag: sum(1 for d in b.data.shape_keys.animation_data.drivers if not d.driver.is_valid) for tag, b in (("old", old), ("A", newA), ("B", newB))}

def timing(b, new, n=60):
    ts = []
    r = np.random.default_rng(1)
    for _ in range(n):
        name = ids[int(r.integers(len(ids)))]
        setc(b, name, float(r.uniform(-1, 1)), new)
        t = time.perf_counter()
        coords(b)
        ts.append((time.perf_counter() - t) * 1000)
    return round(statistics.median(ts), 1), round(sorted(ts)[int(0.9 * len(ts))], 1)

R["P1_slider_ms_median_p90"] = {"current_key_props": timing(old, False), "object_props_RNA_path": timing(newA, True), "object_props_IDprop_path": timing(newB, True)}

bodies = [new_body((10 + 3 * i, 0, 0)) for i in range(9)]
t0 = time.perf_counter()
for b in bodies:
    rewire(b, "A")
R["P1_rewire_9_bodies_s"] = round(time.perf_counter() - t0, 2)
ts = []
for i in range(20):
    bodies[0].hlproto.shoulders = float(i % 5) / 5
    t = time.perf_counter()
    coords(bodies[0])
    ts.append((time.perf_counter() - t) * 1000)
R["P1_12_humans_in_scene_change_one_ms_median"] = round(statistics.median(ts), 1)

def dup_test(b):
    bpy.ops.object.select_all(action="DESELECT")
    b.select_set(True)
    bpy.context.view_layer.objects.active = b
    bpy.ops.object.duplicate()
    d = bpy.context.object
    dk = d.data.shape_keys
    tgt = dk.animation_data.drivers[5].driver.variables[0].targets[0]
    res = {"copy_has_own_keys": d.data.shape_keys != b.data.shape_keys, "driver_target_object": tgt.id.name if tgt.id else None, "orig": b.name, "copy": d.name}
    base_b = coords(b)
    base_d = coords(d)
    d.hlproto.shoulders = 1.0
    cb = coords(b)
    cd = coords(d)
    res["changing_copy_moves_copy_mm"] = round(float(np.abs(cd - base_d).max()) * 1000, 3)
    res["changing_copy_moves_original_mm"] = round(float(np.abs(cb - base_b).max()) * 1000, 3)
    return res

R["P1_duplicate_A_RNA_path"] = dup_test(newA)
R["P1_duplicate_B_IDprop_path"] = dup_test(newB)
newA.hlproto.shoulders = 0.8
newB.hlproto.shoulders = 0.8
old.data.shape_keys["hm_shoulders"] = 0.8
R["P1_saved_objects"] = {"old": old.name, "A": newA.name, "B": newB.name}
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "proto1.blend"))

try:
    bpy.app.translations.register("hlproto", {"fr_FR": {("*", "Height"): "Taille", ("*", "Nose Width"): "Largeur du nez"}})
    v = bpy.context.preferences.view
    v.language = "fr_FR"
    v.use_translate_interface = True
    R["P5_translation"] = {"Height": bpy.app.translations.pgettext_iface("Height"), "Nose Width": bpy.app.translations.pgettext_iface("Nose Width"), "locale": bpy.app.translations.locale}
except Exception as e:
    R["P5_translation"] = "ERR " + str(e)[:150]
R["P2_poll_message_set_exists"] = hasattr(bpy.types.Operator, "poll_message_set")

sc = bpy.context.scene
try:
    old2 = new_body((60, 0, 0))
    rewire(old2, "A")
    old2.hlproto.shoulders = -1.0
    ok1 = old2.keyframe_insert(data_path="hlproto.shoulders", frame=1)
    old2.hlproto.shoulders = 1.0
    ok2 = old2.keyframe_insert(data_path="hlproto.shoulders", frame=101)
    old2.hlproto.age = 0.0
    old2.keyframe_insert(data_path="hlproto.age", frame=1)
    old2.hlproto.age = 3.0
    old2.keyframe_insert(data_path="hlproto.age", frame=101)
    vals = []
    for fr in (1, 51, 101):
        sc.frame_set(fr)
        vals.append((fr, round(old2.hlproto.shoulders, 3), round(old2.hlproto.age, 3), round(float(np.ptp(coords(old2).reshape(-1, 3)[:, 2])), 3)))
    act = old2.animation_data.action
    info = {"keyframe_ok": [ok1, ok2], "frames_shoulders_age_height": vals, "slots": [s.identifier for s in act.slots], "layers": len(act.layers)}
    try:
        slot = act.slots[0]
        strip = act.layers[0].strips[0]
        cb = strip.channelbag(slot)
        info["fcurves_via_channelbag"] = [(fc.data_path, len(fc.keyframe_points)) for fc in cb.fcurves]
    except Exception as e:
        info["channelbag_err"] = str(e)[:150]
    R["P6_animation"] = info
except Exception as e:
    R["P6_animation"] = "ERR " + type(e).__name__ + " " + str(e)[:200]
(OUT / "proto1.json").write_text(json.dumps(R, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
print("PROTO1_DONE")
