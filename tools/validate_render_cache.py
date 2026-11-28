"""Réutilisation des rendus (audit SCI-011) : mêmes paramètres = réutilisé ; asset, réglage, caméra ou version de Blender changés, image modifiée ou sans manifeste = régénération ou refus.

  python tools/validate_render_cache.py    (Python seul ; aucune dépendance à Blender)"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_cache as rc  # noqa: E402

FAILURES = []


def check(label, condition, detail=""):
    print(("OK   " if condition else "ECHEC"), label, detail, flush=True)
    if not condition:
        FAILURES.append(label)


directory = Path(tempfile.mkdtemp(prefix="hl_cache_"))
(directory / "extension" / "data").mkdir(parents=True)
(directory / "extension" / "a.py").write_text("x = 1\n")
(directory / "extension" / "data" / "asset.blend").write_bytes(b"BLEND1")
image = directory / "rendu.png"
settings, camera = {"lumiere": "STUDIO", "resolution": [900, 1500]}, {"ortho": 2.05, "angle": 90}


def expected(**changes):
    args = dict(source=rc.source_fingerprint(directory), settings=settings, camera=camera, blender="5.2.0")
    args.update(changes)
    return rc.fingerprint(**args)


image.write_bytes(b"png-1")
check("sans manifeste : non reutilisable", not rc.is_current(image, expected()))
rc.record(image, expected())
check("memes parametres : reutilisable", rc.is_current(image, expected()))
check("option force : regeneration", not rc.is_current(image, expected(), force=True))
(directory / "extension" / "data" / "asset.blend").write_bytes(b"BLEND2")
check("asset change : regeneration", not rc.is_current(image, expected()))
(directory / "extension" / "data" / "asset.blend").write_bytes(b"BLEND1")
check("asset restaure : reutilisable", rc.is_current(image, expected()))
(directory / "extension" / "a.py").write_text("x = 2\n")
check("code change : regeneration", not rc.is_current(image, expected()))
(directory / "extension" / "a.py").write_text("x = 1\n")
check("reglage change : regeneration", not rc.is_current(image, expected(settings=dict(settings, lumiere="FLAT"))))
check("camera changee : regeneration", not rc.is_current(image, expected(camera=dict(camera, ortho=2.5))))
check("version de Blender changee : regeneration", not rc.is_current(image, expected(blender="5.2.1")))
image.write_bytes(b"png-modifie")
check("image modifiee apres coup : regeneration", not rc.is_current(image, expected()))
try:
    rc.require_current(image, expected())
    refused = False
except ValueError:
    refused = True
check("assembleur : refus d'une image perimee", refused)
rc.record(image, expected())
try:
    rc.require_current(image, expected())
    accepted = True
except ValueError:
    accepted = False
check("assembleur : image conforme acceptee", accepted)
print("RESULTAT", "ECHECS " + ", ".join(FAILURES) if FAILURES else "tout OK")
sys.exit(1 if FAILURES else 0)
