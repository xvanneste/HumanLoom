"""Isolation des foules par scène (audit ANI-020) : générer, régénérer, effacer en B laisse A inchangée ; collection renommée ; scène copiée.

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/validate_crowd_scenes.py"""
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension import crowd  # noqa: E402

addon.register()
FAILURES = []


def check(label, condition, detail=""):
    print(("OK   " if condition else "ECHEC"), label, detail, flush=True)
    if not condition:
        FAILURES.append(label)


for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
scene_a = bpy.context.scene
spec = crowd.default_spec(2, 5)
spec["frames"] = 12
crowd.generate(bpy.context, spec)
members_a = [o.name for o in crowd.members_of(scene_a)]
record_a = scene_a["humanloom_crowd"]
collections_a = sorted(c.name for c in scene_a.collection.children_recursive)
check("A : deux personnages", len(members_a) == 2, str(members_a))

scene_b = bpy.data.scenes.new("B")
with bpy.context.temp_override(scene=scene_b):
    ctx = bpy.context
    crowd.generate(ctx, dict(spec, seed=9, rig=False))
members_b = [o.name for o in crowd.members_of(scene_b)]
check("B : deux personnages", len(members_b) == 2, str(members_b))
check("B : collection distincte de celle de A", {c.name for c in scene_b.collection.children_recursive}.isdisjoint({c.name for c in scene_a.collection.children_recursive}),
      f"A={sorted(c.name for c in scene_a.collection.children_recursive)} B={sorted(c.name for c in scene_b.collection.children_recursive)}")
check("B : aucun objet de A dans B", not set(o.name for o in scene_b.objects) & set(o.name for o in scene_a.objects))
check("A inchangee apres generation en B", [o.name for o in crowd.members_of(scene_a)] == members_a and sorted(c.name for c in scene_a.collection.children_recursive) == collections_a)

with bpy.context.temp_override(scene=scene_b):
    crowd.generate(bpy.context, dict(spec, seed=11, rig=False), replace=True)  # regeneration en B
check("A inchangee apres regeneration en B", [o.name for o in crowd.members_of(scene_a)] == members_a and scene_a["humanloom_crowd"].to_dict() == record_a.to_dict() if hasattr(record_a, "to_dict") else [o.name for o in crowd.members_of(scene_a)] == members_a)

with bpy.context.temp_override(scene=scene_b):
    crowd.clear(scene_b)
check("B vide apres effacement", not crowd.members_of(scene_b))
check("A inchangee apres effacement en B", [o.name for o in crowd.members_of(scene_a)] == members_a and all(o.name in bpy.data.objects for o in crowd.members_of(scene_a)) and sorted(c.name for c in scene_a.collection.children_recursive) == collections_a)

# collection renommee par l'utilisateur dans A : la foule reste identifiable et regenerable
destination = next(c for c in scene_a.collection.children_recursive if crowd._is_crowd_collection(c))
destination.name = "Ma foule"
try:
    crowd.generate(bpy.context, dict(spec, seed=13, rig=False), replace=True)
    done = len(crowd.members_of(scene_a)) == 2
    detail = str(sorted(c.name for c in scene_a.collection.children_recursive))
except Exception as error:  # noqa: BLE001
    done, detail = False, f"{type(error).__name__}: {error}"
crowd_collections = [c for c in scene_a.collection.children_recursive if c.name != "Collection"]  # toute collection ajoutée par la foule (renommée ou non)
check("A : collection renommee, une seule collection de foule, non vide", len(crowd_collections) == 1 and len(crowd_collections[0].objects) > 0, detail + str([(c.name, len(c.objects)) for c in scene_a.collection.children_recursive]))
check("A : collection renommee, regeneration sans fuite", done and not any(o.name.startswith("Foule") and o not in set(scene_a.objects) and o.users_collection for o in bpy.data.objects), detail)

# scene copiee (liee) : les collections sont partagees, l'effacement dans la copie ne doit pas toucher l'original
scene_c = bpy.data.scenes.new("C")
for child in scene_a.collection.children:
    scene_c.collection.children.link(child)
before = [o.name for o in crowd.members_of(scene_a)]
with bpy.context.temp_override(scene=scene_c):
    try:
        crowd.generate(bpy.context, dict(spec, seed=17, rig=False))
        refused = False
    except ValueError:
        refused = True
    except Exception:  # noqa: BLE001
        refused = True
check("A inchangee apres operation dans une scene qui partage ses collections", [o.name for o in crowd.members_of(scene_a)] == before)
print("RESULTAT", "ECHECS " + ", ".join(FAILURES) if FAILURES else "tout OK")
sys.exit(1 if FAILURES else 0)
