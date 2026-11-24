"""Mesures de déformation articulaire (numpy pur, importable) : mêmes critères que `inventory_rig_defects.py` (CONCEPTION_RIG_CORRECTIFS.md §1), appliqués à un maillage posé donné.

Sert au prototype des formes correctives (`proto_shoulder_correctives.py`). Aucune dépendance à bpy."""
import math

import numpy as np

THRESHOLDS = {"aire_min": 0.85, "aire_max": 1.10, "pincement_min": 0.90, "retournees_max": 2, "etirement_max": 3.0}


def tri_normals(points, tris):
    n = np.cross(points[tris[:, 1]] - points[tris[:, 0]], points[tris[:, 2]] - points[tris[:, 0]])
    a = np.linalg.norm(n, axis=1)
    return n / np.maximum(a[:, None], 1e-18), a / 2


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


class Region:
    """Région de mesure : sommets à moins de R du pivot au repos."""

    def __init__(self, rest, tris, edges, pivot, radius, axis_head, axis_unit, distance):
        self.rest, self.tris, self.edges = rest, tris, edges
        self.inside = np.linalg.norm(rest - pivot, axis=1) < radius
        self.rest_n, self.rest_a = tri_normals(rest, tris)
        self.tri_in = self.inside[tris].all(1) & (self.rest_a > 1e-10)
        self.edge_in = self.inside[edges].all(1)
        self.rest_len = np.linalg.norm(rest[edges[:, 0]] - rest[edges[:, 1]], axis=1)
        self.rest_surface = float(self.rest_a[self.tri_in].sum())
        pairs = {}
        for t, tri in enumerate(tris):
            for k in range(3):
                key = (min(tri[k], tri[(k + 1) % 3]), max(tri[k], tri[(k + 1) % 3]))
                pairs.setdefault(key, []).append(t)
        adjacent = np.array([v for v in pairs.values() if len(v) == 2])
        self.adjacent = adjacent[self.tri_in[adjacent[:, 0]] & self.tri_in[adjacent[:, 1]]] if len(adjacent) else adjacent
        self.rest_dots = np.einsum('ij,ij->i', self.rest_n[self.adjacent[:, 0]], self.rest_n[self.adjacent[:, 1]]) if len(self.adjacent) else np.zeros(0)
        self.selection = section_selection(rest, axis_head, axis_unit, pivot, distance)
        self.rest_section = section_area(rest, self.selection) if len(self.selection) >= 8 else None

    def measure(self, points, tri_rotations):
        """`tri_rotations` : matrices 3×3 (n_triangles, 3, 3) de la rotation rigide de l'os dominant de chaque triangle (pour la détection des retournements)."""
        n, a = tri_normals(points, self.tris)
        predicted = np.einsum("tij,tj->ti", tri_rotations, self.rest_n)
        flips = int(((np.einsum("ij,ij->i", n, predicted) < 0) & self.tri_in).sum())
        dots = np.einsum("ij,ij->i", n[self.adjacent[:, 0]], n[self.adjacent[:, 1]])
        folded = np.unique(self.adjacent[(dots < 0.0) & (self.rest_dots >= 0.0)].ravel())  # plis NOUVEAUX : deux triangles voisins à plus de 90° l'un de l'autre alors qu'ils ne l'étaient pas au repos
        e = self.edges[self.edge_in]
        stretch = float((np.linalg.norm(points[e[:, 0]] - points[e[:, 1]], axis=1) / np.maximum(self.rest_len[self.edge_in], 1e-9)).max())
        row = {"retournees": flips, "etirement_max": round(stretch, 2), "aire_surface": round(float(a[self.tri_in].sum()) / self.rest_surface, 3), "plis": int(len(folded))}
        if self.rest_section is not None:
            row["aire_section"] = round(section_area(points, self.selection) / self.rest_section, 3)
        return row


def failures(row):
    out = []
    if row["plis"] > THRESHOLDS["retournees_max"]:
        out.append("plis")  # « retournées » (rotation rigide de l'os dominant) est INFORMATIVE seulement : mal posée à fort angle (CONCEPTION_RIG_CORRECTIFS.md §6)
    if row["etirement_max"] >= THRESHOLDS["etirement_max"]:
        out.append("etirement")
    for key in ("aire_section", "aire_surface"):
        if key in row and not (THRESHOLDS["aire_min"] <= row[key] <= THRESHOLDS["aire_max"]):
            out.append(key)
    return out
