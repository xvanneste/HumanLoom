import bpy, sys, json, re
from pathlib import Path
OUT = Path(sys.argv[-1]); ROOT = Path(__file__).resolve().parents[2]
bpy.ops.wm.open_mainfile(filepath=str(ROOT / "extension" / "data" / "realistic.blend"))
ob = bpy.data.objects["Corps"]; k = ob.data.shape_keys
names = [b.name for b in k.key_blocks]
groups = {}
for n in names:
    g = n.split(" · ")[0] if " · " in n else re.split(r"[ _\-]", n)[0]
    groups.setdefault(g, []).append(n)
OUT.write_text(json.dumps({"n": len(names), "groupes": {g: len(v) for g, v in groups.items()}, "HM": [n for n in names if n.startswith("HM")], "autres": [n for n in names if not n.startswith(("HM", "Age"))][:80], "vertex_groups": [v.name for v in ob.vertex_groups]}, indent=1, ensure_ascii=False), encoding="utf-8")
print("KEYS_DONE")
