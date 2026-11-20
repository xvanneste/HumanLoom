"""Reopen delivered scenes and check editable dependencies, without saving them."""
from pathlib import Path
import json
import bpy

root = Path(__file__).resolve().parents[1]
out = root / 'validation/muscles-regionaux-18'
files = [out / 'Session-modelisation-14.blend'] + sorted((out / 'apercus').glob('*-inspection.blend'))
rows = []
for path in files:
    bpy.ops.wm.open_mainfile(filepath=str(path))
    bodies = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH' and obj.get('human_modeling_body')]
    assert len(bodies) == 2, (path, len(bodies))
    entries = []
    for obj in bodies:
        keys = obj.data.shape_keys
        assert obj.data.get('human_modeling_schema') == 9
        assert keys and keys.animation_data
        bpy.context.view_layer.update()
        assert all(driver.is_valid for driver in keys.animation_data.drivers)
        assert obj.modifiers['Human Modeling · Surface'].show_viewport
        entries.append({'name': obj.name, 'schema': 9, 'drivers_valid': True})
    images = [im for im in bpy.data.images if im.source == 'FILE' and im.users and im.packed_file]
    assert images, path
    rows.append({'file': str(path), 'bodies': entries, 'packed_images': len(images)})
(out / 'reouverture-livraison.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
print('DELIVERY18_REOPEN_PASS', len(rows), flush=True)
