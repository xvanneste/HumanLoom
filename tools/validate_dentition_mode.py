"""Choix explicite de la dentition (audit ANI-024) : automatique selon l'âge (ancien comportement conservé), adulte, lactéale ou mixte ; états par dent représentables ; changement topologique explicite.

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/validate_dentition_mode.py"""
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension import human  # noqa: E402
from extension.animation import dental, skeleton  # noqa: E402

addon.register()
FAILURES = []


def check(label, condition, detail=""):
    print(("OK   " if condition else "ECHEC"), label, detail, flush=True)
    if not condition:
        FAILURES.append(label)


reference = dental.load_reference()
modes = getattr(dental, "DENTITION_MODES", None)
check("ANI-024 modes de dentition declares", modes == ("AUTO", "ADULT", "PRIMARY", "MIXED"), str(modes))


def table(mode, age):
    result = dental.tooth_table(reference, 0.5, age, mode)
    return result if len(result) == 4 else (*result, 1.0)


upper, _, primary, factor = table("AUTO", 0.4)
check("ANI-024 AUTO a 0,4 : lacteale (5 dents, taille 0,8)", primary and len(upper) == 5 and abs(upper[0]["largeur"] - 0.8 * table("ADULT", 0.4)[0][0]["largeur"]) < 1e-9)
upper, _, primary, factor = table("AUTO", 2.0)
check("ANI-024 AUTO a 2,0 : adulte (7 dents)", not primary and len(upper) == 7)
upper, _, primary, _ = table("ADULT", 0.4)
check("ANI-024 ADULT force a 0,4 : 7 dents adultes malgre l'age", not primary and len(upper) == 7)
upper, _, primary, _ = table("PRIMARY", 2.0)
check("ANI-024 PRIMARY force a 2,0 : 5 dents lacteales", primary and len(upper) == 5)
upper, lower, primary, factor = table("MIXED", 0.8)
adult = {t["nom"]: t["largeur"] for t in table("ADULT", 0.8)[0]}
lacteal = {t["nom"]: t["largeur"] for t in table("PRIMARY", 0.8)[0]}
check("ANI-024 MIXED : incisives de taille adulte, canine et molaires lacteales", all(abs(t["largeur"] - (adult[t["nom"]] if t["nom"] in ("incisive_centrale", "incisive_laterale") else lacteal[t["nom"]])) < 1e-9 for t in upper), str([(t["nom"], round(t["largeur"], 2)) for t in upper]))
check("ANI-024 MIXED : arcade intermediaire", 0.8 < factor < 1.0 and not primary, str(factor))
try:
    dental.tooth_table(reference, 0.5, 1.0, "inconnu")
    refused = False
except ValueError:
    refused = True
check("ANI-024 mode inconnu : refus explicite", refused)

for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
bpy.ops.humanloom.create()
body = bpy.context.object
human.set_value(body, "age", 2.0)
skeleton.install(body, correctives=False)
upper_before = dental.part_of(body, "upper")
check("ANI-024 corps adulte : dentition AUTO adulte", upper_before is not None and not upper_before["hl_dental_primary"] and upper_before["hl_dental_mode"] == "AUTO")
count_adult = len(upper_before.data.vertices)
dental.set_dentition(body, "MIXED")
mixed = dental.part_of(body, "upper")
check("ANI-024 passage en MIXED : dents regenerees et mode enregistre", mixed is not None and mixed["hl_dental_mode"] == "MIXED" and body["hl_dentition"] == "MIXED")
check("ANI-024 changement topologique explicite (nombre de sommets different)", len(mixed.data.vertices) != count_adult or mixed["hl_dental_teeth"] != upper_before.get("hl_dental_teeth"), f"{count_adult} -> {len(mixed.data.vertices)}")
dental.set_dentition(body, "AUTO")
back = dental.part_of(body, "upper")
check("ANI-024 retour a AUTO : retour a la dentition adulte d'origine", len(back.data.vertices) == count_adult and not back["hl_dental_primary"])
try:
    dental.set_dentition(body, "nimporte")
    refused = False
except ValueError:
    refused = True
check("ANI-024 mode invalide via l'API : refus sans changement", refused and body.get("hl_dentition") == "AUTO")
bpy.context.view_layer.objects.active = body
result = bpy.ops.humanloom.dentition(mode="PRIMARY")
part = dental.part_of(body, "upper")
check("ANI-024 operateur d'interface : dentition lacteale appliquee", result == {"FINISHED"} and part["hl_dental_primary"] and part["hl_dental_mode"] == "PRIMARY")
print("RESULTAT", "ECHECS " + ", ".join(FAILURES) if FAILURES else "tout OK")
sys.exit(1 if FAILURES else 0)
