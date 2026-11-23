"""Vignettes de la galerie (lot F0-b) : cache disque, génération par lots dans un processus Blender séparé (`thumbnail_worker.py`), chargement paresseux des aperçus.

Le cache est dans le dossier utilisateur (`<cache>/thumbs/<clé>.png`), jamais dans le dépôt ni le paquet. La clé dépend de l'identifiant de l'animation et de l'armature source choisie.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

WORKER = Path(__file__).with_name("thumbnail_worker.py")


def key_for(entry_id, source_name):
    return hashlib.sha1(f"{source_name}|{entry_id}".encode("utf-8")).hexdigest()[:20]


def thumb_path(cache_dir, key):
    return Path(cache_dir) / "thumbs" / f"{key}.png"


def missing(cache_dir, items):
    """Sous-liste de `items` [(clé, nom d'action)] dont la vignette n'existe pas encore."""
    return [(k, a) for k, a in items if not thumb_path(cache_dir, k).is_file()]


def generate(cache_dir, blender, library_blend, source_armature, items, size=96, timeout=900):
    """Génère les vignettes manquantes dans un processus Blender séparé. Retourne {"produced": [...], "errors": [...]} (jamais d'exception pour une action en échec)."""
    todo = missing(cache_dir, items)
    if not todo:
        return {"produced": [], "errors": []}
    with tempfile.TemporaryDirectory(prefix="hl_thumbs_") as work:
        job_path, result_path = Path(work) / "job.json", Path(work) / "result.json"
        job_path.write_text(json.dumps({"library_blend": str(library_blend), "source_armature": source_armature, "actions": todo, "out_dir": str(Path(cache_dir) / "thumbs"),
                                        "package_dir": str(WORKER.parent), "size": size}), encoding="utf-8")
        command = [str(blender), "--background", "--factory-startup", "--offline-mode", "--python-exit-code", "1", "--python", str(WORKER), "--", str(job_path), str(result_path)]
        try:
            subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
        except subprocess.TimeoutExpired:
            return {"produced": [], "errors": [{"message": f"Délai dépassé ({timeout} s)"}]}
        if not result_path.is_file():
            return {"produced": [], "errors": [{"message": "Le processus de vignettes s'est arrêté sans résultat"}]}
        return json.loads(result_path.read_text(encoding="utf-8"))
