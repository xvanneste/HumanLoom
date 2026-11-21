import bpy, json, sys, os
import numpy as np
from pathlib import Path
from extension.proportions import CONTROLS
OUT = Path(sys.argv[-1])
OUT.mkdir(parents=True, exist_ok=True)
R = {}
bpy.ops.human_modeling.create()
body = bpy.context.object
keys = body.data.shape_keys
for m in body.modifiers:
    m.show_viewport = False
nv = len(body.data.vertices)
blocks = [k for k in keys.key_blocks if k != keys.reference_key]

def co(k):
    a = np.empty(nv * 3, np.float32)
    k.data.foreach_get("co", a)
    return a

base = co(keys.reference_key).astype(np.float64)
D = np.stack([(co(k) - co(k.relative_key)).astype(np.float64) for k in blocks])
ids = [c[0] for c in CONTROLS]

def evaluated():
    keys.update_tag()
    bpy.context.view_layer.update()
    e = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = e.to_mesh()
    a = np.empty(nv * 3)
    me.vertices.foreach_get("co", a)
    e.to_mesh_clear()
    return a

rng = np.random.default_rng(11)
states = []
for _ in range(40):
    for i in ids:
        keys["hm_" + i] = float(rng.uniform(-1, 1) * 0.8)
    keys["human_modeling_age"] = float(rng.uniform(0, 3))
    keys.key_blocks["Morphologie"].value = float(rng.uniform(0, 1))
    true = evaluated() - base
    v = np.array([k.value for k in blocks])
    states.append((v, true))
lin_err = max(float(np.abs(v @ D - t).max()) for v, t in states)
R["model_check_linear_in_key_values_max_err_mm"] = round(lin_err * 1000, 6)
U, S, Vt = np.linalg.svd(D, full_matrices=False)
rows = {}
for r in (50, 70, 100, 128, 150, 200):
    Dr = (U[:, :r] * S[:r]) @ Vt[:r]
    errs = [np.abs(v @ Dr - t).max() for v, t in states]
    means = [np.abs(v @ Dr - t).mean() for v, t in states]
    rows[r] = {"max_err_mm": round(float(max(errs)) * 1000, 4), "median_of_max_err_mm": round(float(np.median(errs)) * 1000, 4), "mean_err_mm": round(float(np.mean(means)) * 1000, 5)}
R["reduced_basis_reconstruction_error_40_random_states"] = rows
R["max_displacement_mm_in_states"] = round(max(float(np.abs(t).max()) for v, t in states) * 1000, 1)

# file size impact of storing a basis as vertex attributes
body.data.shape_keys.animation_data_clear if False else None
f0 = OUT / "size_base.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(f0), compress=False)
size_base = os.path.getsize(f0)
# separate mesh with 150 attributes (what a GN-based body would carry)
mesh = bpy.data.meshes.new("basis_carrier")
mesh.from_pydata(base.reshape(-1, 3).tolist(), [], [])
r = 150
B = Vt[:r]
for i in range(r):
    a = mesh.attributes.new("b" + str(i), "FLOAT_VECTOR", "POINT")
    a.data.foreach_set("vector", B[i].astype(np.float32))
obj = bpy.data.objects.new("carrier", mesh)
bpy.context.scene.collection.objects.link(obj)
for k in tuple(body.data.shape_keys.key_blocks):
    pass
f1 = OUT / "size_with_basis.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(f1), compress=False)
f2 = OUT / "size_with_basis_c.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(f2), compress=True)
R["file_size_MB"] = {"body_with_461_shape_keys_uncompressed": round(size_base / 1e6, 1), "plus_150_basis_attributes_uncompressed": round(os.path.getsize(f1) / 1e6, 1), "plus_150_basis_attributes_compressed": round(os.path.getsize(f2) / 1e6, 1)}
for p in (f0, f1, f2):
    os.remove(p)
(OUT / "proto7.json").write_text(json.dumps(R, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
print("PROTO7_DONE")
