import bpy, time, statistics, json, sys
import numpy as np
from pathlib import Path
from extension.proportions import CONTROLS
OUT = Path(sys.argv[-1])
OUT.mkdir(parents=True, exist_ok=True)
ids = [c[0] for c in CONTROLS]
R = {}

# Variant D: PropertyGroup facade whose get/set read and write the Key custom property (no driver rewiring)
def make_prop(name):
    def get(self):
        return float(self.id_data.data.shape_keys.get("hm_" + name, 0.0))
    def set_(self, v):
        k = self.id_data.data.shape_keys
        k["hm_" + name] = float(v)
        k.update_tag()
    return bpy.props.FloatProperty(name=name, min=-1.0, max=1.0, default=0.0, get=get, set=set_)
ann = {i: make_prop(i) for i in ids}
Facade = type("Facade", (bpy.types.PropertyGroup,), {"__annotations__": ann})
bpy.utils.register_class(Facade)
bpy.types.Object.hlface = bpy.props.PointerProperty(type=Facade)

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

def rewire_C(b):
    k = b.data.shape_keys
    for i in ids:
        b["hl_" + i] = float(k.get("hm_" + i, 0.0))
        b.id_properties_ui("hl_" + i).update(min=-1.0, max=1.0, default=0.0, description="HumanLoom " + i)
    b["hl_age"] = float(k["human_modeling_age"])
    b.id_properties_ui("hl_age").update(min=0.0, max=3.0, default=2.0)
    n = 0
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
                continue
            t.id_type = "OBJECT"
            t.id = b
            t.data_path = '["hl_' + name + '"]'
            n += 1
    return n

old = new_body((0, 0, 0))
C = new_body((3, 0, 0))
D = new_body((6, 0, 0))
R["C_rewired_variables"] = rewire_C(C)
rng = np.random.default_rng(5)
maxd = {"C": 0.0, "D": 0.0}
for trial in range(10):
    vals = {i: float(rng.uniform(-1, 1)) for i in ids}
    age = float(rng.uniform(0, 3))
    for i, v in vals.items():
        old.data.shape_keys["hm_" + i] = v
        C["hl_" + i] = v
        setattr(D.hlface, i, v)
    old.data.shape_keys["human_modeling_age"] = age
    C["hl_age"] = age
    D.data.shape_keys["human_modeling_age"] = age
    co = coords(old)
    maxd["C"] = max(maxd["C"], float(np.abs(coords(C) - co).max()))
    maxd["D"] = max(maxd["D"], float(np.abs(coords(D) - co).max()))
R["equality_max_mm_vs_current_system"] = {k: round(v * 1000, 6) for k, v in maxd.items()}
R["invalid_drivers"] = {"C": sum(1 for d in C.data.shape_keys.animation_data.drivers if not d.driver.is_valid), "D": sum(1 for d in D.data.shape_keys.animation_data.drivers if not d.driver.is_valid)}

def timing(setter, b, n=60):
    ts = []
    r = np.random.default_rng(1)
    for _ in range(n):
        name = ids[int(r.integers(len(ids)))]
        setter(name, float(r.uniform(-1, 1)))
        t = time.perf_counter()
        coords(b)
        ts.append((time.perf_counter() - t) * 1000)
    return round(statistics.median(ts), 1), round(sorted(ts)[int(0.9 * len(ts))], 1)

R["slider_ms_median_p90"] = {
    "baseline_key_props": timing(lambda n, v: old.data.shape_keys.__setitem__("hm_" + n, v), old),
    "C_object_custom_props": timing(lambda n, v: C.__setitem__("hl_" + n, v), C),
    "D_facade_proxy": timing(lambda n, v: setattr(D.hlface, n, v), D),
}

def dup(b, setter):
    bpy.ops.object.select_all(action="DESELECT")
    b.select_set(True)
    bpy.context.view_layer.objects.active = b
    bpy.ops.object.duplicate()
    d = bpy.context.object
    tgt = d.data.shape_keys.animation_data.drivers[5].driver.variables[0].targets[0]
    bb = coords(b)
    bd = coords(d)
    setter(d, 1.0)
    return {"copy_driver_target": tgt.id.name if tgt.id else None, "copy": d.name, "orig": b.name,
            "copy_moves_mm": round(float(np.abs(coords(d) - bd).max()) * 1000, 3), "orig_moves_mm": round(float(np.abs(coords(b) - bb).max()) * 1000, 3)}
R["duplicate_C"] = dup(C, lambda d, v: d.__setitem__("hl_shoulders", v))
R["duplicate_D"] = dup(D, lambda d, v: setattr(d.hlface, "shoulders", v))

sc = bpy.context.scene
for label, body, path, setter in (("C", C, '["hl_shoulders"]', lambda v: C.__setitem__("hl_shoulders", v)), ("D", D, "hlface.shoulders", lambda v: setattr(D.hlface, "shoulders", v))):
    try:
        setter(-1.0)
        body.keyframe_insert(data_path=path, frame=1)
        setter(1.0)
        body.keyframe_insert(data_path=path, frame=101)
        rows = []
        for fr in (1, 51, 101):
            sc.frame_set(fr)
            c = coords(body)
            rows.append((fr, round(float(np.ptp(c.reshape(-1, 3)[:, 0])), 4)))
        R["keyframes_" + label + "_width_by_frame"] = rows
    except Exception as e:
        R["keyframes_" + label] = "ERR " + type(e).__name__ + " " + str(e)[:150]
sc.frame_set(1)
C["hl_shoulders"] = 0.8
D.hlface.shoulders = 0.8
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "proto1b.blend"))
R["saved"] = {"C": C.name, "D": D.name, "old": old.name}
(OUT / "proto1b.json").write_text(json.dumps(R, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
print("PROTO1B_DONE")
