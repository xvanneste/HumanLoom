"""Vignettes de la galerie (lot F0-b) : cache disque, génération par lots dans un processus Blender séparé (`thumbnail_worker.py`), chargement paresseux des aperçus.

Le cache est dans le dossier utilisateur (`<cache>/thumbs/<clé>.png`), jamais dans le dépôt ni le paquet. La clé dépend du clip, du squelette de référence et du contenu de la bibliothèque.
"""
from collections import OrderedDict
from concurrent.futures import CancelledError, Future
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from threading import Condition, Event, Thread
import time

WORKER = Path(__file__).with_name("thumbnail_worker.py")
_revision_ready = Condition()
_revision_completed = OrderedDict()
_revision_retry_at = OrderedDict()
_REVISION_RETRY_DELAY = 0.25
_revision_pending = OrderedDict()
_revision_active = None
_revision_thread = None


def _file_version(path):
    stat = path.stat()
    return stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns


def _hash_library(path, version, cancel):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while not cancel.is_set():
            block = source.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    if cancel.is_set():
        raise CancelledError()
    if _file_version(path) != version:
        raise ValueError("La bibliothèque a changé pendant la lecture. Relancez les vignettes.")
    return digest.hexdigest()


def _revision_loop():
    global _revision_active
    while True:
        with _revision_ready:
            _revision_ready.wait_for(lambda: bool(_revision_pending))
            key = min(_revision_pending, key=lambda item: _revision_retry_at.get(item, 0))
            delay = _revision_retry_at.get(key, 0) - time.monotonic()
            if delay > 0:
                _revision_ready.wait(timeout=delay)
                continue
            task, cancel = _revision_pending.pop(key)
            _revision_active = key, task, cancel
        try:
            revision = _hash_library(*key, cancel)
        except Exception as error:
            with _revision_ready:
                _revision_active = None
                if not cancel.is_set():
                    _revision_retry_at[key] = time.monotonic() + _REVISION_RETRY_DELAY
                    _revision_retry_at.move_to_end(key)
                    while len(_revision_retry_at) > 8:
                        _revision_retry_at.popitem(last=False)
            task.set_exception(error)
        else:
            with _revision_ready:
                _revision_active = None
                cancelled = cancel.is_set()
                if not cancelled:
                    _revision_retry_at.pop(key, None)
                    _revision_completed[key] = task
                    while len(_revision_completed) > 8:
                        _revision_completed.popitem(last=False)
            if cancelled:
                task.set_exception(CancelledError())
            else:
                task.set_result(revision)


def _revision_task(library):
    global _revision_thread
    path = Path(library).resolve()
    key = path, _file_version(path)
    with _revision_ready:
        previous = _revision_completed.get(key)
        if previous is not None:
            _revision_completed.move_to_end(key)
            return previous
        if key in _revision_pending:
            return _revision_pending[key][0]
        if _revision_active is not None:
            active_key, task, cancel = _revision_active
            if active_key == key and not cancel.is_set():
                return task
            if active_key[0] == path:
                cancel.set()
        for obsolete in tuple(_revision_pending):
            if obsolete[0] == path:
                _revision_pending.pop(obsolete)[0].cancel()
        if len(_revision_pending) == 2:
            _revision_pending.popitem(last=False)[1][0].cancel()
        task = Future()
        _revision_pending[key] = task, Event()
        if _revision_thread is None:
            _revision_thread = Thread(target=_revision_loop, name="HumanLoomThumbs", daemon=True)
            _revision_thread.start()
        _revision_ready.notify()
        return task


def cancel_library_revisions():
    """Abandonne les tâches à la fermeture ou au changement de scène."""
    with _revision_ready:
        if _revision_active is not None:
            _revision_active[2].set()
        for task, _cancel in _revision_pending.values():
            task.cancel()
        _revision_pending.clear()
        _revision_retry_at.clear()


def request_library_revision(library):
    """Lance le calcul si nécessaire et renvoie None tant qu’il est en cours."""
    task = _revision_task(library)
    try:
        return task.result() if task.done() else None
    except CancelledError:
        return None


def library_revision(library, cancel=None):
    """Attend la révision dans un fil de préparation ou le processus des vignettes."""
    while cancel is None or not cancel.is_set():
        task = _revision_task(library)
        try:
            return task.result(timeout=0.2)
        except CancelledError:
            continue
        except TimeoutError:
            if task.done():
                raise
    raise CancelledError()


def scope_for(rig, revision, euler_order=None):
    """Contexte de cache commun à la grille, au processus de vignettes et aux favoris."""
    encoded = json.dumps((rig.names, rig.parents, rig.rest.tolist(), revision, euler_order), ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def key_for(entry_id, action_name, scope):
    encoded = json.dumps(("pose-v5", entry_id, action_name, scope), ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:32]


def thumb_path(cache_dir, key):
    return Path(cache_dir) / "thumbs" / f"{key}.png"


def missing(cache_dir, items):
    """Sous-liste de `items` [(clé, nom d'action)] dont la vignette n'existe pas encore."""
    return [(k, a) for k, a in items if not thumb_path(cache_dir, k).is_file()]


def _run_worker(command, timeout, cancel):
    deadline = time.monotonic() + timeout
    with subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) as process:
        while process.poll() is None:
            if cancel is not None and cancel.is_set():
                process.kill()
                raise CancelledError()
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                process.kill()
                raise subprocess.TimeoutExpired(command, timeout)
            try:
                process.wait(timeout=min(0.2, remaining))
            except subprocess.TimeoutExpired:
                continue


def generate(cache_dir, blender, library_blend, source_armature, items, size=96, timeout=900, *, source_rig=None, revision=None, euler_order="XYZ", cancel=None):
    """Génère les vignettes manquantes dans un processus Blender séparé. Retourne {"produced": [...], "errors": [...]} (jamais d'exception pour une action en échec)."""
    if cancel is not None and cancel.is_set():
        raise CancelledError()
    todo = missing(cache_dir, items)
    if not todo:
        return {"produced": [], "errors": []}
    out_dir = Path(cache_dir) / "thumbs"
    out_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="hl_thumbs_") as work, tempfile.TemporaryDirectory(prefix=".hl-t-", dir=out_dir) as staging:
        job_path, result_path = Path(work) / "job.json", Path(work) / "result.json"
        job_path.write_text(json.dumps({"library_blend": str(library_blend), "source_armature": source_armature, "actions": todo, "out_dir": str(out_dir), "staging_dir": staging,
                                        "package_dir": str(WORKER.parent), "size": size, "source_rig": source_rig, "revision": revision, "euler_order": euler_order}), encoding="utf-8")
        command = [str(blender), "--background", "--factory-startup", "--offline-mode", "--python-exit-code", "1", "--python", str(WORKER), "--", str(job_path), str(result_path)]
        try:
            _run_worker(command, timeout, cancel)
        except subprocess.TimeoutExpired:
            return {"produced": [], "errors": [{"message": f"Délai dépassé ({timeout} s)"}]}
        if not result_path.is_file():
            return {"produced": [], "errors": [{"message": "Le processus de vignettes s'est arrêté sans résultat"}]}
        return json.loads(result_path.read_text(encoding="utf-8"))
