"""T-R1 — Rigify disponible en 5.2 ? Pile Nœuds (identité) → Armature → Subsurf : déformation correcte et poids stables quand l'identité change.
Via shim ; rien n'est sauvegardé hors du dossier de sortie."""
import sys, json, math, traceback
from pathlib import Path
import bpy, numpy as np
import addon_utils

out = Path(sys.argv[sys.argv.index("--") + 1]).resolve(); out.mkdir(parents=True, exist_ok=True)
R = {}
try:
    r_en = bpy.ops.preferences.addon_enable(module="rigify")
    R["addon_enable"] = str(r_en)
    R["addons_actifs"] = [k for k in bpy.context.preferences.addons.keys() if "rigify" in k]
    import rigify
    R["rigify_version"] = getattr(rigify, "bl_info", {}).get("version", None)
    # enregistrer explicitement les paramètres des types de rig si nécessaire
    try:
        from rigify import feature_set_list  # noqa
    except Exception:
        pass
except Exception as e:
    R["addon_enable"] = "ERR " + str(e)[:200]
R["operateurs_metarig"] = [n for n in dir(bpy.ops.object) if "metarig" in n or "rigify" in n][:20]
assert bpy.ops.human_modeling.create() == {"FINISHED"}
body = bpy.context.object; keys = body.data.shape_keys
R["body"] = body.name
# 1. méta-rig humain (Rigify) + génération
try:
    bpy.ops.object.armature_human_metarig_add()
    meta = bpy.context.object
    R["metarig_os"] = len(meta.data.bones)
    # échelle/position grossière sur le corps (taille 1,64 m environ)
    zmax = max(v.co.z for v in body.data.vertices); meta_h = max(b.tail_local.z for b in meta.data.bones)
    meta.scale = (zmax / meta_h,) * 3
    bpy.context.view_layer.update()
    bpy.ops.pose.rigify_generate()
    rig = bpy.data.objects.get("rig")
    R["rig_genere"] = bool(rig)
    R["rig_os"] = len(rig.data.bones) if rig else 0
except Exception as e:
    R["rigify_erreur"] = traceback.format_exc()[-600:]
    rig = None
(out / "rig_probe.json").write_text(json.dumps(R, indent=1, ensure_ascii=False), encoding="utf-8")
if rig is None:
    print("RIG_PARTIAL"); raise SystemExit
# 2. poids automatiques + ordre de pile
bpy.ops.object.select_all(action="DESELECT"); body.select_set(True); rig.select_set(True); bpy.context.view_layer.objects.active = rig
try:
    bpy.ops.object.parent_set(type="ARMATURE_AUTO")
    R["poids_auto"] = True
    R["groupes_de_sommets"] = len(body.vertex_groups)
except Exception as e:
    R["poids_auto"] = "ERR " + str(e)[:200]
R["modificateurs"] = [m.type for m in body.modifiers]
(out / "rig_probe.json").write_text(json.dumps(R, indent=1, ensure_ascii=False), encoding="utf-8")
print("RIG_DONE")
