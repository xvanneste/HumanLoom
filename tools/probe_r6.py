"""Sonde : lance validate_human_rig avec des réglages DQS temporaires (variables d'environnement HL_DQS_MIN, HL_DQS_HIP)."""
import os
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from extension.animation import skeleton  # noqa: E402

skeleton.DQS_MIN = float(os.environ.get("HL_DQS_MIN", "0"))
skeleton.DQS_HIP = os.environ.get("HL_DQS_HIP", "1") == "1"
runpy.run_path(str(ROOT / "tools" / "validate_human_rig.py"), run_name="__main__")
