"""Annotate the measured snapshots without changing the baked dynamics."""
from pathlib import Path
import sys,math,json
import bpy,numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
import hair_prototype20 as h20

out=h20.ROOT/'validation/physique-cheveux-22'
path=out/'Banc-physique-cheveu-03.blend'
bpy.ops.wm.open_mainfile(filepath=str(path))
hair=bpy.data.objects['XPBD · 12 guides · 6 cm']
hair_name=hair.name
bpy.context.scene.frame_set(48)
expected=h20.evaluated_points(hair).copy()
bpy.context.scene.frame_set(1)
for obj in tuple(bpy.context.scene.objects):
    if obj.name.startswith('Repère visuel · racine fixe') or obj.name in ('Gravite native Blender 5.2','12 guides de 6 cm - racines rouges fixes'):
        bpy.data.objects.remove(obj,do_unlink=True)
red=h20.material('Racines fixes',(.7,.035,.02))
for offset in (-.045,.045):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16,ring_count=8,radius=.0012,location=(offset,0.,0.))
    bpy.context.object.name='Repère visuel · racine fixe'
    bpy.context.object.data.materials.append(red)
textmat=h20.material('Titre',(.8,.8,.8))
for value,z,size in [('Gravite native Blender 5.2',.047,.0048),('12 guides de 6 cm - racines rouges fixes',.037,.0035)]:
    data=bpy.data.curves.new(value,'FONT');data.body=value;data.size=size;data.align_x='CENTER'
    obj=bpy.data.objects.new(value,data);bpy.context.scene.collection.objects.link(obj)
    obj.location=(0.,-.015,z);obj.rotation_euler=(math.pi/2,0,0);data.materials.append(textmat)
for obj in bpy.context.selected_objects:obj.select_set(False)
hair.select_set(True);bpy.context.view_layer.objects.active=hair
bpy.ops.wm.save_as_mainfile(filepath=str(path),compress=True)
bpy.context.scene.render.filepath=str(out/'Gravite-fibre-droite-48-images.png')
bpy.ops.render.render(write_still=True)
bpy.ops.wm.open_mainfile(filepath=str(path));bpy.context.scene.frame_set(48)
assert np.array_equal(expected,h20.evaluated_points(bpy.data.objects[hair_name]))
(out/'cache-final-verifie.json').write_text(json.dumps({'packed_cache_preserved_after_presentation':True,'frame48_identical_after_reopen':True,'pass':True},indent=2),encoding='utf-8')
print('PHYSICS22_FINAL_CACHE_PASS',flush=True)
