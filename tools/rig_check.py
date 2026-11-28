"""Comparaison structurée des poids et ancres du squelette avec les fichiers livrés (audit ANI-030) : rapport localisé et code de sortie, utilisable sans Blender."""
import numpy as np

WEIGHT_TOLERANCE = 1e-6  # écart absolu admis sur un poids : stockage float32 des poids (précision relative ~6e-8) avec marge ; au-delà, un changement réel de l'algorithme ou de la version de Blender


def compare(stored_anchors, new_anchors, stored_names, stored_idx, stored_w, new_names, new_idx, new_w, atol=WEIGHT_TOLERANCE):
    """Retourne un rapport {identique, ancres, noms, influences, poids} où chaque différence est localisée (ancre, os, sommet)."""
    report = {"identique": True, "ancres": [], "noms": [], "influences": 0, "poids": []}
    for key in sorted(set(stored_anchors) | set(new_anchors)):
        if key not in stored_anchors or key not in new_anchors:
            report["ancres"].append({"ancre": key, "probleme": "absente du fichier livre" if key not in stored_anchors else "absente du calcul"})
        elif list(stored_anchors[key]["vertices"]) != list(new_anchors[key]["vertices"]):
            report["ancres"].append({"ancre": key, "probleme": "sommets differents"})
    if list(map(str, stored_names)) != list(map(str, new_names)):
        report["noms"] = sorted(set(map(str, stored_names)) ^ set(map(str, new_names))) or ["ordre des os different"]
    stored_idx, new_idx = np.asarray(stored_idx), np.asarray(new_idx)
    stored_w, new_w = np.asarray(stored_w, float), np.asarray(new_w, float)
    if stored_w.shape != new_w.shape or stored_idx.shape != new_idx.shape:
        report["poids"].append({"probleme": f"formes differentes {stored_w.shape} / {new_w.shape}"})
    else:
        report["influences"] = int((stored_idx != new_idx).sum())
        diff = np.abs(stored_w - new_w)
        for vertex, rank in zip(*np.nonzero(diff > atol)):
            if len(report["poids"]) >= 20:
                break
            bone = int(new_idx[vertex, rank])
            report["poids"].append({"sommet": int(vertex), "rang": int(rank), "os": str(new_names[bone]) if bone < len(new_names) else bone, "ecart": float(diff[vertex, rank])})
        report["ecart_max"] = float(diff.max()) if diff.size else 0.0
    report["identique"] = not (report["ancres"] or report["noms"] or report["influences"] or report["poids"])
    return report
