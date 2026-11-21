#!/bin/bash
# Rejeu de l'état de référence : chaque test dans un Blender 5.2 isolé, 5 min max, journal par test.
# Usage : bash tools/audit/baseline_run.sh <dossier_sortie>
OUT="$1"; mkdir -p "$OUT"
BL="C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
cd /g/_dev/BlenderDev/HumanLoom
: > "$OUT/resume.tsv"
for f in tools/validate_*.py tools/check_*.py; do
  n=$(basename "$f" .py)
  [ "$n" = "validate_groom_collision29" ] && continue   # travail en cours de l'utilisateur
  s=$(date +%s)
  timeout 300 "$BL" --background --factory-startup --offline-mode --threads 4 --python-exit-code 1 --python "$f" -- "$OUT/$n" > "$OUT/$n.log" 2>&1
  rc=$?
  e=$(date +%s)
  printf "%s\t%s\t%ss\n" "$n" "$rc" "$((e-s))" >> "$OUT/resume.tsv"
done
echo FIN >> "$OUT/resume.tsv"
