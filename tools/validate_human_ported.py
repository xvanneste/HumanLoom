"""Lot 2 (schéma 10) : modules portés sur la façade `humanloom` pour un humain natif.

Usage : blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/validate_human_ported.py -- <sortie.json>
Couvre : pile de modificateurs et relief de peau, interface (panneaux, grisage), opérateurs (remise à zéro, hasard, silhouettes,
âge, taille), mesures, repères, préréglages, ajustement de dimension, groom, duplication complète. Les cas déjà couverts par
`validate_human_native.py` (équivalence au moteur de clés, yeux, UUID, rouvert sans l'extension) n'y sont pas répétés."""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import extension as addon
from extension import anatomy, character_presets, groom, human, landmark_sets, measurements
from extension.proportions import CONTROLS, FACE_CONTROLS, NATIVE_CONTROLS

OUT = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
OUT.parent.mkdir(parents=True, exist_ok=True)
R = {}
addon.register()
for obj in tuple(bpy.context.scene.objects):
    bpy.data.objects.remove(obj, do_unlink=True)


def make(sex=.5, age=2.):
    assert bpy.ops.humanloom.create(sex=sex, age=age) == {"FINISHED"}
    return bpy.context.object


def update():
    bpy.context.view_layer.update()


body = make()
context = bpy.context

# --- pile et relief de peau ------------------------------------------------------------------------------------------------
assert human.is_native(body) and not human.is_legacy(body)
assert [m.name for m in body.modifiers] == ["HL Human", "Human Modeling · Surface", "Human Modeling · Relief de peau"], [m.name for m in body.modifiers]
assert body.vertex_groups.get("HM · Relief visage") is not None
assert "human_modeling_schema" not in body.data and body.humanloom.schema_version == 10
relief = body.modifiers["Human Modeling · Relief de peau"]
strengths = {}
for age, amount in ((0., 1.), (2., 1.), (2.5, 0.), (3., 1.), (3., -1.)):
    body.humanloom.age, body.humanloom.skin_relief = age, amount
    update()
    strengths[f"age={age:g} relief={amount:g}"] = round(relief.strength, 6)
assert strengths["age=0 relief=1"] == 0 and strengths["age=2 relief=1"] == 0 and strengths["age=3 relief=-1"] == 0
assert abs(strengths["age=3 relief=1"] - .004) < 1e-6 and abs(strengths["age=2.5 relief=0"] - .001) < 1e-6, strengths
body.humanloom.age, body.humanloom.skin_relief = 2., 0.
R["relief"] = strengths

# --- panneaux : mêmes champs que pour l'ancien moteur, grisage de skin_relief ----------------------------------------------
class Recorder:
    def __init__(self, log, active=True):
        self.log, self.active = log, active

    def prop(self, data, path, **kwargs):
        self.log.append((path, self.active))

    def row(self, **kwargs):
        return Recorder(self.log)

    def label(self, **kwargs):
        self.log.append(("label:" + kwargs.get("text", ""), True))

    def operator(self, name, **kwargs):
        self.log.append(("operator:" + name, True))
        return SimpleNamespace()

    def __getattr__(self, name):
        return lambda *a, **k: Recorder(self.log)


def drawn(panel):
    log = []
    panel.draw(SimpleNamespace(layout=Recorder(log), identifiers=getattr(panel, "identifiers", ())), bpy.context)
    return log


bpy.context.view_layer.objects.active = body
for panel in (addon.HUMANMODELING_PT_body, addon.HUMANMODELING_PT_fat, addon.HUMANMODELING_PT_muscles, addon.HUMANMODELING_PT_age,
              addon.HUMANMODELING_PT_face, addon.HUMANMODELING_PT_measurements, addon.HUMANMODELING_PT_anatomy):
    assert panel.poll(context), panel.__name__
assert not addon.HUMANMODELING_OT_upgrade.poll(context) and not addon.HUMANMODELING_OT_repair_surface.poll(context)
fat = [p for p, _ in drawn(addon.HUMANMODELING_PT_fat)]
assert "body_mass" not in fat and {"whole_body", "adiposity"} <= set(fat), fat
assert "corpulence" not in [p for p, _ in drawn(addon.HUMANMODELING_PT_body)]
seen = []
for cls in addon.FACE_GROUP_CLASSES:
    seen += [p for p, _ in drawn(cls) if not p.startswith(("label", "operator"))]
assert sorted(seen) == sorted(i for i, _ in FACE_CONTROLS)
skin = addon.FACE_GROUP_CLASSES[-1]
grey = {}
for age in (0., 2., 2.5, 3.):
    body.humanloom.age = age
    grey[str(age)] = [a for p, a in drawn(skin) if p == "skin_relief"][0]
assert grey == {"0.0": False, "2.0": False, "2.5": True, "3.0": True}, grey
body.humanloom.age = 2.
R["interface"] = {"fat": fat, "skin_relief_actif": grey}

# --- opérateurs -----------------------------------------------------------------------------------------------------------
body.humanloom.shoulders, body.humanloom.nose_width = .7, -.4
assert bpy.ops.human_modeling.reset_proportions() == {"FINISHED"}
assert all(human.get_value(body, c) == 0 for c, _ in CONTROLS)
assert bpy.ops.human_modeling.randomize(seed=3, strength=.5, scope="ALL") == {"FINISHED"}
random_state = {c: human.get_value(body, c) for c, _ in CONTROLS}
assert any(abs(v) > 1e-3 for v in random_state.values()) and all(abs(v) <= .5 for v in random_state.values())
assert bpy.ops.human_modeling.reset_proportions() == {"FINISHED"}
assert bpy.ops.human_modeling.body_profile(profile="FITNESS") == {"FINISHED"}
assert human.get_value(body, "muscles") > 0
assert bpy.ops.human_modeling.age_reference(stage=3) == {"FINISHED"} and human.get_value(body, "age") == 3.
assert bpy.ops.human_modeling.age_reference(stage=2) == {"FINISHED"}
assert bpy.ops.human_modeling.reset_proportions() == {"FINISHED"}
assert bpy.ops.human_modeling.set_height(height=1.80) == {"FINISHED"}
update()
measured = measurements.measure(body, context)["height_m"]
assert abs(measured - 1.80) < 1e-3, measured
R["operators"] = {"height_after_set_height_m": measured}

# --- mesures et rapport ---------------------------------------------------------------------------------------------------
report = measurements.report(body, context)
assert report["model"]["schema"] == 10 and set(report["model"]["controls"]) == {c for c, _ in NATIVE_CONTROLS}
R["report"] = {"schema": report["model"]["schema"], "morphology": report["model"]["morphology"], "height_m": report["measurement"]["height_m"]}

# --- préréglages : aller-retour, mélange, repères ---------------------------------------------------------------------------
human.set_value(body, "sex", .8)
human.set_value(body, "age", 2.5)
for name, value in (("shoulders", .4), ("whole_body", .3), ("jaw", -.5), ("muscles", .6)):
    human.set_value(body, name, value)
state = character_presets.capture(body)
path = OUT.parent / "native-preset.json"
character_presets.write(path, state)
for name in ("shoulders", "whole_body", "jaw", "muscles"):
    human.set_value(body, name, 0.)
human.set_value(body, "sex", .1)
character_presets.apply(body, character_presets.read(path))
assert character_presets.capture(body) == state
before = character_presets.capture(body)
other = {**state, "morphology": .0, "controls": {**state["controls"], "shoulders": -.4}}
character_presets.apply(body, other, .5)
assert abs(human.get_value(body, "shoulders")) < 1e-6 and abs(human.get_value(body, "sex") - .4) < 1e-6
character_presets.apply(body, state)
R["presets"] = {"roundtrip": True, "blend_half": True}

# --- repères, miroir, ajustement d'une dimension ---------------------------------------------------------------------------
human.set_value(body, "sex", .5)
human.set_value(body, "age", 2.)
for control, _ in CONTROLS:
    human.set_value(body, control, 0.)
base = human.base_coordinates(body)
top, bottom = base[:, 2].max(), base[:, 2].min()
waist_vertex = int(np.argmin(np.abs(base[:, 2] - (bottom + .62 * (top - bottom))) + 10 * (np.abs(base[:, 0]) > .02)))
marker = anatomy.attach(body, "waist_level", waist_vertex)
assert marker.parent == body and anatomy.landmarks(body, context)["waist_level"]["vertex"] == waist_vertex
captured = landmark_sets.capture(body)
assert captured["points"]["waist_level"]["vertex"] == waist_vertex
payload, added = landmark_sets.mirrored(body)
assert isinstance(added, list)
update()
current = anatomy.value(body, context, "waist_level")
original = human.get_value(body, "waist")
fit_note = None
try:
    reached = anatomy.fit(body, context, "waist_level", current * 1.03)
    fit_note = {"target_m": current * 1.03, "reached_m": reached, "waist_control": human.get_value(body, "waist")}
except ValueError as error:  # un repère manuel unique peut ne pas varier régulièrement : le contrôle doit alors être restauré
    fit_note = {"refused": str(error)}
    assert abs(human.get_value(body, "waist") - original) < 1e-9
R["landmarks"] = {"waist_level_vertex": waist_vertex, "perimeter_m": current, "fit": fit_note}
assert bpy.ops.human_modeling.check_geometry() == {"FINISHED"}

# --- groom sur un humain natif -----------------------------------------------------------------------------------------------
groom_collection = bpy.data.collections.new("Autre")
bpy.context.scene.collection.children.link(groom_collection)
bpy.context.view_layer.active_layer_collection = bpy.context.view_layer.layer_collection.children["Autre"]
cfg = groom.defaults("SCALP")
cfg.update(guides=40, viewport=.05)
hair = groom.build(body, "SCALP", cfg)
brow_cfg = groom.defaults("BROWS")
brow_cfg.update(guides=30, viewport=.05)
brows = groom.build(body, "BROWS", brow_cfg)
assert groom.body_from(SimpleNamespace(active_object=hair)) == body
for h in (hair, brows):
    assert h.parent == body and h.data.surface == body
    assert tuple(m.name for m in h.modifiers) == groom.STACK_ANIMATION
    assert [c.name for c in h.users_collection] == [c.name for c in body.users_collection]
update()
evaluated = hair.evaluated_get(bpy.context.evaluated_depsgraph_get())
assert len(evaluated.data.curves) > 0
R["groom"] = {"scalp_guides": len(hair.data.curves), "evaluated_curves": len(evaluated.data.curves)}

# --- duplication complète --------------------------------------------------------------------------------------------------
bpy.context.view_layer.objects.active = body
assert bpy.ops.humanloom.duplicate() == {"FINISHED"}
clone = bpy.context.object
update()
assert clone != body and clone.humanloom.uuid != body.humanloom.uuid and human.is_native(clone)
assert clone.data is not body.data and clone.modifiers["HL Human"].node_group is body.modifiers["HL Human"].node_group
clone_eyes = (clone.humanloom.eye_left, clone.humanloom.eye_right)
assert all(e is not None and e.parent == clone for e in clone_eyes)
assert clone_eyes[0] not in (body.humanloom.eye_left, body.humanloom.eye_right)
clone_hair = next(c for c in clone.children if c.type == "CURVES" and c.get("hl_groom_region") == "SCALP")
assert clone_hair.data is not hair.data and clone_hair.data.surface == clone
assert clone_hair.modifiers["HumanLoom · densité"].node_group is not hair.modifiers["HumanLoom · densité"].node_group
assert clone_hair.data.materials[0] is not hair.data.materials[0]


def eye_position(eye):
    eye.update_tag()
    update()
    evaluated_eye = eye.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated_eye.to_mesh()
    points = np.array([v.co[:] for v in mesh.vertices])
    evaluated_eye.to_mesh_clear()
    return points


original_before = eye_position(body.humanloom.eye_left)
clone_before = eye_position(clone_eyes[0])
clone.humanloom.eye_spacing = 1.
clone.humanloom.eye_height = 1.
update()
original_after = eye_position(body.humanloom.eye_left)
clone_after = eye_position(clone_eyes[0])
moved_clone = float(np.abs(clone_after - clone_before).max())
moved_original = float(np.abs(original_after - original_before).max())
assert moved_clone > 1e-4 and moved_original < 1e-9, (moved_clone, moved_original)
R["duplicate"] = {"clone_eye_moved_m": moved_clone, "original_eye_moved_m": moved_original}

R["verdict"] = "ok"
OUT.write_text(json.dumps(R, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
print("HUMAN_PORTED_PASS", json.dumps(R, ensure_ascii=False, default=str))
