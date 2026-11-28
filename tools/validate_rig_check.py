"""Comparaison des poids/ancres du squelette (audit ANI-030) : fixture identique = identique ; un poids, une ancre ou un nom modifié = différence localisée.

  python tools/validate_rig_check.py"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rig_check  # noqa: E402

FAILURES = []


def check(label, condition, detail=""):
    print(("OK   " if condition else "ECHEC"), label, detail, flush=True)
    if not condition:
        FAILURES.append(label)


names = np.array(["root", "pelvis", "spine"])
idx = np.array([[0, 1], [1, 2], [2, 0]], dtype=np.int16)
w = np.array([[0.7, 0.3], [0.5, 0.5], [1.0, 0.0]], dtype=np.float32)
anchors = {"head": {"vertices": [1, 2, 3]}, "foot": {"vertices": [4]}}


def run(**changes):
    args = dict(stored_anchors=anchors, new_anchors=anchors, stored_names=names, stored_idx=idx, stored_w=w, new_names=names, new_idx=idx, new_w=w.copy())
    args.update(changes)
    return rig_check.compare(**args)


check("ANI-030 fixture identique", run()["identique"])
check("ANI-030 bruit float32 sous la tolerance", run(new_w=(w + 5e-8).astype(np.float32))["identique"])
changed = w.copy()
changed[1, 0] = 0.6
report = run(new_w=changed)
check("ANI-030 poids modifie : difference localisee", not report["identique"] and report["poids"][0]["sommet"] == 1 and report["poids"][0]["os"] == "pelvis", str(report["poids"][:1]))
report = run(new_anchors=dict(anchors, head={"vertices": [1, 2, 9]}))
check("ANI-030 ancre modifiee : difference localisee", not report["identique"] and report["ancres"][0]["ancre"] == "head")
report = run(new_anchors={"head": anchors["head"]})
check("ANI-030 ancre manquante", not report["identique"] and report["ancres"][0]["ancre"] == "foot")
report = run(new_idx=idx[::-1].copy())
check("ANI-030 influences differentes", not report["identique"] and report["influences"] > 0)
report = run(new_names=np.array(["root", "pelvis", "autre"]))
check("ANI-030 noms differents", not report["identique"] and "autre" in report["noms"])
report = run(new_w=w[:2], new_idx=idx[:2])
check("ANI-030 formes differentes", not report["identique"])
print("RESULTAT", "ECHECS " + ", ".join(FAILURES) if FAILURES else "tout OK")
sys.exit(1 if FAILURES else 0)
