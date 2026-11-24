"""Résume les JSON de `diagnose_joints.py` : python tools/summarize_joints.py DOSSIER tag1 [tag2 ...] (une ligne par articulation/angle/morphologie ; plusieurs étiquettes = comparaison)."""
import json
import sys
from pathlib import Path

folder, tags = Path(sys.argv[1]), sys.argv[2:]
data = {t: json.loads((folder / f"articulations_{t}.json").read_text(encoding="utf-8")) for t in tags}
first = data[tags[0]]
for morph in first:
    print("==", morph)
    for joint, rows in first[morph].items():
        if joint == "temps_evaluation_ms":
            print("  temps éval (ms):", {t: data[t][morph].get(joint) for t in tags})
            continue
        if joint.startswith("torsion"):
            print(f"  {joint}: pincement_min " + " | ".join(f"{t}: {data[t][morph][joint]['pincement_min']} (retournées {data[t][morph][joint]['retournees']})" for t in tags))
            continue
        for angle in rows:
            cells = []
            for t in tags:
                r = data[t][morph][joint][angle]
                sec = [v for k, v in r.items() if k.startswith("section_")]
                s = sec[0] if sec else {}
                cells.append(f"{t}: dVloc {r['dV_local_cm3']:+.0f} dVcorps {r['dV_corps_cm3']:+.0f} flip {r['retournees']} axes {s.get('rapport_axes', '-')}/{s.get('rapport_axes_repos', '-')} aire {s.get('aire_sur_repos', '-')}")
            print(f"  {joint} {angle:>4}°  " + "  ||  ".join(cells))
