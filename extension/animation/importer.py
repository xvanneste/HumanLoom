"""Importation d'animations dans la bibliothèque de l'utilisateur (lot A1b) : FBX, BVH, glTF/GLB, .blend (actions) ou dossier.

Chaque source est convertie par un processus Blender séparé (`import_worker.py`) vers `HumanLoom_Actions.blend`, dans le dossier de bibliothèque
choisi par l'utilisateur, avec un `inventory.json` compatible avec l'index du lot A1. Garanties :
- la source n'est jamais écrite (SHA-256 avant/après, consigné dans le rapport) ; le dossier cible ne peut pas être celui d'une bibliothèque qui
  n'est pas la nôtre (marqueur « generator » exigé dans un `inventory.json` existant) ;
- un plantage ou un dépassement de délai d'un processus ne concerne que son fichier (échec consigné, les autres continuent) ;
- déduplication : fichier déjà importé (SHA-256) puis action de contenu identique (empreinte des courbes), quel que soit le nom ;
- rien n'est distribué : l'utilisateur importe ses propres fichiers, dont il détient les droits (voir docs/animations-import.md).

Ce module n'importe pas `bpy` : l'exécutable Blender est passé en paramètre (`bpy.app.binary_path` depuis Blender).
"""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

LIBRARY_BLEND = "HumanLoom_Actions.blend"
INVENTORY = "inventory.json"
GENERATOR = "HumanLoom animation import"
SUFFIXES = (".fbx", ".bvh", ".glb", ".gltf", ".blend")
WORKER = Path(__file__).with_name("import_worker.py")


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(16 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


PATH_PATTERN = re.compile(r"[A-Za-z]:[\\/][^'\"\n]*?([^\\/'\"\n]+)(?=['\"\n]|$)")


def clean_message(text):
    """Retire les chemins locaux d'un message d'erreur (Blender les cite, parfois avec des antislashs doublés) : ne garde que le nom du fichier."""
    return PATH_PATTERN.sub(lambda m: m.group(1), text).strip()


def collect(sources):
    """Liste de (fichier, racine) : un dossier est parcouru récursivement (racine = ce dossier, pour la catégorie) ; un fichier a pour racine None."""
    files = []
    for source in sources:
        source = Path(source)
        if source.is_dir():
            files += [(p, source) for p in sorted(source.rglob("*")) if p.is_file() and p.suffix.lower() in SUFFIXES]
        elif source.is_file():
            files.append((source, None))
    return files


def category_of(path, root):
    """Catégorie d'après le dossier de la source, relatif à la racine choisie (ex. « Marche/Rapide ») ; None si fichier isolé."""
    if root is None:
        return None
    relative = Path(path).parent.relative_to(root)
    return "/".join(relative.parts) or root.name


def read_inventory(library_dir):
    path = Path(library_dir) / INVENTORY
    if not path.is_file():
        return {"schema": 1, "generator": GENERATOR, "animations": {}, "imported_sources": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("generator") != GENERATOR:
        raise ValueError("Ce dossier contient déjà un inventory.json qui n'est pas celui de l'import HumanLoom : choisissez un dossier de bibliothèque dédié "
                         "(les sources ne sont jamais modifiées).")
    data.setdefault("imported_sources", {})
    return data


def write_inventory(library_dir, data):
    path = Path(library_dir) / INVENTORY
    handle, temp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=1)
        os.replace(temp, path)
    except BaseException:
        if os.path.exists(temp):
            os.unlink(temp)
        raise


def import_sources(sources, library_dir, blender, fps=30.0, timeout=900, limit=None, name_filter=None, category=None):
    """Importe `sources` (fichiers et/ou dossiers) dans `library_dir`. Retourne un rapport :
    {"fichiers": [{"source", "statut", ...}], "ajoutées", "doublons", "inchangés", "échecs", "sources_modifiées"}. Statuts : importé, doublon,
    inchangé (déjà importé, SHA-256 identique), échec (avec le message). `limit` / `name_filter` ne concernent que les sources .blend."""
    library_dir = Path(library_dir)
    files = collect(sources)
    library_blend = library_dir / LIBRARY_BLEND
    for path, _ in files:
        if path.resolve() == library_blend.resolve():
            raise ValueError("La bibliothèque cible ne peut pas être une source.")
    library_dir.mkdir(parents=True, exist_ok=True)
    inventory = read_inventory(library_dir)
    before = {str(p): sha256(p) for p, _ in files}
    report = {"fichiers": [], "ajoutées": 0, "doublons": 0, "inchangés": 0, "échecs": 0}
    with tempfile.TemporaryDirectory(prefix="hl_import_") as work:
        for number, (path, root) in enumerate(files):
            entry = {"source": path.name, "statut": None}
            report["fichiers"].append(entry)
            code = before[str(path)]
            if code in inventory["imported_sources"]:
                entry.update(statut="inchangé", actions=inventory["imported_sources"][code].get("actions", []))
                report["inchangés"] += 1
                continue
            job = {"source": str(path), "library_blend": str(library_blend), "fps": fps, "category": category_of(path, root) or category, "limit": limit, "name_filter": name_filter}
            job_path, result_path = Path(work) / f"job{number}.json", Path(work) / f"result{number}.json"
            job_path.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
            command = [str(blender), "--background", "--factory-startup", "--offline-mode", "--python-exit-code", "1", "--python", str(WORKER), "--", str(job_path), str(result_path)]
            try:
                done = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
                tail = (done.stdout + done.stderr)[-400:]
                returncode = done.returncode
            except subprocess.TimeoutExpired:
                entry.update(statut="échec", message=f"Délai dépassé ({timeout} s)")
                report["échecs"] += 1
                continue
            if not result_path.is_file():
                entry.update(statut="échec", message=f"Le processus Blender s'est arrêté sans résultat (code {returncode})", fin_de_journal=tail)
                report["échecs"] += 1
                continue
            result = json.loads(result_path.read_text(encoding="utf-8"))
            if result["errors"] and not result["entries"] and not result["skipped_duplicates"]:
                entry.update(statut="échec", message=clean_message(result["errors"][0]["message"]))
                report["échecs"] += 1
                continue
            for item in result["entries"]:
                inventory["animations"][item["id"]] = item
            names = [item["id"] for item in result["entries"]]
            if result["entries"] or result["skipped_duplicates"]:
                inventory["imported_sources"][code] = {"file": path.name, "actions": names + [d["same_as"] for d in result["skipped_duplicates"]]}
            entry.update(statut="importé" if result["entries"] else "doublon", ajoutées=len(result["entries"]), doublons=result["skipped_duplicates"], erreurs=result["errors"])
            report["ajoutées"] += len(result["entries"])
            report["doublons"] += len(result["skipped_duplicates"])
            if result["entries"] or result["skipped_duplicates"]:
                write_inventory(library_dir, inventory)
    after = {str(p): sha256(p) for p, _ in files}
    report["sources_modifiées"] = sorted(Path(k).name for k in before if before[k] != after[k])
    write_inventory(library_dir, inventory)
    return report
