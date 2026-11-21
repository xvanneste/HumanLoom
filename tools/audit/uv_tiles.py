"""T-U1 (suite) — occupation des tuiles UDIM, aire 3D totale, densité de texels absolue. Lecture seule.
Usage : blender --background --factory-startup --python tools/audit/uv_tiles.py -- <sortie.json>
"""
import bpy, bmesh, sys, json
import numpy as np
from pathlib import Path
OUT = Path(sys.argv[-1]); ROOT = Path(__file__).resolve().parents[2]
bpy.ops.wm.open_mainfile(filepath=str(ROOT / "extension" / "data" / "realistic.blend"))
ob = bpy.data.objects["Corps"]; me = ob.data
bm = bmesh.new(); bm.from_mesh(me); uvk = bm.loops.layers.uv["UVMap"]
R = {}
A3 = sum(f.calc_area() for f in bm.faces)
AUV = 0.0
tiles = {}
zs = np.array([v.co.z for v in bm.verts]); zmin, zmax = zs.min(), zs.max(); H = zmax - zmin
R["aire_3d_totale_m2"] = round(A3, 4); R["hauteur_m"] = round(float(H), 4)
for f in bm.faces:
    uvs = np.array([l[uvk].uv[:] for l in f.loops])
    a = 0.5 * abs(sum(uvs[i, 0] * uvs[(i + 1) % len(uvs), 1] - uvs[(i + 1) % len(uvs), 0] * uvs[i, 1] for i in range(len(uvs))))
    AUV += a
    c = uvs.mean(axis=0); t = (int(np.floor(c[0])), int(np.floor(c[1])))
    d = tiles.setdefault(f"u{t[0]+1}_v{t[1]+1}", {"faces": 0, "aire_3d": 0.0, "aire_uv": 0.0, "z_min": 9, "z_max": -9})
    z = float(np.mean([v.co.z for v in f.verts]))
    d["faces"] += 1; d["aire_3d"] += f.calc_area(); d["aire_uv"] += a
    d["z_min"] = min(d["z_min"], z); d["z_max"] = max(d["z_max"], z)
R["aire_uv_totale"] = round(AUV, 3)
for k, d in tiles.items():
    for kk in ("aire_3d", "aire_uv", "z_min", "z_max"):
        d[kk] = round(d[kk], 4)
    d["z_min_rel"] = round((d["z_min"] - zmin) / H, 3); d["z_max_rel"] = round((d["z_max"] - zmin) / H, 3)
    d["texels_par_m_a_4096"] = round(4096 * (d["aire_uv"] / d["aire_3d"]) ** 0.5, 0) if d["aire_3d"] else None
R["tuiles_udim"] = dict(sorted(tiles.items()))
R["texels_par_m_moyen_a_4096_par_tuile"] = round(4096 * (AUV / A3) ** 0.5, 0)
OUT.write_text(json.dumps(R, indent=1, ensure_ascii=False), encoding="utf-8"); print("UV_TILES_DONE")
