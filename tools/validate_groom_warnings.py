"""Avertissements du groom hors domaine (audit GRM-012, GRM-019) : sous-pas numériques, simulation expérimentale, moteur de rendu sans Principled Hair, sans changer la scène de l'utilisateur.

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/validate_groom_warnings.py"""
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension import groom  # noqa: E402

addon.register()
FAILURES = []


def check(label, condition, detail=""):
    print(("OK   " if condition else "ECHEC"), label, detail, flush=True)
    if not condition:
        FAILURES.append(label)


scene = bpy.context.scene
domain = getattr(groom, "domain_warnings", None)
render = getattr(groom, "render_warnings", None)
check("GRM-012 API d'avertissements presente", domain is not None and render is not None)
if domain is not None:
    base = groom.defaults("SCALP")
    check("GRM-012 reglages par defaut : aucun avertissement", domain(base) == [], str(domain(base)))
    check("GRM-012 sous-pas <= 19 : aucun avertissement", domain(dict(base, physics="XPBD", substeps=19)) == [] or all("sous-pas" not in w for w in domain(dict(base, physics="XPBD", substeps=19))))
    warnings = domain(dict(base, physics="XPBD", substeps=24))
    check("GRM-012 sous-pas 24 : avertissement cible (manuel 5.2 : moins de 20)", any("sous-pas" in w.lower() for w in warnings), str(warnings))
    check("GRM-012 simulation XPBD : indiquee experimentale et non validee", any("expérimental" in w.lower() for w in domain(dict(base, physics="XPBD"))))
    check("GRM-012 mode suivi du corps : aucun avertissement de simulation", all("expérimental" not in w.lower() for w in domain(dict(base, physics="ANIMATION", substeps=30))))
    long_hair = domain(dict(base, physics="XPBD", length=0.45))
    check("GRM-012 fibre longue en XPBD : hors du domaine verifie", any("longueur" in w.lower() for w in long_hair), str(long_hair))
prop = groom.HL_GroomSettings.bl_rna.properties["substeps"]
check("GRM-012 curseur de sous-pas : borne douce a 19, borne dure compatible (32)", prop.soft_max == 19 and prop.hard_max == 32, f"soft {prop.soft_max} hard {prop.hard_max}")
if render is not None:
    engines = {}
    for engine in ("CYCLES", "BLENDER_EEVEE", "BLENDER_WORKBENCH"):
        scene.render.engine = engine
        engines[engine] = render(scene)
    check("GRM-019 Cycles : aucun avertissement", engines["CYCLES"] == [], str(engines["CYCLES"]))
    check("GRM-019 EEVEE : avertissement Cycles requis", any("cycles" in w.lower() for w in engines["BLENDER_EEVEE"]), str(engines["BLENDER_EEVEE"]))
    check("GRM-019 Workbench : avertissement", bool(engines["BLENDER_WORKBENCH"]))
    scene.render.engine = "BLENDER_EEVEE"
    render(scene)
    check("GRM-019 aucun changement silencieux du moteur de la scene", scene.render.engine == "BLENDER_EEVEE")
print("RESULTAT", "ECHECS " + ", ".join(FAILURES) if FAILURES else "tout OK")
sys.exit(1 if FAILURES else 0)
