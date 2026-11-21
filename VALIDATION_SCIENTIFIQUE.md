# VALIDATION_SCIENTIFIQUE — vérification des données des `RECHERCHE_*.md`

Date : 2026-11-21. Méthode : relecture des **sources primaires** par des agents de lecture web, plus extraction locale de 4 PDF (`pdftotext`). Verdicts : ✅ **vérifié** dans la source · 🟡 **partiel** (résumé/abstract seulement) · ❌ **infirmé** · ⬜ **non vérifié** (source inaccessible : reCAPTCHA PMC, PDF > 10 Mo, 403/500). « Non vérifié » ne veut pas dire faux. Rien n'a été repris de mémoire.

## 1. Vérifié dans le texte intégral

| Donnée | Verdict | Source lue |
|---|---|---|
| **Donner 2008** : modèle en couches hétérogène à **6 paramètres spatialement variables** : fraction de mélanine Cm (0–0,5), type de mélanine m (0–1), hémoglobine épidermique Che (0–0,05), carotène Cbc (0–0,05), hémoglobine dermique Chd (0–0,1), huile s (0–1) ; épiderme **0,25 mm** constant, derme semi-infini ; indices de réfraction **1,4 et 1,38** ; diffusion réduite en loi de puissance (épiderme), moitié dans le derme ; Torrance-Sparrow en surface ; rendu spectral à 8 longueurs d'onde (≤ 1 % d'erreur RVB vs 151 échantillons) ; veines, taches de rousseur, tatouages obtenus via cartes de paramètres | ✅ | [PDF Donner 2008](https://gfx.cs.princeton.edu/pubs/Donner_2008_ALH/donner08hskin.pdf) |
| **STAR** : paramètres réduits à **20 % de SMPL**, correctifs locaux parcimonieux (un os n'influence que des sommets proches), entraîné avec **~10 000 scans** supplémentaires (hommes/femmes) | ✅ (le « 6 890 sommets » de SMPL n'est pas dans le texte lu) | [STAR](https://download.is.tue.mpg.de/star/star_paper.pdf) |
| **Régression des articulations SMPL** : poids encouragés positifs et de somme 1 pour rester dans l'enveloppe convexe des sommets ; le régresseur courant est dit **imprécis** (pas d'erreur chiffrée en mm, hanches non nommées) | ✅ / ⬜ chiffres | [Hedlin et al. 2022](https://arxiv.org/abs/2205.00076) (PDF extrait) |
| **Kavan 2009** : l'interpolation linéaire des matrices (LBS) provoque l'effondrement de volume / candy-wrapper | ✅ (gonflement DQS et PSD non vérifiés dans ce texte) | [Kavan 2009](https://users.cs.utah.edu/~ladislav/kavan09automatic/kavan09automatic.pdf) |
| **Rigify** (manuel, page *dev* = **Blender 5.4** au 2026-11-21) : méta-rig « Basic Human » sans visage ni doigts ; Generate Rig ; modifier le méta-rig puis régénérer ; os du visage dans la collection **Face** ; **Upgrade Face Rig** ; os du visage « presque inutiles » avec des shape keys | ✅ (⚠ valable pour 5.4, à recouper en 5.2) | [Rigify basics](https://docs.blender.org/manual/en/dev/addons/rigify/basics.html) |
| **Meta** : **15 visèmes** (AA, CH, DD, E, FF, IH, KK, NN, OH, OU, PP, RR, SIL, SS, TH) ; **70** blendshapes FACS | ✅ | [Meta](https://developers.meta.com/horizon/documentation/unity/move-face-tracking/) |
| **ARKit : 52 blendshapes** (14 yeux, 27 bouche/mâchoire, 10 sourcils/joues/nez, 1 langue) — le total 52 est **compté**, la page ne l'énonce pas ; noms relevés sur la page Apple (`eyeBlinkLeft` … `tongueOut`) | ✅ | [Apple](https://developer.apple.com/documentation/arkit/arfaceanchor/blendshapelocation.md) |
| **Anny** : **267** paramètres de phénotype, chacun dans [0,1] ; distributions **Bêta** conditionnées par âge et genre ; calibrées sur moyenne/écart-type des standards OMS (croissance de l'enfant 2006 + IMC) ; **Apache 2.0** (modèle et code) ; 13 718 sommets, 163 os ; erreur de recalage 2,4 mm sur 400 scans d'adultes ; **mise en garde** : les phénotypes reflètent les préjugés des artistes MakeHuman, pas l'identité | ✅ | [Anny v2](https://arxiv.org/html/2511.03589v2) |
| **ANSUR II** : 4 082 hommes, 1 986 femmes, 93 mesures ; CSV publics (2017) ; **n'approxime pas la population civile** ; piège : « weightkg » est en **hectogrammes** | ✅ (« 15 variables » et absence de scans 3D publics non retrouvées sur cette page) | [ANSUR II](https://www.openlab.psu.edu/ansur2/) |
| **Burley, profil de diffusion normalisé** : R_d(r) = 1/(8πd) · [e^(−r/3d)/r + e^(−r/d)/r] (forme simplifiée, intégrale = 1) | ✅ (brevet) ; 🟡 lien avec l'albédo A **non confirmé** | [US9659404](https://patents.google.com/patent/US9659404) |
| **Blender PR 110989** (fusionnée 2023-09-13) : le subsurface devient une **distance** (rayon), le mélange diffuse/subsurface est possible, **l'entrée Subsurface IOR est supprimée** | ✅ | [API de la PR](https://projects.blender.org/api/v1/repos/blender/blender/pulls/110989) |
| **Manuel Principled (5.2 LTS et 5.4)** : méthodes *Christensen-Burley, Random Walk, Random Walk (Skin), Random Walk (Legacy)* ; Skin = « optimisée pour la peau » ; rayon par canal RVB ; anisotropie 0,8 citée ; Legacy « à supprimer » | 🟡 (résumés automatiques ; désaccord sur « Cycles seulement ») | [manuel 5.2](https://docs.blender.org/manual/en/5.2/render/shader_nodes/shader/principled.html) |
| **Jimenez 2015** : noyau séparable, **2 convolutions 1D**, < 0,5 ms par image (conditions non données) ; l'état de l'art antérieur : jusqu'à 12 convolutions 1D | 🟡 (abstract) | [iryoku](https://iryoku.com/separable-sss) |
| **Weyrich 2006** : 149 sujets, variations avec âge, sexe, race, facteurs externes | 🟡 (résumé) ; aucun chiffre | [Harvard](https://vcg.seas.harvard.edu/publications/20060730-analysis-of-human-faces-using-a-measurement-based-skin-reflectance-model) |
| **Donner & Jensen 2006** : 2 couches, 4 paramètres huile/mélanine/hémoglobine, Torrance-Sparrow ; le 4ᵉ paramètre **n'est pas nommé** sur la page | 🟡 | [projet](https://cseweb.ucsd.edu/~henrik/papers/skin_bssrdf/) |
| **NIST** : moyenne de spectres de **51 sujets**, 250–2 500 nm ; eau, mélanine, hémoglobine = contributeurs majeurs | ✅ | [NIST](https://www.nist.gov/node/414836) |
| **Microgéométrie** : scans ≈ 0,1 mm (mésostructure) ; microstructure mesurée à **10 µm** ; carte mésostructure 4K, microstructure 16K ; peau étirée = plus brillante dans la direction d'étirement, comprimée = plus rugueuse | ✅ (page SkinStretch) | [SkinStretch](https://vgl.ict.usc.edu/Research/SkinStretch) |

## 2. Corrections apportées aux documents

- **« Mélanine ≈ 5 % à 20 % » : vérifié depuis (voir §4).** Avant les PDF : non vérifié. Retiré comme fait ; la plage **0–0,5 de Donner 2008** est une plage de **paramètre de modèle**, pas une mesure physiologique.
- **« Fitzpatrick mal descripteur », « vieillissement intrinsèque/extrinsèque », « Heath-Carter (bandes, 341 adultes) », « graisse androïde/gynoïde et ménopause »** : tous **NON vérifiés** (PMC/Springer bloqués). Gardés comme *connaissance générale à confirmer*, marqués ⬜.
- **« 4 paramètres »** : vrai pour Donner 2006 ; le modèle 2008 en a **6**.
- **Blender** : la page `dev` du manuel affiche **5.4**, pas 5.2 ; la page 5.2 LTS existe et a été lue par résumé.
- **Anny** : 267 paramètres (pas seulement 6) ; licence des **données** d'Anny-One non trouvée ; calibration OMS **enfants** confirmée, adultes non précisée.
- **ARKit « n'est pas FACS »** : non confirmé par Apple (venait d'un extrait de 2026) ⬜.

## 3. Restant à vérifier (sources à fournir ou lire autrement)

1. Articles **PMC** (4463032, 4890358, 9543134, 6540032, 12452521, 4348027) : bloqués par reCAPTCHA ; Europe PMC renvoie 403/500. → l'utilisateur peut les ouvrir dans son navigateur, ou déposer les PDF localement.
2. **Burley 2015 / Disney 2016** (PDF > 10 Mo) : lien entre albédo A et distance d.
3. **Weyrich 2006** (certificat rejeté) : chiffres par âge/sexe/type de peau.
4. **Jimenez 2015** (PDF 27 Mo) : conditions du 0,5 ms.
5. **Donner & Jensen 2006** : 4ᵉ paramètre.
6. Chiffres d'erreur de la régression d'articulations ; PSD/DQS dans Kavan ; liste des 15 variables d'ANSUR.

## 4. Mise à jour : PDF fournis par l'utilisateur (`G:\_dev\BlenderDev\PDF`, lus en local avec `pdftotext`)

Les PDF ne sont **pas** dans le dépôt (droits d'auteur) ; ils ne sont pas committés. Certains sont des articles **différents** de ceux que j'avais cités : c'est noté.

| Donnée | Verdict | Source locale |
|---|---|---|
| **Fraction volumique de mélanine : 5 % (type I, zone non exposée) à 20 % (type VI, exposée au soleil)** ; mesures in vivo (microscopie multiphotonique et spectroscopie SFDS), 2 × plus de mélanine entre types I et VI sur l'avant-bras interne, 3 × sur l'avant-bras externe | ✅ | Saager et al., *J. Biomed. Opt.* 20(6), 2015 (`JBO-020-066005.pdf`) |
| **Fitzpatrick n'est pas un descripteur direct de la pigmentation** : échelle subjective de réaction au soleil ; tendance générale à plus de mélanine avec le type, **mais la mélanine de l'avant-bras externe n'est pas corrélée au type** (exposition, taches de rousseur, protection solaire) | ✅ | `JBO-020-066005.pdf` ; `JBO-021-057001.pdf` (*J. Biomed. Opt.* 21(5), 2016) |
| **Vieillissement** : épiderme aminci de **10 à 50 %** au cours de la vie ; peau exposée aux UV : rides profondes, relâchement, rugosité, changements pigmentaires, télangiectasies ; le derme s'amincit aussi ; les types I-II ont un épiderme atrophique, les types III-V un épaississement ; vieillissement divisé en mécanismes intrinsèques et extrinsèques | ✅ (la formulation « hyperpigmentation » exacte devient « changements pigmentaires ») | Zargaran et al., *Int. J. Cosmet. Sci.* 44, 2022 (`ICS-44-414.pdf`) ; revue sur le derme (`ijms-20-02126.pdf`, non détaillée) |
| **Graisse androïde/gynoïde** : phénotypes « haut du corps » vs « bas du corps » ; différences de répartition liées aux stéroïdes sexuels, qui apparaissent à la puberté et **changent à la ménopause** (accumulation abdominale accrue, indépendamment de la masse grasse totale) ; mécanismes **pas entièrement compris** | ✅ | `nihms-666319.pdf` (*Horm Mol Biol Clin Investig*) |
| **Heath-Carter** : méthode et 13 catégories confirmées ; ce PDF est une étude de **889 athlètes mexicains** (477 H, 412 F), pas l'étude de 341 adultes que j'avais citée ; type dominant : mésomorphe endomorphe (52,4 %) ; les **bandes numériques (< 3, 3-5, 5,5-7, ≥ 7,5) ne sont pas confirmées** ici ; « 341 adultes, hommes endo-mésomorphes / femmes méso-endomorphes » : **non vérifié** (autre article) | 🟡 / ⬜ | Martínez-Mireles et al., *J. Funct. Morphol. Kinesiol.* 10, 329, 2025 (`jfmk-10-00329.pdf`) |
| **Burley 2015 (notes de cours)** : profil de diffusion normalisé R_d(r) = (e^(−r/d) + e^(−r/(3d))) / (8π d r), intégrale égale à 1 ; la couleur voulue s'obtient en **multipliant par la couleur de base** (pas d'inversion d'albédo) ; d est exposé à l'artiste comme `scatterDistance` en **rouge, vert, bleu** ; à 0, retour au BRDF diffus | ✅ (le paramètre « couleur apparente A » appartient à la version 2016, non relue) | `s2015_pbs_disney_bsdf_notes.pdf` |

Points qui restent **non vérifiés** : Weyrich 2006 (chiffres), Jimenez 2015 (conditions du 0,5 ms), Donner-Jensen 2006 (4ᵉ paramètre), bandes Heath-Carter, étude des 341 adultes, erreurs de régression d'articulations, PSD/DQS dans Kavan, ARKit/FACS, 15 variables d'ANSUR.

## 5. Erreur de lien corrigée (2026-11-21)

Les PDF téléchargés par l'utilisateur ne correspondaient pas toujours aux liens que j'avais donnés : **mon erreur**, due à des résumés de recherche web mal rapprochés.
- **Heath-Carter « 341 adultes » (185 hommes, 156 femmes, 18-40 ans)** : c'est **Campa et al., *Frontiers in Physiology* 16, 2025** ([PMC12679298](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12679298/), [PDF Frontiers](https://public-pages-files-2025.frontiersin.org/journals/physiology/articles/10.3389/fphys.2025.1722899/pdf)), **pas** PMC12452521. Le PDF reçu (`jfmk-10-00329.pdf`) est une autre étude (889 athlètes mexicains). L'identité exacte de PMC12452521 n'a pas pu être confirmée.
- **PMC9543134** = « Facial skin ageing: Key concepts and overview of processes » (*Int J Cosmet Sci* 2022) : identité **confirmée**, correspond à `ICS-44-414.pdf`.
- **PMC6540032, PMC4463032, PMC4890358** : identités non confirmées par recherche ; les contenus lus (`ijms-20-02126.pdf`, `JBO-020-066005.pdf`, `JBO-021-057001.pdf`) sont cohérents avec les sujets attendus, sans preuve que ce sont ces identifiants.
- **Liens fiables pour les PDF manquants** (non téléchargés par moi) : Weyrich 2006 [Harvard](https://vcg.seas.harvard.edu/content/3-publications/20060730-analysis-of-human-faces-using-a-measurement-based-skin-reflectance-model/Weyrich_Analysis.pdf) ou [MIT](https://cdfg.csail.mit.edu/pdf/journal/2006-weyrich-analysis-of-human-faces-using-a-measurement-based-skin.pdf) ; Jimenez 2015 [TU Wien](https://cg.tuwien.ac.at/research/publications/2015/Jimenez_SSS_2015) ou [Zaragoza](https://graphics.unizar.es/papers/Separable-Subsurface-Scattering.pdf) ; Donner & Jensen 2006 [page projet](https://graphics.ucsd.edu/~henrik/papers/skin_bssrdf/) (skin_bssrdf.pdf, ≈ 13 Mo).

## 6. Mise à jour : Weyrich 2006 et Jimenez 2015 lus en local

| Donnée | Verdict | Source |
|---|---|---|
| **Weyrich 2006** : 149 sujets (**114 hommes / 35 femmes**), échantillon **jeune** (20 ans ou moins : 61 H / 18 F ; 30 ans : 37/10 ; 40 ans : 10/2 ; 50 ans ou plus : 6/5) ; types de Fitzpatrick II à VI (types I et II regroupés) | ✅ | `2006-weyrich-…skin.pdf` |
| **Weyrich** : les sujets de type V-VI ont une **absorption plus forte et une diffusion plus faible** que les types II-III ; **pas de corrélation avec l'âge** pour ces coefficients ; analyse canonique des paramètres Torrance-Sparrow : corrélations directes **0,766 (type de peau), 0,573 (genre), 0,537 (âge)** ; **le type de peau est le seul prédicteur fiable** des paramètres de BRDF ; les statistiques par genre/âge/type sont publiées | ✅ | idem |
| **Conséquence** : mon affirmation « paramètres variant avec l'âge » est **à nuancer** : l'effet de l'âge est faible (0,537) et l'échantillon est jeune et à 77 % masculin ; on ne peut pas s'en servir comme loi d'âge de la peau | ✅ nuance | idem |
| **Jimenez 2015** : **0,489 ms par image sur une AMD Radeon HD 7970 en 1080p** (post-traitement) ; jusqu'à douze convolutions 1D pour la somme de gaussiennes ; deux pour le noyau séparable | ✅ | `Separable-Subsurface-Scattering.pdf` |

Toujours **non reçus** : Campa et al. 2025 (étude des 341 adultes) et Donner & Jensen 2006 (4ᵉ paramètre). Toujours non vérifiés par ailleurs : erreurs chiffrées de régression d'articulations, PSD/DQS dans Kavan, ARKit/FACS, 15 variables d'ANSUR, bandes numériques Heath-Carter.

## 7. Mise à jour : Donner & Jensen 2006 et Campa et al. 2025 lus en local

| Donnée | Verdict | Source |
|---|---|---|
| **Donner & Jensen 2006** : modèle à **4 paramètres** : fraction d'hémoglobine (≈ 0,001–0,1), fraction de mélanine (jusqu'à 50 % dans leur figure d'exemple), **mélange de types de mélanine** eumélanine/phéomélanine (0–1), **oiliness** (0–1) ; épiderme **0,25 mm** fixe ; indice de réfraction **1,4** constant ; diffusion réduite diminuée de 50 % dans le derme ; derme semi-infini ; surface huileuse en Torrance-Sparrow. Le 4ᵉ paramètre manquant est donc **le mélange de types de mélanine**. (Le tableau 1 est mal extrait par `pdftotext` : les plages exactes sont à relire visuellement.) | ✅ (plages ⚠) | `skin_bssrdf.pdf` |
| **Campa et al. 2025** : **185 hommes et 156 femmes** (341 adultes, 18-40 ans), somatotype par la méthode Heath-Carter en **13 catégories** ; différences de sexe significatives (p < 0,001) ; **forte variabilité intra-catégorie** ; la catégorie dominante du groupe « masse maigre élevée » des hommes est mésomorphe endomorphe (67,5 %) | ✅ | `fphys-16-1722899.pdf` |
| **Bandes numériques Heath-Carter** (< 3, 3-5, 5,5-7, ≥ 7,5) | ⬜ **non retrouvées** dans ces textes ; à ne pas citer comme fait | — |

Reste **non vérifié** : bandes Heath-Carter, erreurs chiffrées de régression d'articulations, gonflement du DQS et PSD dans Kavan, « ARKit n'est pas FACS », les 15 variables d'ANSUR, identités de PMC6540032/4463032/4890358/12452521. Rien de tout cela ne bloque une décision d'architecture.
