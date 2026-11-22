"""Pure-Python core shared by the Unreal exporter and the Blender add-on.

No dependency on `unreal` or `bpy`, so it can be unit-tested with plain Python
and imported from both applications (the Unreal scripts add this folder to
sys.path and `import ualm_core`).

Manifest layout (schema 1) -- see README.md for the full description:

    {
      "schema": 1, "engine": "...", "project": "...", "generated": "ISO",
      "skeletons":  {skel_id: {...}},
      "characters": {char_id: {...}},
      "animations": {anim_id: {...}}
    }
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import time

SCHEMA = 1
MANIFEST_NAME = "manifest.json"

# Animation status values written by the exporter.
ST_OK = "ok"
ST_FAILED = "failed"
ST_UNSUPPORTED = "unsupported"
ST_PENDING = "pending"

_BAD = re.compile(r"[^A-Za-z0-9_\-.]+")


# ---------------------------------------------------------------- utilities
def sanitize(name: str) -> str:
    """Filesystem / identifier safe version of a name (keeps readability)."""
    s = _BAD.sub("_", name).strip("_.")
    return s or "unnamed"


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def long_path(path: str) -> str:
    """Windows: paths over ~250 chars need the extended-length prefix, which
    Blender's embedded Python does not add by itself. No-op elsewhere."""
    if os.name == "nt":
        p = os.path.abspath(path)
        prefix = "\\\\?\\"
        if len(p) > 240 and not p.startswith(prefix):
            return prefix + p
        return p
    return path


def sha1_file(path: str, chunk: int = 1 << 20) -> str:
    h = hashlib.sha1()
    with open(long_path(path), "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def sha1_text(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def atomic_write_json(path: str, data) -> None:
    """Write JSON atomically so an interruption never corrupts the manifest."""
    d = os.path.dirname(os.path.abspath(path))
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tmp_", suffix=".json", dir=d)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=1, sort_keys=True, ensure_ascii=False)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def new_manifest(project: str = "", engine: str = "") -> dict:
    return {"schema": SCHEMA, "project": project, "engine": engine,
            "generated": now_iso(), "skeletons": {}, "characters": {},
            "animations": {}}


def load_manifest(path_or_dir: str) -> dict:
    path = path_or_dir
    if os.path.isdir(path):
        path = os.path.join(path, MANIFEST_NAME)
    with open(path, "r", encoding="utf-8") as f:
        m = json.load(f)
    if m.get("schema") != SCHEMA:
        raise ValueError(f"Unsupported manifest schema {m.get('schema')!r} "
                         f"(expected {SCHEMA})")
    for k in ("skeletons", "characters", "animations"):
        m.setdefault(k, {})
    return m


def save_manifest(manifest: dict, export_root: str) -> str:
    manifest["generated"] = now_iso()
    path = os.path.join(export_root, MANIFEST_NAME)
    atomic_write_json(path, manifest)
    return path


# ------------------------------------------------------------ FBX checking
def check_fbx(path: str) -> str | None:
    """Return None when the file looks like a usable FBX, else an error text."""
    path = long_path(path)
    if not os.path.isfile(path):
        return "file missing"
    size = os.path.getsize(path)
    if size < 64:
        return f"file too small ({size} bytes)"
    with open(path, "rb") as f:
        head = f.read(32)
    if head.startswith(b"Kaydara FBX Binary") or head.lstrip().startswith(
            b"; FBX"):
        return None
    return "not an FBX file (bad header)"


# ----------------------------------------------------------- skeleton logic
def topology_hash(bone_names, parent_indices) -> str:
    """Hash of bone names + parent *names* (order independent of index)."""
    pairs = []
    for i, n in enumerate(bone_names):
        p = parent_indices[i]
        pairs.append(f"{n}<{bone_names[p] if p is not None and p >= 0 else ''}")
    return sha1_text("|".join(sorted(pairs)))


def compare_rest_pose(a: dict, b: dict, pos_tol: float = 1e-3,
                      ang_tol_deg: float = 0.5, scale_tol: float = 1e-3,
                      allow_subset: bool = False):
    """Compare two rest-pose descriptions. Returns (compatible, [reasons]).

    Each description: {bone_name: {"parent": name|None,
                                   "head": (x,y,z), "tail": (x,y,z),
                                   "roll_axis": (x,y,z)}}
    where vectors are in the armature's local space (head/tail), `axis` is the
    bone's local Y axis and `roll_axis` its local Z axis in armature space.
    Bone *lengths* are deliberately ignored (importer heuristic); positions
    of the heads (which already encode scale) and axes are compared.
    Names alone never make two rigs compatible: hierarchy, bone lengths,
    positions and orientation must match.
    """
    import math
    reasons = []
    na, nb = set(a), set(b)
    if allow_subset:
        # A skeletal mesh may carry fewer bones than its Skeleton asset (or the
        # reverse). Compare only the common bones, but require a real overlap.
        common = na & nb
        if len(common) < max(2, int(0.5 * min(len(na), len(nb)))):
            reasons.append(f"too few common bones ({len(common)} of "
                           f"{len(na)}/{len(nb)})")
            return False, reasons
        a = {n: a[n] for n in common}
        b = {n: b[n] for n in common}
    elif na != nb:
        miss = sorted(na - nb)[:5]
        extra = sorted(nb - na)[:5]
        reasons.append(f"bone sets differ (missing {miss}, extra {extra})")
        return False, reasons
    for n in sorted(a):
        x, y = a[n], b[n]
        if allow_subset and (x["parent"] not in a or y["parent"] not in a):
            continue  # parent chain legitimately skips missing bones
        if x["parent"] != y["parent"]:
            reasons.append(f"parent of '{n}' differs "
                           f"({x['parent']} vs {y['parent']})")
            break
    if reasons:
        return False, reasons
    la = sum(_dist(a[n]["head"], a[n]["tail"]) for n in a) or 1.0
    cos_tol = math.cos(math.radians(ang_tol_deg))
    bad_pos = bad_axis = bad_roll = 0
    worst = None
    for n in sorted(a):
        x, y = a[n], b[n]
        if _dist(x["head"], y["head"]) > pos_tol * max(1.0, la / len(a)):
            bad_pos += 1
            worst = worst or n
        # Bone direction: use the bone's own Y axis when provided (tail length
        # is a heuristic of the importer and differs when children differ).
        da = _norm(x["axis"] if "axis" in x else _sub(x["tail"], x["head"]))
        db = _norm(y["axis"] if "axis" in y else _sub(y["tail"], y["head"]))
        if _dot(da, db) < cos_tol:
            bad_axis += 1
            worst = worst or n
        if _dot(_norm(x["roll_axis"]), _norm(y["roll_axis"])) < cos_tol:
            bad_roll += 1
            worst = worst or n
    if bad_pos:
        reasons.append(f"{bad_pos} bone positions differ (e.g. '{worst}')")
    if bad_axis:
        reasons.append(f"{bad_axis} bone directions differ")
    if bad_roll:
        reasons.append(f"{bad_roll} bone rolls differ")
    return (not reasons), reasons


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _dist(a, b):
    d = _sub(a, b)
    return (d[0] ** 2 + d[1] ** 2 + d[2] ** 2) ** 0.5


def _norm(v):
    l = (v[0] ** 2 + v[1] ** 2 + v[2] ** 2) ** 0.5 or 1.0
    return (v[0] / l, v[1] / l, v[2] / l)


# ---------------------------------------------------------------- diffing
def anim_fingerprint(entry: dict) -> str:
    """What identifies the *content* of an exported animation.

    `source_hash` (hash of the .uasset when available) changes whenever the
    asset is edited in Unreal; export settings are included so a settings
    change re-exports too.
    """
    return sha1_text("|".join(str(entry.get(k, "")) for k in (
        "source_hash", "skeleton", "length", "num_frames", "additive",
        "root_motion", "export_settings")))


def diff_manifests(old: dict | None, new: dict) -> dict:
    """Classify animation ids: new / modified / unchanged / removed."""
    old_a = (old or {}).get("animations", {})
    new_a = new.get("animations", {})
    res = {"new": [], "modified": [], "unchanged": [], "removed": []}
    for k, e in new_a.items():
        if k not in old_a:
            res["new"].append(k)
        elif anim_fingerprint(old_a[k]) != anim_fingerprint(e):
            res["modified"].append(k)
        else:
            res["unchanged"].append(k)
    res["removed"] = [k for k in old_a if k not in new_a]
    return res


def unique_action_names(entries: dict, skeleton_label) -> dict:
    """Map anim_id -> unique Blender action name.

    Base: `<skeleton_label>__<AnimName>`; collisions (same name in different
    folders) get the shortest distinguishing folder suffix, then a counter.
    """
    names, used = {}, {}
    for aid in sorted(entries):
        e = entries[aid]
        base = f"{skeleton_label(e['skeleton'])}__{e['name']}"
        if base in used:
            folder = sanitize(e.get("folder", "").strip("/").replace("/", "_"))
            cand = f"{base}__{folder}" if folder else base
            i = 2
            while cand in used:
                cand = f"{base}__{folder}_{i}"
                i += 1
            base = cand
        used[base] = aid
        names[aid] = base[:63]  # Blender ID name limit is 63 chars
        if names[aid] != base:  # truncation could collide again
            stem, i = names[aid][:58], 2
            while names[aid] in used and used[names[aid]] != aid:
                names[aid] = f"{stem}_{i:02d}"
                i += 1
            used[names[aid]] = aid
    return names
