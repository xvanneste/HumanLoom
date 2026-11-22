"""Entry point, run from the Unreal Editor:

  py "<...>/unreal/run_export.py"                       # incremental export (sync)
  py "<...>/unreal/run_export.py" --force               # re-export everything
  py "<...>/unreal/run_export.py" --analyze-only        # inventory only
  py "<...>/unreal/run_export.py" --out D:/Export --root /Game/Characters
  py "<...>/unreal/run_export.py" --skeleton <skeleton_id> --filter Locomotion

Defaults: output = <Project>/Saved/BlenderExport. Save all assets first
(File > Save All): change detection hashes the saved .uasset files.
"""
import argparse
import importlib
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import ue_inventory  # noqa: E402
import ue_export     # noqa: E402

for m in (ue_inventory, ue_export):      # pick up edits without restarting the editor
    importlib.reload(m)


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--out")
    p.add_argument("--root", action="append", help="content root(s), default /Game")
    p.add_argument("--force", action="store_true")
    p.add_argument("--analyze-only", action="store_true")
    p.add_argument("--no-meshes", action="store_true")
    p.add_argument("--skeleton")
    p.add_argument("--filter")
    p.add_argument("--batch", type=int, default=100)
    p.add_argument("--no-dialog", action="store_true")
    a, _ = p.parse_known_args(argv if argv is not None else sys.argv[1:])
    return ue_export.export_all(
        out_dir=a.out, roots=tuple(a.root or ["/Game"]), force=a.force,
        include_meshes=not a.no_meshes, analyze_only=a.analyze_only,
        only_skeleton=a.skeleton, name_filter=a.filter, batch_size=a.batch,
        progress=not a.no_dialog)


if __name__ == "__main__":
    main()
