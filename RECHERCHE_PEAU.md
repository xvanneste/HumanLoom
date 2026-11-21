# RECHERCHE_PEAU — rendu de la peau pour HumanLoom (film, réaliste **et** stylisé)

> **Validation faite le 2026-11-21 : voir `VALIDATION_SCIENTIFIQUE.md`** (vérifié / partiel / non vérifié par donnée). En cas de désaccord, ce fichier de validation prévaut. Corrections : Donner 2008 = 6 paramètres (pas 4) ; Blender : méthode *Random Walk (Skin)* et PR #110989 (subsurface en distance, IOR retiré) vérifiés ; la page `dev` du manuel = 5.4.

Date : 2026-11-21. Statut : **recherche documentaire, rien n'est implémenté ni mesuré dans HumanLoom.** Les sources sont des résumés de recherche web (extraits) : je n'ai pas relu les équations des articles ; ce qui est chiffré vient d'un extrait cité. État actuel du dépôt : 1 UV (`UVMap`), 0 matériau sur le corps et les yeux (D-15).

Légende : ✅ source lue/extraite · ⚠ extrait seulement, à vérifier dans l'article · ⬜ non établi / à tester dans Blender 5.2.

## 1. Comment la peau réagit à la lumière (science)

| Sujet | Ce qu'on retient | Source |
|---|---|---|
| Modèle spectral à 2 couches (épiderme + derme) | Donner & Jensen 2006 : un BSDF/BSSRDF spectral piloté par **4 paramètres** (✅ PDF lu : fraction d'hémoglobine, fraction de mélanine, mélange eumélanine/phéomélanine, huile), profils de diffusion dépendant de la longueur d'onde, couche huileuse type Torrance-Sparrow ; couvre peaux africaine, asiatique, caucasienne. ⚠ | [Donner & Jensen 2006](https://cseweb.ucsd.edu/~henrik/papers/skin_bssrdf/) |
| Modèle hétérogène en couches | Donner et al. 2008 : ajoute fraction d'hémoglobine épidermique, absorption inter-couches, diffusion hétérogène ; reproduit **veines, taches de rousseur, tatouages**. ⚠ | [Donner 2008](https://gfx.cs.princeton.edu/pubs/Donner_2008_ALH/donner08hskin.pdf), [projet Columbia](https://www.cs.columbia.edu/cg/hskin) |
| Mesures sur 149 personnes | Weyrich et al. 2006 : 149 sujets (114 H / 35 F, majorité de moins de 40 ans) ; **le type de peau est le seul prédicteur fiable** (corrélation 0,77, genre 0,57, âge 0,54) ; types V-VI : absorption plus forte, diffusion plus faible ; pas de corrélation avec l'âge pour ces coefficients ; facteurs externes (sueur, froid, maquillage) ; statistiques publiées. ✅ (PDF lu) | [Weyrich 2006](https://vcg.seas.harvard.edu/publications/20060730-analysis-of-human-faces-using-a-measurement-based-skin-reflectance-model) |
| Diffusion normalisée (Disney) | Burley 2015 / Chiang-Kutz-Burley 2016 : l'artiste règle la **couleur apparente** A et une **distance de diffusion** d ; c'est la base de la plupart des SSS de production. Équations non relues. ⚠ | [notes Burley](https://blog.selfshadow.com/publications/s2015-shading-course/burley/s2015_pbs_disney_bsdf_notes.pdf), [SIGGRAPH 2016](https://media.disneyanimation.com/uploads/production/publication_asset/153/asset/siggraph2016SSS.pdf) |
| SSS séparable (temps réel) | Jimenez et al. 2015 : noyau unique séparable, 2 convolutions 1D, 0,489 ms en 1080p sur une Radeon HD 7970 (✅ PDF lu). Pertinent pour Eevee/viewport, pas pour Cycles. ⚠ | [iryoku](https://iryoku.com/separable-sss) |
| Mélanine et phototype | ✅ **Vérifié** (Saager 2015, in vivo) : fraction volumique de mélanine de 5 % (type I non exposé) à 20 % (type VI exposé) ; Fitzpatrick n'est pas un descripteur direct de la pigmentation (avant-bras exposé non corrélé au type). ✅ Vérifié : spectres NIST de 51 sujets, 250–2 500 nm. **Valeurs de modèle vérifiées** (Donner 2008) : mélanine 0–0,5, hémoglobine épidermique 0–0,05, dermique 0–0,1, carotène 0–0,05, huile 0–1, épiderme 0,25 mm, IOR 1,4/1,38 (voir `VALIDATION_SCIENTIFIQUE.md`). | [PMC4463032](https://pmc.ncbi.nlm.nih.gov/articles/PMC4463032), [NIST](https://www.nist.gov/node/414836), [PMC4890358](https://pmc.ncbi.nlm.nih.gov/articles/PMC4890358) |
| Échelles de teint | ⬜ non vérifié : « Fitzpatrick = réaction aux UV, pas teint », « Monk 10 teintes, CC BY 4.0 ». 🟡 Vérifié (abstract arXiv 2410.21005) : une échelle **colorimétrique** (CST) est proposée, jugée plus sensible et plus exacte que FST/MST notées à la main. | [arXiv 2410.21005](https://arxiv.org/abs/2410.21005), [Monk](https://www.Wikipedia.com/wiki/Monk_Skin_Tone_Scale) |
| Microrelief (pores, rides fines) | Les scans résolvent pores/rides à ≈ 0,1 mm ; synthèse de microgéométrie, déformation des pores à l'étirement (convolution de carte de déplacement), micro-rides procédurales par graphe de pores. ⚠ | [Graham 2013](https://vgl.ict.usc.edu/Research/Microgeometry/Measurement_Based_Synthesis_of_Facial_Microgeometry.pdf), [Skin Stretch](https://vgl.ict.usc.edu/Research/SkinStretch) |
| Vieillissement (✅ vérifié, Zargaran 2022 : épiderme aminci de 10 à 50 %, UV : rides profondes, relâchement, changements pigmentaires) | Intrinsèque : rides fines, épiderme aminci. Extrinsèque (soleil) : rides profondes, relâchement, **hyperpigmentation**. Collagène fragmenté, élastine altérée, jonction dermo-épidermique aplatie, vascularisation réduite. ⚠ | [PMC9543134](https://pmc.ncbi.nlm.nih.gov/articles/PMC9543134), [PMC6540032](https://pmc.ncbi.nlm.nih.gov/articles/PMC6540032), [Cosmetics 2025](https://flore.unifi.it/bitstream/2158/1429553/1/128%29%20cosmetics-12-00144.pdf) |

## 2. Ce que Blender offre (manuel, versions 4.x/dev ; **non vérifié en 5.2**)

- Principled BSDF : méthodes de subsurface **Random Walk (Skin)** (rayon ajusté automatiquement d'après la couleur, plus proche de la mesure) ; « Random Walk (Legacy) » et Christensen-Burley annoncés comme à supprimer ; rayon **par canal RVB** (rouge pénètre plus) ; anisotropie ≈ 0,8 citée pour la peau ; poids SSS à 0 ou 1. Cycles seulement pour la marche aléatoire. [Manuel Principled](https://docs.blender.org/manual/en/dev/render/shader_nodes/shader/principled.html), [PR #110989](https://projects.blender.org/blender/blender/pulls/110989).
- Stylisé : Blender Studio (Wing It!) documente un rendu 2D/toon dans Eevee (contours, reflets de bord, ombrage toon) ; technique de base : nœud **Shader to RGB** ; pistes à surveiller : proposition NPR de Blender (issue #120403). Piège cité : le backface culling d'une tête toon donne un mauvais rendu aux lèvres. [Wing It!](https://studio.blender.org/blog/shading-and-rendering-of-wing-it), [toon shading](https://studio.blender.org/blog/toon-character-workflow-shading), [NPR #120403](https://projects.blender.org/blender/blender/issues/120403).
- ⬜ À tester en 5.2 : état réel de Random Walk (Skin) dans Cycles 5.2, comportement avec le modificateur de nœuds, Eevee Next et SSS, nouveaux nœuds d'éclairage de matériau (un module tiers cite « Material Lighting » en 5.3 — **non applicable à 5.2**).

## 3. Ce que font les autres plugins (voir `RECHERCHE_PLUGINS.md`)

- **MPFB2** (code local analysé) : nœud de groupe `MpfbSkin` avec entrées `SkinColor`, `SpotColor`, `VeinColor`, rugosité, normale, poids SSS, multiplicateur de rayon et rayons X/Y/Z (défauts 1 / 0,2 / 0,1), IOR 1,4 ; sous-nœuds *variation de couleur, couleur maître, nombril, derme normal, irrégularité de normale, taches, veines* ; échelle SSS dépendant de l'unité de la scène. Idée à retenir : **un groupe de nœuds de peau paramétrique + masques procéduraux** (taches, veines).
- **MB-Lab** : carte de mélanine (1.8) + cartes SSS, rugosité, spéculaire, bump, déplacement. **CharMorph** : matériaux en bibliothèque, textures par jeu, couleur de peau directe, déplacement par matériau.
- **Globalskin / Human Generator** (commerciaux) : références de fonctionnalités, pas de code à reprendre.

## 4. Implications pour HumanLoom (propositions, à valider)

1. **Un groupe de nœuds de matériau « HL Skin »**, livré dans un `.blend` de ressources comme le groupe de déformation, utilisable aussi sans l'extension. Entrées **physiques et continues** plutôt qu'un « type de peau » : mélanine, hémoglobine (rougeur/veines), épaisseur/rayon de diffusion, huile (rugosité/brillance), rugosité de base, intensité du microrelief. Des **préréglages** (échelle de Monk comme repère de teinte, non comme catégories) peuvent charger ces valeurs.
2. **Âge relié à la peau** : l'entrée d'âge existante pilote aussi rides, taches d'âge, rugosité, hémoglobine, rayon SSS (amincissement) — sans prétendre à une calibration clinique (cf. `README.md`).
3. **Variation régionale** (visage plus rouge, mains/pieds, lèvres, aréoles) par **masques** sur l'UV ou attributs de groupes de sommets — c'est ce qui rend la peau crédible.
4. **Deux modes de rendu dans le même groupe** : *réaliste* (Principled + Random Walk Skin, microrelief) et *stylisé* (Shader to RGB, rampes, contours) ; l'interface expose un seul curseur « style », sans dupliquer les paramètres de teinte.
5. **Microrelief** : normal/déplacement tuilé (pores) + masques de rides d'âge ; piège : le déplacement dépend de la **subdivision** et de la **densité de texel** (voir mapping).
6. **Yeux, dents, cheveux** : matériaux séparés (cornée/iris à indice et réfraction, humidité ; les cheveux ont déjà Principled Hair BSDF).
7. Ne pas promettre la « justesse physique » : les paramètres spectraux de la littérature sont des repères, la fidélité dépendra des tests visuels.

## 5. Lacunes de cette recherche (à ne pas ignorer)

- Équations (Burley, Donner) **non relues** ; Weyrich : statistiques non extraites. Utiles pour fixer des valeurs de départ défendables.
- Aucune valeur mélanine/hémoglobine → couleur RVB **calculée** : à construire (ou à prendre dans les tables NIST/Weyrich après lecture).
- Rendu des **yeux** (sclère, iris, caustiques) et des **lèvres/muqueuses** non étudié.
- Rien n'a été testé dans Blender 5.2.

## 6. Tests proposés (rien n'est fait)

- T-S1 : valider dans Cycles 5.2 un groupe « HL Skin » minimal (mélanine/hémoglobine → couleur, rayon par canal) sur le corps actuel.
- T-S2 : coût et rendu Eevee vs Cycles avec Subsurf et nœuds de déformation.
- T-S3 : comparaison visuelle sur trois teintes extrêmes de l'échelle de Monk (rendu, pas mesure).
