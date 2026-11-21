#!/bin/bash
D="$(cd "$(dirname "$0")"; pwd -W)"; cd "$(dirname "$0")/hl"; B='/c/Program Files/Blender Foundation/Blender 5.2/blender.exe'
A="$D/hl/extension/data/realistic.blend"; O="$D/hl/validation/proportions-14/extension-13/data/realistic.blend"
mkdir -p ../logs8 ../out8
run() { t=$1; shim=$2; shift 2; mkdir -p ../out8/$t; OUT="$D/out8/$t"; s=$(date +%s)
  args=(); for a in "$@"; do a=${a//@OUTF/$OUT/r.json}; a=${a//@OUT/$OUT}; a=${a//@A/$A}; a=${a//@O/$O}; args+=("$a"); done
  if [ "$shim" = 1 ]; then timeout 900 "$B" --background --factory-startup --offline-mode --threads 4 --python-exit-code 1 --python ../shim.py -- --shim-root "$D/hl" --shim-test "$D/hl/tools/$t.py" -- "${args[@]}" > ../logs8/$t.log 2>&1
  else timeout 900 "$B" --background --factory-startup --offline-mode --threads 4 --python-exit-code 1 --python tools/$t.py -- "${args[@]}" > ../logs8/$t.log 2>&1; fi
  echo "$t exit=$? secs=$(( $(date +%s)-s ))" >> ../logs8/summary.txt; }
run validate_age_dimensions 1 @A @OUT
run validate_modeling_workflow 1 @O @OUT
run validate_skin_relief 1 @O @OUT
run validate_surface_fix 1 @O @OUT
run validate_physics_profile22 1
run check_review_scenes23 0
echo DONE >> ../logs8/summary.txt
