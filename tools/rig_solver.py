"""Solveur de CIBLES de correctif (numpy pur, sans bpy) : positions posées optimisées par gradient exact (CONCEPTION_RIG_CORRECTIFS.md §6).

Énergie = λe Σ (longueur d'arête / longueur de repos − 1)² + λf Σ relu(seuil − n_a·n_b)² (plis ; seuil RELATIF au repos) + λa Σ (√(aire de section / aire de repos) − 1)² + rappel vers la peau de départ (fort vers le bord de zone
et sur le visage) + lissage du déplacement ; Adam avec décroissance quadratique du pas ; le déplacement est ensuite atténué près du visage (distance en arêtes) sans coupure nette."""
import math

import numpy as np


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


def hop_protection(n, edges, locked, hops_full=6.0):
    """Facteur de déplacement 0 sur les sommets `locked` (visage), croissant en lissé jusqu'à 1 à `hops_full` arêtes."""
    hops = np.where(locked, 0.0, 1e9)
    for _ in range(int(hops_full) + 6):
        h2 = hops.copy()
        np.minimum.at(h2, edges[:, 0], hops[edges[:, 1]] + 1.0)
        np.minimum.at(h2, edges[:, 1], hops[edges[:, 0]] + 1.0)
        hops = h2
    p = np.clip(hops / hops_full, 0.0, 1.0)
    return p * p * (3 - 2 * p)


def rbf_fit(features, sigma_scale=1.5):
    """Bases cardinales de type Sloan (2001) : approximation LINÉAIRE aux moindres carrés + bases radiales qui corrigent les résidus ; base radiale gaussienne de rayon sigma_j = `sigma_scale` × distance à l'exemple le plus proche
    (écart documenté : Sloan utilise une B-spline cubique de rayon 2× cette distance, non exprimable en expression de driver). Retourne (sigma, A) : poids du clé k au point f = Σ_j A[k, j] φ_j(f) + A[k, J] + A[k, J+1:] · f."""
    J = len(features)
    d = np.linalg.norm(features[:, None] - features[None], axis=2)
    np.fill_diagonal(d, 1e9)
    sigma = sigma_scale * d.min(1)
    Phi = np.exp(-(np.linalg.norm(features[:, None] - features[None], axis=2) / sigma[None, :]) ** 2)  # Phi[i, j] = φ_j(f_i)
    # inconnues par clé k : c_k (J), a0, a1..a3 ; contraintes : A_k(f_i) = δ_ik ; orthogonalité du radial au linéaire (conditions standard)
    P = np.c_[np.ones(J), features]
    M = np.block([[Phi + 1e-8 * np.eye(J), P], [P.T, np.zeros((P.shape[1], P.shape[1]))]])
    rhs = np.vstack([np.eye(J), np.zeros((P.shape[1], J))])
    sol = np.linalg.solve(M, rhs)  # (J+4, J) : colonnes = clés
    return sigma, sol.T  # (K, J+4) : coefficients radiaux puis constante et linéaire


def rbf_weights(f, features, sigma, A):
    phi = np.exp(-(np.linalg.norm(features - f, axis=1) / sigma) ** 2)
    return A[:, : len(features)] @ phi + A[:, len(features)] + A[:, len(features) + 1:] @ f


def shepard_weights(f, features, sigma):
    """Poids normalisés (partition de l'unité) : φ_k(f) / Σ_j φ_j(f), φ gaussienne de rayon sigma_k. Bornés dans [0, 1] : aucun dépassement entre les exemples ni hors de leur enveloppe (le terme linéaire de Sloan extrapolait et
    aggravait les poses hors entraînement, mesuré). Écart documenté par rapport à Sloan, Rose & Cohen 2001 (linéaire + radial, cardinal) : on garde leurs bases radiales centrées sur les exemples, pas leur partie linéaire."""
    phi = np.exp(-(np.linalg.norm(features - f, axis=1) / sigma) ** 2)
    total = float(phi.sum())
    return phi / total if total > 1e-9 else np.zeros_like(phi)
