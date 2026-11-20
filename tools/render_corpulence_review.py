"""Render the new corpulence control and export matching reusable presets."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_modeling_review as review


def main():
    from bl_ext.user_default.human_modeling import character_presets
    import bpy

    output = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
    review.VARIANTS = tuple(
        (f"{label} · {name}", sex, {"corpulence": amount})
        for sex, label in ((0.0, "Féminine"), (1.0, "Masculine"))
        for name, amount in (("Mince", -1.0), ("Référence", 0.0), ("Plus ample", 1.0))
    )
    review.main()
    for body in bpy.context.scene.objects:
        if body.get("human_modeling_body"):
            name = body.name.replace(" · ", "-").replace(" ", "-")
            character_presets.write(output / (name + ".json"), character_presets.capture(body))
    print("CORPULENCE_REVIEW_AND_PRESETS_READY", flush=True)


if __name__ == "__main__":
    main()
