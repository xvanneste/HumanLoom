"""Valide la tranche verticale native du lot 2 (schéma 10) : création, façade, yeux, UUID, animation, sauvegarde, enregistrement.

Usage : blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/validate_human_native.py -- <sortie.json>
Compare un humain natif (`humanloom.create`) à un corps de l'ancien moteur (`human_modeling.create`) aux mêmes réglages."""
import json
import subprocess
import sys
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import extension as addon
from extension import human

OUT = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
OUT.parent.mkdir(parents=True, exist_ok=True)
R = {}
PROBE = '''
import bpy, sys, json
saved, out = sys.argv[-2], sys.argv[-1]
bpy.ops.wm.open_mainfile(filepath=saved)
obj = next(o for o in bpy.data.objects if o.type == "MESH" and "HL Human" in o.modifiers)
def pts(o):
    o.update_tag(); bpy.context.view_layer.update()
    e = o.evaluated_get(bpy.context.evaluated_depsgraph_get()); m = e.to_mesh()
    r = [list(v.co) for v in m.vertices]; e.to_mesh_clear(); return r
eye = obj.humanloom.eye_left if hasattr(obj, "humanloom") else next(c for c in obj.children if c.name.startswith("Œil gauche"))
json.dump({"body": pts(obj), "eye": pts(eye), "has_facade": hasattr(obj, "humanloom"),
           "extension_loaded": any("human_modeling" in k for k in sys.modules)}, open(out, "w"))
print("NATIVE_REOPEN_OK")
'''


def clear():
    for obj in tuple(bpy.context.scene.objects):
        bpy.data.objects.remove(obj, do_unlink=True)


def evaluated(obj):
    obj.update_tag()
    bpy.context.view_layer.update()
    ev = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = ev.to_mesh()
    pts = np.array([v.co[:] for v in mesh.vertices])
    ev.to_mesh_clear()
    return pts


addon.register()
clear()
assert bpy.ops.humanloom.create() == {"FINISHED"}
native = bpy.context.object
props = native.humanloom
R["creation"] = {"type": native.type, "is_human": props.is_human, "uuid": props.uuid, "schema": props.schema_version,
                 "generator": props.generator_version, "modifiers": [m.name for m in native.modifiers],
                 "shape_keys": native.data.shape_keys is not None, "eye_left": props.eye_left.name if props.eye_left else None,
                 "eye_right": props.eye_right.name if props.eye_right else None}
assert native.type == "MESH" and props.is_human and len(props.uuid) == 36 and props.schema_version == 10
assert native.data.shape_keys is None and props.eye_left and props.eye_right
assert [m.name for m in native.modifiers][:2] == ["HL Human", "Human Modeling · Surface"], "ordre : nœuds puis Subsurf"
native.modifiers["Human Modeling · Surface"].show_viewport = False  # comparaison sur la cage

# --- ancien moteur au même état ----------------------------------------------------------------------------------------------
assert bpy.ops.human_modeling.create() == {"FINISHED"}
legacy = bpy.context.object
legacy_keys = legacy.data.shape_keys
legacy_eyes = {("Œil gauche" if o.name.startswith("Œil gauche") else "Œil droit"): o for o in legacy.children if o.type == "MESH"}
for modifier in legacy.modifiers:
    modifier.show_viewport = False
STATES = [
    {"sex": 0.0, "age": 2.0},
    # Contrôles à l'amplitude d'origine seulement : les contrôles amplifiés (lot 4) diffèrent de l'ancien moteur par construction,
    # leur amplitude exacte (corps et yeux) est vérifiée par `validate_human_amplitudes.py`.
    {"sex": 1.0, "age": 2.0, "shoulders": 0.7, "waist": -0.5, "head_width": 0.8, "fat_face": 0.6, "legs": 0.4, "muscles": 0.5},
    {"sex": 0.3, "age": 1.0, "head_height": -0.7, "eye_spacing": 0.9, "fat_arms": 0.5, "torso": -0.6, "adiposity": 0.4},
]
rows = []
for state in STATES:
    legacy_keys.key_blocks["Morphologie"].value = state["sex"]
    legacy_keys["human_modeling_age"] = state["age"]
    for control in addon.CONTROLS:
        legacy_keys["hm_" + control[0]] = state.get(control[0], 0.0)
    for name in human.sockets():
        default = 2.0 if name == "age" else 0.0
        setattr(props, name, state.get(name, default))
    body_error = float(np.abs(evaluated(native) - evaluated(legacy)).max())
    eye_errors = []
    for attribute, name in (("eye_left", "Œil gauche"), ("eye_right", "Œil droit")):
        eye_errors.append(float(np.abs(evaluated(getattr(props, attribute)) - evaluated(legacy_eyes[name])).max()))
    rows.append({"state": state, "body_error_m": body_error, "eye_errors_m": eye_errors})
R["equivalence"] = {"per_state": rows, "max_body_m": max(r["body_error_m"] for r in rows),
                    "max_eye_m": max(max(r["eye_errors_m"]) for r in rows)}

# --- façade : lecture/écriture -----------------------------------------------------------------------------------------------
props.shoulders = 0.37
assert abs(getattr(native.modifiers["HL Human"].properties.inputs, human.sockets()["shoulders"][0]).value - 0.37) < 1e-6 and abs(props.shoulders - 0.37) < 1e-6

# --- animation : image clé sur la façade -------------------------------------------------------------------------------------
props.shoulders = 0.0
native.keyframe_insert("humanloom.shoulders", frame=1)
props.shoulders = 1.0
native.keyframe_insert("humanloom.shoulders", frame=11)
bpy.context.scene.frame_set(6)
animated = props.shoulders
bpy.context.scene.frame_set(1)
assert 0.3 < animated < 0.7, animated
R["animation"] = {"value_at_frame_6": animated}
native.animation_data_clear()

# --- duplication avec nouvel UUID, indépendance ------------------------------------------------------------------------------
bpy.ops.object.select_all(action="DESELECT")
native.select_set(True)
bpy.context.view_layer.objects.active = native
props.waist = 0.5
before = props.uuid
bpy.ops.object.duplicate()
copy = bpy.context.object
bpy.context.view_layer.update()
human.ensure_unique_uuid()
assert copy is not native and copy.humanloom.uuid != native.humanloom.uuid and native.humanloom.uuid == before
copy.humanloom.waist = -0.5
independent = abs(native.humanloom.waist - 0.5) < 1e-6
R["duplication"] = {"uuid_original": native.humanloom.uuid, "uuid_copie": copy.humanloom.uuid,
                    "groupe_de_noeuds_partage": copy.modifiers["HL Human"].node_group is native.modifiers["HL Human"].node_group,
                    "independants": independent,
                    "yeux_de_la_copie_sont_ceux_de_l_original": copy.humanloom.eye_left is props.eye_left}

# --- duplication complète (opérateur humanloom.duplicate) : yeux indépendants, nouvel UUID, maillage propre -----------------------
bpy.ops.object.select_all(action="DESELECT")
native.select_set(True)
bpy.context.view_layer.objects.active = native
assert bpy.ops.humanloom.duplicate() == {"FINISHED"}
full = bpy.context.object
eyes_full = (full.humanloom.eye_left, full.humanloom.eye_right)
assert full.humanloom.uuid not in (native.humanloom.uuid, copy.humanloom.uuid)
assert full.data is not native.data and all(e is not None and e.parent == full for e in eyes_full)
assert eyes_full[0] is not props.eye_left and eyes_full[1] is not props.eye_right


def eye_points(eye):
    eye.update_tag()
    bpy.context.view_layer.update()
    evaluated_eye = eye.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated_eye.to_mesh()
    points = np.array([v.co[:] for v in mesh.vertices])
    evaluated_eye.to_mesh_clear()
    return points


original_eye_before, full_eye_before = eye_points(props.eye_left), eye_points(eyes_full[0])
full.humanloom.eye_spacing = 1.0
original_eye_after, full_eye_after = eye_points(props.eye_left), eye_points(eyes_full[0])
R["duplication_complete"] = {"uuid": full.humanloom.uuid, "yeux_independants_de_l_original": True,
                             "oeil_de_la_copie_deplace_m": float(np.abs(full_eye_after - full_eye_before).max()),
                             "oeil_de_l_original_deplace_m": float(np.abs(original_eye_after - original_eye_before).max())}
assert R["duplication_complete"]["oeil_de_la_copie_deplace_m"] > 1e-4 and R["duplication_complete"]["oeil_de_l_original_deplace_m"] < 1e-9
bpy.data.objects.remove(full, do_unlink=True)
for eye in eyes_full:
    bpy.data.objects.remove(eye, do_unlink=True)

# --- sauvegarde / rechargement SANS l'extension ------------------------------------------------------------------------------
for other in tuple(bpy.context.scene.objects):
    if other is not native and other not in (props.eye_left, props.eye_right):
        bpy.data.objects.remove(other, do_unlink=True)
for modifier in native.modifiers:
    modifier.show_viewport = modifier.name == "HL Human"
props.shoulders, props.waist, props.head_width = 0.6, -0.3, 0.9
expected_body = evaluated(native)
expected_eye = evaluated(props.eye_left)
saved = OUT.parent / "human_native_scene.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(saved), compress=True)
probe = OUT.parent / "native_reopen_probe.py"
probe.write_text(PROBE, encoding="utf-8")
answer = OUT.parent / "native_reopen_answer.json"
run = subprocess.run([bpy.app.binary_path, "--background", "--factory-startup", "--offline-mode", "--python-exit-code", "1", "--python", str(probe),
                      "--", str(saved), str(answer)], capture_output=True, text=True, timeout=600)
assert run.returncode == 0 and "NATIVE_REOPEN_OK" in run.stdout, run.stdout[-600:] + run.stderr[-600:]
reopened = json.loads(answer.read_text(encoding="utf-8"))
body_err = float(np.abs(np.array(reopened["body"]) - expected_body).max())
eye_err = float(np.abs(np.array(reopened["eye"]) - expected_eye).max())
R["reopen_without_extension"] = {"body_error_m": body_err, "eye_error_m": eye_err,
                                 "facade_present_without_extension": reopened["has_facade"],
                                 "extension_loaded": reopened["extension_loaded"]}

# --- désactivation / réactivation x3 -----------------------------------------------------------------------------------------
for _ in range(3):
    addon.unregister()
    addon.register()
assert hasattr(bpy.types.Object, "humanloom")
R["register_cycles"] = 3

verdict = {
    "corps natif = ancien moteur < 2e-5 m": R["equivalence"]["max_body_m"] < 2e-5,
    "yeux natifs = anciens yeux < 2e-5 m": R["equivalence"]["max_eye_m"] < 2e-5,
    "rouvert sans extension identique (corps) < 1e-6 m": body_err < 1e-6 and not reopened["extension_loaded"],
    "rouvert sans extension identique (yeux) < 1e-6 m": eye_err < 1e-6,
    "UUID unique après duplication": R["duplication"]["uuid_copie"] != R["duplication"]["uuid_original"],
    "deux humains indépendants": independent,
}
R["verdict"] = verdict
OUT.write_text(json.dumps(R, indent=1, ensure_ascii=False), encoding="utf-8")
print("HUMAN_NATIVE", json.dumps({k: R[k] for k in ("creation", "animation", "duplication", "reopen_without_extension", "verdict")}, ensure_ascii=False))
print("HUMAN_NATIVE_EQUIV", json.dumps({"max_body_m": R["equivalence"]["max_body_m"], "max_eye_m": R["equivalence"]["max_eye_m"]}))
assert all(verdict.values()), verdict
print("HUMAN_NATIVE_PASS")
