"""Validation du lot A1 : index de la bibliothèque d'animations (extension/animation/index.py).

Exécution (Blender 5.2 en arrière-plan, nécessaire seulement pour le repli par noms d'actions) :
  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/validate_animation_index.py -- [--library DOSSIER | variable HL_ANIMATION_LIBRARY] [--out FICHIER.json] [--skip-fallback]

Critères (ANALYSE_ANIMATION.md, lot A1) :
  C1 index de 2 046 entrées < 1 s depuis le cache ; C2 recherche < 50 ms (pire requête) ; C3 0 modification de la source (SHA-256 avant/après,
  .blend de 1,6 Go compris) ; C4 catégories avec compte « Sans catégorie » explicite ; C5 cache invalidé si la source change ; C6 favoris et
  corrections persistants, fichier utilisateur corrompu mis de côté ; C7 rien de la bibliothèque dans l'extension ni dans le dépôt.
Le cache et les données utilisateur du test vont dans un dossier temporaire (jamais dans le dossier utilisateur réel).
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import shutil
import statistics
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]


def option(name, default=None):
    return ARGS[ARGS.index(name) + 1] if name in ARGS else default


import os
library_arg = option("--library", os.environ.get("HL_ANIMATION_LIBRARY"))
if not library_arg or not Path(library_arg).is_dir():
    # Pas de bibliothèque locale : la bibliothèque de l'utilisateur n'est pas dans le dépôt, le test s'ignore (jamais PASS).
    print("RESULT IGNORÉ : aucune bibliothèque (--library DOSSIER ou variable HL_ANIMATION_LIBRARY)")
    sys.exit(0)
library = Path(library_arg)
out = option("--out")
skip_fallback = "--skip-fallback" in ARGS

spec = importlib.util.spec_from_file_location("hl_animation_index", ROOT / "extension/animation/index.py")
index_module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = index_module
spec.loader.exec_module(index_module)


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(16 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


results = {"library": str(library)}
failures = []


def check(name, ok, detail=None):
    results[name] = {"ok": bool(ok), "detail": detail}
    print(("OK  " if ok else "KO  ") + name, detail if detail is not None else "")
    if not ok:
        failures.append(name)


inventory = library / index_module.INVENTORY_NAME
blends = sorted(library.glob("*.blend"))
sources = [inventory] + blends[:1]
before = {p.name: sha256(p) for p in sources}
before_stat = {p.name: (p.stat().st_size, p.stat().st_mtime_ns) for p in sources}

workdir = Path(tempfile.mkdtemp(prefix="hl_anim_index_"))
try:
    cache = workdir / "cache"

    # C1 : démarrage à froid (lecture de inventory.json) puis cache.
    start = time.perf_counter()
    index, origin = index_module.open_index(library, cache, force=True)
    cold = time.perf_counter() - start
    check("froid_inventory", origin == "inventory" and len(index) == 2046, {"origine": origin, "entrées": len(index), "secondes": round(cold, 3)})
    timings = []
    for _ in range(7):
        start = time.perf_counter()
        index, origin = index_module.open_index(library, cache)
        timings.append(time.perf_counter() - start)
    check("C1_cache_moins_de_1s", origin == "cache" and len(index) == 2046 and max(timings) < 1.0,
          {"origine": origin, "entrées": len(index), "max_s": round(max(timings), 4), "médiane_s": round(statistics.median(timings), 4),
           "cache_octets": index_module.cache_path(cache).stat().st_size})

    # C2 : recherche (pire requête sur un lot varié, filtres compris).
    random.seed(7)
    pool = sorted({t for row in index.rows for t in index_module.tokens(row[1])})
    queries = ["", "w", "wa", "walk", "walk fwd", "run start", "crouch idle loop", "xyz-inexistant", "mm"] + [f"{random.choice(pool)} {random.choice(pool)[:2]}" for _ in range(150)]
    slow = 0.0
    hits = {}
    for query in queries:
        start = time.perf_counter()
        found = index.search(query)
        elapsed = time.perf_counter() - start
        slow = max(slow, elapsed)
        hits[query] = len(found)
    filtered_start = time.perf_counter()
    filtered = index.search("walk", category=index.category(index.search("walk")[0]), root_motion=True)
    filtered_time = time.perf_counter() - filtered_start
    check("C2_recherche_moins_de_50ms", slow < 0.05 and filtered_time < 0.05,
          {"requêtes": len(queries), "pire_ms": round(slow * 1000, 2), "filtrée_ms": round(filtered_time * 1000, 2), "walk": hits["walk"], "vide": hits[""], "inexistant": hits["xyz-inexistant"]})
    # Cohérence de la recherche : « walk » ne renvoie que des entrées contenant un jeton commençant par « walk » ; préfixe plus court ⊇ plus long.
    consistent = all(any(t.startswith("walk") for t in index_module.tokens(index.rows[p][1]) | index_module.tokens(index.rows[p][2]) | index_module.tokens(index_module.skeleton_label(index.rows[p][3]))) for p in index.search("walk"))
    check("C2b_recherche_coherente", consistent and set(index.search("walk")) <= set(index.search("wal")) and hits[""] == 2046 and hits["xyz-inexistant"] == 0,
          {"préfixe_inclusion": set(index.search("walk")) <= set(index.search("wal"))})

    # C4 : catégories.
    categories = index.categories()
    check("C4_categories", sum(categories.values()) == 2046 and index_module.UNCATEGORIZED in categories,
          {"catégories": len(categories), "sans_catégorie": categories[index_module.UNCATEGORIZED], "plus_grandes": sorted(categories.items(), key=lambda kv: -kv[1])[:5],
           "root_motion": sum(1 for r in index.rows if r[7]), "additives": sum(1 for r in index.rows if r[8]), "retargetées": sum(1 for r in index.rows if r[9])})

    # C5 : invalidation du cache quand la source change (copie temporaire ; la vraie source n'est jamais touchée).
    copy_dir = workdir / "copy"
    copy_dir.mkdir()
    shutil.copy2(inventory, copy_dir / index_module.INVENTORY_NAME)
    cache2 = workdir / "cache2"
    first, origin1 = index_module.open_index(copy_dir, cache2)
    again, origin2 = index_module.open_index(copy_dir, cache2)
    data = json.loads((copy_dir / index_module.INVENTORY_NAME).read_text(encoding="utf-8"))
    first_key = next(iter(data["animations"]))
    del data["animations"][first_key]
    (copy_dir / index_module.INVENTORY_NAME).write_text(json.dumps(data), encoding="utf-8")
    changed, origin3 = index_module.open_index(copy_dir, cache2)
    check("C5_invalidation_cache", (origin1, origin2, origin3) == ("inventory", "cache", "inventory") and len(changed) == 2045,
          {"origines": [origin1, origin2, origin3], "entrées_après_changement": len(changed)})

    # C6 : favoris, corrections de catégorie, fichier corrompu.
    userdir = workdir / "user"
    user = index_module.UserData(userdir)
    target = index.rows[0][0]
    other = index.rows[1][0]
    user.toggle_favorite(target)
    user.set_category(other, "Mes corrections/Test")
    reloaded = index_module.UserData(userdir)
    reloaded.apply(index)
    ok_persist = target in reloaded.favorites and index.category(1) == "Mes corrections/Test" and index.search("", favorites=reloaded.favorites) == [0]
    reloaded.set_category(other, None)
    reloaded.apply(index)
    ok_reset = index.category(1) == index_module.group_of(index.rows[1][2])
    (userdir / "user.json").write_text("{pas du json", encoding="utf-8")
    broken = index_module.UserData(userdir)
    check("C6_favoris_et_corrections", ok_persist and ok_reset and broken.recovered and (userdir / "user.bad").is_file() and not broken.favorites,
          {"persistant": ok_persist, "rétabli": ok_reset, "corrompu_mis_de_côté": broken.recovered})

    # C3b : repli par noms d'actions du .blend (une seule ouverture en lecture, aucun bloc chargé).
    if skip_fallback or not blends:
        results["fallback_blend"] = {"ok": None, "detail": "non exécuté (--skip-fallback ou aucun .blend)"}
        print("--  fallback_blend non exécuté")
    else:
        import bpy
        isolated = workdir / "blend_only"
        isolated.mkdir()
        start = time.perf_counter()
        names = index_module.names_from_blend(blends[0])
        seconds = time.perf_counter() - start
        fallback = index_module.Index(names, "blend", index_module.fingerprint(blends[0]))
        check("fallback_blend_noms", len(fallback) == len(index) and fallback.categories()[index_module.UNCATEGORIZED] == len(fallback) and not bpy.data.actions and not bpy.data.libraries,
              {"entrées": len(fallback), "secondes": round(seconds, 1), "sans_catégorie": fallback.categories()[index_module.UNCATEGORIZED], "actions_chargées": len(bpy.data.actions), "bibliothèques_liées": len(bpy.data.libraries),
               "mêmes_noms_que_inventory": sorted(r[1] for r in fallback.rows) == sorted(r[1] for r in index.rows)})
        # Association inventaire → action du .blend : bijection exacte, mise en cache, rechargement sans relire le .blend.
        unresolved = index_module.resolve_actions(index, cache, blends[0])
        matched = [a for a in index.actions if a is not None]
        reloaded_actions, origin_actions = index_module.open_index(library, cache)
        left = [i for i, a in enumerate(index.actions) if a is None]
        by_skeleton = {}
        for i in left:
            label = index_module.skeleton_label(index.rows[i][3])
            by_skeleton[label] = by_skeleton.get(label, 0) + 1
        unused = sorted(set(r[0] for r in fallback.rows) - set(matched))
        # Aucune association fausse : chaque action associée existe dans le .blend et sert une fois ; le reste est signalé, pas deviné
        # (mesuré : actions renommées par UALM, ex. « AS_28 », ou suffixe « _02 » après troncature à 63 octets : seul `ualm_id` sur l'action chargée tranche).
        check("fallback_actions_associees", len(set(matched)) == len(matched) and set(matched) <= set(r[0] for r in fallback.rows) and len(matched) >= 0.98 * len(index)
              and origin_actions == "cache" and reloaded_actions.actions == index.actions and fallback.categories()[index_module.UNCATEGORIZED] == 2046 and len(unused) == unresolved,
              {"associées": len(matched), "non_résolues": unresolved, "par_squelette": by_skeleton, "actions_sans_entrée": len(unused), "rechargées_depuis_le_cache": reloaded_actions.actions == index.actions,
               "exemple_non_résolu": index.rows[left[0]][1] if left else None, "exemple_action_restante": unused[0] if unused else None})

    # C7 : rien de la bibliothèque dans l'extension ni dans le dépôt (ids Unreal, noms), cache hors dépôt.
    sample = random.sample([r[0] for r in index.rows if "/Game/" in r[0]], 60)
    leaked = []
    for path in list((ROOT / "extension").rglob("*.py")) + list((ROOT / "extension").rglob("*.json")) + list((ROOT / "extension").rglob("*.toml")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        leaked += [(path.name, s) for s in sample if s in text]
    cache_outside = ROOT not in cache.resolve().parents and ROOT not in Path(index_module.cache_path(cache)).resolve().parents
    check("C7_aucune_donnee_dans_le_depot", not leaked and cache_outside, {"fuites": leaked[:3], "cache_hors_dépôt": cache_outside, "ids_testés": len(sample)})
finally:
    shutil.rmtree(workdir, ignore_errors=True)

# C3 : sources inchangées.
after = {p.name: sha256(p) for p in sources}
after_stat = {p.name: (p.stat().st_size, p.stat().st_mtime_ns) for p in sources}
check("C3_source_inchangee", before == after and before_stat == after_stat, {"sha256": {k: v[:16] for k, v in before.items()}, "taille_et_date_identiques": before_stat == after_stat})

if out:
    Path(out).write_text(json.dumps(results, indent=1, ensure_ascii=False), encoding="utf-8")
print("RESULT", "FAIL " + ", ".join(failures) if failures else "PASS")
sys.exit(1 if failures else 0)
