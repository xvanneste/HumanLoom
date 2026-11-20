"""Run in Blender's console to load the installed update without losing the scene."""

import importlib
import json
from pathlib import Path
import sys
import tomllib

import bpy

assert bpy.app.version[:2] == (5, 2), "Cette mise à jour cible Blender 5.2 uniquement."
package = "bl_ext.user_default.human_modeling"
addon = importlib.import_module(package)
addon.unregister()
for suffix in ("proportions", "anatomy", "landmark_sets", "measurements", "character_presets", "geometry_quality", "surface_fix", "body_profiles", "age_shapes", "skin_relief"):
    module_name = package + "." + suffix
    if module_name in sys.modules:
        importlib.reload(sys.modules[module_name])
    else:
        importlib.import_module(module_name)
addon = importlib.reload(addon)
addon.register()
for screen in bpy.data.screens:
    for area in screen.areas:
        for space in area.spaces:
            if space.type == "VIEW_3D":
                space.overlay.show_relationship_lines = False
root = Path(__file__).resolve().parents[1]
output = root / "validation" / "morphologie-globale-13" / "session-interface.json"
output.parent.mkdir(parents=True, exist_ok=True)
version = tomllib.loads((Path(addon.__file__).parent / "blender_manifest.toml").read_text(encoding="utf-8"))["version"]
output.write_text(json.dumps({"blender": bpy.app.version_string, "extension_version": version, "scene": bpy.data.filepath,
    "operators_registered": all(hasattr(bpy.ops.human_modeling, name) for name in ("save_landmarks", "load_landmarks", "mirror_landmarks", "check_geometry")),
    "module": addon.__file__}, indent=2), encoding="utf-8")
print(f"Human Modeling {version} chargé. Scène conservée.")
