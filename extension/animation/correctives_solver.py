"""Solveur de cibles de correctif (numpy pur) : positions posées optimisées par gradient exact — arêtes, plis relatifs au repos, aire de section, rappel vers la peau de départ, lissage (CONCEPTION_RIG_CORRECTIFS.md §6).
Copie de travail de `tools/rig_solver.py` (même algorithme) pour que l'extension puisse RECALCULER les correctifs sur la morphologie courante sans dépendre de `tools/`."""
import math

import numpy as np


def _invariant(cov):
    """Deuxième invariant de la covariance (λ1λ2 + λ1λ3 + λ2λ3) : même grandeur au repos et dans le gradient (ANI-013)."""
    return 0.5 * (np.trace(cov) ** 2 - np.trace(cov @ cov))


def section_area(points, selection):
    """Mesure de section au repos : racine du MÊME invariant que celui dérivé par `section_grad` (invariant par rotation et translation ; un repos a donc un résidu et un gradient nuls)."""
    c = points[selection] - points[selection].mean(0)
    return math.sqrt(max(_invariant(c.T @ c / len(selection)), 1e-18))


def section_selection(rest, axis_head, axis_unit, pivot, distance, radius=0.11, half=0.01):
    s = (rest - axis_head) @ axis_unit
    offset = (pivot - axis_head) @ axis_unit
    radial = np.linalg.norm((rest - axis_head) - np.outer(s, axis_unit), axis=1)
    return np.where((np.abs(s - offset - distance) < half) & (radial < radius))[0]


class Problem:
    def __init__(self, rest, edges, tris, free, sections, protect, pull, tau=0.3):
        rest = np.asarray(rest, dtype=float)
        if not np.isfinite(rest).all():
            raise ValueError("Les positions de repos doivent être finies.")
        if len(free) == 0:
            raise ValueError("Aucun sommet libre à optimiser.")
        self.rest, self.edges, self.tris, self.free = rest, edges, tris, free
        n = len(rest)
        self.local = -np.ones(n, int)
        self.local[free] = np.arange(len(free))
        region = np.zeros(n, bool)
        region[free] = True
        sel = region[edges[:, 0]] | region[edges[:, 1]]
        self.E = edges[sel]
        self.L0 = np.linalg.norm(rest[self.E[:, 0]] - rest[self.E[:, 1]], axis=1)
        if len(self.E) == 0 or self.L0.min() <= 1e-9:
            raise ValueError("Une arête de longueur nulle (ou aucune arête) interdit la mesure d'étirement relatif.")
        both = region[edges[:, 0]] & region[edges[:, 1]]
        self.ea, self.eb = self.local[edges[both, 0]], self.local[edges[both, 1]]
        tri_free = region[tris].any(1)
        pair_map = {}
        for t, tri in enumerate(tris):
            if tri_free[t]:
                for k in range(3):
                    pair_map.setdefault((min(tri[k], tri[(k + 1) % 3]), max(tri[k], tri[(k + 1) % 3])), []).append(t)
        self.pairs = np.array([v for v in pair_map.values() if len(v) == 2], dtype=int).reshape(-1, 2)
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
            e2 = _invariant(C)
            f = max(e2 / (rest_area ** 2), 1e-9)
            r = math.sqrt(f) - 1.0
            G = (np.trace(C) * np.eye(3) - C) / (rest_area ** 2)
            gx[sel] += (r / math.sqrt(f)) * (2.0 / len(sel)) * cen @ G.T

    def section_energy(self, x):
        total = 0.0
        for sel, rest_area in self.sections:
            cen = x[sel] - x[sel].mean(0)
            f = max(_invariant(cen.T @ cen / len(sel)) / (rest_area ** 2), 1e-9)
            total += (math.sqrt(f) - 1.0) ** 2
        return total

    def energy(self, x, start, le=1.0, lf=0.5, la=2.0, ls=25.0):
        """Énergie dont `solve` descend le gradient (mêmes pondérations)."""
        E, L0 = self.E, self.L0
        length = np.linalg.norm(x[E[:, 0]] - x[E[:, 1]], axis=1)
        total = le * float((((length - L0) / L0) ** 2).sum())
        if lf > 0 and len(self.pairs):
            u = self.normals(x)[0]
            h = np.maximum(self.thr - np.einsum("ij,ij->i", u[self.pairs[:, 0]], u[self.pairs[:, 1]]), 0.0)
            total += lf * float((h ** 2).sum())
        if la > 0:
            total += la * self.section_energy(x)
        disp = x[self.free] - start[self.free]
        total += float((self.pull * (disp ** 2).sum(1)).sum())
        diff = disp[self.ea] - disp[self.eb]
        return total + ls * float((diff ** 2).sum())

    def solve(self, start, **options):
        """Positions optimisées ; le résultat n'est jamais pire que le départ (voir `solve_report`)."""
        return self.solve_report(start, **options)[0]

    def solve_report(self, start, iterations=400, lr=0.0006, le=1.0, lf=0.5, la=2.0, ls=25.0):
        """(positions, rapport) : énergie initiale/finale, finitude, déplacement maximal, motif d'arrêt. Si le résultat n'est pas fini ou n'abaisse pas l'énergie, le DÉPART est retourné (`accepte` = False)."""
        start = np.asarray(start, dtype=float)
        if start.shape != self.rest.shape or not np.isfinite(start).all():
            raise ValueError("Les positions de départ doivent être finies et de même forme que le repos.")
        weights = dict(le=le, lf=lf, la=la, ls=ls)
        initial = self.energy(start, start, **weights)
        x = self._descend(start, iterations, lr, le, lf, la, ls)
        finite = bool(np.isfinite(x).all())
        final = self.energy(x, start, **weights) if finite else float("inf")
        accepted = finite and final <= initial * (1.0 + 1e-9)
        displacement = float(np.linalg.norm(x[self.free] - start[self.free], axis=1).max()) if finite else float("inf")
        report = {"energie_initiale": initial, "energie_finale": final if accepted else initial, "finie": finite, "accepte": bool(accepted),
                  "iterations": iterations, "motif_arret": "iterations_max" if accepted else ("non_fini" if not finite else "energie_non_reduite"),
                  "deplacement_max_m": displacement if finite else None}
        return (x if accepted else start.copy()), report

    def _descend(self, start, iterations, lr, le, lf, la, ls):
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
