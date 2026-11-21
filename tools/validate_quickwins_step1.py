"""Gains rapides de l'étape 1 (I-19, I-28, I-35, I-36, I-27, interface des contrôles).

Usage : blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/validate_quickwins_step1.py -- <sortie.json>
Importe `extension` depuis le dépôt (pas l'extension installée), recrée sa propre scène, n'écrit que le JSON de sortie."""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import extension as addon
from extension import groom
from extension.proportions import FACE_CONTROLS, property_name

assert bpy.app.background and bpy.app.version[:2] == (5, 2)
OUT = Path(sys.argv[sys.argv.index("--") + 1]) if "--" in sys.argv else ROOT / "validation/quickwins-step1/resume.json"
OUT.parent.mkdir(parents=True, exist_ok=True)
result = {}

addon.register()
for obj in tuple(bpy.context.scene.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
bpy.ops.human_modeling.create()
body = bpy.context.object
body_collection = body.users_collection[0]
# La collection active n'est PAS celle du corps : reproduit la condition de I-28.
other = bpy.data.collections.new("Collection")
bpy.context.scene.collection.children.link(other)
bpy.context.view_layer.active_layer_collection = bpy.context.view_layer.layer_collection.children["Collection"]
bpy.context.view_layer.objects.active = body


def f32(value):
    return float(np.float32(value))


# --- I-19 : bornes lues en simple précision acceptées, valeurs hors bornes toujours refusées -------------------------
bounds = {"variation": (0, .8), "radius": (.000005, .00015), "length": (.001, .45), "roughness": (.05, 1), "density": (0, 8000000)}
accepted, rejected = {}, {}
for key, (lo, hi) in bounds.items():
    for end, value in (("min", lo), ("max", hi)):
        cfg = groom.defaults("SCALP")
        cfg[key] = f32(value)
        groom.validate(cfg)
        accepted[f"{key}.{end}"] = cfg[key]
    for end, value in (("sous_min", lo - max(abs(lo), 1e-6) * .01 if lo else -1e-3), ("sur_max", hi * 1.01)):
        cfg = groom.defaults("SCALP")
        cfg[key] = value
        try:
            groom.validate(cfg)
        except ValueError:
            rejected[f"{key}.{end}"] = value
        else:
            raise AssertionError(f"accepté à tort : {key} {end}")
assert len(rejected) == 2 * len(bounds)
result["I-19"] = {"acceptees_float32": accepted, "refusees": rejected}

# --- I-28 / I-36 : collection et ordre de pile ---------------------------------------------------------------------
stacks = {}
for region in ("SCALP", "BROWS", "BEARD"):
    cfg = groom.defaults(region)
    cfg["guides"] = 40
    cfg["viewport"] = .05
    hair = groom.build(body, region, cfg)
    assert [c.name for c in hair.users_collection] == [body_collection.name], (region, [c.name for c in hair.users_collection])
    assert tuple(m.name for m in hair.modifiers) == groom.STACK_ANIMATION, (region, [m.name for m in hair.modifiers])
    assert not any(m.use_pin_to_last for m in hair.modifiers)
    stacks[region] = {"collections": [c.name for c in hair.users_collection], "animation": [m.name for m in hair.modifiers]}
    cfg_xpbd = dict(groom.state(hair.hl_groom), physics="XPBD")
    groom.configure(hair, cfg_xpbd)
    assert tuple(m.name for m in hair.modifiers) == groom.STACK_XPBD, (region, [m.name for m in hair.modifiers])
    stacks[region]["xpbd"] = [m.name for m in hair.modifiers]
    groom.configure(hair, dict(cfg_xpbd, physics="ANIMATION"))
    assert tuple(m.name for m in hair.modifiers) == groom.STACK_ANIMATION
result["I-28"] = {"collection_corps": body_collection.name, "collection_active_au_depart": "Collection"}
result["I-36"] = stacks

# --- I-35 : budget recalculé sur le masque peint --------------------------------------------------------------------
scalp = groom.find(body, "SCALP")
stored = scalp["hl_mask_area_m2"]
area_now = groom.mask_area(scalp)
assert abs(area_now - stored) / stored < 1e-6, (area_now, stored)
groom.check_viewport_budget(scalp, .3)
groom.appearance(scalp, groom.state(scalp.hl_groom))
group = body.vertex_groups["hl_density_scalp"]
group.add(list(range(len(body.data.vertices))), 1.0, "REPLACE")
area_full = groom.mask_area(scalp)
assert area_full > 10 * stored
errors = {}
for label, call in (("check_viewport_budget", lambda: groom.check_viewport_budget(scalp, .3)),
                    ("appearance", lambda: groom.appearance(scalp, groom.state(scalp.hl_groom)))):
    try:
        call()
    except ValueError as error:
        errors[label] = str(error)
    else:
        raise AssertionError("garde-fou absent : " + label)
result["I-35"] = {"aire_au_build_m2": stored, "aire_recalculee_apres_build_m2": area_now,
                  "aire_masque_a_1_m2": area_full, "refus": errors}

# --- I-27 : retours d'interface ------------------------------------------------------------------------------------
def run(cls, **attrs):
    reports = []
    fake = SimpleNamespace(report=lambda kind, message: reports.append((sorted(kind)[0], message)), **attrs)
    return cls.execute(fake, bpy.context), reports


status, reports = run(groom.HL_OT_groom_preset, preset="SHORT")
assert status == {"FINISHED"} and reports[0][0] == "INFO" and "Aucune zone ajoutée" in reports[0][1], reports
result["I-27"] = {"groom_preset_deja_present": reports}
status, reports = run(addon.HUMANMODELING_OT_smooth)
assert status == {"FINISHED"} and "déjà actif" in reports[0][1], reports
result["I-27"]["smooth_deja_actif"] = reports
status, reports = run(addon.HUMANMODELING_OT_mirror_landmarks)
assert status == {"FINISHED"} and reports and reports[0][0] == "INFO", (status, reports)
result["I-27"]["mirror_landmarks_rien_a_faire"] = reports
reports = None

# --- Interface : ce que chaque panneau dessine ----------------------------------------------------------------------
class Recorder:
    def __init__(self, log, active=True):
        self.log, self.active = log, active

    def prop(self, data, path, **kwargs):
        self.log.append((path, self.active))

    def row(self, **kwargs):
        return Recorder(self.log)

    def label(self, **kwargs):
        self.log.append(("label:" + kwargs.get("text", ""), True))

    def operator(self, *args, **kwargs):
        return SimpleNamespace()


def drawn(panel):
    log = []
    panel.draw(SimpleNamespace(layout=Recorder(log), identifiers=getattr(panel, "identifiers", ())), bpy.context)
    return log


bpy.context.view_layer.objects.active = body
keys = body.data.shape_keys
wm = bpy.context.window_manager
fat = [p for p, _ in drawn(addon.HUMANMODELING_PT_fat)]
assert '["hm_body_mass"]' not in fat and '["hm_whole_body"]' in fat and '["hm_adiposity"]' in fat, fat
body_panel = [p for p, _ in drawn(addon.HUMANMODELING_PT_body)]
assert '["hm_corpulence"]' not in body_panel
assert wm.human_modeling_show_legacy is False and not addon.HUMANMODELING_PT_legacy_volumes.poll(bpy.context)
wm.human_modeling_show_legacy = True
assert addon.HUMANMODELING_PT_legacy_volumes.poll(bpy.context)
legacy = [p for p, _ in drawn(addon.HUMANMODELING_PT_legacy_volumes)]
assert legacy == ['["hm_corpulence"]', '["hm_body_mass"]'], legacy
wm.human_modeling_show_legacy = False
groups = {}
seen = []
for cls in addon.FACE_GROUP_CLASSES:
    assert hasattr(bpy.types, cls.__name__) and cls.bl_parent_id == "HUMANMODELING_PT_face"
    paths = [p for p, _ in drawn(cls) if p.startswith("[")]
    groups[cls.bl_label] = paths
    seen += paths
assert sorted(seen) == sorted(f'["{property_name(i)}"]' for i, _ in FACE_CONTROLS), "chaque contrôle du visage dans un seul groupe"
assert drawn(addon.HUMANMODELING_PT_face) == []
skin = addon.FACE_GROUP_CLASSES[-1]
skin_state = {}
for age in (0., 2., 2.5, 3.):
    keys["human_modeling_age"] = age
    skin_state[str(age)] = [a for p, a in drawn(skin) if p == '["hm_skin_relief"]'][0]
assert skin_state == {"0.0": False, "2.0": False, "2.5": True, "3.0": True}, skin_state
result["interface"] = {"groupes_visage": groups, "fat": fat, "legacy": legacy, "skin_relief_actif_selon_age": skin_state}

# Les propriétés hm_* sont intactes : aucune clé retirée ni renommée.
assert all(property_name(i) in keys for i, _ in FACE_CONTROLS) and "hm_body_mass" in keys and "hm_corpulence" in keys
addon.unregister()
addon.register()
addon.unregister()
result["cycle_registre"] = "ok"
OUT.write_text(json.dumps(result, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
print("QUICKWINS_STEP1_OK", OUT)
