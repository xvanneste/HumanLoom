"""Index de la bibliothèque d'animations de l'utilisateur (lot A1) : lecture seule, cache persistant, recherche par préfixes.

Principes (ANALYSE_ANIMATION.md, §6 lot A1) :
- la bibliothèque est locale, hors dépôt et hors paquet : rien d'elle (noms, index, miniatures) n'est stocké dans l'extension ;
  l'index vit dans le dossier utilisateur de Blender (`cache_dir`) ;
- source préférée : `inventory.json` (≈ 2 Mo) ; repli : noms d'actions du .blend par `bpy.data.libraries.load(link=True)`
  (liste des noms seule, rien n'est chargé ni écrit) ; le .blend de 1,6 Go n'est jamais ouvert au démarrage ;
- cache invalidé par (chemin, taille, date de modification) de la source ; format JSON (pas de pickle : fichier utilisateur non fiable) ;
- recherche : jetons (minuscules, CamelCase et séparateurs découpés), vocabulaire trié + `bisect` pour les préfixes, intersection des
  postings (recherche de type « saisie au fil de l'eau » ; ~2 000 entrées, quelques millisecondes) ;
- favoris et corrections de catégorie : JSON utilisateur, écriture atomique.

Ce module n'importe `bpy` que dans `names_from_blend` et `default_cache_dir` (tests possibles hors Blender).
"""
from bisect import bisect_left
import json
import os
from pathlib import Path
import re
import tempfile

CACHE_VERSION = 1
UNCATEGORIZED = "Sans catégorie"
INVENTORY_NAME = "inventory.json"
ACTION_SEPARATOR = "__"

# Colonnes d'une entrée (ordre du cache).
FIELDS = ("id", "name", "folder", "skeleton", "fps", "length", "frames", "root_motion", "additive", "retargeted")

_SPLIT = re.compile(r"[^0-9A-Za-z]+")
_CAMEL = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")


def tokens(text):
    """Jetons minuscules : séparateurs et frontières CamelCase (« MM_WalkFwd01 » → mm, walk, fwd, 01, mais aussi le mot entier non coupé)."""
    found = set()
    for chunk in _SPLIT.split(text):
        if not chunk:
            continue
        found.add(chunk.lower())
        for part in _CAMEL.split(chunk):
            if part:
                found.add(part.lower())
    return found


def group_of(folder):
    """Catégorie d'affichage d'après le dossier Unreal (`ualm_category`) : segments après « Animations » s'il existe, sinon les deux
    derniers segments. Aucune catégorie n'est inventée : un dossier vide donne `UNCATEGORIZED`."""
    segments = [s for s in folder.replace("\\", "/").split("/") if s]
    if not segments:
        return UNCATEGORIZED
    if "Animations" in segments:
        rest = segments[segments.index("Animations") + 1:]
        return "/".join(rest) if rest else "Animations"
    return "/".join(segments[-2:])


def skeleton_label(skeleton):
    """Nom court d'un squelette (identifiant Unreal avec « _ » à la place de « / »)."""
    for marker in ("_Meshes_", "_Skeleton"):
        if marker in skeleton:
            head, _, tail = skeleton.partition(marker)
            return (tail or head).strip("_") or skeleton
    return skeleton


def default_cache_dir():
    """Dossier utilisateur de l'extension (`bpy.utils.extension_path_user`), créé au besoin ; lève si hors extension (tests : passer `directory`)."""
    import bpy
    package = (__package__ or "").split(".")[0]
    return Path(bpy.utils.extension_path_user(package, path="animation", create=True))


def find_source(path):
    """Résout la source : dossier ou fichier. Retourne (type, chemin) avec type « inventory » ou « blend » ; None si rien de lisible.
    Le `inventory.json` voisin du .blend est préféré ; sinon le premier .blend du dossier (repli)."""
    if not path:
        return None
    p = Path(path)
    if p.is_file():
        if p.suffix.lower() == ".json":
            return ("inventory", p)
        if p.suffix.lower() == ".blend":
            sibling = p.with_name(INVENTORY_NAME)
            return ("inventory", sibling) if sibling.is_file() else ("blend", p)
        return None
    if p.is_dir():
        if (p / INVENTORY_NAME).is_file():
            return ("inventory", p / INVENTORY_NAME)
        blends = sorted(p.glob("*.blend"))
        if blends:
            return ("blend", blends[0])
    return None


def fingerprint(source):
    stat = os.stat(source)
    return {"path": str(source), "size": stat.st_size, "mtime_ns": stat.st_mtime_ns}


def entries_from_inventory(path):
    """Lit `inventory.json` (lecture seule). Une entrée = tuple dans l'ordre de `FIELDS`."""
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    rows = []
    for key, item in data["animations"].items():
        flags = set(item.get("flags") or ())
        rows.append((
            item.get("id") or key, item.get("name") or key.rsplit("/", 1)[-1], item.get("folder") or "", item.get("skeleton") or "",
            float(item.get("frame_rate") or 0.0), float(item.get("length") or 0.0), int(item.get("num_frames") or 0),
            bool(item.get("root_motion") or "root_motion" in flags),
            bool(item.get("additive") not in (None, "NONE") or "additive" in flags), "retargeted" in flags,
        ))
    return rows


def names_from_blend(path):
    """Repli : noms des actions du .blend par `libraries.load(link=True)` sans rien affecter à `data_to` (rien n'est chargé ni écrit ;
    ~17 s mesurées sur 1,6 Go). Aucune catégorie n'est disponible par ce chemin : les entrées sont « Sans catégorie »."""
    import bpy
    with bpy.data.libraries.load(str(path), link=True) as (data_from, _data_to):
        names = list(data_from.actions)
    rows = []
    for action in names:
        skeleton, separator, name = action.partition(ACTION_SEPARATOR)  # mesuré : nom d'action = « <squelette>__<nom> »
        rows.append((action, name, "", skeleton, 0.0, 0.0, 0, False, False, False) if separator else (action, action, "", "", 0.0, 0.0, 0, False, False, False))
    return rows


NAME_LIMIT = 63  # Blender tronque les noms de blocs à 63 octets (mesuré : 38 actions concernées)


def _truncated(text):
    return text.encode("utf-8")[:NAME_LIMIT].decode("utf-8", "ignore")


def match_actions(rows, blend_names):
    """Nom d'action du .blend pour chaque entrée de l'inventaire (liste parallèle à `rows`, None si introuvable).
    Mesuré : le nom d'action est « <préfixe>__<nom> », tronqué à 63 octets par Blender (suffixe « .001 » en cas de collision après troncature) ;
    le préfixe est une fin du nom de squelette de l'inventaire (UALM garde le nom court de l'asset : « SK_UEFN_Mannequin », « SK_Echo »,
    « metahuman_base_skel »…, ou le nom complet en cas de collision : RIGIPO / UE5 « SK_Mannequin »).
    Règle : pour chaque entrée, on essaie ses préfixes candidats du plus long au plus court ; une action du .blend ne sert qu'une fois."""
    pool = set(blend_names)
    prefixes = sorted({a.partition(ACTION_SEPARATOR)[0] for a in blend_names if ACTION_SEPARATOR in a}, key=lambda p: -len(p))
    collision = re.compile(r"^(.*)\.\d{3}$")
    by_stem = {}
    for action in sorted(pool):
        match = collision.match(action)
        if match:
            by_stem.setdefault(match.group(1), []).append(action)
    resolved = [None] * len(rows)
    for position in sorted(range(len(rows)), key=lambda p: -len(rows[p][3])):  # squelettes à nom long d'abord (RIGIPO avant UE5)
        row = rows[position]
        for prefix in prefixes:
            if not row[3].endswith(prefix):
                continue
            expected = _truncated(f"{prefix}{ACTION_SEPARATOR}{row[1]}")
            chosen = expected if expected in pool else None
            if chosen is None:
                stem = _truncated(f"{prefix}{ACTION_SEPARATOR}{row[1]}")[:NAME_LIMIT - 4]
                chosen = next((a for a in by_stem.get(stem, ()) if a in pool), None)
            if chosen is not None:
                pool.discard(chosen)
                resolved[position] = chosen
                break
    return resolved


class Index:
    """Entrées + jetons + vocabulaire trié. Construit en une passe ; les requêtes ne modifient rien."""

    def __init__(self, rows, source_type="inventory", fingerprint_=None):
        self.rows = [tuple(r) for r in rows]
        self.source_type = source_type
        self.fingerprint = fingerprint_ or {}
        self.overrides = {}
        self.actions = [r[0] for r in self.rows] if source_type == "blend" else None  # noms d'actions du .blend (inventory : voir `resolve_actions`)
        self._build()

    def _build(self):
        postings = {}
        for position, row in enumerate(self.rows):
            entry = dict(zip(FIELDS, row))
            words = tokens(entry["name"]) | tokens(entry["folder"]) | tokens(skeleton_label(entry["skeleton"]))
            for word in words:
                postings.setdefault(word, []).append(position)
        self.vocabulary = sorted(postings)
        self.postings = postings
        self.names_lower = [r[1].lower() for r in self.rows]
        self.positions = {r[0]: i for i, r in enumerate(self.rows)}

    def __len__(self):
        return len(self.rows)

    def entry(self, position):
        return dict(zip(FIELDS, self.rows[position]))

    def category(self, position):
        """Catégorie effective : correction manuelle si elle existe, sinon dérivée du dossier."""
        override = self.overrides.get(self.rows[position][0])
        return override if override else group_of(self.rows[position][2])

    def categories(self):
        """{catégorie: nombre d'actions}, y compris `UNCATEGORIZED` (compte explicite, 0 si aucune)."""
        counts = {UNCATEGORIZED: 0}
        for position in range(len(self.rows)):
            name = self.category(position)
            counts[name] = counts.get(name, 0) + 1
        return counts

    def skeletons(self):
        counts = {}
        for row in self.rows:
            counts[row[3]] = counts.get(row[3], 0) + 1
        return counts

    def _prefix(self, word):
        start = bisect_left(self.vocabulary, word)
        found = set()
        index = start
        while index < len(self.vocabulary) and self.vocabulary[index].startswith(word):
            found.update(self.postings[self.vocabulary[index]])
            index += 1
        return found

    def search(self, query="", category=None, skeleton=None, root_motion=None, additive=None, favorites=None, limit=None):
        """Positions triées (nom commençant par le premier jeton d'abord, puis ordre alphabétique). Chaque jeton de `query` est un préfixe ;
        tous doivent correspondre (ET). Filtres facultatifs : catégorie, squelette, drapeaux, ensemble de favoris (ids)."""
        words = [w for w in (t.lower() for t in _SPLIT.split(query)) if w]
        if words:
            result = None
            for word in words:
                matches = self._prefix(word)
                result = matches if result is None else result & matches
                if not result:
                    return []
        else:
            result = set(range(len(self.rows)))
        if category is not None:
            result = {p for p in result if self.category(p) == category}
        if skeleton is not None:
            result = {p for p in result if self.rows[p][3] == skeleton}
        if root_motion is not None:
            result = {p for p in result if self.rows[p][7] == root_motion}
        if additive is not None:
            result = {p for p in result if self.rows[p][8] == additive}
        if favorites is not None:
            result = {p for p in result if self.rows[p][0] in favorites}
        first = words[0] if words else ""
        ordered = sorted(result, key=lambda p: (not self.names_lower[p].startswith(first), self.names_lower[p], p))
        return ordered[:limit] if limit else ordered


# --- cache persistant ---------------------------------------------------------------------------------------------------------------

def _write_json_atomic(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False, separators=(",", ":"))
        os.replace(temp, path)
    except BaseException:
        if os.path.exists(temp):
            os.unlink(temp)
        raise


def cache_path(directory):
    return Path(directory) / "index.json"


def load_cache(directory, source_type, fingerprint_):
    """Index depuis le cache si version, type de source et empreinte (chemin, taille, mtime) concordent ; sinon None."""
    path = cache_path(directory)
    try:
        with open(path, encoding="utf-8") as stream:
            data = json.load(stream)
    except (OSError, ValueError):
        return None
    if data.get("version") != CACHE_VERSION or data.get("fields") != list(FIELDS) or data.get("source_type") != source_type or data.get("fingerprint") != fingerprint_:
        return None
    index = Index(data["rows"], source_type, fingerprint_)
    if source_type == "inventory" and isinstance(data.get("actions"), list) and len(data["actions"]) == len(index.rows):
        index.actions = data["actions"]
    return index


def save_cache(directory, index):
    _write_json_atomic(cache_path(directory), {"version": CACHE_VERSION, "fields": list(FIELDS), "source_type": index.source_type,
                                               "fingerprint": index.fingerprint, "rows": index.rows, "actions": index.actions})


def open_index(path, directory, force=False):
    """Point d'entrée : (Index, origine) avec origine « cache », « inventory » ou « blend ». Lève `FileNotFoundError` si rien de lisible.
    La source n'est jamais écrite."""
    found = find_source(path)
    if found is None:
        raise FileNotFoundError(f"Aucune bibliothèque lisible à {path!r} (attendu : inventory.json ou un .blend)")
    source_type, source = found
    stamp = fingerprint(source)
    if not force:
        cached = load_cache(directory, source_type, stamp)
        if cached is not None:
            return cached, "cache"
    rows = entries_from_inventory(source) if source_type == "inventory" else names_from_blend(source)
    index = Index(rows, source_type, stamp)
    save_cache(directory, index)
    return index, source_type


def resolve_actions(index, directory, blend_path):
    """Associe chaque entrée de l'inventaire à son action du .blend (une seule liste de noms, ~17 s, puis mise en cache). Retourne le nombre
    d'entrées non résolues. Aucune action n'est chargée ; le .blend n'est pas écrit."""
    if index.actions is None or any(a is None for a in index.actions):
        index.actions = match_actions(index.rows, [r[0] for r in names_from_blend(blend_path)])
        save_cache(directory, index)
    return sum(1 for a in index.actions if a is None)


# --- données utilisateur : favoris et corrections de catégorie -------------------------------------------------------------------------

class UserData:
    """Favoris (ids) et corrections de catégorie {id: catégorie}, en JSON utilisateur. Un fichier illisible est mis de côté (`.bad`), pas écrasé."""

    def __init__(self, directory):
        self.path = Path(directory) / "user.json"
        self.favorites = set()
        self.categories = {}
        self.recovered = False
        self.load()

    def load(self):
        try:
            with open(self.path, encoding="utf-8") as stream:
                data = json.load(stream)
            self.favorites = {str(v) for v in data.get("favorites", ())}
            self.categories = {str(k): str(v) for k, v in data.get("categories", {}).items() if str(v)}
        except FileNotFoundError:
            pass
        except (OSError, ValueError, AttributeError):
            try:
                os.replace(self.path, self.path.with_suffix(".bad"))
            except OSError:
                pass
            self.recovered = True

    def save(self):
        _write_json_atomic(self.path, {"version": 1, "favorites": sorted(self.favorites), "categories": self.categories})

    def toggle_favorite(self, animation_id):
        self.favorites.symmetric_difference_update({animation_id})
        self.save()
        return animation_id in self.favorites

    def set_category(self, animation_id, category):
        """Corrige la catégorie d'une action ; `None` ou vide rétablit la catégorie dérivée."""
        if category:
            self.categories[animation_id] = category
        else:
            self.categories.pop(animation_id, None)
        self.save()

    def apply(self, index):
        index.overrides = dict(self.categories)
