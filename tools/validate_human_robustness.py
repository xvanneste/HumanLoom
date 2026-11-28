"""Robustesse du corps natif (audit SCI-003, SCI-006, INT-008) : contrôle d'intersection des yeux après installation du rig, modificateur « HL Human » renommé / supprimé / dupliqué / remplacé, création échouée sans reste.

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/validate_human_robustness.py

Chaque critère s'exécute dans une scène neuve ; le script n'écrit que dans un dossier temporaire. Utilisable avant/après une correction : un critère non satisfait est un échec (pas une erreur de script)."""
import sys
import tempfile
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension import geometry_quality, human, skin_relief  # noqa: E402
from extension.animation import skeleton  # noqa: E402

addon.register()
FAILURES = []


def check(label, condition, detail=""):
    print(("OK   " if condition else "ECHEC"), label, detail, flush=True)
    if not condition:
        FAILURES.append(label)


def fresh():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.ops.humanloom.create()
    return bpy.context.object


def eyes_report(body):
    return geometry_quality.eye_fit(body, bpy.context)


def eyes_ok(report, count=2):
    return report.get("status") == "computed" and len(report.get("eyes", [])) == count


# ---------------------------------------------------------------- SCI-003
body = fresh()
check("SCI-003 avant rig : deux yeux", eyes_ok(eyes_report(body)), str(eyes_report(body).get("status")))
rig = skeleton.install(body, correctives=False)
bpy.context.view_layer.update()
report = eyes_report(body)
check("SCI-003 apres installation du rig : deux yeux", eyes_ok(report), report.get("status", ""))
for bone in rig.pose.bones:
    if bone.name.startswith("eye."):
        bone.rotation_mode = "XYZ"
        bone.rotation_euler = (0.0, 0.0, 0.45)
bpy.context.view_layer.update()
report = eyes_report(body)
check("SCI-003 regard extreme : deux yeux", eyes_ok(report), report.get("status", ""))
body.humanloom.eye_left.name = "Globe renomme"
report = eyes_report(body)
check("SCI-003 oeil renomme : deux yeux", eyes_ok(report), report.get("status", ""))
skeleton.remove(body)
bpy.context.view_layer.update()
report = eyes_report(body)
check("SCI-003 apres retrait du rig : deux yeux", eyes_ok(report), report.get("status", ""))
skeleton.install(body, correctives=False)
bpy.context.view_layer.update()
directory = Path(tempfile.mkdtemp(prefix="hl_robust_"))
path = str(directory / "yeux.blend")
bpy.ops.wm.save_as_mainfile(filepath=path)
bpy.ops.wm.open_mainfile(filepath=path)
addon.register() if not hasattr(bpy.types.Object, "humanloom") else None
reopened = next(o for o in bpy.data.objects if human.is_native(o))
report = eyes_report(reopened)
check("SCI-003 apres sauvegarde et rechargement : deux yeux", eyes_ok(report), report.get("status", ""))
reopened.humanloom.eye_right = reopened.humanloom.eye_left
report = eyes_report(reopened)
check("SCI-003 pointeur d'oeil double : refus explicite", report.get("status") not in ("computed",) and report.get("status") != "no_separate_eyes", report.get("status", ""))

# ---------------------------------------------------------------- SCI-006
status_of = getattr(human, "modifier_status", None)
repair = getattr(human, "repair_modifier", None)
error_type = getattr(human, "HumanStateError", None)


def raises_state_error(function):
    try:
        function()
    except Exception as error:  # noqa: BLE001
        return error_type is not None and isinstance(error, error_type) or (error_type is None and False)
    return False


body = fresh()
human.set_value(body, "age", 1.0)
modifier = body.modifiers[human.MODIFIER_NAME]
modifier.name = "Renomme par l'utilisateur"
check("SCI-006 renomme : valeur lue conservee", abs(human.get_value(body, "age") - 1.0) < 1e-6, str(human.get_value(body, "age")))
human.set_value(body, "age", 2.5)
group_value = float(getattr(body.modifiers["Renomme par l'utilisateur"].properties.inputs, human.sockets()["age"][0]).value)
check("SCI-006 renomme : ecriture effective", abs(group_value - 2.5) < 1e-6, str(group_value))
check("SCI-006 renomme : diagnostic explicite", status_of is not None and status_of(body)[0] == "renamed", str(status_of(body)[0] if status_of else "API absente"))
if repair is not None:
    repair(body)
check("SCI-006 reparation : nom canonique et valeur conservee", human.MODIFIER_NAME in body.modifiers and abs(human.get_value(body, "age") - 2.5) < 1e-6)
check("SCI-006 reparation : pilotes des yeux valides", all(fc.is_valid for eye in (body.humanloom.eye_left, body.humanloom.eye_right) for fc in eye.data.shape_keys.animation_data.drivers))

body = fresh()
human.set_value(body, "age", 1.0)
body.modifiers.remove(body.modifiers[human.MODIFIER_NAME])
check("SCI-006 supprime : diagnostic explicite", status_of is not None and status_of(body)[0] == "missing", str(status_of(body)[0] if status_of else "API absente"))
check("SCI-006 supprime : lecture sans silence", raises_state_error(lambda: human.get_value(body, "age")))
check("SCI-006 supprime : ecriture sans silence", raises_state_error(lambda: human.set_value(body, "age", 2.0)))
check("SCI-006 supprime : non editable", not human.is_editable(body))

body = fresh()
second = body.modifiers.new("Copie", "NODES")
second.node_group = body.modifiers[human.MODIFIER_NAME].node_group
check("SCI-006 doublon : diagnostic explicite", status_of is not None and status_of(body)[0] == "duplicate", str(status_of(body)[0] if status_of else "API absente"))
check("SCI-006 doublon : ecriture sans silence", raises_state_error(lambda: human.set_value(body, "age", 2.0)))

body = fresh()
stranger = bpy.data.node_groups.new("Autre groupe", "GeometryNodeTree")
body.modifiers[human.MODIFIER_NAME].node_group = stranger
check("SCI-006 groupe incompatible : diagnostic explicite", status_of is not None and status_of(body)[0] == "incompatible", str(status_of(body)[0] if status_of else "API absente"))
check("SCI-006 groupe incompatible : lecture sans silence", raises_state_error(lambda: human.get_value(body, "age")))

# ---------------------------------------------------------------- INT-008
TRACKED = ("objects", "meshes", "node_groups", "materials", "textures", "images", "shape_keys", "actions", "armatures", "curves", "collections")


def inventory():
    return {name: sorted(i.name for i in getattr(bpy.data, name)) for name in TRACKED}


def attempt_failure(label, patches, **kwargs):
    existing = fresh()
    existing_state = (existing.name, existing.humanloom.uuid, existing.humanloom.eye_left.name, existing.humanloom.eye_right.name, len(existing.modifiers))
    before = inventory()
    originals = [(owner, name, getattr(owner, name)) for owner, name, _ in patches]
    for owner, name, replacement in patches:
        setattr(owner, name, replacement)
    failed = False
    try:
        human.create_human(bpy.context, **kwargs)
    except Exception:  # noqa: BLE001
        failed = True
    finally:
        for owner, name, original in originals:
            setattr(owner, name, original)
    after = inventory()
    unchanged = before == after
    state = (existing.name, existing.humanloom.uuid, existing.humanloom.eye_left.name, existing.humanloom.eye_right.name, len(existing.modifiers))
    detail = "" if unchanged else str({k: (sorted(set(after[k]) - set(before[k])), sorted(set(before[k]) - set(after[k]))) for k in TRACKED if before[k] != after[k]})
    check(f"INT-008 {label} : erreur remontee", failed)
    check(f"INT-008 {label} : inventaire identique", unchanged, detail[:300])
    check(f"INT-008 {label} : corps preexistant intact", state == existing_state)
    check(f"INT-008 {label} : aucun corps partiel", sum(1 for o in bpy.data.objects if o.humanloom.is_human) == 1)


def boom(*_a, **_k):
    raise RuntimeError("panne injectee")


original_load = human.load_nodes


def load_then_fail():
    original_load()
    raise RuntimeError("panne injectee apres chargement des noeuds")


calls = {"n": 0}
original_drivers = human._retarget_eye_drivers


def fail_second_eye(eye, body):
    calls["n"] += 1
    if calls["n"] == 2:
        raise RuntimeError("panne injectee sur le second oeil")
    return original_drivers(eye, body)


attempt_failure("chargement des noeuds", [(human, "load_nodes", load_then_fail)])
attempt_failure("fichier des yeux absent", [(human, "EYES_PATH", Path(tempfile.gettempdir()) / "absent_hl_eyes.blend")])
calls["n"] = 0
attempt_failure("second oeil", [(human, "_retarget_eye_drivers", fail_second_eye)])
attempt_failure("relief de peau", [(skin_relief, "attach_native", boom)])
attempt_failure("positionnement final", [], location="pas un vecteur")

body = fresh()
check("INT-008 succes : corps complet", body.humanloom.is_human and body.humanloom.eye_left is not None and body.humanloom.eye_right is not None and body.modifiers.get("Displace") is not None or body.modifiers.get(skin_relief.NAME) is not None,
      str([m.name for m in body.modifiers]))
check("INT-008 succes : un seul corps, deux yeux", sum(1 for o in bpy.data.objects if o.humanloom.is_human) == 1 and len([o for o in bpy.data.objects if o.name.startswith(("Œil", "Globe"))]) == 2)

print("RESULTAT", "ECHECS " + ", ".join(FAILURES) if FAILURES else "tout OK")
sys.exit(1 if FAILURES else 0)
