"""Import partiel puis complet d'une même source (audit ANI-027) : dix actions présentes, aucun doublon ; un changement de filtre, de cadence ou de catégorie est traité comme une nouvelle demande.

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/validate_animation_partial_import.py"""
import importlib.util
import sys
import tempfile
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(f"hl_anim_{name}", ROOT / f"extension/animation/{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


importer = load("importer")
FAILURES = []


def check(label, condition, detail=""):
    print(("OK   " if condition else "ECHEC"), label, detail, flush=True)
    if not condition:
        FAILURES.append(label)


bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.object.armature_add()
arm = bpy.context.object
bpy.ops.object.mode_set(mode="EDIT")
bones = arm.data.edit_bones
bones[0].name, bones[0].head, bones[0].tail = "root", (0, 0, 0), (0, 0, 0.1)
pelvis = bones.new("pelvis")
pelvis.head, pelvis.tail, pelvis.parent = (0, 0, 1), (0, 0, 1.2), bones["root"]
bpy.ops.object.mode_set(mode="POSE")
for bone in arm.pose.bones:
    bone.rotation_mode = "QUATERNION"
actions = []
for index in range(10):
    arm.animation_data_clear()
    for frame in (1, 16, 31):
        a = 0.08 * (index + 1) * (frame - 1) / 30
        arm.pose.bones["pelvis"].rotation_quaternion = (1 - a * a / 2, a, 0, 0)
        arm.pose.bones["pelvis"].keyframe_insert("rotation_quaternion", frame=frame)
    action = arm.animation_data.action
    action.name = f"geste_{index:02d}"
    action.use_fake_user = True
    actions.append(action)
work = Path(tempfile.mkdtemp(prefix="hl_partial_"))
source = work / "sources"
source.mkdir()
bpy.data.libraries.write(str(source / "pack.blend"), set(actions), fake_user=True)
library = work / "bibliotheque"
exe = bpy.app.binary_path


def library_actions():
    path = library / importer.LIBRARY_BLEND
    if not path.is_file():
        return []
    with bpy.data.libraries.load(str(path), link=False) as (data_from, _):
        return sorted(data_from.actions)


first = importer.import_sources([source], library, exe, fps=30.0, limit=3)
partial = library_actions()
check("ANI-027 import partiel : 3 actions", len(partial) == 3, f"{first['ajoutées']} ajoutées, {len(partial)} presentes")
second = importer.import_sources([source], library, exe, fps=30.0)
complete = library_actions()
check("ANI-027 import complet apres partiel : 10 actions presentes", len(complete) == 10, f"{len(complete)} presentes ; rapport {second['ajoutées']} ajoutées / {second['doublons']} doublons / {second['inchangés']} inchangés")
check("ANI-027 aucune action dupliquee (noms uniques)", len(set(complete)) == len(complete) and not any(".00" in n for n in complete), str(complete))
third = importer.import_sources([source], library, exe, fps=30.0)
check("ANI-027 troisieme import identique : inchange", third["inchangés"] == 1 and third["ajoutées"] == 0 and len(library_actions()) == 10, str({k: third[k] for k in ("ajoutées", "doublons", "inchangés")}))
fourth = importer.import_sources([source], library, exe, fps=24.0)
check("ANI-027 cadence differente : nouvelle demande traitee sans perte", len(library_actions()) >= 10 and fourth["échecs"] == 0, str({k: fourth[k] for k in ("ajoutées", "doublons", "inchangés", "échecs")}))
print("RESULTAT", "ECHECS " + ", ".join(FAILURES) if FAILURES else "tout OK")
sys.exit(1 if FAILURES else 0)
