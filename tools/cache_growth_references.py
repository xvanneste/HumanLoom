"""Cache CC0 source geometry and anatomical helper positions for offline studies."""
from pathlib import Path
import json
import sys
import addon_utils
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from experimental_age_transfer import reference

NAMES = ("joint-l-ankle", "joint-l-knee", "joint-pelvis", "joint-l-shoulder", "joint-neck", "joint-jaw", "joint-l-eye")
AGES = (5, 15, 30, 75)


def main():
    output = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    addon_utils.enable("bl_ext.user_default.mpfb", default_set=True)
    values = {"names": np.array(NAMES)}
    # Convert the user-selected ages using the source application's nominal
    # endpoints (1,25,90 years). This is not a biological calibration.
    parameters = [(age-1)/48 if age < 25 else .5+(age-25)/130 for age in AGES]
    values["nominal_ages"] = np.array(AGES)
    values["parameters"] = np.array(parameters)
    for sex in (0, 1):
        for stage, age in enumerate(parameters):
            points, triangles, joints = reference(age, sex, True, NAMES)
            values[f"points_{sex}_{stage}"] = points
            values[f"triangles_{sex}_{stage}"] = triangles
            values[f"joints_{sex}_{stage}"] = np.array([joints[name] for name in NAMES])
    values["source"] = np.array("MPFB 2.0.18 MakeHuman CC0 macro geometry; age parameters not calibrated years")
    np.savez_compressed(output, **values)
    output.with_suffix(".json").write_text(json.dumps({"ages_requested": AGES, "source_parameters": parameters,
        "conversion_source": "https://github.com/makehumancommunity/makehuman/blob/master/makehuman/apps/human.py",
        "scope": "Source geometry convention only. Statistical and anatomical calibration is separate."}, indent=2), encoding="utf-8")
    print("GROWTH_SOURCE_CACHE_READY", flush=True)


if __name__ == "__main__":
    main()
