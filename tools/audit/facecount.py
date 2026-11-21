import bpy, re, numpy as np
from extension.proportions import BODY_CONTROLS, FAT_CONTROLS, MUSCLE_CONTROLS, FACE_CONTROLS
bpy.ops.human_modeling.create(); b = bpy.context.object; k = b.data.shape_keys
nv = len(b.data.vertices)
cat = {}
for n, _ in BODY_CONTROLS: cat[n] = "body"
for n, _ in FAT_CONTROLS: cat[n] = "fat"
for n, _ in MUSCLE_CONTROLS: cat[n] = "muscle"
for n, _ in FACE_CONTROLS: cat[n] = "face"
cnt = {}
verts = {}
def co(x):
    a = np.empty(nv * 3, np.float32); x.data.foreach_get("co", a); return a
for x in k.key_blocks:
    if x == k.reference_key: continue
    m = re.search(r"HM · ([a-z_0-9]+)", x.name)
    c = cat.get(m.group(1), "other") if m else "other"
    cnt[c] = cnt.get(c, 0) + 1
    d = (co(x) - co(x.relative_key)).reshape(-1, 3)
    mv = np.linalg.norm(d, axis=1) > 1e-5
    verts.setdefault(c, np.zeros(nv, bool)); verts[c] |= mv
print("FC keys by category", cnt)
print("FC verts touched by category", {c: int(v.sum()) for c, v in verts.items()}, "of", nv)
print("FC face controls", [n for n, _ in FACE_CONTROLS])
