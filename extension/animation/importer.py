"""Import d’animations par source vers une bibliothèque à publication récupérable.

Un worker Blender écrit en préparation. Le parent vérifie le .blend relu, sérialise
les imports d’un même dossier et publie les deux fichiers avec un journal de reprise.
"""
from contextlib import contextmanager, ExitStack
import errno
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import stat
import struct
from tempfile import TemporaryDirectory
import time
from urllib.parse import unquote
import uuid

LIBRARY_BLEND = "HumanLoom_Actions.blend"
INVENTORY = "inventory.json"
JOURNAL = ".humanloom-animation-journal.json"
GENERATOR = "HumanLoom animation import"
SUFFIXES = (".fbx", ".bvh", ".glb", ".gltf", ".blend")
WORKER = Path(__file__).with_name("import_worker.py")
STAGE_PATTERN = re.compile(r"\.humanloom-animation-[0-9a-f]{32}", re.IGNORECASE)


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


def _in_stage(path):
    return any(STAGE_PATTERN.fullmatch(part) for part in path.parts)


def _is_target(source, resolved, target):
    if target is None:
        return False
    if resolved == target:
        return True
    try:
        return target.is_file() and os.path.samefile(source, target)
    except FileNotFoundError:
        return False


def collect(sources, target=None):
    """Parcourt les sources sans ouvrir les dossiers privés de préparation."""
    files = []
    for selection in sources:
        source = Path(selection).absolute()
        resolved = source.resolve()
        if _in_stage(source) or _in_stage(resolved):
            raise ValueError("Un fichier de préparation ne peut pas être une source.")
        if _is_target(source, resolved, target):
            raise ValueError("La bibliothèque cible ne peut pas être une source.")
        if source.is_dir():
            found = []
            for directory, children, names in os.walk(source):
                children[:] = [name for name in children if not STAGE_PATTERN.fullmatch(name)]
                for name in names:
                    path = Path(directory) / name
                    if path.suffix.lower() not in SUFFIXES or not path.is_file():
                        continue
                    resolved_path = path.resolve()
                    if not _in_stage(resolved_path) and not _is_target(path, resolved_path, target):
                        found.append(path)
            files.extend((path, source) for path in sorted(found))
        elif source.is_file():
            files.append((source, None))
    return files


def category_of(path, root):
    """Catégorie d'après le dossier de la source, relatif à la racine choisie (ex. « Marche/Rapide ») ; None si fichier isolé."""
    if root is None:
        return None
    relative = Path(path).parent.relative_to(root)
    return "/".join(relative.parts) or root.name


def find_export(path, cache):
    """Dossier d'export de l'outil Unreal (UnrealBlenderBridge) qui contient `path` : remonte de 12 niveaux au plus (les dossiers Unreal sont profonds) à la recherche d'un
    `manifest.json` dont les animations déclarent un fichier (« file »). Retourne (racine, {chemin relatif: entrée}) ou None."""
    for parent in list(Path(path).resolve().parents)[:12]:
        key = str(parent)
        if key not in cache:
            cache[key] = None
            manifest = parent / "manifest.json"
            if manifest.is_file():
                try:
                    animations = json.loads(manifest.read_text(encoding="utf-8")).get("animations", {})
                except (OSError, ValueError, AttributeError):
                    animations = {}
                files = {str(item["file"]).replace("\\", "/"): item for item in animations.values() if isinstance(item, dict) and item.get("file")}
                if files:
                    cache[key] = (parent, files)
        if cache[key]:
            return cache[key]
    return None


def sha1(path):
    digest = hashlib.sha1()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(16 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _regular(path):
    """Refuse aliases and special entries before any destination write."""
    try:
        st = path.lstat()
    except FileNotFoundError:
        return False
    if (
        not stat.S_ISREG(st.st_mode)
        or getattr(st, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        or st.st_nlink != 1
    ):
        raise ValueError(f"Entrée de bibliothèque non ordinaire : {path.name}")
    return True


def _signature(path):
    return sha256(path) if _regular(path) else None


def _pair(library):
    return [_signature(library / name) for name in (LIBRARY_BLEND, INVENTORY)]


@contextmanager
def _locked(library, timeout):
    lock = library / ".humanloom-animation.lock"
    _regular(lock)
    flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
    with os.fdopen(os.open(lock, flags, 0o600), "r+b", buffering=0) as handle:
        if not _regular(lock) or not os.path.samestat(lock.stat(), os.fstat(handle.fileno())):
            raise ValueError("Verrou de bibliothèque incohérent")
        if os.name == "nt":
            import msvcrt

            def acquire():
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            def acquire():
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)

        deadline = time.monotonic() + timeout
        while True:
            try:
                acquire()
                break
            except OSError as error:
                if error.errno not in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
                    raise
                if time.monotonic() >= deadline:
                    raise TimeoutError("La bibliothèque est utilisée par un autre import") from error
                time.sleep(0.05)
        yield


def _sync_file(path):
    with path.open("r+b") as stream:
        os.fsync(stream.fileno())


def _sync_directory(path):
    if os.name != "nt":
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


def _replace(candidate, target, *, before=None):
    deadline = time.monotonic() + 2
    while True:
        if before is not None:
            before()
        try:
            os.replace(candidate, target)
            return
        except PermissionError as error:
            if os.name != "nt" or error.winerror not in (5, 32, 33) or time.monotonic() >= deadline:
                raise
            time.sleep(0.05)


def _expect_pair(library, expected, message):
    if _pair(library) != expected:
        raise ValueError(message)


def _write_json(path, data):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False, allow_nan=False, indent=1)
        stream.flush()
        os.fsync(stream.fileno())


def _valid_hash(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _read_json(path, signature=None):
    def unique_keys(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Clé JSON en double : {key}")
            result[key] = value
        return result

    payload = path.read_bytes()
    if signature is not None and hashlib.sha256(payload).hexdigest() != signature:
        raise ValueError(f"{path.name} a changé pendant sa lecture")
    return json.loads(payload.decode("utf-8"), object_pairs_hook=unique_keys)


def _stage_from_journal(library, data):
    name = data.get("stage") if isinstance(data, dict) else None
    if not isinstance(name, str) or re.fullmatch(r"\.humanloom-animation-[0-9a-f]{32}", name) is None:
        raise ValueError("Journal d’import invalide")
    stage = library / name
    st = stage.lstat()
    if not stat.S_ISDIR(st.st_mode) or getattr(st, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0):
        raise ValueError("Dossier de préparation invalide")
    if data.get("version") != 1:
        raise ValueError("Version du journal d’import invalide")
    for key in ("old", "new"):
        hashes = data.get(key)
        if not isinstance(hashes, list) or len(hashes) != 2 or any(h is not None and not _valid_hash(h) for h in hashes):
            raise ValueError("Empreintes du journal d’import invalides")
    if not all(data["new"]) or data["old"] == data["new"] or data["old"][1] == data["new"][1]:
        raise ValueError("Transition du journal d’import invalide")
    return stage


def _discard(stage):
    # Les seuls chemins effacés sont des noms fixes au sein d’un stage reconnu.
    for name in (LIBRARY_BLEND, INVENTORY, "journal.tmp", "job.json", "result.json", "verified.json"):
        candidate = stage / name
        try:
            if _regular(candidate):
                candidate.unlink()
        except (OSError, ValueError):
            pass  # Un fichier occupé ou inattendu reste dans le stage.
    try:
        stage.rmdir()
    except OSError:
        pass  # Conserver tout fichier inconnu pour examen.


def _recover(library):
    journal = library / JOURNAL
    if not _regular(journal):
        return
    data = _read_json(journal)
    stage = _stage_from_journal(library, data)
    old, new = data["old"], data["new"]
    live = _pair(library)
    if live == old:
        pass  # Aucun élément de cette transaction n’a été publié.
    elif live == new:
        pass
    elif live == [new[0], old[1]] and old[0] != new[0]:
        candidate = stage / INVENTORY
        if _signature(candidate) != new[1]:
            raise ValueError("Candidat d’index absent ou altéré après interruption")
        _owned_inventory(stage, new)
        _replace(candidate, library / INVENTORY, before=lambda: _expect_pair(
            library, live, "Le couple a changé pendant la reprise",
        ))
        _sync_directory(library)
    else:
        raise ValueError("Couple bibliothèque/index incohérent après interruption")
    # Fermer le journal avant de nettoyer le stage pour permettre une seconde reprise.
    journal.unlink()
    _sync_directory(library)
    _discard(stage)


def _publish(library, stage, old, new):
    if _pair(library) != old:
        raise ValueError("La bibliothèque a changé pendant la préparation")
    journal = library / JOURNAL
    if _regular(journal):
        raise ValueError("Transaction précédente encore ouverte")
    _write_json(stage / "journal.tmp", {"version": 1, "stage": stage.name, "old": old, "new": new})
    _sync_directory(stage)
    _replace(stage / "journal.tmp", journal)
    _sync_directory(library)
    if old[0] != new[0]:
        _replace(stage / LIBRARY_BLEND, library / LIBRARY_BLEND, before=lambda: _expect_pair(
            library, old, "La bibliothèque a changé après la publication du journal",
        ))
        _sync_directory(library)
    _replace(stage / INVENTORY, library / INVENTORY, before=lambda: _expect_pair(
        library, [new[0], old[1]], "Le couple bibliothèque/index a changé avant la publication de l’index",
    ))
    _sync_directory(library)
    _recover(library)


def read_inventory(library_dir):
    library = Path(library_dir)
    return _owned_inventory(library, _pair(library))


def _owned_inventory(library, signatures):
    if signatures[1] is None:
        if signatures[0] is not None:
            raise ValueError("Bibliothèque HumanLoom_Actions.blend sans inventaire de propriété")
        return {"schema": 1, "generator": GENERATOR, "animations": {}, "imported_sources": {}}
    data = _read_json(library / INVENTORY, signatures[1])
    if not isinstance(data, dict) or data.get("generator") != GENERATOR or data.get("schema") != 1:
        raise ValueError("Inventaire étranger ou invalide : choisissez un dossier dédié")
    animations = data.get("animations")
    imported = data.setdefault("imported_sources", {})
    if not isinstance(animations, dict) or not isinstance(imported, dict):
        raise ValueError("Inventaire HumanLoom invalide")
    if signatures[0] is None and not animations and not imported and "blend_sha256" not in data:
        return data
    if signatures[0] is None or data.get("blend_sha256") != signatures[0] or data.get("transaction_schema") != 1:
        raise ValueError("Propriété ou intégrité de la paire HumanLoom non démontrée ; choisissez un dossier dédié")
    _action_records(animations)
    return data


def _action_records(animations):
    records = {}
    for identifier, item in animations.items():
        if not isinstance(item, dict) or item.get("id") != identifier or not identifier:
            raise ValueError("Identifiant d’action invalide")
        name = item.get("action")
        digest = item.get("digest")
        signature = item.get("content_sha256")
        version = item.get("digest_version")
        if version is None:
            valid_digest = isinstance(digest, str) and re.fullmatch(r"[0-9a-f]{40}", digest) is not None
        else:
            valid_digest = type(version) is int and version == 2 and (digest is None or _valid_hash(digest))
        if (
            not isinstance(name, str)
            or not name
            or name in records
            or not valid_digest
            or not _valid_hash(signature)
        ):
            raise ValueError("Nom ou empreinte d’action invalide")
        records[name] = [identifier, digest, signature, version]
    return records


def _worker(blender, job_path, result_path, timeout):
    command = [
        str(blender), "--background", "--factory-startup", "--offline-mode", "--disable-autoexec",
        "--python-exit-code", "1", "--python", str(WORKER), "--", str(job_path), str(result_path),
    ]
    try:
        done = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, check=False)
    except subprocess.TimeoutExpired as error:
        raise ValueError(f"Délai dépassé ({timeout} s)") from error
    if done.returncode != 0 or not _regular(result_path):
        raise ValueError(f"Le processus Blender a échoué (code {done.returncode})")
    data = _read_json(result_path)
    if not isinstance(data, dict) or not isinstance(data.get("errors"), list):
        raise ValueError("Résultat Blender invalide")
    if data["errors"]:
        raise ValueError(clean_message(data["errors"][0]["message"]))
    return data


# Extensions obligatoires prises en charge par l'importateur Blender 5.2.
# Le profil d'usine utilise les buffers et images du document pour ses fichiers.
GLTF_REQUIRED_EXTENSIONS = {
    "KHR_materials_pbrSpecularGlossiness", "KHR_lights_punctual", "KHR_materials_unlit",
    "KHR_texture_transform", "KHR_materials_clearcoat", "KHR_mesh_quantization",
    "EXT_meshopt_compression", "KHR_meshopt_compression", "EXT_mesh_gpu_instancing",
    "KHR_draco_mesh_compression", "KHR_materials_variants", "KHR_materials_emissive_strength",
    "KHR_materials_transmission", "KHR_materials_specular", "KHR_materials_sheen",
    "KHR_materials_ior", "KHR_animation_pointer", "KHR_materials_volume", "EXT_texture_webp",
    "KHR_materials_anisotropy", "KHR_materials_dispersion", "KHR_materials_iridescence",
}


def _gltf_stamp(item):
    return item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns, item.st_ctime_ns


def _gltf_plan(path, code=None):
    """Lit le JSON comme Blender 5.2 et énumère les dépendances locales."""
    stamp = _gltf_stamp(path.stat())
    with path.open("rb") as stream:
        opened = _gltf_stamp(os.fstat(stream.fileno()))
        magic = stream.read(4)
        if magic == b"glTF":
            header = stream.read(16)
            version, size, length, chunk = struct.unpack("<III4s", header)
            if (version, chunk) != (2, b"JSON") or size != stamp[2] or length > size - 20:
                raise ValueError("Conteneur GLB invalide")
            data = stream.read(length)
            if len(data) != length:
                raise ValueError("Document GLB tronqué")
            tail = stream.tell()
        else:
            stream.seek(0)
            data = stream.read()
            tail = None
        if code is not None:
            digest = hashlib.sha256()
            if tail is not None:
                digest.update(magic + header)
            digest.update(data)
            if tail is not None:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
            if digest.hexdigest() != code:
                raise ValueError("La source glTF a changé pendant sa lecture")
        # Sous Windows, stat(path) et fstat(fd) peuvent exposer des IDs différents.
        if opened != _gltf_stamp(os.fstat(stream.fileno())) or stamp != _gltf_stamp(path.stat()):
            raise ValueError("La source glTF a changé pendant sa lecture")
    document = json.loads(data.decode("utf-8"))
    if not isinstance(document, dict) or not isinstance(document.get("asset"), dict) or document["asset"].get("version") != "2.0":
        raise ValueError("Document glTF 2.0 attendu")

    dependencies = {}
    for field in ("buffers", "images"):
        records = document.get(field, [])
        if not isinstance(records, list) or any(not isinstance(item, dict) for item in records):
            raise ValueError("Ressources glTF invalides")
        for item in records:
            uri = item.get("uri")
            if uri is None or (field == "buffers" and uri == ""):
                continue
            if not isinstance(uri, str):
                raise ValueError("URI glTF invalide")
            if uri.startswith("data:") and ";base64," in uri:
                continue
            # Blender normalise après décodage, y compris son repli pour un
            # préfixe data: sans ;base64,. Les images packées utilisent ce même chargeur.
            relative = os.path.normpath(unquote(uri.replace("\\", "/")))
            resource = Path(os.path.join(path.parent, relative))
            if resource.drive.startswith(("\\\\", "//")):
                raise ValueError("Ressource glTF distante non qualifiée")
            dependencies.setdefault(resource, []).append(item)

    required = document.get("extensionsRequired") or []
    if not isinstance(required, list) or any(
        not isinstance(name, str) or name not in GLTF_REQUIRED_EXTENSIONS for name in required
    ):
        raise ValueError("Extension glTF obligatoire dont les dépendances ne sont pas qualifiées")
    # Blender ignore les extensions optionnelles inconnues. Les extras et les
    # champs non lus de ces extensions peuvent contenir des URI documentaires.
    return document, tail, dependencies, stamp


def _gltf_file_state(path):
    try:
        before = path.stat()
        if not stat.S_ISREG(before.st_mode):
            raise ValueError("Ressource glTF non ordinaire")
        digest = sha256(path)
        if _gltf_stamp(before) != _gltf_stamp(path.stat()):
            raise ValueError("Une ressource glTF a changé pendant sa lecture")
    except OSError as error:
        raise ValueError("Une ressource glTF est absente ou illisible") from error
    return _gltf_stamp(before), digest


def _check_gltf_files(expected):
    if any(_gltf_file_state(path) != state for path, state in expected.items()):
        raise ValueError("Une ressource glTF a changé pendant l’import")


def _snapshot_gltf(path, plan, directory, code):
    document, tail, dependencies, stamp = plan
    original = {item: _gltf_file_state(item) for item in (path, *dependencies)}
    if original[path] != (stamp, code):
        raise ValueError("La source a changé pendant l’import")
    raw_dir = directory
    if dependencies:
        raw_dir = directory / "original"
        raw_dir.mkdir()
    raw_source = raw_dir / path.name
    shutil.copyfile(path, raw_source)
    raw_state = _gltf_file_state(raw_source)
    if raw_state[1] != code:
        raise ValueError("La source glTF a changé pendant sa copie")
    snapshot = {raw_source: raw_state}
    if not dependencies:
        guards = original | snapshot
        _check_gltf_files(guards)
        return raw_source, guards

    resource_dir = directory / "resources"
    resource_dir.mkdir()
    for number, (resource, items) in enumerate(dependencies.items()):
        suffix = resource.suffix
        suffix = suffix if re.fullmatch(r"\.[a-zA-Z0-9]{1,12}", suffix) else ""
        target = resource_dir / f"{number}{suffix}"
        shutil.copyfile(resource, target)
        state = _gltf_file_state(target)
        if state[1] != original[resource][1]:
            raise ValueError("Une ressource glTF a changé pendant sa copie")
        snapshot[target] = state
        for item in items:
            item["uri"] = target.relative_to(directory).as_posix()
    source = directory / path.name
    payload = json.dumps(document, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
    with source.open("wb") as output:
        if tail is None:
            output.write(payload)
        else:
            payload += b" " * (-len(payload) % 4)
            total = 20 + len(payload) + original[path][0][2] - tail
            output.write(struct.pack("<4sIII4s", b"glTF", 2, total, len(payload), b"JSON"))
            output.write(payload)
            with raw_source.open("rb") as stream:
                stream.seek(tail)
                shutil.copyfileobj(stream, output)
    snapshot[source] = _gltf_file_state(source)
    guards = original | snapshot
    _check_gltf_files(guards)
    return source, guards


def _source_request(path, root, fps, limit, name_filter, category, declared):
    extension = path.suffix.lower()
    options = {
        "format": extension,
        "fps": float(fps) if extension in {".bvh", ".glb", ".gltf"} else None,
        "category": category_of(path, root) or category,
        "limit": int(limit) if extension == ".blend" and limit else None,
        "name_filter": name_filter or None if extension == ".blend" else None,
        "declared": declared,
    }
    # L’ancien reçu par fichier ne prouve pas que toutes les actions ont été
    # traitées, ni qu’un doublon a été retenu à bon droit.
    payload = json.dumps([4, options], sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest(), options


def _import_file(path, library, inventory, old, blender, code, timeout, request_code, options, gltf_plan):
    stage = library / (".humanloom-animation-" + uuid.uuid4().hex)
    stage.mkdir()
    cleanup = ExitStack()
    try:
        worker_source, gltf_guards = path, {}
        if gltf_plan is not None:
            directory = cleanup.enter_context(TemporaryDirectory(prefix="gltf-", dir=stage, ignore_cleanup_errors=True))
            worker_source, gltf_guards = _snapshot_gltf(path, gltf_plan, Path(directory), code)
        candidate = stage / LIBRARY_BLEND
        # Les anciennes entrées BVH ont perdu leur période non arrondie.
        legacy_eligible = {
            item["action"] for item in inventory["animations"].values()
            if item.get("digest_version") is None and item.get("source_format") in {"blend", "fbx", "glb", "gltf"}
        }
        job = {
            "source": str(worker_source), "previous_blend": str(library / LIBRARY_BLEND) if old[0] else None,
            "candidate_blend": str(candidate), "legacy_eligible": sorted(legacy_eligible), **options,
        }
        job_path = stage / "job.json"
        _write_json(job_path, job)
        result = _worker(blender, job_path, stage / "result.json", timeout)
        _check_gltf_files(gltf_guards)
        entries, duplicates = result.get("entries"), result.get("skipped_duplicates")
        if not isinstance(entries, list) or not isinstance(duplicates, list) or result.get("added") != len(entries):
            raise ValueError("Comptage des actions importées invalide")
        if not entries and not duplicates:
            return inventory, old, entries, duplicates
        if code != sha256(path):
            raise ValueError("La source a changé pendant l’import")

        animations = inventory["animations"].copy()
        for item in entries:
            identifier = item["id"]
            if identifier in animations:
                raise ValueError(f"L’identifiant d’action existe déjà : {identifier}")
            animations[identifier] = item
        expected = _action_records(animations)
        duplicate_ids = []
        for item in duplicates:
            identifier = item["same_as"]
            prior = animations.get(identifier)
            if not prior or not _valid_hash(item.get("digest")):
                raise ValueError("Doublon sans action correspondante")
            if prior["action"] not in legacy_eligible and (prior.get("digest_version") != 2 or prior["digest"] != item["digest"]):
                raise ValueError("Empreinte du doublon incohérente")
            duplicate_ids.append(identifier)
        if entries:
            if not _regular(candidate):
                raise ValueError("La conversion ne contient aucun .blend sauvegardé")
            job_path.unlink()
            _write_json(job_path, {"verify_blend": str(candidate)})
            verified = _worker(blender, job_path, stage / "verified.json", timeout)
            if verified.get("actions") != expected:
                raise ValueError("Les actions relues ne correspondent pas à l’inventaire préparé")
            _sync_file(candidate)
            blend_sha = sha256(candidate)
        elif old[0] is None or _regular(candidate):
            raise ValueError("Résultat de déduplication incohérent")
        else:
            blend_sha = old[0]

        updated = dict(inventory, animations=animations, blend_sha256=blend_sha, transaction_schema=1)
        previous_source = inventory["imported_sources"].get(code, {})
        by_name = {item["action"]: identifier for identifier, item in animations.items()}
        previous_ids = [value if value in animations else by_name.get(value) for value in previous_source.get("actions", ())]
        request_ids = list(dict.fromkeys([item["id"] for item in entries] + duplicate_ids))
        updated["imported_sources"] = inventory["imported_sources"] | {
            code: {
                "file": previous_source.get("file", path.name),
                "actions": list(dict.fromkeys([aid for aid in previous_ids if aid is not None] + request_ids)),
                "requests": previous_source.get("requests", {}) | {request_code: request_ids},
            },
        }
        _check_gltf_files(gltf_guards)
        cleanup.close()
        if updated == inventory:
            return inventory, old, entries, duplicates
        _write_json(stage / INVENTORY, updated)
        new = [blend_sha, sha256(stage / INVENTORY)]
        _publish(library, stage, old, new)
        return updated, new, entries, duplicates
    finally:
        cleanup.close()
        if not (library / JOURNAL).exists():
            _discard(stage)


def import_sources(sources, library_dir, blender, fps=30.0, timeout=900, limit=None, name_filter=None, category=None):
    """Importe chaque source dans une transaction indépendante et retourne son statut."""
    library = Path(library_dir).resolve()
    files = collect(sources, target=library / LIBRARY_BLEND)
    library.mkdir(parents=True, exist_ok=True)
    before = {p: sha256(p) for p, _ in files}
    report = {"fichiers": [], "ajoutées": 0, "doublons": 0, "inchangés": 0, "échecs": 0, "ignorés": 0}
    exports = {}
    with _locked(library, timeout):
        _recover(library)
        signatures = _pair(library)
        inventory = _owned_inventory(library, signatures)
        for path, root in files:
            entry = {"source": path.name, "statut": None}
            report["fichiers"].append(entry)
            code = before[path]
            declared = None
            if path.suffix.lower() == ".fbx":
                found = find_export(path, exports)
                if found:
                    declared = found[1].get(path.resolve().relative_to(found[0]).as_posix())
                    if declared is None:
                        entry.update(statut="ignoré", message="Absent des animations du manifest.json (maillage de personnage ou autre fichier)")
                        report["ignorés"] += 1
                        continue
                    entry["metadonnees"] = "déclarées (manifest.json)"
                    if declared.get("fbx_sha1") and sha1(path) != declared["fbx_sha1"]:
                        entry["avertissement"] = "Empreinte SHA-1 différente de celle du manifest.json (fichier modifié depuis l'export ?)"
                else:
                    entry["metadonnees"] = "heuristique (aucun manifest.json)"
            try:
                request_code, options = _source_request(path, root, fps, limit, name_filter, category, declared)
                requests = inventory["imported_sources"].get(code, {}).get("requests", {})
                gltf_plan = _gltf_plan(path, code) if options["format"] in {".glb", ".gltf"} else None
                if request_code in requests and (gltf_plan is None or not gltf_plan[2]):
                    if code != sha256(path):
                        raise ValueError("La source a changé pendant l’import")
                    entry.update(statut="inchangé", actions=requests[request_code])
                    report["inchangés"] += 1
                    continue
                inventory, signatures, entries, duplicates = _import_file(
                    path, library, inventory, signatures, blender, code, timeout, request_code, options, gltf_plan,
                )
            except (OSError, ValueError, TypeError, KeyError, AttributeError, RecursionError, struct.error) as error:
                if (library / JOURNAL).exists():
                    raise RuntimeError("Publication interrompue, relancez l’import pour déclencher la reprise") from error
                entry.update(statut="échec", message=clean_message(str(error)))
                report["échecs"] += 1
                continue
            entry.update(statut="importé" if entries else "doublon", ajoutées=len(entries), doublons=duplicates, erreurs=[])
            report["ajoutées"] += len(entries)
            report["doublons"] += len(duplicates)
    report["sources_modifiées"] = sorted(p.name for p, code in before.items() if not p.is_file() or sha256(p) != code)
    return report
