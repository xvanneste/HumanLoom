#!/bin/bash
D="$(cd "$(dirname "$0")"; pwd -W)"; cd "$(dirname "$0")/hl"; B='/c/Program Files/Blender Foundation/Blender 5.2/blender.exe'
A="$D/hl/extension/data/realistic.blend"; O="$D/hl/validation/proportions-14/extension-13/data/realistic.blend"
mkdir -p ../logs7 ../out7
run() { # name shim(1/0) args...
  t=$1; shim=$2; shift 2; mkdir -p ../out7/$t; OUT="$D/out7/$t"; s=$(date +%s)
  args=(); for a in "$@"; do a=${a//@A/$A}; a=${a//@O/$O}; a=${a//@OUTF/$OUT/r.json}; a=${a//@OUT/$OUT}; args+=("$a"); done
  if [ "$shim" = 1 ]; then
    timeout 900 "$B" --background --factory-startup --offline-mode --threads 4 --python-exit-code 1 --python ../shim.py -- --shim-root "$D/hl" --shim-test "$D/hl/tools/$t.py" -- "${args[@]}" > ../logs7/$t.log 2>&1
  else
    timeout 900 "$B" --background --factory-startup --offline-mode --threads 4 --python-exit-code 1 --python tools/$t.py -- "${args[@]}" > ../logs7/$t.log 2>&1
  fi
  echo "$t exit=$? secs=$(( $(date +%s)-s ))" >> ../logs7/summary.txt
}
run validate_age_dimensions 1 @A @OUT
run validate_age_eye_fit 1 @A @OUT
run validate_age_geometry 1 @A @OUT 1
run validate_age_transitions 1 @A @O @OUT
run validate_atlas14_measurements 1 07
run validate_atlas14_reopen 1 07
run validate_body_mass_neutral 1 @O @OUT
run validate_delivery12_reopen 1
run validate_delivery13_reopen 1
run check_delivery18 1
run validate_extended_body 1 @OUTF
run validate_global_physique 1 @OUTF 1
run validate_mass_render_surface 1 @OUTF
run validate_mass_transitions 1 @OUTF
run validate_relief_render_surface 1 @OUTF
run validate_modeling_batch 1 @A @OUTF 1 2
run validate_modeling_workflow 1 @O @OUT
run validate_muscle_workflow 1 @O @OUT
run validate_musculature 1 @A @O @OUT
run validate_regional_compat18 1
run validate_regional_muscles18 1 @OUTF regional
run validate_regional_upgrade18 1
run validate_skin_relief 1 @O @OUT
run validate_surface_fix 1 @O @OUT
run validate_surface_atlas15 1
run validate_surface_atlas15_ages 1
run validate_hair20 1
run validate_dense_hair20 1
run validate_physics_profile22 1
run check_nature21 1
run validate_groom_reopen25 0
run validate_groom28 0
run check_groom_continuity25 0
run check_review_scenes23 0
run validate_groom_collision29 0
echo DONE >> ../logs7/summary.txt
