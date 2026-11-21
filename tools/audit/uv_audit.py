"""T-U1 — audit chiffré du dépliage UV de extension/data/realistic.blend (lecture seule, rien n'est sauvegardé).
Usage : blender --background --factory-startup --python tools/audit/uv_audit.py -- <sortie.json>
"""
import bpy, bmesh, sys, json, math
import numpy as np
from pathlib import Path

OUT = Path(sys.argv[-1])
ROOT = Path(__file__).resolve().parents[2]
bpy.ops.wm.open_mainfile(filepath=str(ROOT / "extension" / "data" / "realistic.blend"))
R = {"fichier": "extension/data/realistic.blend", "objets": {}}


def tri_stats(me, uvname):
    me.calc_loop_triangles()
    nt = len(me.loop_triangles)
    verts = np.empty(len(me.vertices) * 3); me.vertices.foreach_get("co", verts); verts = verts.reshape(-1, 3)
    tl = np.empty(nt * 3, np.int32); me.loop_triangles.foreach_get("loops", tl); tl = tl.reshape(-1, 3)
    tv = np.empty(nt * 3, np.int32); me.loop_triangles.foreach_get("vertices", tv); tv = tv.reshape(-1, 3)
    uvl = me.uv_layers[uvname]
    uv = np.empty(len(me.loops) * 2); uvl.data.foreach_get("uv", uv); uv = uv.reshape(-1, 2)
    P = verts[tv]; U = uv[tl]
    a3 = 0.5 * np.linalg.norm(np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0]), axis=1)
    e1, e2 = U[:, 1] - U[:, 0], U[:, 2] - U[:, 0]
    sa = 0.5 * (e1[:, 0] * e2[:, 1] - e1[:, 1] * e2[:, 0])
    return verts, uv, P, U, a3, sa, tv, tl


def stretch(P, U):
    # distorsion par triangle : valeurs singulières de la jacobienne 3D->UV (rapport max/min)
    out = np.empty(len(P))
    for i in range(len(P)):
        p1, p2 = P[i, 1] - P[i, 0], P[i, 2] - P[i, 0]
        l1 = np.linalg.norm(p1)
        if l1 < 1e-12:
            out[i] = np.nan; continue
        x = p1 / l1
        n = np.cross(p1, p2); ln = np.linalg.norm(n)
        if ln < 1e-14:
            out[i] = np.nan; continue
        y = np.cross(n / ln, x)
        A = np.array([[l1, np.dot(p2, x)], [0.0, np.dot(p2, y)]])
        B = np.array([U[i, 1] - U[i, 0], U[i, 2] - U[i, 0]]).T
        try:
            J = B @ np.linalg.inv(A)
            s = np.linalg.svd(J, compute_uv=False)
            out[i] = s[0] / max(s[1], 1e-12)
        except Exception:
            out[i] = np.nan
    return out


def pct(a, qs=(1, 5, 25, 50, 75, 95, 99)):
    a = a[np.isfinite(a)]
    return {str(q): round(float(np.percentile(a, q)), 6) for q in qs} if len(a) else {}


for ob in bpy.data.objects:
    if ob.type != "MESH":
        continue
    me = ob.data
    d = {"sommets": len(me.vertices), "faces": len(me.polygons), "couches_uv": [u.name for u in me.uv_layers],
         "materiaux": [m.name if m else None for m in me.materials],
         "modificateurs": [m.type for m in ob.modifiers], "shape_keys": len(me.shape_keys.key_blocks) if me.shape_keys else 0}
    if me.uv_layers:
        for uvl in me.uv_layers:
            verts, uv, P, U, a3, sa, tv, tl = tri_stats(me, uvl.name)
            u = {}
            u["bornes_uv"] = [round(float(uv[:, 0].min()), 4), round(float(uv[:, 0].max()), 4), round(float(uv[:, 1].min()), 4), round(float(uv[:, 1].max()), 4)]
            u["hors_0_1_pct_boucles"] = round(float(((uv < 0) | (uv > 1)).any(axis=1).mean() * 100), 3)
            u["triangles"] = int(len(sa))
            u["triangles_aire_uv_negative"] = int((sa < 0).sum())
            u["triangles_aire_uv_nulle"] = int((np.abs(sa) < 1e-12).sum())
            ok = (a3 > 1e-12) & (np.abs(sa) > 1e-12)
            # densite de texel relative : sqrt(aire_uv / aire_3d)
            dens = np.sqrt(np.abs(sa[ok]) / a3[ok])
            med = np.median(dens)
            u["densite_texel_relative_percentiles"] = pct(dens / med)
            u["densite_texel_max_sur_min_p5_p95"] = round(float(np.percentile(dens, 95) / np.percentile(dens, 5)), 3)
            st = stretch(P[ok], U[ok])
            u["etirement_rapport_sv_percentiles"] = pct(st)
            u["triangles_etirement_sup_2_pct"] = round(float((st > 2).mean() * 100), 3)
            u["utilisation_espace_uv_pct"] = round(float(np.abs(sa).sum() * 100), 2)
            # chevauchements : rasterisation 1024^2, comptage de triangles par pixel
            N = 1024
            grid = np.zeros((N, N), np.int16)
            sel = np.arange(len(sa))
            cx = U.mean(axis=1)
            for i in sel[:: 1]:
                tri = U[i]
                mn = np.clip(np.floor(tri.min(axis=0) * N).astype(int), 0, N - 1)
                mx = np.clip(np.ceil(tri.max(axis=0) * N).astype(int), 0, N - 1)
                if mx[0] - mn[0] > 64 or mx[1] - mn[1] > 64:
                    continue
                xs = (np.arange(mn[0], mx[0] + 1) + 0.5) / N
                ys = (np.arange(mn[1], mx[1] + 1) + 0.5) / N
                X, Y = np.meshgrid(xs, ys)
                a, b, c = tri
                den = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
                if abs(den) < 1e-14:
                    continue
                w1 = ((b[1] - c[1]) * (X - c[0]) + (c[0] - b[0]) * (Y - c[1])) / den
                w2 = ((c[1] - a[1]) * (X - c[0]) + (a[0] - c[0]) * (Y - c[1])) / den
                w3 = 1 - w1 - w2
                m = (w1 >= 0) & (w2 >= 0) & (w3 >= 0)
                grid[mn[1]:mx[1] + 1, mn[0]:mx[0] + 1] += m.astype(np.int16)
            cover = (grid > 0).sum(); over = (grid > 1).sum()
            u["pixels_couverts_1024"] = int(cover)
            u["pixels_en_chevauchement_pct_des_couverts"] = round(float(over / max(cover, 1) * 100), 3)
            # ilots (composantes connexes par aretes UV partagees)
            bm = bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table()
            uvk = bm.loops.layers.uv[uvl.name]
            par = list(range(len(bm.faces)))

            def find(x):
                while par[x] != x:
                    par[x] = par[par[x]]; x = par[x]
                return x
            seams = 0
            for e in bm.edges:
                if len(e.link_faces) == 2:
                    f1, f2 = e.link_faces
                    def uvs(f, v):
                        for l in f.loops:
                            if l.vert == v:
                                return tuple(np.round(l[uvk].uv, 5))
                    same = all(uvs(f1, v) == uvs(f2, v) for v in e.verts)
                    if same:
                        par[find(f1.index)] = find(f2.index)
                    else:
                        seams += 1
            roots = {}
            for f in bm.faces:
                roots.setdefault(find(f.index), []).append(f.index)
            u["ilots"] = len(roots)
            u["aretes_de_couture_uv"] = seams
            fa3 = np.array([f.calc_area() for f in bm.faces])
            sizes = sorted(((len(v), float(fa3[v].sum())) for v in roots.values()), reverse=True)
            u["plus_gros_ilots_(faces, aire_3d_m2)"] = [(a, round(b, 4)) for a, b in sizes[:12]]
            u["petits_ilots_moins_de_10_faces"] = int(sum(1 for a, b in sizes if a < 10))
            # zones du corps : tete (z haut), mains, pieds via position 3D des sommets
            zs = verts[:, 2]; zmax, zmin = zs.max(), zs.min(); H = zmax - zmin
            reg = {"tete (z > 87 % taille)": zs > zmin + 0.87 * H, "bas des jambes (z < 12 %)": zs < zmin + 0.12 * H}
            u["densite_par_zone_relative_a_la_mediane"] = {}
            fz = verts[tv][:, :, 2].mean(axis=1)[ok]
            for k, mask in reg.items():
                tz = (verts[tv][:, :, 2].mean(axis=1) > (zmin + 0.87 * H)) if "tete" in k else (verts[tv][:, :, 2].mean(axis=1) < (zmin + 0.12 * H))
                tz = tz[ok]
                if tz.sum():
                    u["densite_par_zone_relative_a_la_mediane"][k] = round(float(np.median(dens[tz]) / med), 3)
            # symetrie en miroir : les triangles de x>0 et x<0 occupent-ils les memes pixels ?
            ctr = verts[tv].mean(axis=1)[:, 0]
            u["triangles_x_positif_vs_negatif"] = [int((ctr > 1e-6).sum()), int((ctr < -1e-6).sum())]
            d.setdefault("uv", {})[uvl.name] = u
            bm.free()
    R["objets"][ob.name] = d

OUT.write_text(json.dumps(R, indent=1, ensure_ascii=False), encoding="utf-8")
print("UV_AUDIT_DONE", OUT)
