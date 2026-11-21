import sys, types, runpy, importlib
from pathlib import Path
ROOT = Path(sys.argv[sys.argv.index("--shim-root")+1]); TEST = sys.argv[sys.argv.index("--shim-test")+1]
i = len(sys.argv) - 1 - sys.argv[::-1].index("--"); rest = sys.argv[i+1:]
sys.path.insert(0, str(ROOT))
import extension
for n in ("bl_ext","bl_ext.user_default"):
    sys.modules.setdefault(n, types.ModuleType(n))
sys.modules["bl_ext.user_default.human_modeling"] = extension
sys.modules["bl_ext.user_default"].human_modeling = extension
for m in list(sys.modules):
    if m.startswith("extension."): sys.modules["bl_ext.user_default.human_modeling."+m[10:]] = sys.modules[m]
extension.register()
sys.argv = [TEST, "--"] + rest
runpy.run_path(TEST, run_name="__main__")
