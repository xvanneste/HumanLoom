"""Flux normal des joues : propriétés mathématiques et comparaison à une métrique indépendante (audit ANI-025).

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/validate_face_flux.py   (numpy pur ; Blender n'importe que le paquet)

Contrôles : invariance rigide, facteur k³ sous mise à l'échelle isotrope, accord au premier ordre avec la variation de volume d'une sphère fermée (métrique indépendante : volume par tétraèdres), et noms de sortie qui ne prétendent plus mesurer un volume."""
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import extension  # noqa: E402,F401
from extension.animation import face  # noqa: E402

FAILURES = []


def check(label, condition, detail=""):
    print(("OK   " if condition else "ECHEC"), label, detail, flush=True)
    if not condition:
        FAILURES.append(label)


def sphere(radius=0.05, rings=24, segments=36):
    pts = [[0, 0, radius]]
    for i in range(1, rings):
        phi = math.pi * i / rings
        for j in range(segments):
            theta = 2 * math.pi * j / segments
            pts.append([radius * math.sin(phi) * math.cos(theta), radius * math.sin(phi) * math.sin(theta), radius * math.cos(phi)])
    pts.append([0, 0, -radius])
    pts = np.array(pts)
    tris = []
    for j in range(segments):
        tris.append([0, 1 + j, 1 + (j + 1) % segments])
    for i in range(rings - 2):
        for j in range(segments):
            a, b = 1 + i * segments + j, 1 + i * segments + (j + 1) % segments
            c, d = a + segments, b + segments
            tris += [[a, c, b], [b, c, d]]
    last = len(pts) - 1
    for j in range(segments):
        tris.append([last, 1 + (rings - 2) * segments + (j + 1) % segments, 1 + (rings - 2) * segments + j])
    return pts, np.array(tris)


def enclosed_volume(points, tris):
    a, b, c = points[tris[:, 0]], points[tris[:, 1]], points[tris[:, 2]]
    return float(np.einsum("ij,ij->i", a, np.cross(b, c)).sum() / 6.0)


rest, tris = sphere()
rng = np.random.default_rng(2)
posed = rest * 1.02 + 0.0004 * rng.standard_normal(rest.shape)
flux = face.normal_flux(rest, posed, tris)
reference = enclosed_volume(posed, tris) - enclosed_volume(rest, tris)
check("ANI-025 surface fermee : somme du flux = variation de volume independante (premier ordre)", abs(flux.sum() - reference) / abs(reference) < 0.05, f"flux {flux.sum():.3e} vs volume {reference:.3e}")
theta = 0.9
R = np.array([[math.cos(theta), 0, math.sin(theta)], [0, 1, 0], [-math.sin(theta), 0, math.cos(theta)]])
shift = np.array([0.4, -0.7, 1.1])
rotated = face.normal_flux(rest @ R.T + shift, posed @ R.T + shift, tris)
check("ANI-025 invariance par rotation et translation", float(np.abs(rotated - flux).max()) < 1e-15 + 1e-9 * float(np.abs(flux).max()))
for k in (0.1, 10.0):
    scaled = face.normal_flux(rest * k, posed * k, tris)
    check(f"ANI-025 facteur k^3 sous echelle isotrope k={k}", abs(scaled.sum() / flux.sum() - k ** 3) < 1e-9 * k ** 3, f"{scaled.sum() / flux.sum():.6g}")
region = np.arange(len(rest)) < len(rest) // 3
patch = flux[region].sum()
check("ANI-025 patch ouvert : le flux d'un disque n'est pas la variation du volume enclos", abs(patch - reference) / abs(reference) > 0.2, f"patch {patch:.3e} / volume total {reference:.3e}")
source = Path(face.__file__).read_text(encoding="utf-8")
check("ANI-025 sorties nommees flux normal (plus « volume »)", "joue_flux_normal_net_cm3" in source and "joue_volume_net_cm3" not in source and "joue_volume_brut_cm3" not in source)
print("RESULTAT", "ECHECS " + ", ".join(FAILURES) if FAILURES else "tout OK")
sys.exit(1 if FAILURES else 0)
