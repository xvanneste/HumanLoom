"""Une seule couleur de pièce (audit GRM-009) : interface, matériau d'affichage, entrée du shader rendu et tenue enregistrée concordent numériquement.

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/validate_garment_color.py"""
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension import garments  # noqa: E402
from extension.animation import skeleton  # noqa: E402

addon.register()
FAILURES = []


def check(label, condition, detail=""):
    print(("OK   " if condition else "ECHEC"), label, detail, flush=True)
    if not condition:
        FAILURES.append(label)


def close(a, b, tol=1e-6):
    return all(abs(x - y) < tol for x, y in zip(a, b)) and len(a) == len(b)


for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
bpy.ops.humanloom.create()
body = bpy.context.object
skeleton.install(body, correctives=False)
piece = garments.add_garment(body, "chemise")
material = piece.material_slots[0].material
shader = material.node_tree.nodes["Principled BSDF"]
rendered = lambda: tuple(shader.inputs["Base Color"].default_value[:3])  # noqa: E731
saved = lambda: next(item for item in garments.outfit_of(body) if item["piece"] == "chemise")["couleur"]  # noqa: E731

# 1. passage par l'interface (set_color)
garments.set_color(piece, (0.2, 0.4, 0.6))
check("set_color : shader, affichage et tenue concordent", close(rendered(), (0.2, 0.4, 0.6), 1e-6) and close(material.diffuse_color[:3], (0.2, 0.4, 0.6), 1e-6) and close(saved(), (0.2, 0.4, 0.6), 1e-6))
check("set_color : lecture de l'interface", close(garments.color_of(piece) if hasattr(garments, "color_of") else (), (0.2, 0.4, 0.6), 1e-6))

# 2. reglage direct dans l'editeur de materiaux (shader) : la tenue et l'interface doivent suivre le rendu
shader.inputs["Base Color"].default_value = (0.9, 0.1, 0.3, 1.0)
check("shader modifie : la tenue enregistree suit le rendu", close(saved(), rendered(), 1e-6), f"tenue={saved()} rendu={rendered()}")
check("shader modifie : l'interface lit le rendu", hasattr(garments, "color_of") and close(garments.color_of(piece), rendered(), 1e-6))

# 3. aller-retour de la tenue : mêmes valeurs numeriques apres rechargement
outfit = garments.outfit_of(body)
garments.apply_outfit(body, outfit)
again = next(g for g in garments.garments_of(body) if g[garments.MARKER] == "chemise")
new_shader = again.material_slots[0].material.node_tree.nodes["Principled BSDF"]
check("aller-retour de la tenue : rendu identique", close(tuple(new_shader.inputs["Base Color"].default_value[:3]), (0.9, 0.1, 0.3), 1e-6), str(tuple(new_shader.inputs["Base Color"].default_value[:3])))
check("aller-retour de la tenue : affichage identique", close(again.material_slots[0].material.diffuse_color[:3], (0.9, 0.1, 0.3), 1e-6))
print("RESULTAT", "ECHECS " + ", ".join(FAILURES) if FAILURES else "tout OK")
sys.exit(1 if FAILURES else 0)
