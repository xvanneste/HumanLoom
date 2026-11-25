"""Solveur de cibles de correctif (numpy pur) : positions posées optimisées par gradient exact — arêtes, plis relatifs au repos, aire de section, rappel vers la peau de départ, lissage (CONCEPTION_RIG_CORRECTIFS.md §6).
Copie de travail de `tools/rig_solver.py` (même algorithme) pour que l'extension puisse RECALCULER les correctifs sur la morphologie courante sans dépendre de `tools/`."""
import math

import numpy as np


def section_area(points, selection):
    """Aire d'une tranche (sqrt(λ1·λ2) des deux plus grandes variances de l'analyse en composantes principales)."""
    c = points[selection] - points[selection].mean(0)
    eig = np.sort(np.linalg.eigvalsh(c.T @ c / len(selection)))[::-1]
    return math.sqrt(max(eig[0] * eig[1], 1e-18))


def section_selection(rest, axis_head, axis_unit, pivot, distance, radius=0.11, half=0.01):
    s = (rest - axis_head) @ axis_unit
    offset = (pivot - axis_head) @ axis_unit
    radial = np.linalg.norm((rest - axis_head) - np.outer(s, axis_unit), axis=1)
    return np.where((np.abs(s - offset - distance) < half) & (radial < radius))[0]


class Problem:
    def __init__(self, rest, edges, tris, free, sections, protect, pull, tau=0.3):
        self.rest, self.edges, self.tris, self.free = rest, edges, tris, free
        n = len(rest)
        self.local = -np.ones(n, int)
        self.local[free] = np.arange(len(free))
        region = np.zeros(n, bool)
        region[free] = True
        sel = region[edges[:, 0]] | region[edges[:, 1]]
        self.E = edges[sel]
        self.L0 = np.linalg.norm(rest[self.E[:, 0]] - rest[self.E[:, 1]], axis=1)
        both = region[edges[:, 0]] & region[edges[:, 1]]
        self.ea, self.eb = self.local[edges[both, 0]], self.local[edges[both, 1]]
        tri_free = region[tris].any(1)
        pair_map = {}
        for t, tri in enumerate(tris):
            if tri_free[t]:
                for k in range(3):
                    pair_map.setdefault((min(tri[k], tri[(k + 1) % 3]), max(tri[k], tri[(k + 1) % 3])), []).append(t)
        self.pairs = np.array([v for v in pair_map.values() if len(v) == 2])
        rn = self.normals(rest)[0]
        self.thr = np.minimum(tau, np.einsum("ij,ij->i", rn[self.pairs[:, 0]], rn[self.pairs[:, 1]]) - 0.25)
        self.sections, self.protect, self.pull = sections, protect, pull

    def normals(self, x):
        N = np.cross(x[self.tris[:, 1]] - x[self.tris[:, 0]], x[self.tris[:, 2]] - x[self.tris[:, 0]])
        norm = np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-12)
        return N / norm, norm

    def fold_grad(self, x, gx):
        tris, pairs = self.tris, self.pairs
        a, b, c = x[tris[:, 0]], x[tris[:, 1]], x[tris[:, 2]]
        u, norm = self.normals(x)
        d = np.einsum("ij,ij->i", u[pairs[:, 0]], u[pairs[:, 1]])
        h = np.maximum(self.thr - d, 0.0)
        active = h > 0
        pa, pb = pairs[active, 0], pairs[active, 1]
        ca = (-2 * h[active])[:, None]
        ua, ub = u[pa], u[pb]
        dot = np.einsum("ij,ij->i", ua, ub)[:, None]
        gN = np.zeros_like(x[tris[:, 0]])
        np.add.at(gN, pa, (ub - ua * dot) / norm[pa] * ca)
        np.add.at(gN, pb, (ua - ub * dot) / norm[pb] * ca)
        gb_, gc_ = np.cross(c - a, gN), np.cross(gN, b - a)
        np.add.at(gx, tris[:, 1], gb_)
        np.add.at(gx, tris[:, 2], gc_)
        np.add.at(gx, tris[:, 0], -(gb_ + gc_))

    def section_grad(self, x, gx):
        for sel, rest_area in self.sections:
            cen = x[sel] - x[sel].mean(0)
            C = cen.T @ cen / len(sel)
            e2 = 0.5 * (np.trace(C) ** 2 - np.trace(C @ C))
            f = max(e2 / (rest_area ** 2), 1e-9)
            r = math.sqrt(f) - 1.0
            G = (np.trace(C) * np.eye(3) - C) / (rest_area ** 2)
            gx[sel] += (r / math.sqrt(f)) * (2.0 / len(sel)) * cen @ G.T

    def solve(self, start, iterations=400, lr=0.0006, le=1.0, lf=0.5, la=2.0, ls=25.0):
        x = start.copy()
        free = self.free
        m_ = np.zeros((len(free), 3))
        v_ = np.zeros((len(free), 3))
        E, L0 = self.E, self.L0
        for it in range(1, iterations + 1):
            gx = np.zeros_like(x)
            d = x[E[:, 0]] - x[E[:, 1]]
            length = np.maximum(np.linalg.norm(d, axis=1), 1e-9)
            r = (length - L0) / L0
            g = (2 * r / L0 / length)[:, None] * d
            np.add.at(gx, E[:, 0], le * g)
            np.add.at(gx, E[:, 1], -le * g)
            if lf > 0:
                gf = np.zeros_like(x)
                self.fold_grad(x, gf)
                gx += lf * gf
            if la > 0:
                ga = np.zeros_like(x)
                self.section_grad(x, ga)
                gx += la * ga
            gfree = gx[free]
            disp = x[free] - start[free]
            gfree = gfree + 2 * self.pull[:, None] * disp
            diff = disp[self.ea] - disp[self.eb]
            np.add.at(gfree, self.ea, 2 * ls * diff)
            np.add.at(gfree, self.eb, -2 * ls * diff)
            m_ = 0.9 * m_ + 0.1 * gfree
            v_ = 0.999 * v_ + 0.001 * gfree ** 2
            x[free] -= lr * (1.0 - (it - 1) / iterations) ** 2 * (m_ / (1 - 0.9 ** it)) / (np.sqrt(v_ / (1 - 0.999 ** it)) + 1e-9)
        x[free] = start[free] + self.protect[:, None] * (x[free] - start[free])
        return x
