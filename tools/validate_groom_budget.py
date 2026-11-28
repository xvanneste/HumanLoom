"""Budget de mèches du groom (audit GRM-011) : le nombre de points estimé avant construction n'est jamais inférieur au nombre de points réellement produits, sur une grille longueur x nature x style x variation.

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/validate_groom_budget.py

L'estimation avant correction (`len(fiber(...))` seul) sert de contrôle négatif : elle doit être prise en défaut sur au moins un cas lisse long, sinon le test ne prouve rien."""
import itertools
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension import groom  # noqa: E402
from extension.groom_fibers import fiber  # noqa: E402

addon.register()
FAILURES = []


def check(label, condition, detail=""):
    print(("OK   " if condition else "ECHEC"), label, detail, flush=True)
    if not condition:
        FAILURES.append(label)


for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
bpy.ops.humanloom.create()
body = bpy.context.object
estimate_of = getattr(groom, "points_per_strand", None)
old_estimate = lambda region, cfg: len(fiber(cfg["length"], cfg["nature"]))  # noqa: E731
under, old_under, cases = [], 0, 0
for region, length, nature, style, variation in itertools.product(("SCALP", "BEARD"), (0.03, 0.12, 0.3, 0.45), (0.0, 0.2, 0.34, 0.5, 1.0), ("SWEPT", "PARTED", "UPRIGHT"), (0.0, 0.5)):
    cfg = groom.defaults(region)
    cfg.update(length=length, nature=nature, style=style, variation=variation, guides=12)
    root, normals, *_ = groom.sample(body, region, cfg["guides"], cfg["seed"])
    produced = max(len(p) for p in groom.make_positions(body, root, normals, region, cfg))
    cases += 1
    if old_estimate(region, cfg) < produced:
        old_under += 1
    if estimate_of is None or estimate_of(region, cfg) < produced:
        under.append((region, length, nature, style, variation, produced, None if estimate_of is None else estimate_of(region, cfg)))
check("GRM-011 controle negatif : l'ancienne estimation sous-estime des cas de la grille", old_under > 0, f"{old_under}/{cases}")
check("GRM-011 estimation >= points produits sur toute la grille", not under, f"{len(under)}/{cases} en defaut, ex. {under[:2]}")
cfg = groom.defaults("SCALP")
cfg.update(length=0.45, nature=0.0, style="SWEPT", variation=0.0)
ratio = (estimate_of(("SCALP"), cfg) if estimate_of else old_estimate("SCALP", cfg))
check("GRM-011 cas du constat (45 cm, nature 0) : estimation proche de 114 points", ratio >= 114, str(ratio))
# refus avant construction : un budget franchi n'altere pas un groom existant
cfg2 = groom.defaults("SCALP")
cfg2.update(length=0.45, nature=0.0, density=8.0e6)
existing = groom.build(body, "SCALP", groom.defaults("SCALP"))
before = (existing.name, len(existing.data.curves), existing.data.curves[0].points_length if len(existing.data.curves) else 0)
try:
    groom.build(body, "SCALP", cfg2)
    refused = False
except ValueError:
    refused = True
hair = groom.find(body, "SCALP")
after = (hair.name, len(hair.data.curves), hair.data.curves[0].points_length if len(hair.data.curves) else 0) if hair else None
check("GRM-011 budget franchi : refus", refused)
check("GRM-011 budget franchi : groom existant intact", after == before, f"{before} -> {after}")
print("RESULTAT", "ECHECS " + ", ".join(FAILURES) if FAILURES else "tout OK")
sys.exit(1 if FAILURES else 0)
