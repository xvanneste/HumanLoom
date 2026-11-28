"""Cohérence de la documentation d'entrée avec le code (audit INT-005) : version, chemins cités, états périmés.

  python tools/check_docs_consistency.py     (Python seul, aucune dépendance à Blender)"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FAILURES = []


def check(label, condition, detail=""):
    print(("OK   " if condition else "ECHEC"), label, detail, flush=True)
    if not condition:
        FAILURES.append(label)


readme = (ROOT / "README.md").read_text(encoding="utf-8")
manifest = (ROOT / "extension" / "blender_manifest.toml").read_text(encoding="utf-8")
version = re.search(r'^version\s*=\s*"([^"]+)"', manifest, re.M).group(1)
check("INT-005 version du manifeste citee dans le README", f"HumanLoom {version}" in readme or f"**HumanLoom {version}**" in readme, version)
guide = ROOT / "docs" / "guide-utilisateur.md"
if guide.is_file():
    check("INT-005 version du manifeste citee dans le guide ou absente de toute version anterieure", version in guide.read_text(encoding="utf-8") or not re.search(r"\b0\.1[0-5]\.\d\b", guide.read_text(encoding="utf-8")))
paths = sorted(set(re.findall(r"`((?:extension|tools|docs)/[A-Za-z0-9_./*-]+)`", readme)))
missing = [p for p in paths if "*" not in p and not (ROOT / p).exists()]
check("INT-005 chaque chemin cite par le README existe", not missing, str(missing))
stale = ["Le rig n'est pas livré", "schéma de formes **9** (ancien moteur ; le corps natif est au schéma 10)" if False else "Le rig n’est pas livré"]
check("INT-005 aucun etat perime (rig non livre)", not any(s in readme for s in stale))
check("INT-005 le README ne fige pas un nombre de tests", not re.search(r"\b\d+/\d+ tests requis", readme))
sys.exit_code = 0
print("RESULTAT", "ECHECS " + ", ".join(FAILURES) if FAILURES else "tout OK")
sys.exit(1 if FAILURES else 0)
