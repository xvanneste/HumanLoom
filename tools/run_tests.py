"""Lanceur des tests HumanLoom (I-04, I-44, I-47). Python normal (pas Blender), Blender 5.2 uniquement.

Usage :
  python tools/run_tests.py --out <dossier_sortie> [--seed-validation <validation_source>] [--filter texte] [--compare ref.json]

Garanties :
- les tests tournent dans un CLONE (`<out>/clone`, copie de `extension/` et `tools/`), jamais dans le dépôt ni dans son
  `validation/` : plusieurs scripts écrivent en dur dans `validation/` ;
- `--out` ne peut pas être dans le `validation/` du dépôt ; le dossier source `--seed-validation` n'est que LU (copie des
  fichiers listés dans SEED, qui servent d'entrées à certains tests) ;
- un Blender 5.2 séparé par test (`--background --factory-startup`), délai maximal 900 s ;
- fixtures d'anciennes versions (`adult-original.blend`, `legacy-03.blend`) générées par `tools/make_legacy_fixtures.py`
  (SYNTHÉTIQUES, voir son en-tête) et copiées dans le dossier de sortie des tests qui les attendent ;
- sortie `<out>/resume.json` au même format que `docs/audit/baseline-tests.json`, puis comparaison avec la référence
  (`--compare`, par défaut ce fichier) : code de sortie 1 si un test OK de la référence n'est plus OK."""
import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BLENDER = r"C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
TIMEOUT = 900
OLD_ASSET = "validation/proportions-14/extension-13/data/realistic.blend"
# Entrées de tests lues dans validation/ (chemins relatifs, fichiers ou dossiers ; * accepté).
SEED = (
    "proportions-14/extension-13", "proportions-14/revue-travail-07", "proportions-14/candidat-adulte-07.*",
    "proportions-14/candidat-adulte-15.blend", "corpulences-12/Session-modelisation-12.blend",
    "corpulences-12/revue-livree-09", "morphologie-globale-13/Session-modelisation-13.blend",
    "morphologie-globale-13/revue-livraison-04", "muscles-regionaux-18/Session-modelisation-14.blend",
    "muscles-regionaux-18/candidat-04.blend", "muscles-regionaux-18/apercus/*-inspection.blend", "atlas-15", "groom-25",
    "nature-cheveux-21", "cheveux-20", "physique-cheveux-22", "source-growth", "planches-modelisation-23/Revue-editable-*.blend",
)
# Tests qui attendent une fixture dans leur dossier de sortie : nom du test -> fichiers à y copier.
FIXTURES = {"validate_controls": ("adult-original.blend",), "validate_presets": ("legacy-03.blend",)}
# Scripts exclus : travail en cours de l'utilisateur.
SKIP = {"validate_groom_collision29": "travail en cours de l'utilisateur (non suivi)"}
# Tests périmés par décision de l'utilisateur (I-34) : listés OBSOLÈTE, jamais comptés comme échec ni comme régression.
OBSOLETE = {
    "validate_controls": "D-21 : acceptation de la migration d'anciens fichiers, abandonnée (aucune migration au schéma 10) ; conservé",
    "validate_presets": "D-21 : acceptation de la migration d'anciens fichiers, abandonnée (aucune migration au schéma 10) ; conservé",
    "validate_surface_fix": "I-34 : dépend d'un ancien asset non reproductible (82 croisements) ; remplacé par validate_geometry_quality",
}
SHIM = '''import sys, types, runpy
from pathlib import Path
ROOT = Path(sys.argv[sys.argv.index("--shim-root") + 1]); TEST = sys.argv[sys.argv.index("--shim-test") + 1]
rest = sys.argv[len(sys.argv) - sys.argv[::-1].index("--"):]
sys.path.insert(0, str(ROOT))
import extension
for n in ("bl_ext", "bl_ext.user_default"):
    sys.modules.setdefault(n, types.ModuleType(n))
sys.modules["bl_ext.user_default.human_modeling"] = extension
sys.modules["bl_ext.user_default"].human_modeling = extension
for m in list(sys.modules):
    if m.startswith("extension."):
        sys.modules["bl_ext.user_default.human_modeling." + m[10:]] = sys.modules[m]
extension.register()
sys.argv = [TEST, "--"] + rest
runpy.run_path(TEST, run_name="__main__")
'''


def registry(clone, out):
    """Arguments propres à chaque script (I-44) ; `o(nom)` = chemin de sortie du test."""
    def o(name):
        return str(out / name)
    asset = str(clone / "extension/data/realistic.blend")
    old = str(clone / OLD_ASSET)
    return {
        "validate_age_dimensions": [asset, o("age_dimensions")], "validate_age_eye_fit": [asset, o("age_eye_fit")],
        "validate_age_geometry": [asset, o("age_geometry.json")], "validate_age_transitions": [asset, o("age_transitions")],
        "validate_anatomy": [o("anatomy")], "validate_atlas14_measurements": ["07"], "validate_atlas14_reopen": ["07"],
        "validate_body_mass_neutral": [old, o("body_mass_neutral")], "validate_controls": [o("controls")],
        "validate_extended_body": [o("extended_body")], "validate_geometry_quality": [o("geometry_quality")],
        "validate_global_physique": [o("global_physique")],
        "validate_human_nodes": [str(clone / "extension/data/human_nodes.blend"), o("human_nodes/resultat.json")], "validate_human_native": [o("human_native/resultat.json")], "validate_human_ported": [o("human_ported/resultat.json")], "validate_landmark_sets": [o("landmark_sets")],
        "validate_mass_render_surface": [o("mass_render_surface")], "validate_mass_transitions": [o("mass_transitions")],
        "validate_measurements": [o("measurements")], "validate_model": [o("model")],
        "validate_modeling_batch": [asset, o("modeling_batch.json"), "0.0", "2.0"],
        "validate_modeling_workflow": [old, o("modeling_workflow")], "validate_muscle_workflow": [old, o("muscle_workflow")],
        "validate_musculature": [asset, o("musculature")], "validate_presets": [o("presets")],
        "validate_quickwins_step1": [o("quickwins.json")],
        "validate_regional_muscles18": [o("regional_muscles18.json"), "regional"],
        "validate_relief_render_surface": [o("relief_render_surface")], "validate_skin_relief": [old, o("skin_relief")],
        "validate_surface_fix": [old, o("surface_fix")],
    }


def copy_isolated(out):
    clone = out / "clone"
    if clone.exists():
        if not (clone / ".run_tests_clone").exists():
            sys.exit(f"Refus : {clone} existe et n'est pas un clone créé par ce lanceur.")
        shutil.rmtree(clone)
    clone.mkdir(parents=True)
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", "*.blend1")
    for name in ("extension", "tools"):
        shutil.copytree(ROOT / name, clone / name, ignore=ignore)
    (clone / ".run_tests_clone").write_text("clone isolé créé par tools/run_tests.py\n", encoding="utf-8")
    return clone


def seed(clone, source):
    """Copie en lecture seule les entrées de tests ; renvoie (copiés, absents)."""
    copied, missing = [], []
    for pattern in SEED:
        found = sorted(source.glob(pattern))
        if not found:
            missing.append(pattern)
        for path in found:
            target = clone / "validation" / path.relative_to(source)
            target.parent.mkdir(parents=True, exist_ok=True)
            if path.is_dir():
                shutil.copytree(path, target, dirs_exist_ok=True)
            else:
                shutil.copy2(path, target)
            copied.append(str(path.relative_to(source)).replace("\\", "/"))
    return copied, missing


def blender_cmd(*extra):
    return [BLENDER, "--background", "--factory-startup", "--offline-mode", "--threads", "4", "--python-exit-code", "1", *extra]


def run(cmd, cwd):
    started = time.time()
    try:
        done = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT, cwd=str(cwd), encoding="utf-8", errors="replace")
        code, text = done.returncode, (done.stdout or "") + (done.stderr or "")
    except subprocess.TimeoutExpired as error:
        output = error.stdout.decode("utf-8", "replace") if isinstance(error.stdout, bytes) else (error.stdout or "")
        code, text = -9, f"TIMEOUT {TIMEOUT} s\n" + output
    return code, text, round(time.time() - started, 1)


def compare(summary, reference_path):
    reference = {row["test"]: row for row in json.loads(Path(reference_path).read_text(encoding="utf-8"))}
    now = {row["test"]: row for row in summary}
    ok = lambda row: row is not None and row["statut"] == "OK"
    report = {
        "regressions": sorted(t for t in now if ok(reference.get(t)) and not ok(now[t]) and now[t]["statut"] != "OBSOLÈTE"),
        "corriges": sorted(t for t in now if reference.get(t) and not ok(reference[t]) and ok(now[t])),
        "nouveaux_tests": sorted(t for t in now if t not in reference),
        "absents_de_cette_execution": sorted(t for t in reference if t not in now),
        "ok_avant": sum(ok(r) for r in reference.values()), "ok_maintenant": sum(ok(r) for r in now.values()),
    }
    return report


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser =argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--out", required=True, help="dossier de sortie (hors du validation/ du dépôt)")
    parser.add_argument("--seed-validation", help="dossier validation/ SOURCE, lu seulement")
    parser.add_argument("--filter", default="", help="sous-chaîne du nom de test")
    parser.add_argument("--compare", default=str(ROOT / "docs/audit/baseline-tests.json"))
    options = parser.parse_args()
    out = Path(options.out).resolve()
    if (ROOT / "validation").resolve() in (out, *out.parents):
        sys.exit("Refus : la sortie ne doit pas être dans le validation/ du dépôt.")
    out.mkdir(parents=True, exist_ok=True)
    clone = copy_isolated(out)
    info = {"clone": str(clone)}
    if options.seed_validation:
        info["seed_copies"], info["seed_absents"] = seed(clone, Path(options.seed_validation).resolve())
    (out / "shim.py").write_text(SHIM, encoding="utf-8")
    code, text, _ = run(blender_cmd("--python", str(clone / "tools/make_legacy_fixtures.py"), "--", str(out / "fixtures")), clone)
    (out / "fixtures.log").write_text(text, encoding="utf-8")
    info["fixtures"] = "ok" if code == 0 else f"ÉCHEC (code {code}, voir fixtures.log)"
    scripts = sorted(p for p in (clone / "tools").glob("*.py") if re.match(r"(validate|check)_", p.name))
    args_by_test = registry(clone, out)
    summary = []
    for script in scripts:
        name = script.stem
        if options.filter and options.filter not in name:
            continue
        if name in OBSOLETE:
            summary.append({"test": name, "statut": "OBSOLÈTE", "raison": OBSOLETE[name]})
            print(name, "OBSOLÈTE", flush=True)
            continue
        if name in SKIP:
            summary.append({"test": name, "statut": "IGNORÉ", "raison": SKIP[name]})
            continue
        args = args_by_test.get(name, [])
        outputs = [Path(a) for a in args if Path(a).parent == out]
        text_source = script.read_text(encoding="utf-8", errors="replace")
        needs_alias = ("bl_ext.user_default" in text_source or "human_modeling" in text_source) and "register()" not in text_source
        if needs_alias:
            cmd = blender_cmd("--python", str(out / "shim.py"), "--", "--shim-root", str(clone), "--shim-test", str(script), "--", *args)
        else:
            cmd = blender_cmd("--python", str(script), "--", *args)
        # Some scripts write their output argument as a file, others as a folder (I-44): try the likely form, then the other.
        modes = ("dir", "file") if name in FIXTURES else ("file", "dir")
        for attempt, mode in enumerate(modes):
            for path in outputs:
                if path.is_dir() and not any(path.iterdir()):
                    path.rmdir()
                if mode == "dir":
                    path.mkdir(parents=True, exist_ok=True)
                    for fixture in FIXTURES.get(name, ()):
                        if (out / "fixtures" / fixture).exists():
                            shutil.copy2(out / "fixtures" / fixture, path / fixture)
            code, text, seconds = run(cmd, clone)
            if code == 0 or attempt == 1 or not re.search(r"(PermissionError|IsADirectoryError|NotADirectoryError|FileNotFoundError|for writing: No such file)", text):
                break
        (out / f"{name}.log").write_text(text, encoding="utf-8")
        error = next((l for l in reversed(text.splitlines()) if re.search(r"(Error|Exception|AssertionError|FAILED)", l)), "")
        status = "OK" if code == 0 else ("TIMEOUT" if code == -9 else "ÉCHEC")
        summary.append({"test": name, "statut": status, "code": code,
                        "secondes": seconds, "args": [Path(a).name if "/" in a or "\\" in a else a for a in args],
                        "derniere_erreur": error[:220]})
        (out / "resume.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False), encoding="utf-8")
        print(name, summary[-1]["statut"], seconds, flush=True)
    (out / "resume.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False), encoding="utf-8")
    report = compare(summary, options.compare) if Path(options.compare).exists() else {}
    (out / "comparaison.json").write_text(json.dumps({"info": info, "comparaison": report}, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"info": info, "comparaison": report}, indent=1, ensure_ascii=False))
    sys.exit(1 if report.get("regressions") else 0)


if __name__ == "__main__":
    main()
