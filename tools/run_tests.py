"""Lanceur des tests HumanLoom (I-04, I-44, I-47). Python normal (pas Blender), Blender 5.2 uniquement.

Le verdict strict (`verdict.json`) exige une référence valide et au moins un test requis
sélectionné. Chaque test requis doit réussir. Code 1 si cette condition échoue, code 2
si une précondition ou l'infrastructure fait défaut. Le filtre s'applique également
aux tests attendus. Les tests déclarés obsolètes restent visibles comme historiques.

Les tests et leurs sorties de travail sont isolés dans une copie de `extension/` et
`tools/`. `--seed-validation` copie certaines entrées en lecture seule. Les tests
utilisent Blender en arrière-plan, sauf `validate_install`, lancé en Python ordinaire
avec un dossier de travail et des ressources utilisateur Blender isolés.

`resume.json` conserve le format de la référence. `comparaison.json` décrit les écarts
historiques. `--compare-only RESUME.json` compare des résultats déjà produits, avec un
code de sortie historique (1 si régression), sans exécuter les tests ni établir un
verdict strict."""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BLENDER = r"C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
TIMEOUT = 900
INSTALL_TIMEOUT = 1830  # validate_install peut démarrer trois Blender de 600 s chacun.
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
# Un test requis ignoré reste bloquant pour le verdict strict.
SKIP = {"validate_groom_collision29": "travail en cours de l'utilisateur"}
# Tests périmés par décision de l'utilisateur (I-34) : listés OBSOLÈTE, jamais comptés comme échec ni comme régression.
OBSOLETE = {
    "validate_controls": "D-21 : acceptation de la migration d'anciens fichiers, abandonnée (aucune migration au schéma 10) ; conservé",
    "validate_presets": "D-21 : acceptation de la migration d'anciens fichiers, abandonnée (aucune migration au schéma 10) ; conservé",
    "validate_surface_fix": "I-34 : dépend d'un ancien asset non reproductible (82 croisements) ; remplacé par validate_eyelids_native (corps natif) et validate_geometry_quality",
}
# Tests Blender dont les arguments par défaut suffisent. Les autres sont dans registry().
DEFAULT_BLENDER_TESTS = set("""
check_delivery18 check_groom_continuity25 check_nature21 check_review_scenes23
validate_accessories validate_animation_derived_library validate_animation_derived
validate_animation_import validate_animation_index validate_animation_mapping_library
validate_animation_mapping_ui validate_animation_mapping validate_animation_retarget_library
validate_animation_retarget_ui validate_animation_retarget validate_animation_rigs_a5
validate_animation_ui validate_cloth_sim validate_correctives validate_crowd
validate_delivery12_reopen validate_delivery13_reopen validate_dense_hair20
validate_dental validate_eyelids_native validate_face_pilot validate_face_poses
validate_garments_import validate_garments validate_gaze validate_groom_collision29
validate_groom_quality26 validate_groom_reopen25 validate_groom_workflow25 validate_groom25
validate_groom28 validate_hair20 validate_human_rig validate_nature21
validate_physics_profile22 validate_physics_rest21 validate_regional_compat18
validate_regional_upgrade18 validate_surface_atlas15_ages validate_surface_atlas15
""".split())
DIRECTORY_OUTPUTS = {
    "validate_anatomy", "validate_body_mass_neutral", "validate_geometry_quality",
    "validate_landmark_sets", "validate_measurements", "validate_model",
    "validate_modeling_workflow", "validate_muscle_workflow", "validate_skin_relief",
}
INSTALL_TEST = "validate_install"
SCRIPT_NAME = re.compile(r"(?:validate|check)_\w+")
SKIP_RESULT = re.compile(r"^\s*RESULT\s+(?:IGNOR[ÉE]|SKIP(?:PED)?)\b", re.MULTILINE)
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
    asset = str(clone / "tools/data/realistic.blend")
    old = str(clone / OLD_ASSET)
    return {
        "validate_age_dimensions": [asset, o("age_dimensions")], "validate_age_eye_fit": [asset, o("age_eye_fit")],
        "validate_age_geometry": [asset, o("age_geometry.json")], "validate_age_transitions": [asset, o("age_transitions")],
        "validate_anatomy": [o("anatomy")], "validate_atlas14_measurements": ["07"], "validate_atlas14_reopen": ["07"],
        "validate_body_mass_neutral": [old, o("body_mass_neutral")], "validate_controls": [o("controls")],
        "validate_extended_body": [o("extended_body")], "validate_geometry_quality": [o("geometry_quality")],
        "validate_global_physique": [o("global_physique")],
        "validate_human_nodes": [str(clone / "extension/data/human_nodes.blend"), o("human_nodes/resultat.json")], "validate_human_amplitudes": [o("human_amplitudes/resultat.json")], "validate_human_native": [o("human_native/resultat.json")], "validate_human_ported": [o("human_ported/resultat.json")], "validate_landmark_sets": [o("landmark_sets")],
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
        clone = Path(tempfile.mkdtemp(prefix="clone-", dir=out))
    else:
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


def run(cmd, cwd, *, timeout=TIMEOUT, env=None):
    started = time.monotonic()
    try:
        done = subprocess.run(cmd, capture_output=True, timeout=timeout, cwd=cwd, env=env)
        code = done.returncode
        text = (done.stdout + b"\n" + done.stderr).decode("utf-8", "replace")
        status = "OK" if code == 0 else "ÉCHEC"
    except subprocess.TimeoutExpired as error:
        output = (error.stdout or b"") + b"\n" + (error.stderr or b"")
        code, status, text = None, "TIMEOUT", f"TIMEOUT {timeout} s\n" + output.decode("utf-8", "replace")
    except OSError as error:
        code, status, text = None, "INFRASTRUCTURE", str(error)
    return code, status, text, round(time.monotonic() - started, 1)


def load_results(path):
    rows = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(rows, list) or not rows:
        raise ValueError("liste de résultats vide ou invalide")
    names = set()
    for row in rows:
        if (not isinstance(row, dict) or not isinstance(row.get("test"), str)
                or not SCRIPT_NAME.fullmatch(row["test"]) or not isinstance(row.get("statut"), str)
                or not row["statut"].strip() or row["test"] in names):
            raise ValueError("résultat invalide ou nom de test répété")
        names.add(row["test"])
    return rows


def compare(summary, reference_rows):
    reference = {row["test"]: row for row in reference_rows}
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


def write_report(path, value):
    path.write_text(json.dumps(value, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def isolated_env(clone):
    env = {key: value for key, value in os.environ.items()
           if not key.upper().startswith("BLENDER_USER_")
           and key.upper() not in {"PYTHONOPTIMIZE", "HL_RIG_WEIGHTS", "HL_RIG_ONLY_POSES"}}
    scratch = clone / ".temp"
    scratch.mkdir()
    env.update(BLENDER=BLENDER, BLENDER_USER_RESOURCES=str(clone / ".blender-user"),
               TMP=str(scratch), TEMP=str(scratch), TMPDIR=str(scratch))
    return env


def execute_test(name, script, args, clone, out, shim, env, timeout):
    runtime = "Python" if name == INSTALL_TEST else "Blender"
    if name == INSTALL_TEST:
        # validate_install nettoie argv[1], qui doit donc être un emplacement neuf.
        args = [str(clone / ".installation-isolee")]
        cmd = [sys.executable, "-E", "-B", str(script), *args]
    else:
        outputs = clone / ".sorties"
        for arg in args:
            path = Path(arg)
            if path.is_relative_to(outputs):
                target = path if name in DIRECTORY_OUTPUTS else path.parent
                target.mkdir(parents=True, exist_ok=True)
            elif path.is_relative_to(clone) and not path.is_file():
                return {"test": name, "statut": "BLOQUÉ", "runtime": runtime,
                        "raison": f"entrée absente : {path.relative_to(clone)}"}
        source = script.read_text(encoding="utf-8", errors="replace")
        needs_alias = ("bl_ext.user_default" in source or "human_modeling" in source) and "register()" not in source
        if needs_alias:
            cmd = blender_cmd("--python", str(shim), "--", "--shim-root", str(clone),
                              "--shim-test", str(script), "--", *args)
        else:
            cmd = blender_cmd("--python", str(script), "--", *args)

    timeout = timeout or (INSTALL_TIMEOUT if name == INSTALL_TEST else TIMEOUT)
    code, status, output, seconds = run(cmd, clone, timeout=timeout, env=env)
    message = next((line for line in reversed(output.splitlines())
                    if re.search(r"Error|Exception|FAILED", line)), "")
    if status == "OK":
        skip = SKIP_RESULT.search(output)
        if skip:
            status, message = "IGNORÉ", output[skip.start():].strip().splitlines()[0]
        elif name == INSTALL_TEST and not re.search(r"^VALIDATE_INSTALL_PASS\b", output, re.MULTILINE):
            status, message = "ÉCHEC", "marqueur VALIDATE_INSTALL_PASS absent"
    if status in {"TIMEOUT", "INFRASTRUCTURE"}:
        message = output.splitlines()[0]
    (out / f"{name}.log").write_text(output, encoding="utf-8")
    return {"test": name, "statut": status, "code": code, "secondes": seconds,
            "runtime": runtime, "delai_s": timeout, "commande": cmd,
            "args": [Path(arg).name if Path(arg).is_absolute() else arg for arg in args],
            "derniere_erreur": message[:220]}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser =argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--out", required=True, help="dossier de sortie des résultats et du clone")
    parser.add_argument("--seed-validation", help="dossier validation/ SOURCE, lu seulement")
    parser.add_argument("--filter", default="", help="sous-chaîne du nom de test")
    parser.add_argument("--compare", default=str(ROOT / "docs/audit/baseline-tests.json"), help="référence historique JSON")
    parser.add_argument("--compare-only", metavar="RESUME.json", help="comparaison historique d'un résultat existant")
    parser.add_argument("--timeout", type=int, metavar="SECONDES", help="remplace le délai maximal de chaque test")
    options = parser.parse_args()
    if options.timeout is not None and options.timeout <= 0:
        parser.error("--timeout doit être > 0")
    if options.compare_only and (options.filter or options.seed_validation or options.timeout):
        parser.error("--compare-only utilise uniquement --compare et --out")
    out = Path(options.out).resolve()
    if any(out.is_relative_to((ROOT / name).resolve()) for name in ("validation", "extension", "tools")):
        parser.error("la sortie doit être en dehors des répertoires validation/, extension/ et tools/ du dépôt")
    out.mkdir(parents=True, exist_ok=True)
    info = {"mode": "comparaison" if options.compare_only else "strict", "reference": options.compare}
    try:
        reference = load_results(options.compare)
        if options.compare_only:
            report = compare(load_results(options.compare_only), reference)
            write_report(out / "comparaison.json", {"info": info, "comparaison": report})
            return int(bool(report["regressions"]))
    except (OSError, ValueError) as error:
        info["erreur"] = str(error)
        write_report(out / "comparaison.json", {"info": info, "comparaison": {}})
        if not options.compare_only:
            write_report(out / "resume.json", [])
            write_report(out / "verdict.json", {"statut": "INFRASTRUCTURE", "code": 2, "info": info})
        print(f"INFRASTRUCTURE : {error}", file=sys.stderr)
        return 2

    summary = []
    info["filtre"] = options.filter
    try:
        clone = copy_isolated(out)
        info["clone"] = str(clone)
        if options.seed_validation:
            info["seed_copies"], info["seed_absents"] = seed(clone, Path(options.seed_validation).resolve())
        env = isolated_env(clone)
        shim = clone / ".shim.py"
        shim.write_text(SHIM, encoding="utf-8")
        scripts = {path.stem: path for path in (clone / "tools").glob("*.py")
                   if SCRIPT_NAME.fullmatch(path.stem)}
        args_by_test = registry(clone, clone / ".sorties")
        expected = DEFAULT_BLENDER_TESTS | args_by_test.keys() | {INSTALL_TEST}
        names = expected | scripts.keys() | {row["test"] for row in reference}

        for name in sorted(name for name in names if options.filter in name):
            required = name not in OBSOLETE
            if not required:
                result = {"test": name, "statut": "OBSOLÈTE", "raison": OBSOLETE[name]}
            elif name not in scripts:
                result = {"test": name, "statut": "ABSENT", "raison": "script requis absent du clone"}
            elif name in SKIP:
                result = {"test": name, "statut": "IGNORÉ", "raison": SKIP[name]}
            else:
                result = execute_test(name, scripts[name], args_by_test.get(name, []), clone,
                                      out, shim, env, options.timeout)
            summary.append(dict(result, requis=required))
            print(name, result["statut"], flush=True)
    except OSError as error:
        info["erreur"] = str(error)
        print(f"INFRASTRUCTURE : {error}", file=sys.stderr)

    required_results = [row for row in summary if row["requis"]]
    failures = [row["test"] for row in required_results if row["statut"] != "OK"]
    infrastructure = {"INFRASTRUCTURE", "BLOQUÉ", "ABSENT", "TIMEOUT"}
    if "erreur" in info or any(row["statut"] in infrastructure for row in required_results):
        status, exit_code = "INFRASTRUCTURE", 2
    elif failures or not required_results:
        status, exit_code = "ÉCHEC", 1
    else:
        status, exit_code = "OK", 0
    write_report(out / "resume.json", summary)
    write_report(out / "comparaison.json", {"info": info, "comparaison": compare(summary, reference)})
    write_report(out / "verdict.json", {"statut": status, "code": exit_code, "info": info,
                                        "requis": len(required_results), "non_valides": failures})
    print(f"Verdict strict : {status} ({len(required_results) - len(failures)}/{len(required_results)} requis OK)")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
