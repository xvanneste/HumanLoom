"""Propriété et portabilité des ressources de tissu (audit GRM-006, GRM-018) : groupes natifs locaux sur toute la fermeture transitive, noms homonymes d'utilisateur intacts, collection de collision rattachée à la scène du corps, corps réellement visible au rendu.

  blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/validate_cloth_ownership.py

Chaque critère s'exécute dans une scène neuve. Un critère non satisfait est un échec (pas une erreur de script), ce qui permet la comparaison avant/après."""
import sys
import tempfile
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension import cloth_sim, garments  # noqa: E402
from extension.animation import skeleton  # noqa: E402

addon.register()
FAILURES = []
TMP = Path(tempfile.mkdtemp(prefix="hl_cloth_own_"))


def check(label, condition, detail=""):
    print(("OK   " if condition else "ECHEC"), label, detail, flush=True)
    if not condition:
        FAILURES.append(label)


def reset():
    for scene in list(bpy.data.scenes)[1:]:
        bpy.data.scenes.remove(scene)
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for collection in list(bpy.data.collections):
        bpy.data.collections.remove(collection)
    for group in list(bpy.data.node_groups):
        if group.users == 0 and group.library is None:
            bpy.data.node_groups.remove(group)


def dressed():
    reset()
    bpy.ops.humanloom.create()
    body = bpy.context.object
    skeleton.install(body, correctives=False)
    dress = garments.add_garment(body, "robe_courte")
    return body, dress


def closure_list(tree, seen):
    result = []
    if tree is None or tree.as_pointer() in seen:
        return result
    seen.add(tree.as_pointer())
    result.append(tree)
    for node in tree.nodes:
        if node.type == "GROUP" and node.node_tree is not None:
            result += closure_list(node.node_tree, seen)
    return result


def linked_trees(*objects):
    found = []
    seen = set()
    for obj in objects:
        for modifier in obj.modifiers:
            if modifier.type == "NODES" and modifier.node_group is not None:
                found += [t for t in closure_list(modifier.node_group, seen) if t.library is not None]
    return found


def painted_pixels(scene, body):
    """Nombre de pixels opaques d'un rendu Workbench du seul corps."""
    for obj in scene.objects:
        obj.hide_render = obj is not body and obj.type == "MESH"
    camera = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    scene.collection.objects.link(camera)
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 2.4
    camera.location = (0.0, -6.0, 0.9)
    camera.rotation_euler = (1.5707963, 0.0, 0.0)
    scene.camera = camera
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = scene.render.resolution_y = 64
    scene.render.film_transparent = True
    path = str(TMP / "rendu.png")
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    image = bpy.data.images.load(path)
    pixels = np.array(image.pixels[:]).reshape(-1, 4)
    bpy.data.images.remove(image)
    scene.collection.objects.unlink(camera)
    bpy.data.objects.remove(camera)
    return int((pixels[:, 3] > 0.5).sum())


# ---------------------------------------------------------------- GRM-018
body, dress = dressed()
cloth_sim.enable(dress)
remaining = linked_trees(dress, body)
check("GRM-018 fermeture transitive locale apres activation", not remaining, str([(t.name, t.library.filepath) for t in remaining]))
cloth_sim.disable(dress)
body, dress = dressed()
cloth_sim.enable(dress)
path = str(TMP / "tissu.blend")
bpy.ops.wm.save_as_mainfile(filepath=path)
bpy.ops.wm.open_mainfile(filepath=path)
body = next(o for o in bpy.data.objects if o.get("human_modeling_body") or o.humanloom.is_human)
dress = next(o for o in bpy.data.objects if o.parent == body and "Epinglage" in o.vertex_groups)
check("GRM-018 aucune bibliotheque externe apres rechargement", not [lib for lib in bpy.data.libraries], str([lib.filepath for lib in bpy.data.libraries]))
check("GRM-018 simulation toujours active apres rechargement", cloth_sim.is_enabled(dress))

# ---------------------------------------------------------------- GRM-006
# a) collection utilisateur homonyme
body, dress = dressed()
mine = bpy.data.collections.new(cloth_sim.COLLECTION)
bpy.context.scene.collection.children.link(mine)
cube = bpy.data.objects.new("cube utilisateur", bpy.data.meshes.new("cube utilisateur"))
mine.objects.link(cube)
mine.hide_render = False
cloth_sim.enable(dress)
cloth_sim.disable(dress)
check("GRM-006 collection homonyme : contenu conserve", mine.name in bpy.data.collections and cube.name in mine.objects)
check("GRM-006 collection homonyme : visibilite de rendu inchangee", not mine.hide_render)
check("GRM-006 collection homonyme : toujours liee a la scene", bpy.context.scene.user_of_id(mine) > 0 or mine.name in bpy.context.scene.collection.children)

# b) modificateur utilisateur homonyme d'un autre type
body, dress = dressed()
foreign = body.modifiers.new(cloth_sim.COLLIDER_MODIFIER, "SUBSURF")
cloth_sim.enable(dress)
cloth_sim.disable(dress)
check("GRM-006 modificateur homonyme : conserve apres activation/desactivation", body.modifiers.get(cloth_sim.COLLIDER_MODIFIER) is not None and body.modifiers[cloth_sim.COLLIDER_MODIFIER].type == "SUBSURF")

# c) groupes locaux homonymes mais de mauvaise signature
body, dress = dressed()
for name in (cloth_sim.CLOTH_GROUP, cloth_sim.COLLIDER_GROUP):
    while name in bpy.data.node_groups:
        bpy.data.node_groups[name].name = "ancien " + name  # libere le nom exact pour les groupes factices
fake_cloth = bpy.data.node_groups.new(cloth_sim.CLOTH_GROUP, "GeometryNodeTree")
fake_collider = bpy.data.node_groups.new(cloth_sim.COLLIDER_GROUP, "GeometryNodeTree")
try:
    modifier = cloth_sim.enable(dress)
    ok = modifier.node_group is not fake_cloth and any(i.name == "Substeps" for i in modifier.node_group.interface.items_tree)
    detail = modifier.node_group.name
except Exception as error:  # noqa: BLE001
    ok, detail = False, f"{type(error).__name__}: {error}"
check("GRM-006 groupes homonymes factices : tissu fonctionnel avec le vrai groupe", ok, detail)
check("GRM-006 groupes homonymes factices : donnees utilisateur conservees", fake_cloth.name in bpy.data.node_groups and fake_collider.name in bpy.data.node_groups and not fake_cloth.nodes and not any(m.node_group == fake_cloth for o in bpy.data.objects for m in o.modifiers if m.type == "NODES"))

# d) corps d'une autre scene que la scene courante
body, dress = dressed()
first = bpy.context.scene
other = bpy.data.scenes.new("Autre scene")
moved = [body, dress] + [o for o in bpy.data.objects if o not in (body, dress) and o.parent == body or o.type == "ARMATURE"]
for obj in moved:
    for collection in tuple(obj.users_collection):
        collection.objects.unlink(obj)
    other.collection.objects.link(obj)
cloth_sim.enable(dress)
check("GRM-006 scene du corps : corps absent de la scene courante", body.name not in first.objects, str([o.name for o in first.objects]))
effectors = body["hl_cloth_session"]["collection"]
check("GRM-006 scene du corps : collection de collision liee a la scene du corps", effectors.name in [c.name for c in other.collection.children] and effectors.name not in [c.name for c in first.collection.children])
cloth_sim.disable(dress)

# e) rendu reel du corps pendant la simulation
body, dress = dressed()
scene = bpy.context.scene
before = painted_pixels(scene, body)
cloth_sim.enable(dress)
during = painted_pixels(scene, body)
check("GRM-006 corps visible au rendu pendant la simulation", before > 50 and during > 0.9 * before, f"avant {before}, pendant {during}")
cloth_sim.disable(dress)

print("RESULTAT", "ECHECS " + ", ".join(FAILURES) if FAILURES else "tout OK")
sys.exit(1 if FAILURES else 0)
