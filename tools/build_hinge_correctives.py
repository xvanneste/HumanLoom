"""Génère les données LIVRÉES des correctifs de charnière (coude, genou) pour le corps par défaut : `extension/data/human_rig_hinges.npz` (même algorithme que le recalcul de l'extension : `extension/animation/correctives.generate`).

  blender --background --factory-startup --offline-mode --python-exit-code 0 --python tools/build_hinge_correctives.py -- DOSSIER_DE_SORTIE [--write 1] [--morph defaut]

`--morph` : morphologie sur laquelle générer (pour des essais ; le fichier livré est celui du corps par défaut). Aucune donnée tierce."""
from pathlib import Path
import sys
import time

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import proto_shoulder_correctives as P  # noqa: E402
from extension.animation import correctives  # noqa: E402

ARGS = P.ARGS


def main():
    scene = P.Scene(P.MORPH)
    start = time.perf_counter()
    generator = correctives.generate(scene.body, scene.rig)
    payload = None
    while True:
        try:
            label, done, total = next(generator)
            if done % 10 == 0:
                print(f"  {done}/{total} ({label}) {time.perf_counter() - start:.0f} s", flush=True)
        except StopIteration as stop:
            payload = stop.value
            break
    sizes = {k: v.shape for k, v in payload.items() if k.endswith("_delta")}
    print("terminé en", round(time.perf_counter() - start), "s ;", sizes, flush=True)
    out = P.OUT
    out.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out / f"human_rig_hinges_{P.MORPH}.npz", **payload)
    if "--write" in ARGS and ARGS[ARGS.index("--write") + 1] == "1":
        target = Path(__file__).resolve().parents[1] / "extension" / "data" / "human_rig_hinges.npz"
        np.savez_compressed(target, **payload)
        print("écrit :", target, round(target.stat().st_size / 1024), "Ko")


main()
