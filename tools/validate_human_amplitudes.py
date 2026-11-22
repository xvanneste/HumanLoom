"""Lot 4 (schéma 10, I-45, D-18) : facteurs d'amplitude des contrôles « timides », selon l'âge.

Usage : blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/validate_human_amplitudes.py -- <sortie.json>
Pour chaque contrôle de `AMPLITUDE_FACTORS` et chaque contrôle timide laissé à l'amplitude d'origine, à ±1, pour les sexes 0 et 1
et les stades d'âge 0 à 3 par demi-stade :
- amplitude : le déplacement de la cage native vaut `amplitude(contrôle, âge)` fois celui de l'ancien moteur (écart < 2e-5 m) ;
- qualité géométrique de la cage native (critère de `AMPLITUDES_CONTROLES.md` §7) : 0 face retournée, au plus 2 faces d'aire
  < 10 % de l'originale, au plus 12 arêtes étirées de plus de 2,5 fois.
Puis, sur la SURFACE LISSÉE (Subsurf niveau 1, sans le relief de peau), pour les stades entiers 0 à 3 : 0 face retournée et au
plus 8 faces d'aire < 10 % (4 fois la tolérance de la cage : une face de cage donne 4 faces lissées).
Les yeux suivent : le déplacement de chaque œil natif vaut le même facteur fois celui de l'œil de l'ancien moteur (écart < 2e-5 m).
Un contrôle à la fois : les combinaisons de contrôles amplifiés ne sont pas couvertes."""
import json
import sys
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import extension as addon
from extension import human
from extension.proportions import AMPLITUDE_FACTORS, MERGED_IN_SCHEMA_10, amplitude

OUT = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
OUT.parent.mkdir(parents=True, exist_ok=True)
SHY = ["eyelid_aperture", "lip_thickness", "lips", "muscle_definition", "nose_width", "mouth_corner", "mouth", "facial_asymmetry",
       "eye_height", "eye_spacing", "cheeks", "nose_bridge", "jaw_angle", "chin", "ears_angle", "ears_size", "nose_length", "forehead",
       "head_width", "jaw", "head_height"]
NATIVE_SHY = [c for c in SHY if c not in MERGED_IN_SCHEMA_10]  # lot 3 bis : lip_thickness et jaw_angle sont fusionnés dans lips et jaw
PARTS = {c: [c] + [m for m, t in MERGED_IN_SCHEMA_10.items() if t == c] for c in NATIVE_SHY}  # contrôles de l'ancien moteur sommés par contrôle natif
SEXES, STAGES, SIGNS = (0., 1.), (0., .5, 1., 1.5, 2., 2.5, 3.), (1., -1.)

addon.register()
for obj in tuple(bpy.context.scene.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
assert bpy.ops.humanloom.create() == {"FINISHED"}
native = bpy.context.object
assert bpy.ops.human_modeling.create() == {"FINISHED"}
engine = bpy.context.object
for modifier in native.modifiers:
    modifier.show_viewport = modifier.name == "HL Human"  # la cage native = le groupe de nœuds seul
for modifier in engine.modifiers:
    modifier.show_viewport = False
legacy_eye = next(o for o in engine.children if o.type == "MESH" and o.name.startswith("Œil gauche"))
native_eye = native.humanloom.eye_left
faces = np.array([p.vertices[:3] for p in native.data.polygons])
edges = np.array([e.vertices[:] for e in native.data.edges])


def cage(obj):
    human.touch(obj)
    bpy.context.view_layer.update()
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    buffer = np.empty(len(mesh.vertices) * 3, np.float32)
    mesh.vertices.foreach_get("co", buffer)
    evaluated.to_mesh_clear()
    return buffer.reshape(-1, 3).astype(np.float64)


def geometry(points):
    p0, p1, p2 = points[faces[:, 0]], points[faces[:, 1]], points[faces[:, 2]]
    normals = np.cross(p1 - p0, p2 - p0)
    return normals, np.linalg.norm(normals, axis=1) / 2, np.linalg.norm(points[edges[:, 0]] - points[edges[:, 1]], axis=1)


def set_state(obj, sex, age, control=None, amount=0.):
    for name in SHY:
        if human.has_control(obj, name):
            human.set_value(obj, name, 0.)
    human.set_value(obj, "sex", sex)
    human.set_value(obj, "age", age)
    if control:
        for part in (PARTS[control] if not human.is_native(obj) else [control]):  # l'ancien moteur reçoit la valeur sur chaque partie
            human.set_value(obj, part, amount)


rows, failures = [], []
for sex in SEXES:
    for age in STAGES:
        set_state(native, sex, age)
        set_state(engine, sex, age)
        neutral_native, neutral_engine = cage(native), cage(engine)
        eye_neutral_native, eye_neutral_engine = cage(native_eye), cage(legacy_eye)
        normals0, areas0, edges0 = geometry(neutral_native)
        valid = areas0 > 1e-10
        for control in NATIVE_SHY:
            for sign in SIGNS:
                set_state(native, sex, age, control, sign)
                shifted_native = cage(native)
                expected = np.zeros_like(shifted_native)
                eye_expected = np.zeros_like(eye_neutral_engine)
                for part in PARTS[control]:  # somme des parties, chacune avec son propre facteur d'âge
                    set_state(engine, sex, age)
                    human.set_value(engine, part, sign)
                    expected += amplitude(part, age) * (cage(engine) - neutral_engine)
                    eye_expected += amplitude(part, age) * (cage(legacy_eye) - eye_neutral_engine)
                set_state(engine, sex, age)
                error = float(np.abs((shifted_native - neutral_native) - expected).max())
                eye_now = cage(native_eye) - eye_neutral_native
                eye_error = float(np.abs(eye_now - eye_expected).max())
                normals, areas, lengths = geometry(shifted_native)
                flipped = int(((np.einsum("ij,ij->i", normals, normals0) < 0) & valid).sum())
                small = int(((areas < .1 * areas0) & valid).sum())
                stretched = int((lengths > 2.5 * np.maximum(edges0, 1e-9)).sum())
                row = {"control": control, "sex": sex, "age": age, "sign": sign, "factor": amplitude(control, age), "amplitude_error_m": error, "eye_amplitude_error_m": eye_error, "eye_displacement_m": float(np.abs(eye_now).max()),
                       "flipped": flipped, "small": small, "stretched": stretched,
                       "max_displacement_mm": round(float(np.linalg.norm(shifted_native - neutral_native, axis=1).max()) * 1000, 2)}
                rows.append(row)
                if error >= 2e-5 or eye_error >= 2e-5 or flipped > 0 or small > 2 or stretched > 12:
                    failures.append(row)
        set_state(native, sex, age)
# --- surface lissée (Subsurf niveau 1) ---------------------------------------------------------------------------------------
subsurf = native.modifiers["Human Modeling · Surface"]
subsurf.show_viewport = True
subsurf.levels = 1
smooth_rows, smooth_failures = [], []


def surface(obj):
    human.touch(obj)
    bpy.context.view_layer.update()
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    mesh.calc_loop_triangles()
    points = np.empty(len(mesh.vertices) * 3, np.float32)
    mesh.vertices.foreach_get("co", points)
    triangles = np.array([t.vertices[:] for t in mesh.loop_triangles])
    evaluated.to_mesh_clear()
    points = points.reshape(-1, 3).astype(np.float64)
    p0, p1, p2 = points[triangles[:, 0]], points[triangles[:, 1]], points[triangles[:, 2]]
    normals = np.cross(p1 - p0, p2 - p0)
    return normals, np.linalg.norm(normals, axis=1) / 2


for sex in SEXES:
    for age in (0., 1., 2., 3.):
        set_state(native, sex, age)
        normals0, areas0 = surface(native)
        valid = areas0 > 1e-10
        for control in NATIVE_SHY:
            for sign in SIGNS:
                set_state(native, sex, age, control, sign)
                normals, areas = surface(native)
                flipped = int(((np.einsum("ij,ij->i", normals, normals0) < 0) & valid).sum())
                small = int(((areas < .1 * areas0) & valid).sum())
                row = {"control": control, "sex": sex, "age": age, "sign": sign, "flipped": flipped, "small": small}
                smooth_rows.append(row)
                if flipped > 0 or small > 8:
                    smooth_failures.append(row)
        set_state(native, sex, age)
subsurf.show_viewport = False
failures += [dict(r, surface="lissée") for r in smooth_failures]
worst = max(rows, key=lambda r: r["amplitude_error_m"])
result = {
    "states": len(rows), "amplified_controls": sorted(AMPLITUDE_FACTORS), "merged": MERGED_IN_SCHEMA_10, "unchanged_controls": sorted(c for c in NATIVE_SHY if c not in AMPLITUDE_FACTORS),
    "max_amplitude_error_m": worst["amplitude_error_m"], "max_eye_amplitude_error_m": max(r["eye_amplitude_error_m"] for r in rows),
    "eye_moves_with_control": sorted({r["control"] for r in rows if r["eye_amplitude_error_m"] >= 0 and r.get("eye_displacement_m", 0) > 0}), "worst": [worst["control"], worst["sex"], worst["age"], worst["sign"]],
    "total_flipped": sum(r["flipped"] for r in rows), "max_small": max(r["small"] for r in rows), "max_stretched": max(r["stretched"] for r in rows),
    "smooth_states": len(smooth_rows), "smooth_total_flipped": sum(r["flipped"] for r in smooth_rows),
    "smooth_max_small": max(r["small"] for r in smooth_rows), "failures": failures, "per_state": rows, "per_state_smooth": smooth_rows,
}
OUT.write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding="utf-8")
summary = {k: v for k, v in result.items() if k not in ("per_state", "per_state_smooth")}
summary["failures"] = failures[:12]
summary["n_failures"] = len(failures)
print("HUMAN_AMPLITUDES", json.dumps(summary, ensure_ascii=False))
assert not failures, f"{len(failures)} états hors critère"
print("HUMAN_AMPLITUDES_PASS")
