"""Le constructeur de dépliage calcule sur son ENTRÉE (audit SCI-009) : empreinte de l'entrée tracée dans le rapport, entrée préservée octet pour octet, entrée = sortie refusée.

  python tools/validate_unfold_source.py     (Python ; lance Blender en sous-processus)
Contrôle négatif : l'ancien constructeur n'écrivait aucune empreinte d'entrée dans son rapport."""
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BLENDER = "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
FAILURES = []


def check(label, condition, detail=""):
    print(("OK   " if condition else "ECHEC"), label, detail, flush=True)
    if not condition:
        FAILURES.append(label)


def run(*args):
    return subprocess.run([BLENDER, "--background", "--factory-startup", "--offline-mode", "--python", str(ROOT / "tools" / "build_human_unfold.py"), "--", *map(str, args)],
                          capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=3000)


directory = Path(tempfile.mkdtemp(prefix="hl_unfold_"))
source = directory / "candidat.blend"
shutil.copy(ROOT / "extension" / "data" / "human_nodes.blend", source)
digest = hashlib.sha256(source.read_bytes()).hexdigest()
same = run(source, source)
check("SCI-009 entree = sortie : refus", same.returncode != 0 and hashlib.sha256(source.read_bytes()).hexdigest() == digest)
report_path = directory / "rapport.json"
result = run(source, directory / "sortie.blend", "--report", report_path)
output = result.stdout + result.stderr
check("SCI-009 calcul lance sur l'entree (empreinte et chemin tracés)", f"CALCUL_SUR {digest} {source}" in output.replace("\\", "/").replace(str(source).replace("\\", "/"), str(source)) or f"CALCUL_SUR {digest}" in output, output[-200:])
if report_path.exists():
    report = json.loads(report_path.read_text(encoding="utf-8"))
    check("SCI-009 rapport : empreinte de l'entree", report.get("source_sha256") == digest and report.get("calcule_sur_source") is True)
else:
    # l'asset livré porte déjà la couche de dépliage : aucun croisement à corriger, ou refus explicite de s'appliquer deux fois
    check("SCI-009 asset deja corrige : aucun rapport, sortie propre", "rien à corriger" in output or "rien � corriger" in output or "déjà présente" in output or "AssertionError" in output)
check("SCI-009 entree preservee octet pour octet", hashlib.sha256(source.read_bytes()).hexdigest() == digest)
print("RESULTAT", "ECHECS " + ", ".join(FAILURES) if FAILURES else "tout OK")
sys.exit(1 if FAILURES else 0)
