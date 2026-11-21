"""Rejeu de l'état de référence des tests historiques, dans un CLONE ISOLÉ (jamais dans le dépôt de l'utilisateur).
Usage (Python normal, pas Blender) : python tools/audit/run_baseline.py <racine_clone> <dossier_sortie> [filtre]
Chaque test tourne dans un Blender 5.2 séparé (--background --factory-startup), 900 s maximum. Le registre ci-dessous donne les arguments propres à chaque script (I-44)."""
import subprocess, sys, json, time, re
from pathlib import Path

BL = r"C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
CLONE = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2]).resolve(); OUT.mkdir(parents=True, exist_ok=True)
FILTER = sys.argv[3] if len(sys.argv) > 3 else ""
SHIM = Path(__file__).resolve().parent / "shim.py"
ASSET = CLONE / "extension/data/realistic.blend"
OLD = CLONE / "validation/proportions-14/extension-13/data/realistic.blend"
TOOLS = CLONE / "tools"


def o(name):
    return str(OUT / name)


# nom -> liste d'arguments (None = pas d'arguments)
ARGS = {
    "validate_age_dimensions": [str(ASSET), o("age_dimensions")],
    "validate_age_eye_fit": [str(ASSET), o("age_eye_fit")],
    "validate_age_geometry": [str(ASSET), o("age_geometry.json")],
    "validate_age_transitions": [str(ASSET), str(OLD), o("age_transitions")],
    "validate_anatomy": [o("anatomy")],
    "validate_atlas14_measurements": ["07"],
    "validate_atlas14_reopen": ["07"],
    "validate_body_mass_neutral": [str(OLD), o("body_mass_neutral")],
    "validate_controls": [o("controls")],
    "validate_extended_body": [o("extended_body")],
    "validate_geometry_quality": [o("geometry_quality")],
    "validate_global_physique": [o("global_physique.json")],
    "validate_landmark_sets": [o("landmark_sets")],
    "validate_mass_render_surface": [o("mass_render_surface")],
    "validate_mass_transitions": [o("mass_transitions")],
    "validate_measurements": [o("measurements")],
    "validate_model": [o("model")],
    "validate_modeling_batch": [str(ASSET), o("modeling_batch.json"), "0.0", "2.0"],
    "validate_modeling_workflow": [str(OLD), o("modeling_workflow")],
    "validate_muscle_workflow": [str(OLD), o("muscle_workflow")],
    "validate_musculature": [str(ASSET), str(OLD), o("musculature")],
    "validate_presets": [o("presets")],
    "validate_regional_muscles18": [o("regional_muscles18.json"), "regional"],
    "validate_relief_render_surface": [o("relief_render_surface")],
    "validate_skin_relief": [str(OLD), o("skin_relief")],
    "validate_surface_fix": [str(OLD), o("surface_fix")],
}
SKIP = {"validate_groom_collision29": "travail en cours de l'utilisateur (non suivi)"}
OBSOLETE = {"validate_surface_fix": "I-34 : dépend d'un ancien asset non reproductible (82 croisements) ; remplacé par validate_geometry_quality"}

scripts = sorted(p for p in TOOLS.glob("*.py") if re.match(r"(validate|check)_", p.name))
summary = []
for p in scripts:
    n = p.stem
    if FILTER and FILTER not in n:
        continue
    if n in SKIP:
        summary.append({"test": n, "statut": "IGNORÉ", "raison": SKIP[n]}); continue
    if n in OBSOLETE:
        summary.append({"test": n, "statut": "OBSOLÈTE", "raison": OBSOLETE[n]})
        (OUT / "resume.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False), encoding="utf-8"); print(n, "OBSOLÈTE", flush=True); continue
    text = p.read_text(encoding="utf-8", errors="replace")
    args = ARGS.get(n, [])
    cmd = [BL, "--background", "--factory-startup", "--offline-mode", "--threads", "4", "--python-exit-code", "1"]
    for a in args:
        if str(OUT) in a and "." not in Path(a).name:
            Path(a).mkdir(parents=True, exist_ok=True)
    needs_ext = ("bl_ext.user_default" in text or "bpy.ops.human_modeling" in text or "human_modeling" in text) and "register()" not in text
    if needs_ext:
        cmd += ["--python", str(SHIM), "--", "--shim-root", str(CLONE), "--shim-test", str(p), "--"] + args
    else:
        cmd += ["--python", str(p), "--"] + args
    t0 = time.time()
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=900, cwd=str(CLONE), encoding="utf-8", errors="replace")
        rc, out = r.returncode, (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired as e:
        rc, out = -9, "TIMEOUT 900 s\n" + ((e.stdout or b"").decode("utf-8", "replace") if isinstance(e.stdout, bytes) else (e.stdout or ""))
    dt = round(time.time() - t0, 1)
    (OUT / f"{n}.log").write_text(out, encoding="utf-8")
    tail = [l for l in out.strip().splitlines() if l.strip()][-6:]
    err = next((l for l in reversed(out.splitlines()) if re.search(r"(Error|Exception|AssertionError|FAILED)", l)), "")
    summary.append({"test": n, "statut": "OK" if rc == 0 else ("TIMEOUT" if rc == -9 else "ÉCHEC"), "code": rc, "secondes": dt,
                    "args": [Path(a).name if "/" in a or "\\" in a else a for a in args], "derniere_erreur": err[:220]})
    (OUT / "resume.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False), encoding="utf-8")
    print(n, summary[-1]["statut"], dt, flush=True)
print("BASELINE_DONE", flush=True)
