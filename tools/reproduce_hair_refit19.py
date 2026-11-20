"""Exercise an archived CharMorph function with controlled particle stand-ins."""
from pathlib import Path
from types import SimpleNamespace
from contextlib import nullcontext
import ast
import json
import zipfile
import numpy

root = Path(__file__).resolve().parents[1]
with zipfile.ZipFile('G:/_dev/BlenderDev/CharMorph-downloader.zip') as archive:
    source = archive.read('CharMorph-downloader/lib/hair.py').decode('utf-8-sig')
function = next(node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef) and node.name == 'update_hair')

class HairKeys:
    def __init__(self, count):
        self.count = count
        self.written = None
    def __len__(self):
        return self.count
    def __getitem__(self, index):
        return SimpleNamespace(co_local=(0., 0., 0.))
    def foreach_set(self, name, values):
        self.written = numpy.asarray(values).reshape((-1, 3)).copy()

first = SimpleNamespace(hair_keys=HairKeys(2))  # Source counts expect 3 keys.
second = SimpleNamespace(hair_keys=HairKeys(3))
obj = SimpleNamespace(matrix_world=None, particle_systems=SimpleNamespace(active=SimpleNamespace(particles=[first, second])))
errors = []
environment = {
    'bpy': SimpleNamespace(context=SimpleNamespace(temp_override=lambda **kw: nullcontext()), ops=SimpleNamespace(particle=SimpleNamespace(disconnect_hair=lambda: None, connect_hair=lambda: None))),
    'utils': SimpleNamespace(Timer=lambda: SimpleNamespace(time=lambda *args: None), np_matrix_transform=lambda *args: None),
    'logger': SimpleNamespace(error=lambda *args: errors.append(str(args))),
}
exec(compile(ast.Module(body=[function], type_ignores=[]), '<archived CharMorph update_hair>', 'exec'), environment)
target = numpy.array([[0., 0., 0.], [1., 0., 0.], [2., 0., 0.], [3., 0., 0.], [4., 0., 0.]])
result = environment['update_hair'](obj, [2, 2], target)
actual = second.hair_keys.written[1:, 0].tolist()
assert result is True and actual == [1., 2.] and errors
report = {'scope': 'Original function, controlled stand-ins; not a complete character or UI test', 'mismatch_logged': bool(errors), 'returned_success': result, 'second_strand_expected_x': [3., 4.], 'second_strand_actual_x': actual, 'defect_reproduced': True}
(root / 'validation/pilosite-19/charmorph-refit-reproduction.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('CHARMORPH_REFIT_MISMATCH_REPRODUCED', actual, flush=True)
