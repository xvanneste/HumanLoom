# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Reprise d'une session (lire d'abord)

Branche de travail : `codex/natif` (D-17 ; aucun commit sans accord). `SUIVI_REPRISE.md` est le document de reprise : décisions, registre des tests techniques avec verdicts et preuves (ne pas refaire un test déjà fait), questions closes, pièges d'environnement, prochaines étapes. Les rapports de l'audit (`ETAT_DES_LIEUX.md`, `ISSUES.md`, `DESIGN_NATIF.md`, `IDEES.md`) et les scripts de mesure (`tools/audit/`) en dépendent. Ne jamais toucher à la session Blender de l'utilisateur ni aux autres versions de Blender installées.

## Project

HumanLoom is a Blender **5.2-only** extension (`blender_manifest.toml`: min 5.2.0, max 5.3.0) that generates editable human models (body, face, morphology, age) plus native Blender hair/body-hair grooming. Documentation, UI strings and commit messages are in **French**; keep that convention. The extension id `human_modeling` is deliberately kept so existing installs/scenes keep working — don't rename it, nor the `human_modeling_*` custom properties/markers (e.g. `human_modeling_body`, `human_modeling_schema`).

Branches: `main` (common snapshot), `codex/modelisation` (body/face/age work), `codex/groom` (hair work). Each branch keeps the other domain's files; separate changes by commit.

## Commands

There is no pytest/lint/build system. "Tests" are standalone scripts in `tools/` run in an isolated headless Blender 5.2 process (many recreate scenes — never run them in a user scene):

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' --background --factory-startup --offline-mode --threads 4 --python-exit-code 1 --python tools/validate_groom25.py
```

Run a single check by swapping the script (`tools/validate_*.py`, `check_*.py`, `probe_*.py`). Read a script's header/dependencies first: many read inputs from the gitignored `validation/` directory (e.g. `validate_groom_collision29.py` opens `validation/groom-25/HumanLoom-groom-revue.blend`, produced by earlier scripts), and some historical tools hardcode local paths. Outputs go to `validation/<topic>-<NN>/`.

Build the installable extension (`extension/` is the extension root):

```powershell
Set-Location extension
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' --command extension build
```

Render-board assemblers (`assemble_*.py`) run under a separate Python with Pillow (PDF output also ReportLab/pypdf/pypdfium2), not Blender's.

## Architecture

- `extension/__init__.py` (~1100 lines) is the add-on entry: operators, the **Humain** sidebar panels, `register()`. It imports the helper modules and the `groom` module; tools import it via `sys.path.insert(0, ROOT); import extension; extension.register()`.
- Current bodies are **schema 10 native humans** (`extension/human.py`): an ordinary mesh object (`Object.humanloom` facade) driven by the geometry-node group "HL Human" from `extension/data/human_nodes.blend` (eyes in `human_eyes.blend`); parameters are the modifier's inputs, not shape keys. The legacy engine (shape keys "Morphologie" + drivers, `human_modeling.create`, schema 9 `CURRENT_SCHEMA = 9` in `proportions.py`, `human_modeling_schema` on the mesh data) is kept for old scenes and shared modules go through the accessors in `human.py` (`is_native`, `get_value`, `set_value`). Controls are declared in `proportions.py` (`BODY_CONTROLS`, `FAT_CONTROLS`, `MUSCLE_CONTROLS`, `FACE_CONTROLS`, `bind_control`). Panels and operators gate on the schema, and older bodies are upgraded by migration operators. Bumping a schema or the rig `VERSION` (`animation/skeleton.py`) requires a matching migration plus the `tools/validate_*reopen*` style checks. Provenance of reference assets is in `extension/CREDITS.md`.
- Supporting modules: `anatomy`, `landmark_sets`, `measurements` (anthropometry/reports), `geometry_quality`, `surface_fix`, `skin_relief`, `age_shapes`, `body_profiles`, `character_presets`, `muscle_upgrade`; reference data in `extension/data/` (WHO / NHANES / physique JSON).
- **Groom** (`extension/groom.py`, `groom_fibers.py`, doc in `docs/groom.md`): 11 independent regions (`REGIONS`), each a native Blender 5.2 Hair Curves object parented to the body, attached by UV with stored triangle indices/barycentrics. The modifier stack uses native node groups (Interpolate Hair Curves, Hair Dynamics, Set Hair Curve Profile, Principled Hair BSDF), made **local** so `.blend` files stay portable. No legacy particle systems. Production code must not depend on `tools/` prototypes or `validation/`. Per-region settings live in `HL_GroomSettings` (`FIELDS`), JSON export/import transfers procedural settings only (not sculpted guides or painted weights). Viewport density (% of render density) is separate from render density. Physics has "follow body" (no gravity) vs experimental XPBD; XPBD results are not generally validated — see `docs/groom.md` before claiming physical correctness.
- `tools/` holds ~100 numbered dev scripts (suffix = iteration, e.g. `groom25`, `groom28`, `collision29`): `build_*` construct scenes/candidates, `validate_*`/`check_*` assert, `diagnose_*`/`inspect_*`/`probe_*` measure, `render_*`/`assemble_*` make review boards. Older numbered prototypes are history; the integrated code is in `extension/`. The `*_collision29` scripts (guard/audit/validate) are the current untracked work in progress.
- `unreal/HumanReferenceStudy/` is a separate Unreal reference-study project (generated dirs and `Content/Reference*` are gitignored).

## Conventions and gotchas

- Blender 5.2 only: don't add compatibility shims for older versions.
- `validation/`, `*.log`, `*.blend1`, `*.zip` are gitignored; a fresh clone lacks experiment results, so don't assume those files exist.
- Root-level `*.md` files (audits, research, deliveries, spec, implementation plan) are the project record; `README.md` states current validation status (shapes and prototypes are still under review, groom presets are artistic starting points, rig not shipped). Don't present them as validated or clinically calibrated.
- Version strings live in `blender_manifest.toml` (`version`), README and `docs/groom.md`; update together on release.
