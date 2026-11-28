"""Cas dégénérés du noyau de retargeting : erreurs explicites, aucun NaN, aucune mutation (audit ANI-007).

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/validate_retarget_degenerate.py   (numpy pur ; Blender n'importe que le paquet)"""
import copy
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import extension  # noqa: E402,F401
from extension.animation import retarget as rt  # noqa: E402

FAILURES = []


def check(label, condition, detail=""):
    print(("OK   " if condition else "ECHEC"), label, detail, flush=True)
    if not condition:
        FAILURES.append(label)


def matrix(position):
    m = np.eye(4)
    m[:3, 3] = position
    return m


def chain(scale=1.0, pelvis_height=1.0):
    """pelvis -> spine -> arm (bras tendu vers +x) ; un os par ligne."""
    names = ["pelvis", "spine", "arm"]
    rest = np.array([matrix((0, 0, pelvis_height * scale)), matrix((0, 0, (pelvis_height + 0.3) * scale)), matrix((0.2 * scale, 0, (pelvis_height + 0.3) * scale))])
    return rt.Rig(names, [-1, 0, 1], rest)


def motion(frames=3, rig=None):
    count = 3
    loc = np.zeros((frames, count, 3))
    quat = np.zeros((frames, count, 4))
    quat[..., 0] = 1.0
    return rt.Motion(loc, quat, 30.0)


MAPPING = {"pelvis": "pelvis", "spine": "spine", "arm": "arm"}


def attempt(label, build, expect_error=True):
    """Appelle `build()` ; une erreur doit être un ValueError explicite (pas AssertionError/IndexError/ZeroDivisionError) et la sortie ne doit contenir aucun NaN."""
    try:
        result = build()
    except ValueError as error:
        check(label, expect_error, "ValueError : " + str(error)[:80])
        return
    except Exception as error:  # noqa: BLE001
        check(label, False, f"{type(error).__name__}: {str(error)[:80]}")
        return
    if expect_error:
        check(label, False, "aucune erreur")
        return
    finite = bool(np.isfinite(result.quat).all() and np.isfinite(result.loc).all())
    check(label, finite, "NaN dans le resultat" if not finite else "")


def run(source=None, target=None, mapping=None, mo=None, options=None):
    return rt.retarget(source or chain(), target or chain(), MAPPING if mapping is None else mapping, mo or motion(), options)


attempt("ANI-007 cas nominal : fini", lambda: run(), expect_error=False)
attempt("ANI-007 squelette cible vide", lambda: run(target=rt.Rig([], [], np.zeros((0, 4, 4)))))
attempt("ANI-007 squelette source vide", lambda: run(source=rt.Rig([], [], np.zeros((0, 4, 4)))))
attempt("ANI-007 bassin source a hauteur nulle (echelle automatique)", lambda: run(source=chain(pelvis_height=0.0)))
attempt("ANI-007 bassin source a hauteur nulle avec echelle explicite", lambda: run(source=chain(pelvis_height=0.0), options=rt.Options(translation_scale=1.0)), expect_error=False)
bad = motion()
bad.quat[1, 1] = 0.0
attempt("ANI-007 quaternion nul", lambda: run(mo=bad))
bad = motion()
bad.loc[0, 0, 0] = float("nan")
attempt("ANI-007 translation non finie", lambda: run(mo=bad))
attempt("ANI-007 aucune image", lambda: run(mo=rt.Motion(np.zeros((0, 3, 3)), np.zeros((0, 3, 4)), 30.0)))
attempt("ANI-007 mapping vide", lambda: run(mapping={}))
attempt("ANI-007 mapping vers un os inexistant", lambda: run(mapping=dict(MAPPING, spine="fantome")))
attempt("ANI-007 echelle de translation negative", lambda: run(options=rt.Options(translation_scale=-1.0)))
attempt("ANI-007 echelle de translation NaN", lambda: run(options=rt.Options(translation_scale=float("nan"))))
attempt("ANI-007 mode de pose inconnu", lambda: run(options=rt.Options(pose_mode="inconnu")))
attempt("ANI-007 limb_blend hors bornes", lambda: run(options=rt.Options(limb_blend=3.0)))
attempt("ANI-007 neck_twist hors bornes", lambda: run(options=rt.Options(neck_twist=2.0)))
broken = rt.Rig.__new__(rt.Rig)
try:
    rt.Rig(["a", "b"], [1, -1], np.array([np.eye(4), np.eye(4)]))
    check("ANI-007 parents dans le desordre : ValueError", False, "aucune erreur")
except ValueError:
    check("ANI-007 parents dans le desordre : ValueError", True)
except AssertionError:
    check("ANI-007 parents dans le desordre : ValueError", False, "AssertionError")
# antiparalleles : pas de division par zero ni de NaN dans arc_rotations
a = np.array([[1.0, 0, 0], [0, 1.0, 0], [0, 0, 1.0]])
with np.errstate(all="raise"):
    try:
        out = rt.arc_rotations(a, -a)
        ok = bool(np.isfinite(out).all()) and bool(np.allclose(np.einsum("fij,fj->fi", out, a), -a, atol=1e-9))
    except FloatingPointError as error:
        ok = False
        print("   ", error)
check("ANI-007 vecteurs antiparalleles : rotations exactes sans erreur flottante", ok)
# bras replie (colineaire avec l'axe du thorax) : pas de NaN
folded = chain()
folded.rest[2][:3, 3] = folded.rest[1][:3, 3] + np.array([0, 0, 0.0])
attempt("ANI-007 segment nul (bras replie sur le thorax)", lambda: run(source=folded), expect_error=False)
# vitesse invalide
base = run()
for speed in (0.0, -2.0, float("nan")):
    attempt(f"ANI-007 vitesse {speed}", lambda speed=speed: rt.trim_and_speed(base, speed=speed))
# aucune mutation partielle
source, mo = chain(), motion()
snapshot = (copy.deepcopy(source.rest), mo.loc.copy(), mo.quat.copy())
try:
    run(source=source, mo=mo, options=rt.Options(pose_mode="inconnu"))
except Exception:  # noqa: BLE001
    pass
check("ANI-007 entrees non mutees apres erreur", np.array_equal(snapshot[0], source.rest) and np.array_equal(snapshot[1], mo.loc) and np.array_equal(snapshot[2], mo.quat))
print("RESULTAT", "ECHECS " + ", ".join(FAILURES) if FAILURES else "tout OK")
sys.exit(1 if FAILURES else 0)
