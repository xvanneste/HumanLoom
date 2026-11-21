import bpy, re, json, sys
import numpy as np
from collections import defaultdict
from extension.proportions import CONTROLS
bpy.ops.human_modeling.create()
b = bpy.context.object
k = b.data.shape_keys
nv = len(b.data.vertices)
blocks = [x for x in k.key_blocks if x != k.reference_key]

def co(x):
    a = np.empty(nv * 3, np.float32)
    x.data.foreach_get("co", a)
    return a

groups = defaultdict(list)
for x in blocks:
    m = re.search(r"HM · ([a-z_0-9]+)", x.name)
    groups[m.group(1) if m else "other:" + x.name.split(" · ")[0]].append(x)
tot = {1e-3: 0, 1e-4: 0, 1e-5: 0}
rows = {}
for g, xs in groups.items():
    D = np.stack([(co(x) - co(x.relative_key)).astype(np.float64) for x in xs])
    if np.abs(D).max() < 1e-9:
        continue
    s = np.linalg.svd(D, compute_uv=False)
    r = {t: int((s > s[0] * t).sum()) for t in tot}
    for t in tot:
        tot[t] += r[t]
    rows[g] = (len(xs), r[1e-4], r[1e-5])
print("GR groups", len(rows), "total keys", len(blocks))
print("GR sum of per-group ranks at 1e-3/1e-4/1e-5:", tot)
print("GR sample", dict(list(rows.items())[:8]))
print("GR other", {g: v for g, v in rows.items() if g.startswith("other")})
