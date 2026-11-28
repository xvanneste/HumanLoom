"""Solveur de correctifs : même invariant de section au repos et en gradient, préconditions, rapport de convergence, résultat jamais pire que le départ (audit ANI-013, ANI-014).

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/validate_corrective_solver.py   (numpy pur ; Blender n'est nécessaire que pour importer le paquet)"""
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import extension  # noqa: E402,F401
from extension.animation import correctives_solver as solver  # noqa: E402

FAILURES = []
N = 7


def check(label, condition, detail=""):
    print(("OK   " if condition else "ECHEC"), label, detail, flush=True)
    if not condition:
        FAILURES.append(label)


def slab(scale=1.0, layers=3):
    """Dalle épaisse (plusieurs couches) : λ3 > 0, comme une vraie tranche de membre."""
    pts, tris, edges = [], [], set()
    rng = np.random.default_rng(3)

    def index(k, i, j):
        return k * N * N + i * N + j

    for k in range(layers):
        for i in range(N):
            for j in range(N):
                pts.append([i * 0.01, j * 0.012 + 0.0005 * rng.standard_normal(), k * 0.01])
    for k in range(layers):
        for i in range(N - 1):
            for j in range(N - 1):
                a, b, c, d = index(k, i, j), index(k, i + 1, j), index(k, i + 1, j + 1), index(k, i, j + 1)
                tris += [[a, b, c], [a, c, d]]
                edges |= {(min(p, q), max(p, q)) for p, q in ((a, b), (b, c), (c, a), (a, d), (c, d))}
        if k:
            for i in range(N):
                for j in range(N):
                    edges.add((index(k - 1, i, j), index(k, i, j)))
    return np.array(pts) * scale, np.array(tris), np.array(sorted(edges))


def problem(scale=1.0, free_layer=1, sections=True):
    rest, tris, edges = slab(scale)
    free = np.arange(free_layer * N * N, (free_layer + 1) * N * N)
    selection = np.arange(len(rest))
    secs = [(selection, solver.section_area(rest, selection))] if sections else []
    return solver.Problem(rest, edges, tris, free, secs, np.ones(len(free)), np.ones(len(free)) * 2.0), rest


def e2(points):
    c = points - points.mean(0)
    lam = np.linalg.eigvalsh(c.T @ c / len(points))
    return lam[0] * lam[1] + lam[0] * lam[2] + lam[1] * lam[2]


# ---------------------------------------------------------------- ANI-013
p, rest = problem()
gx = np.zeros_like(rest)
p.section_grad(rest, gx)
check("ANI-013 gradient de section nul au repos", float(np.abs(gx).max()) < 1e-9, f"{float(np.abs(gx).max()):.2e}")
area = p.sections[0][1]
check("ANI-013 mesure au repos = racine de l'invariant du gradient", abs(area ** 2 - e2(rest)) < 1e-12, f"{area ** 2:.3e} vs {e2(rest):.3e}")
x = rest + 0.002 * np.random.default_rng(1).standard_normal(rest.shape)
gx = np.zeros_like(x)
p.section_grad(x, gx)


def energy(y):
    return (math.sqrt(max(e2(y) / area ** 2, 1e-9)) - 1.0) ** 2


worst = 0.0
for vertex in (0, 17, 60, 100):
    for axis in range(3):
        h = 1e-6
        a, b = x.copy(), x.copy()
        a[vertex, axis] += h
        b[vertex, axis] -= h
        worst = max(worst, abs((energy(a) - energy(b)) / (2 * h) - gx[vertex, axis]))
check("ANI-013 gradient analytique = differences finies", worst < 1e-5 * max(1.0, float(np.abs(gx).max())), f"ecart {worst:.2e}")
theta = 0.7
R = np.array([[math.cos(theta), -math.sin(theta), 0], [math.sin(theta), math.cos(theta), 0], [0, 0, 1]])
moved = x @ R.T + np.array([0.3, -0.2, 0.9])
check("ANI-013 invariance rigide de la mesure", abs(e2(moved) - e2(x)) < 1e-12)
for scale in (0.1, 10.0):
    ps, rs = problem(scale)
    g = np.zeros_like(rs)
    ps.section_grad(rs, g)
    check(f"ANI-013 repos sans gradient a l'echelle {scale}", float(np.abs(g).max()) < 1e-9 * max(1.0, scale))

# ---------------------------------------------------------------- ANI-014
rest, tris, edges = slab()
free = np.arange(N * N, 2 * N * N)


def raises(factory):
    try:
        factory()
    except ValueError:
        return True
    except Exception as error:  # noqa: BLE001
        return type(error).__name__
    return False


duplicate = rest.copy()
duplicate[N * N + 1] = duplicate[N * N]
res = raises(lambda: solver.Problem(duplicate, edges, tris, free, [], np.ones(len(free)), np.ones(len(free))))
check("ANI-014 arete de longueur nulle : ValueError explicite", res is True, str(res))
res = raises(lambda: solver.Problem(rest, edges, tris, np.array([], dtype=int), [], np.array([]), np.array([])))
check("ANI-014 selection vide : ValueError explicite", res is True, str(res))
nan_rest = rest.copy()
nan_rest[3, 0] = float("nan")
res = raises(lambda: solver.Problem(nan_rest, edges, tris, free, [], np.ones(len(free)), np.ones(len(free))))
check("ANI-014 repos non fini : ValueError explicite", res is True, str(res))
try:
    lone = solver.Problem(rest[:3], np.array([[0, 1], [1, 2], [0, 2]]), np.array([[0, 1, 2]]), np.array([1]), [], np.ones(1), np.ones(1))
    out = lone.solve(rest[:3] + 0.001, iterations=5)
    ok = bool(np.isfinite(out).all())
except Exception as error:  # noqa: BLE001
    ok = False
    print("   ", type(error).__name__, error)
check("ANI-014 aucune paire de triangles : pas de plantage", ok)
p, rest = problem()
start = rest.copy()
start[p.free] += 0.003 * np.random.default_rng(5).standard_normal((len(p.free), 3))
if hasattr(p, "solve_report"):
    out, report = p.solve_report(start)
    check("ANI-014 rapport : champs publies", {"energie_initiale", "energie_finale", "finie", "accepte", "iterations", "motif_arret"} <= set(report), str(sorted(report)))
    check("ANI-014 energie finale <= initiale", report["energie_finale"] <= report["energie_initiale"] * (1 + 1e-9), f"{report['energie_initiale']:.3e} -> {report['energie_finale']:.3e}")
    check("ANI-014 resultat fini", bool(np.isfinite(out).all()))
    bad = start.copy()
    bad[p.free[0], 0] = float("nan")
    check("ANI-014 depart non fini : ValueError", raises(lambda: p.solve_report(bad)) is True)
    diverging = p.solve_report(start, lr=50.0)
    check("ANI-014 pas excessif : depart conserve ou energie en baisse", diverging[1]["energie_finale"] <= diverging[1]["energie_initiale"] * (1 + 1e-9) and bool(np.isfinite(diverging[0]).all()), diverging[1]["motif_arret"])
    for scale in (0.1, 1.0, 10.0):
        ps, rs = problem(scale)
        s0 = rs.copy()
        s0[ps.free] += 0.003 * scale * np.random.default_rng(6).standard_normal((len(ps.free), 3))
        out, rep = ps.solve_report(s0)
        check(f"ANI-014 echelle {scale} : fini et accepte", bool(np.isfinite(out).all()) and rep["accepte"], f"{rep['energie_initiale']:.3e} -> {rep['energie_finale']:.3e}")
else:
    check("ANI-014 rapport de convergence disponible", False, "solve_report absent")
print("RESULTAT", "ECHECS " + ", ".join(FAILURES) if FAILURES else "tout OK")
sys.exit(1 if FAILURES else 0)
