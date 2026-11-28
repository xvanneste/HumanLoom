"""Réutilisation sûre des images de rendu (audit SCI-011) : une image n'est réutilisée que si son manifeste (empreinte SHA-256 du code, des assets, des réglages, de la caméra et de la version de Blender) correspond à celui du rendu demandé ; sinon elle est régénérée (ou refusée à l'assemblage).

Sans dépendance à Blender : utilisable aussi par les assembleurs (Python + Pillow)."""
import hashlib
import json
from pathlib import Path


def _digest(paths):
    sha = hashlib.sha256()
    for path in sorted(Path(p) for p in paths):
        sha.update(path.name.encode("utf-8"))
        sha.update(path.read_bytes())
    return sha.hexdigest()


def source_fingerprint(root, patterns=("extension/*.py", "extension/data/*.blend", "extension/data/*.json"), extra_files=()):
    root = Path(root)
    files = [p for pattern in patterns for p in root.glob(pattern) if p.is_file()] + [Path(f) for f in extra_files]
    return _digest(files)


def fingerprint(source, settings, camera, blender):
    """Empreinte d'un rendu : source (voir source_fingerprint), réglages, caméra et version de Blender (valeurs sérialisables)."""
    payload = json.dumps({"source": source, "settings": settings, "camera": camera, "blender": blender}, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def manifest_path(image):
    image = Path(image)
    return image.with_suffix(image.suffix + ".json")


def is_current(image, expected, force=False):
    """Vrai si l'image existe, si son manifeste porte l'empreinte attendue et si le PNG est celui que le manifeste a enregistré."""
    image = Path(image)
    manifest = manifest_path(image)
    if force or not image.is_file() or not manifest.is_file():
        return False
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return data.get("fingerprint") == expected and data.get("png_sha256") == hashlib.sha256(image.read_bytes()).hexdigest()


def record(image, expected):
    image = Path(image)
    manifest_path(image).write_text(json.dumps({"fingerprint": expected, "png_sha256": hashlib.sha256(image.read_bytes()).hexdigest()}, indent=1), encoding="utf-8")


def require_current(image, expected):
    """Pour les assembleurs : refus explicite d'une image sans manifeste ou d'une génération différente."""
    if not is_current(image, expected):
        raise ValueError(f"Image périmée ou sans manifeste : {image} (relancer le rendu, éventuellement avec --force)")
