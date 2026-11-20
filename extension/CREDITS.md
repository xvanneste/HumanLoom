# Human Modeling

The body and eyes are adapted from Human Base Meshes v1.4.1 by Blender Studio and community contributors, distributed under CC0.

[Blender asset library and source](https://www.blender.org/download/demo-files/)

Version 0.8 adds our reversible correction to the inner female eyelid surface and its interactions with the modeling controls. Vertex indexing and the original base shapes are retained.

Version 0.9 adds original artistic muscle deformation fields, global and regional controls, and editable body profiles. These amplitudes are not calibrated muscle mass or body fat measurements. No MPFB or CharMorph source code is included.

Version 0.10 adds original regional adipose and facial fields, reference age shapes, age-dependent control transport and reversible eye fitting. MPFB 2.0.18 CC0 reference geometry informed regional age profiles; its source code is not bundled. Age interpolation and deformation amplitudes are artistic engineering approximations.

Version 0.11 adds an original procedural UV displacement texture for age-related facial relief and a local inner-eyelid correction checked at subdivision two. The packed texture is generated from mathematical fields, without external images or scans. It is an artistic surface model, not a calibrated skin-aging dataset.

Version 0.12 adds original radial body-volume fields and age-dependent transport for extended body shapes. The ranges and interactions are artistic modeling bounds, not calibrated weight, BMI or tissue-composition estimates. No MPFB or CharMorph source code is included.

Version 0.13 adds original global tissue-envelope flow fields and separate bony and muscle surface cues, informed by the anatomical and body-composition references documented in Recherche-morphologie-globale.md in the development workspace. No research images, individual scans, trained models or numerical population coefficients are bundled. Amplitudes remain artistic approximations. The 0.12 volume fields are retained for compatibility.

Selected rounded WHO stature medians at 60 and 180 months are transcribed as individual numerical reference values. The bundled reference JSON files retain their official publication URLs, units and row locations. WHO stature references do not validate the remaining shape anatomy.

Adult stature reference values are transcribed from NCHS, Anthropometric Reference Data for Children and Adults, United States, August 2021–August 2023, Table 7, printed page 8. The report identifies its material as public domain.

[NCHS report](https://stacks.cdc.gov/view/cdc/174595) · [DOI](https://doi.org/10.15620/cdc/174595)

The 0.12 maintenance layer also repairs the female adult inner eyelid at subdivision two through a separate reversible age key; the maximum cage displacement is 0.0969 mm.

Version 0.14 unifies global and regional adult muscle controls through original atlas-based surface fields. Supplied stylized and MetaHuman bodies were inspected as visual references; no vertices, textures or rigs from those assets are included. OpenStax Anatomy and Physiology 2e sections 11.5 and 11.6 informed the distinction of regional muscle groups. The adult neutral shape retains the reviewed modeling candidate, including its provisional ANSUR II girth fits and CC0 MakeHuman/MPFB relative tissue references. These are artistic modeling controls, not calibrated muscle mass or clinical body composition. Released child, teen and senior control behavior is retained outside the adult interpolation anchor.

