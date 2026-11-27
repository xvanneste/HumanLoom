# Anatomie et biomécanique des articulations — référence pour juger les déformations du rig

Document de référence pour HumanLoom (rig humain .L/.R, maillage de corps unique). Il sert à **juger si une déformation est anatomiquement plausible**. Ce n'est pas un document clinique, et rien ici n'est une calibration validée du rig.

## Mode d'emploi et niveau de preuve

- Chaque chiffre renvoie à une source `[Sx]` listée en fin de document (titre, auteurs, année, URL). Les passages sont reformulés, pas recopiés.
- **« vérifié (résumé) »** : chiffre lu dans le résumé PubMed/PMC de la source. **« vérifié (texte) »** : lu dans le texte intégral. **« rapporté par [Sy] »** : chiffre d'une source primaire que je n'ai pas lue, mais que cite une source lue. **« non vérifié »** : valeur courante dans les manuels mais que je n'ai pas pu confirmer à la page. Ne s'appuyer dessus qu'après contrôle.
- Les amplitudes dépendent beaucoup de la méthode (goniomètre, capteurs cutanés, broches osseuses, scanner), de la posture (debout ou couché), de l'âge, du sexe et de la convention de zéro. Une amplitude « normale » est une plage, pas une cible unique.
- Conventions d'axes : pour l'épaule, le coude, le poignet et la main, les recommandations ISB sont celles de Wu et al. 2005 [S1]. Pour la cheville, la hanche et le rachis, ce sont celles de Wu et al. 2002 [S2]. Seules les métadonnées et le résumé de [S1] ont été lus. Les séquences d'Euler citées plus bas sont confirmées par [S8], qui les applique.
- Les descriptions de **surface** (volumes musculaires, plis) sont qualitatives. Je n'ai trouvé aucune source chiffrée sur la forme de la peau par phase de mouvement. Ces passages sont marqués « qualitatif » : ils reposent sur l'anatomie descriptive et restent à valider sur des références photographiques ou des scans.

---

## 1. Complexe de l'épaule (priorité)

### 1.1 Les quatre articulations

| Articulation | Type | DDL utiles au rig | Rôle dans l'élévation du bras |
|---|---|---|---|
| Gléno-humérale (GH) | Sphéroïde (synoviale, « rotule ») | 3 rotations (plan d'élévation, élévation, rotation axiale) + petites translations | Fournit la plus grande part de l'élévation |
| Sterno-claviculaire (SC) | Synoviale en selle, fonctionnellement à 3 DDL [S10] | Élévation/abaissement, protraction/rétraction, **rotation axiale** de la clavicule | Porte la clavicule, donc l'omoplate |
| Acromio-claviculaire (AC) | Synoviale plane | Rotations de l'omoplate par rapport à la clavicule : sonnette (upward rotation), bascule postérieure (tilt), rotation interne/externe | Oriente l'omoplate sur la clavicule |
| Scapulo-thoracique (ST) | « Pseudo-articulation » de glissement | Résultat des mouvements SC et AC | Ce que l'on voit dans le dos |

Point clé [S6, S7] : les « translations » de l'omoplate décrites en clinique (élévation/abaissement, abduction/adduction) ne sont pas des mouvements indépendants. Elles découlent des mouvements de la clavicule à la SC. L'élévation ST vient de l'élévation SC, l'abduction/adduction ST de la protraction/rétraction SC (vérifié, texte [S7]).

### 1.2 Conventions ISB (Wu et al. 2005)

- Omoplate par rapport au thorax : séquence **Y, X', Z''** = rotation interne/externe, sonnette (upward/downward rotation), bascule antérieure/postérieure. Humérus par rapport au thorax : **Y, X', Y''** = plan d'élévation, angle d'élévation, rotation axiale. Ces deux séquences sont appliquées et attribuées à [S1] par [S8] (vérifié, texte [S8]).
- Clavicule par rapport au thorax : en pratique, rétraction/protraction, élévation, puis rotation axiale (postérieure/antérieure), comme dans [S5]. **Ordre exact de la séquence ISB pour la clavicule : non vérifié** dans le texte de [S1].
- [S8] rappelle que les positions proches d'une singularité (gimbal lock) d'une séquence d'Euler, à moins d'environ 20°, deviennent très sensibles aux erreurs (vérifié, texte).
- Pour la séquence Y-X'-Y'' de l'humérus, la singularité se trouve à élévation nulle (bras le long du corps), où le premier et le troisième axe coïncident. C'est une propriété mathématique de la séquence, pas un chiffre publié. Conséquence pour le rig : ne pas piloter des correctifs par le « plan d'élévation » quand le bras est près du corps.

### 1.3 Amplitudes globales (humérus par rapport au thorax)

| Mouvement | Valeur | Source / statut |
|---|---|---|
| Flexion | 180° | Table « AAOS » reproduite dans [S12] (vérifié, texte) |
| Extension | 60° | [S12] |
| Abduction | 180° | [S12] |
| Adduction | 40° | [S12] ; valeur ajoutée par les auteurs, absente de l'AAOS |
| Flexion active mesurée, 20–44 ans | F 172,0° (IC 95 % 170,9–173,1), H 168,8° (167,3–170,3) | Soucie et al. [S11] (vérifié, page CDC) |
| Flexion active, 45–69 ans | F 168,1°, H 164,0° | [S11] |
| Flexion active, population générale ≥ 20 ans (inclinomètre) | H 161,5°, F 158,5° (bras droit) | Gill et al. 2020 [S13] (vérifié, résumé) |
| Abduction active, idem | H 151,5°, F 149,7° | [S13] |
| Rotation externe / interne (bras le long du corps ou à 90° d'abduction) | Valeurs « manuel » courantes : RE ≈ 90°, RI ≈ 70° | **non vérifié** (absent de la table [S12]) ; [S13] et [S14] montrent une baisse avec l'âge et une RE moyenne < 90° chez des sujets sans douleur |

Avec l'âge, la flexion baisse d'environ 40° entre les plus jeunes et les plus âgés de [S13] (−43° chez l'homme, −40,6° chez la femme) (vérifié, résumé). [S14] (6 635 sujets, capture sans marqueurs) trouve aussi une baisse avec l'âge, une RE plus grande d'environ 5° du côté droit et une RI plus grande d'environ 5° du côté gauche (vérifié, résumé ; valeurs absolues en annexe, non lues).

### 1.4 Rythme scapulo-huméral : ratios publiés

| Source | Méthode | Ratio GH : ST | Remarques |
|---|---|---|---|
| Inman, Saunders & Abbott 1944 [S3] | Radiographies 2D | 2:1 global | Rapporté par [S4]. Pour 180° d'élévation, 2:1 donne 120° GH + 60° ST (simple arithmétique). La base de sujets est mince selon une revue (non lue). |
| McClure et al. 2001 [S4] | Broches osseuses dans l'épine de l'omoplate, capteurs électromagnétiques, 8 sujets | **1,7:1** dans le plan de l'omoplate, **2,0:1** en flexion ; 1,9 et 2,3 si l'on suppose un départ à 0° | Vérifié, texte. Les ratios publiés vont de 1,25:1 à 3,2:1 selon les études citées par [S4]. |
| Scibek & Carcia 2012 [S9] | Inclinomètre, 13 sujets, plan de l'omoplate | 2,34:1 global, de **40:1 à 0,9:1** selon la tranche | Vérifié, résumé. L'omoplate fournit 2,5 % du mouvement de 0 à 30°, 21 à 38 % de 30 à 90°, 53 % de 90 à 120°. |

**Conclusion pour le rig : le rythme n'est pas linéaire.** L'omoplate bouge très peu pendant les 30 premiers degrés d'élévation humérothoracique. En fin d'élévation, la vitesse de sonnette augmente par rapport au milieu de course. Un ajustement polynomial d'ordre 3 colle mieux qu'une droite (R² = 0,999 contre 0,957) (vérifié, texte [S4]). La descente du bras est plus linéaire (R² = 0,997). L'orientation moyenne de l'omoplate reste à moins de 5° de celle de la montée, avec les plus grands écarts entre 60 et 120° (vérifié, texte [S4]).

### 1.5 Omoplate par rapport au thorax pendant l'élévation (valeurs à broches osseuses)

McClure 2001 [S4], élévation dans le plan de l'omoplate (vérifié, texte) :
- **Sonnette (upward rotation) : 50° (ET 4,8°)**, à peu près linéaire, surtout au-delà de 50° d'élévation ;
- **Bascule postérieure : 30° (ET 13°)**, non linéaire, essentiellement au-delà de 90° d'élévation, avec une forte hausse en fin de course ;
- **Rotation externe : 24° (ET 12,8°)**, non linéaire, essentiellement au-delà de 90° ;
- en flexion : sonnette 46°, bascule postérieure 31°, rotation interne −26° (soit une rotation externe), clavicule −20° de protraction (soit une rétraction) et 9° d'élévation (table de [S4]).

Valeurs d'autres auteurs reprises dans la table de [S4] (excursion totale, méthodes hétérogènes) : sonnette de 32° à 64° ; bascule postérieure de 9° à 40° ; rotation interne ou externe de signe variable selon les études. [S4] attribue ces écarts aux méthodes par palpation.

Synthèse de Ludewig & Reynolds 2009 [S7] (vérifié, texte) : la sonnette est le mouvement ST dominant. La bascule postérieure l'accompagne. La rotation interne ou externe varie beaucoup selon les sujets et le plan d'élévation ; une légère rotation interne peut être normale en début de course, et une petite rotation externe est admise en fin de course. L'extension thoracique normale pendant l'élévation du bras ne dépasse pas environ 10°.

Selon le plan d'élévation [S6] (vérifié, texte) : en flexion, l'omoplate tourne un peu en interne au début ; en abduction frontale, elle tourne en externe dès le début. Les plus grandes différences entre flexion et abduction portent sur le plan d'élévation GH, en moyenne 46° (vérifié, résumé [S5]).

### 1.6 Clavicule (SC) et AC : mouvements couplés et rotation axiale

Mesures in vivo à broches (Ludewig et al. 2009 [S5], 12 sujets ; vérifié, résumé) : pendant l'élévation, la clavicule s'élève, se rétracte et **tourne vers l'arrière autour de son grand axe**. À la SC, c'est la rotation postérieure qui domine, **en moyenne 31°**. À l'AC, c'est la bascule postérieure de l'omoplate qui domine, **en moyenne 19°**. L'omoplate fait aussi une rotation interne et une sonnette par rapport à la clavicule. La GH s'élève et tourne en externe.

Synthèse de Ludewig & Braman 2011 [S6] (vérifié, texte) :
- dans tous les plans sauf l'extension, la rotation postérieure de la clavicule à la SC vaut environ **30°** ;
- la clavicule se rétracte d'environ **15°**, y compris en flexion, un peu moins en flexion et un peu plus en abduction ;
- l'élévation de la clavicule reste **en général sous 10°** chez le sujet sain ;
- à l'AC, l'omoplate fait surtout une sonnette et une bascule postérieure par rapport à la clavicule, puis une rotation interne, même en abduction ;
- au repos, l'omoplate est en moyenne **tournée de 60° en interne par rapport à la clavicule**. Le couplage SC→ST vaut donc environ 2/3 d'un montage à 90° et 1/3 d'un montage parallèle ;
- conséquence chiffrée : **30° de rotation postérieure de la clavicule donnent environ 20° de sonnette ST et 10° de bascule postérieure ST**. 9° d'élévation de la clavicule donnent environ 6° de bascule antérieure et 3° de sonnette ST. 9° de rétraction donnent environ 9° de rotation externe ST ;
- exemple à 120° d'abduction dans le plan de l'omoplate : 20° + 3° de sonnette venant de la clavicule, plus 11° à l'AC, soit **34° de sonnette ST** ; 4° de bascule venant de la clavicule, plus 16° à l'AC, soit **20° de bascule ST** ; 9° de rotation externe venant de la rétraction, moins 6° de rotation interne à l'AC, soit **3° de rotation externe ST** ;
- plus de 50 % de la sonnette ST passe par la rotation postérieure de la clavicule. Cette rotation est probablement produite passivement par la tension des ligaments coraco- et acromio-claviculaires, car aucun muscle claviculaire n'a la bonne ligne d'action.

McClure 2001 [S4] (vérifié, texte ; clavicule non suivie directement par broches) :
- rétraction d'environ 20°, surtout entre 130 et 150° d'élévation. Elle ne commence vraiment qu'après environ 25° (plan de l'omoplate) ou 50° (flexion) ;
- élévation d'environ 10° au total ;
- Inman [S3], rapporté par [S4] : environ 30° d'élévation de la clavicule, surtout avant 90° (méthode jugée peu claire par [S4]), et environ **40° de rotation postérieure**, surtout **après 90°**, donc non linéaire (broche dans la clavicule d'un sujet).

Amplitudes passives et maximales de la SC (source secondaire Kenhub [S10], d'après des manuels non attribués précisément) : élévation/abaissement d'environ 40°, protraction/rétraction d'environ 35°, rotation axiale de 20 à 40° selon la position de la clavicule. **Non vérifié en source primaire.** La valeur de 45° de rotation axiale parfois citée n'a pas été trouvée.

Rotations axiales humérales et omoplate [S4] (vérifié, texte) : bras à 90° d'abduction, la rotation interne ou externe de l'humérus fait peu bouger l'omoplate, **sauf en fin de rotation externe**. L'omoplate fait alors une bascule postérieure, une sonnette et une rotation externe assez brusques, et la clavicule se rétracte. Pendant l'élévation, l'humérus tourne spontanément en externe, plus tôt et davantage dans le plan de l'omoplate qu'en flexion.

### 1.7 Muscles moteurs (pour savoir quoi « gonfler » et où)

Selon [S6] (vérifié, texte) :
- **Trapèze supérieur** : il s'insère sur la clavicule distale. Il élève et rétracte la clavicule, mais n'est pas un vrai moteur de la sonnette ;
- **Trapèze moyen et inférieur** : rotation externe de l'omoplate à l'AC ;
- **Dentelé antérieur et trapèze inférieur** : couple de sonnette.

Rôle du deltoïde, du grand pectoral et du grand dorsal : anatomie descriptive classique (abduction et flexion pour le deltoïde ; flexion, adduction et rotation interne pour le grand pectoral ; extension, adduction et rotation interne pour le grand dorsal). C'est qualitatif. Je n'ai pas lu de source primaire chiffrée, et la description fonctionnelle du grand pectoral vient de pages cliniques (AAOS OrthoInfo, HSS) trouvées par recherche, non lues en détail.

### 1.8 Ce qui change à la surface, phase par phase (qualitatif)

Repères anatomiques confirmés : le **pli axillaire antérieur** est formé par le bord inférieur du grand pectoral, le **pli axillaire postérieur** par le tendon du grand dorsal et le grand rond [S46]. Le pli antérieur est plus haut que le pli postérieur [S46].

| Phase (élévation humérothoracique) | Squelette (chiffres ci-dessus) | Surface attendue (qualitatif, à valider) |
|---|---|---|
| 0–30° | Presque tout se passe à la GH ; l'omoplate bouge peu (2,5 % du mouvement [S9]) ; la clavicule bouge à peine | Le deltoïde moyen se raccourcit et s'épaissit sous l'acromion. L'acromion et le contour de l'omoplate restent quasiment fixes. Le creux axillaire commence à s'ouvrir. Un rig qui fait déjà monter le moignon de l'épaule ici est faux. |
| 30–90° | L'omoplate fournit environ 20 à 40 % du mouvement [S9] ; sonnette à peu près linéaire [S4] ; la rétraction de la clavicule commence après environ 25 à 50° [S4] | L'angle inférieur de l'omoplate glisse vers le côté (sonnette) et devient visible sous la peau du flanc. Le deltoïde forme une masse arrondie avec un sillon à l'arrière de l'acromion (non vérifié). Les plis axillaires se tendent, le grand pectoral et le grand dorsal s'étirent. |
| 90–180° | L'omoplate pèse plus (53 % entre 90 et 120° [S9]) ; la bascule postérieure et la rotation externe de l'omoplate surviennent surtout ici [S4] ; la rotation postérieure de la clavicule surtout après 90° (Inman, via [S4]) ; la rétraction surtout entre 130 et 150° [S4] | Le bord supérieur du trapèze se raccourcit et se rapproche du cou, car la clavicule s'élève et se rétracte. Une dépression peut apparaître au-dessus de l'acromion, entre deltoïde et trapèze (non vérifié). Le creux axillaire est largement ouvert et les plis forment un « pont » tendu vers le bras. Le grand pectoral semble s'aligner avec le bras (non vérifié). Le grand dorsal s'étire sur le flanc. L'humérus est en rotation externe, ce qui déplace le relief du biceps et du deltoïde antérieur. |

Torsion du tendon du grand pectoral : une source anatomique décrit un tendon en trois couches qui tournent de 90° les unes sur les autres. D'autres auteurs contestent ce point (repéré par recherche, PMC6378447/PMC3666500, articles non lus en entier). **L'idée que ces fibres se « détordent » au-dessus de la tête : non vérifié.**

### 1.9 Erreurs typiques de rig et de skinning (épaule)

- **Toute l'élévation mise à la GH** (pas d'omoplate ni de clavicule motorisées) : au-delà d'environ 90 à 120°, le deltoïde passe à travers l'acromion, le moignon de l'épaule ne monte pas et l'aisselle s'écrase. Anatomiquement, environ un tiers de l'élévation vient de l'omoplate (ratio de 1,7:1 à 2,3:1 [S4, S9]), et le couplage est non linéaire.
- **Omoplate qui suit le bras dès 0°** (ratio linéaire constant) : le moignon monte trop tôt. Les données montrent presque aucun mouvement de l'omoplate avant 30° [S4, S9].
- **Clavicule qui s'élève beaucoup** (« haussement ») au lieu de tourner vers l'arrière et de se rétracter : chez le sujet sain, l'élévation de la clavicule reste sous environ 10° [S6] (Inman donne environ 30° [S3 via S4]). Une élévation exagérée de la clavicule est justement un signe des épaules symptomatiques [S7].
- **Rotation axiale de la clavicule absente** : c'est le mouvement SC principal (environ 30° [S5, S6]). Sans lui, la bascule postérieure et la sonnette de l'omoplate doivent être « inventées » ailleurs.
- **Effondrement de l'épaule en Linear Blend Skinning** : Lewis et al. [S43] décrivent l'épaule comme une zone particulièrement difficile pour le skinning squelettique, à cause de sa grande amplitude de rotation (vérifié, texte : figure 8b). Les correctifs y doivent être pilotés par au moins deux dimensions de pose [S43].
- **Rotation axiale humérale perdue** : en élévation, l'humérus tourne naturellement en externe [S4, S5]. Un rig qui garde la rotation axiale à 0 pendant l'abduction frontale produit une torsion anormale du deltoïde et du biceps.

---

## 2. Rachis, tête et cou

### 2.1 Rachis cervical et tête

- **Type** : occiput–C1 (atlanto-occipitale) = condyles ; C1–C2 (atlanto-axoïdienne) = pivot (dent de C2) avec articulations latérales ; C2–C7 = disques et articulations zygapophysaires.
- **Amplitudes globales (table « AAOS » de [S12])** : flexion 45°, extension 45°, rotation 60°, inclinaison latérale 45°.
- **Normes actives** : [S31] (400 sujets de 20 à 60 ans, dispositif CROM) montre une baisse après 50 ans et aucun effet du sexe (vérifié, résumé ; valeurs non lues).
- **Rotation, part de C1–C2** :
  - Kang et al. 2019 [S32], scanner 3D, rotation maximale active couché (vérifié, texte) : rotation cervicale totale **69,7 ± 5,5°** d'un côté, dont **44,0 ± 8,0°** pour l'étage supérieur (Oc–C2, 63 %). C1–C2 seul fait **37,9 ± 5,1°**, soit 54 % du total. Oc–C1 ne fait que 3,9 ± 3,0° ; d'autres études in vivo trouvent de 1,7 à 2,5°.
  - Revue systématique de Lindenmann et al. 2022 [S33] (vérifié, texte) : C1–C2 assure **63 à 73 %** de la rotation axiale ; selon les études, C1–C2 va de 38,5° à 65,8°. Les segments C3–C4 à C5–C6 font chacun 5 à 11 % de la rotation. La flexion-extension se répartit entre l'étage atlanto-axoïdien et les étages inférieurs, alors que l'inclinaison latérale vient surtout des étages inférieurs (C2–C7).
- **Couplages** [S32] (vérifié, texte) : quand la tête tourne, l'étage supérieur s'incline latéralement du côté **opposé**, l'étage inférieur du **même** côté. Oc–C5 se couple avec une extension.
- **Surface (qualitatif)** : le sterno-cléido-mastoïdien du côté opposé à la rotation fait saillie en corde. Des plis apparaissent sur le côté du cou en rotation et en inclinaison. Le trapèze supérieur reste relativement passif en rotation pure (non vérifié).
- **Erreurs de rig typiques** : faire tourner la tête à la base du cou (C7) au lieu de C1–C2. Le cou « vrille » alors comme un tube, et la mâchoire et le menton passent à travers les clavicules. Mettre toute la flexion dans un seul os de cou donne une cassure angulaire au lieu d'une courbe.

### 2.2 Rachis thoracique

- **Rotation** (Fujimori et al. 2012 [S35], scanner 3D in vivo, rotation maximale du tronc ; vérifié, résumé) : T1 par rapport à L1 = **24,9 ± 4,9°** d'un côté. Par segment, de **0,5° (T12–L1) à 2,7° (T9–T10)**. La rotation est plus grande au milieu (T6–T11) qu'en haut et en bas. Le couplage avec l'inclinaison va dans le même sens en haut et est variable plus bas.
- **Flexion, extension et inclinaison thoraciques** : **non vérifié** (aucune valeur primaire lue). La cage thoracique limite ces mouvements.
- **Erreur de rig** : concentrer la torsion du tronc dans la région lombaire. Anatomiquement, c'est l'inverse (voir 2.3) : le rachis lombaire tourne peu.

### 2.3 Rachis lombaire

- Pearcy [S36], radiographie biplane, jeunes hommes (vérifié, résumés) :
  - flexion + extension d'environ **14° par étage**, L4–L5 un peu plus mobile ;
  - environ **2° de rotation axiale par étage** ;
  - inclinaison latérale d'environ **10°** aux trois étages supérieurs, 6° à L4–L5, 3° à L5–S1 ;
  - couplage aux trois étages supérieurs : une rotation axiale à droite s'accompagne d'une inclinaison à gauche ; à L5–S1, les deux vont dans le même sens. Il n'existe pas de couplage mécanique simple.
- Troke et al. 2005 [S37], 405 sujets de 16 à 90 ans (vérifié, résumé) : flexion de 73° (jeunes) à 40° (âgés) ; inclinaison latérale de 28° à 14° de chaque côté ; extension de 29° à 6°. Rotation axiale médiane de **7° de chaque côté**, stable avec l'âge.
- **Surface (qualitatif)** : en extension, les plis transverses lombaires se creusent et les muscles érecteurs du rachis forment deux bourrelets. En flexion, la peau s'étire et les épineuses deviennent visibles.
- **Erreur de rig** : flexion du tronc portée par un seul os (cassure) ; rotation lombaire exagérée.

---

## 3. Coude et avant-bras

- **Type** : huméro-ulnaire (trochléenne, charnière) + huméro-radiale + radio-ulnaires proximale et distale (pivot) → 2 DDL fonctionnels : flexion-extension et prono-supination.
- **Amplitudes** :
  - AAOS [S12] : flexion 150°, extension 0° ;
  - Soucie [S11], 20–44 ans : flexion F 150,0°, H 144,6° ; extension F 4,7°, H 0,8° (valeur positive = hyperextension probable, **signe à vérifier** dans l'article) ; pronation F 82,0°, H 76,9° ; supination F 90,6°, H 85,0° ;
  - arc fonctionnel (Morrey et al. 1981 [S15], vérifié, résumé) : **30–130° de flexion et 50° de pronation / 50° de supination** suffisent à la plupart des activités quotidiennes. Toucher l'occiput demande environ 140°, nouer ses lacets environ 15°.
- **Valgus physiologique (angle de port)** (Paraskevas et al. 2004 [S16], 600 sujets, vérifié, résumé) : **12,9 ± 5,9°** en extension complète ; H 11,0 ± 4,3°, F 15,1 ± 5,0°. Il est plus grand du côté dominant. L'idée qu'il diminue en flexion est classique mais **non vérifiée** ici.
- **Axe de prono-supination** (Tay et al. 2010 [S17], in vivo, vérifié, résumé) : axe hélicoïdal allant de la tête radiale à la région **dorsale** de la tête ulnaire. Il est **variable** selon la position. Le radius tourne autour de l'ulna, et la main suit le radius.
- **Surface (qualitatif)** : en flexion, le biceps se raccourcit, se ramasse et monte. Un pli se forme au pli du coude, et l'olécrane devient saillant à l'arrière. En pronation, les muscles de l'avant-bras (brachio-radial et épicondyliens) s'enroulent : la torsion de la peau est progressive le long de l'avant-bras, la plus forte au poignet (non vérifié).
- **Erreurs de rig typiques** :
  - **« Coude qui s'effondre »** (perte de volume au pli) : défaut caractéristique du skinning squelettique linéaire (SSD/LBS) [S43] (vérifié, texte, figures 1 et 2) ; cité aussi par [S45] ;
  - **Effet « papillote » (candy-wrapper)** quand la prono-supination est portée par le poignet seul. [S43] montre l'avant-bras qui s'effondre quand la torsion approche 180° (vérifié, texte, figure 3). [S45] cite les « candy wrapper twists ». Le skinning par quaternions duaux (DQS) évite cet effondrement [S44], mais produit un gonflement de l'articulation [S45] et, au-delà de 180°, un « retournement » (il prend toujours le chemin le plus court ; page projet de [S44], vérifié par recherche) ;
  - **Absence de valgus** : avant-bras dans l'axe du bras alors qu'il devrait être écarté de 10 à 15°.

---

## 4. Poignet

- **Type** : radio-carpienne (condylienne) + médio-carpienne → 2 DDL principaux (flexion-extension, inclinaison radiale/ulnaire). Palmer [S18] décrit 3 DDL en incluant une composante de rotation (vérifié, résumé).
- **Amplitudes** : AAOS [S12] : extension 70°, flexion 80°. Inclinaison radiale et ulnaire : valeurs manuel courantes de 20° et 30°, **non vérifiées** (absentes de [S12]).
- **Amplitude fonctionnelle** :
  - Palmer 1985 [S18] (vérifié, résumé) : 5° de flexion, 30° d'extension, 10° d'inclinaison radiale, 15° d'inclinaison ulnaire ;
  - Ryu 1991 [S19] (vérifié, résumé) : l'ensemble des tâches demande 60° d'extension, 54° de flexion, 40° d'inclinaison ulnaire et 17° d'inclinaison radiale. La majorité tient dans 40° de flexion, 40° d'extension et 40° d'inclinaison combinée.
- **Couplage** : le mouvement « du lanceur de fléchettes » (extension + inclinaison radiale vers flexion + inclinaison ulnaire) est classique. **Non vérifié** ici.
- **Surface (qualitatif)** : en flexion, plis palmaires transverses ; en extension, plis dorsaux. Les tendons des fléchisseurs deviennent saillants en flexion contrariée.
- **Erreurs de rig** : poignet porteur de la prono-supination (voir 3), pivot placé au milieu de la main au lieu du carpe proximal.

---

## 5. Doigts et pouce

- **Types** : MCP (métacarpo-phalangiennes) = condyliennes, 2 DDL (flexion-extension, abduction-adduction) ; IPP et IPD = charnières, 1 DDL ; trapézo-métacarpienne du pouce (CMC1) = en selle, 2 DDL plus une rotation couplée (opposition).
- **Amplitudes** (table [S12], valeurs des doigts tirées de Richard & Parry, médiane de l'index droit) :
  - MCP flexion 80°, IPP 90°, IPD 65° ;
  - pouce : MCP flexion 50°, IP flexion 80° ;
  - CMC1 : abduction palmaire 60° et radiale 60°. Ces valeurs ont été ajoutées par les auteurs de [S12] (non AAOS) ; leur source primaire est **non vérifiée**.
- **Amplitude fonctionnelle** :
  - Hume et al. 1990 [S20] (vérifié, résumé) : postures fonctionnelles moyennes de 61° (MCP), 60° (IPP) et 39° (IPD) ; pouce 21° (MCP) et 18° (IP) ;
  - Bain et al. 2015 [S21] (vérifié, résumé) : 19–71° (MCP), 23–87° (IPP), 10–64° (IPD), soit 48 à 60 % de l'amplitude active. Les doigts ulnaires ont une amplitude plus grande.
- **Pouce** : Crisco et al. 2025 [S22] (vérifié, texte) montrent que le mouvement du « pouce » (premier métacarpien par rapport au radius) **n'est pas** celui de la CMC1. À 20° de rotation du pouce, la CMC1 tourne de 3 à 30° selon les cas ; en moyenne, la mesure du pouce surestime la CMC1 d'environ 10°. Pour le rig, le pivot de base du pouce doit inclure le scaphoïde et le trapèze, pas seulement la CMC1.
- **Couplage** : la flexion de l'IPD est couplée à celle de l'IPP (tendon commun). Le rapport classique « IPD ≈ 2/3 IPP » est **non vérifié**.
- **Surface (qualitatif)** : plis cutanés palmaires fixes (plis de flexion) et plis dorsaux qui se tendent sur les articulations. L'éminence thénar se gonfle en opposition.
- **Erreurs de rig** : perte de volume au dos des articulations (jointures « pincées », défaut LBS de même nature que le coude [S43]) ; pouce qui tourne autour d'un pivot unique trop distal ; doigts qui s'écartent sans rotation axiale associée.

---

## 6. Hanche

- **Type** : sphéroïde (coxo-fémorale), 3 DDL.
- **Amplitudes** :
  - AAOS [S12] : flexion 120°, extension 20°, abduction 40°, adduction 20° ;
  - Soucie [S11], 20–44 ans : flexion F 133,8°, H 130,4° ; extension F 18,1°, H 17,4° ;
  - rotations (Kouyoumdjian et al. 2012 [S23], 120 adultes, vérifié, résumé) : couché sur le dos, RE 38,5° et RI 29,6° ; couché sur le ventre, RE 41,8° et RI 35,2° ; assis, RI 37,9°. Le résumé donne aussi « RE = 78,5° » assis, valeur identique au total de l'arc (78,5°) : **coquille probable du résumé, non vérifiée**. Les rotations baissent avec l'âge et le surpoids, et sont plus faibles d'environ 4,7° chez l'homme ;
  - d'après les données NHANES I, Roach & Miles 1991 [S24] trouvent des valeurs normales qui s'écartent des manuels jusqu'à 18° et une baisse modeste avec l'âge, sauf pour l'extension (vérifié, résumé ; valeurs non lues).
- **Couplages** : la rétroversion du bassin accompagne la flexion de hanche en fin de course (rythme lombo-pelvien), sans chiffre vérifié ici (**non vérifié**).
- **Surface (qualitatif)** : en flexion, pli de l'aine profond et fesse étirée. Le grand fessier s'aplatit et se tend ; en extension, il se contracte et se ramasse. En abduction, les adducteurs forment une corde à l'intérieur de la cuisse.
- **Erreurs de rig** : pli de l'aine qui s'effondre ou traverse le ventre en flexion profonde ; fesse qui « suit » la cuisse comme un bloc rigide ; pivot de hanche placé trop haut ou trop en dehors (le centre de la tête fémorale est profond, sous le milieu du pli de l'aine — repère anatomique, non chiffré ici).

---

## 7. Genou (dont rotation tibiale couplée)

- **Type** : bicondylien (fémoro-tibiale) + fémoro-patellaire. Ce n'est **pas** une charnière pure : flexion-extension, plus rotation axiale et translations couplées.
- **Amplitudes** :
  - AAOS [S12] : flexion 135°, extension 0° ;
  - Soucie [S11], 20–44 ans : flexion F 141,9°, H 137,7° ; extension (hyperextension probable) F 1,6°, H 1,0°.
- **Rotation tibiale couplée à la flexion** :
  - Freeman & Pinskerova 2005 [S26] (vérifié, résumé) : de 0 à 120°, le condyle médial ne bouge presque pas d'avant en arrière, tandis que le condyle latéral recule. Il en résulte une **rotation interne du tibia autour d'un axe médial**. Au-delà de 120°, les deux condyles reculent sur la corne postérieure des ménisques et l'articulation se subluxe ;
  - Johal et al. 2005 [S27], IRM interventionnelle, genoux en charge (vérifié, résumé) : le condyle latéral recule de 22 mm jusqu'à 120°, puis de 10 mm de plus jusqu'à l'accroupissement. Le fémur tourne de **20° en externe** (soit le tibia en interne) entre l'hyperextension et 120°. La rotation est plus grande et plus précoce en charge ;
  - « screw-home » (Kim et al. 2015 [S28], marche, vérifié, résumé) : environ **17°** de rotation de verrouillage en fin d'oscillation et en pré-oscillation. Au début de l'appui, une rotation « paradoxale » d'environ 6° (tibia en rotation externe pendant que le genou commence à fléchir) a aussi été observée.
- **Rotation axiale volontaire, genou fléchi** (Mossberg & Smith 1983 [S29], 85 femmes, vérifié, résumé) : rotation totale de **35°, 40° et 44°** à 70°, 90° et 110° de flexion. La rotation externe vaut environ **le double** de la rotation interne. Genou tendu, la rotation est quasi nulle (verrouillage ; affirmation classique, **non vérifiée** en chiffres).
- **Surface (qualitatif)** : en flexion, la rotule s'enfonce dans la trochlée et le relief antérieur s'aplatit puis s'arrondit. Le creux poplité se ferme en pli, et les tendons des ischio-jambiers forment deux cordes de part et d'autre. Les mollets et la cuisse s'écrasent l'un contre l'autre en flexion profonde.
- **Erreurs de rig** :
  - genou en charnière pure (tibia sans rotation interne en flexion) ;
  - effondrement du creux poplité en LBS, analogue au coude [S43, S45] ;
  - rotule absente du rig (sans os ni correctif) : la face antérieure se plie comme du carton ;
  - en flexion profonde (> 120°), pas de prise en compte du contact mollet–cuisse.

---

## 8. Cheville et pied

- **Types** : talo-crurale (tibio-tarsienne) = charnière à axe oblique ; sous-talienne = axe oblique, inversion-éversion ; médio-tarsienne (Chopart), tarso-métatarsiennes ; MTP = condyliennes ; IP des orteils = charnières.
- **Axes** (Brockett & Chapman 2016 [S30], vérifié, texte) : l'axe sous-talien est incliné d'environ **40°** sur l'horizontale dans le plan sagittal et d'environ **23°** sur l'axe du pied dans le plan transverse. Les axes de la talo-crurale peuvent différer jusqu'à 30° dans le plan frontal selon les études.
- **Amplitudes** :
  - [S30] : arc sagittal total de **65 à 75°**, de 10–20° de flexion dorsale à 40–55° de flexion plantaire ; arc frontal d'environ **35°** (23° d'inversion, 12° d'éversion). La marche demande au maximum 30° sagittal ; monter et descendre un escalier, 37° et 56° ; la sous-talienne fait environ 15° d'inversion-éversion à la marche ;
  - AAOS [S12] : flexion plantaire 50°, flexion dorsale 20° ; MTP des orteils : extension 70°, flexion 45° ;
  - Soucie [S11], 20–44 ans : flexion dorsale F 13,8°, H 12,7° ; flexion plantaire F 62,1°, H 54,6°.
- **Couplage** : la plus grande partie de la flexion plantaire et dorsale se fait à la talo-crurale, avec quelques degrés à la sous-talienne [S30]. La pronation et la supination du pied combinent plusieurs articulations (description classique, **non vérifiée** en chiffres).
- **Surface (qualitatif)** : en flexion plantaire, le tendon d'Achille se détend, des plis apparaissent derrière la cheville et le triceps sural se ramasse. En flexion dorsale, pli antérieur au cou-de-pied et tendons extenseurs saillants. En extension des orteils, l'aponévrose plantaire se tend (mécanisme du treuil).
- **Erreurs de rig** : pivot de cheville placé sous la malléole au lieu de passer entre les malléoles ; inversion-éversion faite à la cheville au lieu de la sous-talienne ; pied « planche » sans articulation des orteils (MTP) pour la propulsion.

---

## 9. Mâchoire (articulation temporo-mandibulaire, ATM)

- **Type** : bicondylienne, double. Un compartiment inférieur (rotation) et un compartiment supérieur (translation du condyle sur l'éminence) séparés par le disque. Les deux ATM sont **mécaniquement liées** par la mandibule.
- **Amplitudes (distances incisives)** :
  - ouverture maximale moyenne de 43 mm (H) et 41 mm (F), en baisse avec l'âge (Gallagher et al. 2004 [S38], 1 513 adultes, vérifié, résumé) ;
  - Campillo et al. 2017 [S39], 40 jeunes adultes à occlusion idéale (vérifié, résumé) : ouverture maximale 37,4 mm, latéralité 7,5 mm, propulsion 8,4 mm.
- **Cinématique** (Chen et al. 2021 [S40], fluoroscopie 3D, vérifié, résumé) : la **rotation** de la mandibule explique **91 %** de l'ouverture maximale et 73 % du déplacement latéral de l'incisive. La **translation** du condyle explique **99 %** de la propulsion. La trajectoire de l'incisive est presque verticale pendant les premiers 60 % de l'ouverture. La translation est surtout antéro-postérieure.
- La règle « rotation pure jusqu'à 20–25 mm, puis translation » des manuels est **non vérifiée**. [S40] suggère plutôt que la rotation domine tout le long et que la translation sert surtout à la propulsion.
- **Surface (qualitatif)** : à l'ouverture, le menton descend et recule. Une dépression se forme devant le tragus quand le condyle avance. Le masséter s'étire et s'aplatit, et la peau sous le menton se tend ou se plisse selon la morphologie.
- **Erreurs de rig** : mâchoire en charnière pure centrée sur l'oreille (pas d'avancée du condyle, donc la propulsion est impossible) ; pivot placé trop bas (la mâchoire « glisse » vers l'arrière dans le cou) ; ouverture supérieure à environ 45–50 mm sur un adulte moyen sans intention stylistique.

---

## 10. Cage thoracique

- **Types** : costo-vertébrales (tête et tubercule de la côte) et sterno-costales. Chaque côte tourne autour d'un axe passant près du rachis.
- **Cinématique respiratoire** (Wilson et al. 1987 [S41], scanner, 2 sujets couchés, de la capacité résiduelle fonctionnelle à la capacité pulmonaire totale ; vérifié, résumé) :
  - côte 3 : composante en **« bras de pompe »** (élévation antérieure du sternum) de **11°** et en **« anse de seau »** (élévation latérale) de **13°** ;
  - ces composantes diminuent vers la côte 7 (7° et 10°) ;
  - les axes de rotation font environ 35° avec le plan médian.
- **Couplage** : la position du sternum influe sur le déplacement des côtes (De Troyer & Wilson 1993, chien, résumé lu — hors humain, cité seulement pour le principe).
- **Surface (qualitatif)** : à l'inspiration, le thorax s'élargit (anse de seau, côtes basses) et s'avance (bras de pompe, côtes hautes), le creux épigastrique varie et les espaces intercostaux s'ouvrent sur les sujets minces. L'élévation du bras soulève et ouvre la cage du même côté (non vérifié en chiffres).
- **Erreurs de rig** : thorax rigide qui plie comme un seul segment en flexion ou en inclinaison du tronc ; respiration simulée par une simple mise à l'échelle uniforme (alors que les deux composantes diffèrent selon le niveau).

---

## 11. Bassin

- **Types** : sacro-iliaques (synoviales partiellement fibreuses) + symphyse pubienne (amphiarthrose). Le bassin se comporte comme un **anneau presque rigide**.
- **Amplitudes sacro-iliaques** :
  - Sturesson et al. 1989 [S42], stéréophotogrammétrie, 25 patients (vérifié, résumé) : rotations moyennes de **2,5°** (de 0,8 à 3,9°), surtout autour de l'axe transverse ; translations moyennes de 0,7 mm (de 0,1 à 1,6 mm). Pas de différence entre côté symptomatique et asymptomatique ;
  - études de 2000 sur la position en fente et le test de flexion de hanche debout (même équipe) : mouvements très petits, environ dix fois plus faibles que ceux d'études antérieures (vérifié, résumés).
- **Conséquence** : l'inclinaison antéro-postérieure, l'obliquité et la rotation du bassin pendant la marche ou une posture sont des mouvements du bassin **entier** par rapport aux hanches et au rachis lombaire, pas des déformations internes.
- **Surface (qualitatif)** : les épines iliaques antéro-supérieures et la crête iliaque restent des repères quasi fixes du bassin. Les fossettes lombaires (épines iliaques postéro-supérieures) servent de repères visibles.
- **Erreurs de rig** : pondération du bassin partagée avec la cuisse ou le lombaire, ce qui déforme l'anneau pelvien (crête iliaque qui se plie) ; pivot de racine (« root ») confondu avec le pivot pelvien.

---

## 12. Tableau de synthèse

Valeurs « max » = amplitude active ou passive normale publiée (adulte) ; les amplitudes fonctionnelles sont entre parenthèses. « NV » = non vérifié.

| Articulation | DDL (rig) | Mouvement | Min / max publiés | Source |
|---|---|---|---|---|
| Épaule (humérothoracique) | 3 | Flexion | 158,5–180° (selon population et méthode) | [S12], [S11], [S13] |
| Épaule | | Extension | 60° | [S12] |
| Épaule | | Abduction | 149,7–180° | [S12], [S13] |
| Épaule | | Adduction | 40° (hors AAOS) | [S12] |
| Épaule | | Rotation externe / interne | ≈ 90° / ≈ 70° | NV |
| Scapulo-thoracique | 3 (résultat SC + AC) | Sonnette | 32–64° (50 ± 4,8° à broches, plan de l'omoplate) | [S4] |
| Scapulo-thoracique | | Bascule postérieure | 9–40° (30 ± 13°) | [S4] |
| Scapulo-thoracique | | Rotation externe | 24 ± 12,8° (signe variable selon les études) | [S4] |
| Rythme GH : ST | — | Ratio | 1,25:1 à 3,2:1 (classique 2:1) ; local de 40:1 à 0,9:1 | [S3 via S4], [S4], [S9] |
| Sterno-claviculaire | 3 | Rotation postérieure (élévation du bras) | ≈ 30–31° (Inman ≈ 40°) | [S5], [S6], [S3 via S4] |
| Sterno-claviculaire | | Rétraction (élévation du bras) | ≈ 15–20° | [S6], [S4] |
| Sterno-claviculaire | | Élévation (élévation du bras) | < 10° (Inman ≈ 30°) | [S6], [S4] |
| Sterno-claviculaire | | Amplitudes maximales | élév./abaiss. ≈ 40°, prot./rétr. ≈ 35°, rot. 20–40° | [S10] (secondaire, NV) |
| Acromio-claviculaire | 3 | Bascule postérieure (élévation du bras) | ≈ 19° | [S5] |
| Coude | 1 | Flexion | 144,6–150° (fonctionnel 30–130°) | [S12], [S11], [S15] |
| Coude | | Valgus (angle de port) | 12,9 ± 5,9° (H 11°, F 15°) | [S16] |
| Radio-ulnaire | 1 | Pronation / supination | 76,9–82° / 85–90,6° (fonctionnel 50/50°) | [S11], [S15] |
| Poignet | 2 | Flexion / extension | 80° / 70° (fonctionnel 54/60° max) | [S12], [S19] |
| Poignet | | Inclinaison radiale / ulnaire | ≈ 20° / ≈ 30° (fonctionnel 17/40°) | NV ; [S19] |
| Doigts MCP | 2 | Flexion | 80° (fonctionnel 19–71°) | [S12], [S21] |
| Doigts IPP | 1 | Flexion | 90° (fonctionnel 23–87°) | [S12], [S21] |
| Doigts IPD | 1 | Flexion | 65° (fonctionnel 10–64°) | [S12], [S21] |
| Pouce MCP / IP | 1–2 / 1 | Flexion | 50° / 80° | [S12] |
| Pouce CMC1 | 2 (+ rotation couplée) | Abduction palmaire / radiale | 60° / 60° (hors AAOS) | [S12] |
| Hanche | 3 | Flexion / extension | 120–133,8° / 17,4–20° | [S12], [S11] |
| Hanche | | Abduction / adduction | 40° / 20° | [S12] |
| Hanche | | RE / RI | 38,5–41,8° / 29,6–37,9° | [S23] |
| Genou | 1 + rotation couplée | Flexion | 135–141,9° | [S12], [S11] |
| Genou | | Rotation tibiale couplée (0–120°) | ≈ 20° (tibia en rotation interne) | [S27] |
| Genou | | Rotation axiale volontaire (genou fléchi 70–110°) | 35–44° au total, RE ≈ 2 × RI | [S29] |
| Genou | | Screw-home (marche) | ≈ 17° | [S28] |
| Cheville (talo-crurale) | 1 | Flexion dorsale / plantaire | 10–20° / 40–55° (AAOS 20/50) | [S30], [S12] |
| Sous-talienne | 1 (axe oblique) | Inversion / éversion | 23° / 12° | [S30] |
| Orteils MTP | 2 | Extension / flexion | 70° / 45° | [S12] |
| Rachis cervical | 3 par segment | Flexion / extension / rotation / inclinaison | 45° / 45° / 60° / 45° | [S12] |
| Rachis cervical | | Rotation totale (un côté, scanner) | 69,7 ± 5,5°, dont C1–C2 37,9° | [S32] |
| Rachis thoracique | 3 par segment | Rotation T1/L1 (un côté) | 24,9 ± 4,9° ; 0,5–2,7° par segment | [S35] |
| Rachis lombaire | 3 par segment | Flexion + extension par étage | ≈ 14° | [S36] |
| Rachis lombaire | | Global : flexion / extension / inclinaison / rotation | 40–73° / 6–29° / 14–28° / ≈ 7° | [S37] |
| ATM | Rotation + translation (×2, liées) | Ouverture / latéralité / propulsion | 37–43 mm / ≈ 7,5 mm / ≈ 8,4 mm | [S38], [S39] |
| Côtes 3–7 | 1 (axe oblique) | Bras de pompe / anse de seau | 7–11° / 10–13° | [S41] |
| Sacro-iliaque | Quasi nul | Rotation / translation | 0,8–3,9° (moy. 2,5°) / 0,1–1,6 mm | [S42] |

---

## 13. Implications pour le rig et le skinning HumanLoom

Ces recommandations découlent des données ci-dessus. Elles ne valident pas l'état actuel du rig, qu'il faut mesurer avec les outils `tools/` du projet.

### 13.1 Épaule
1. **Répartir l'élévation entre trois niveaux** : la GH, la clavicule (SC) et l'omoplate (AC), ou leur équivalent si le rig n'a pas d'os d'omoplate dédié. Ordre de grandeur pour une élévation complète : GH ≈ 2/3, ST ≈ 1/3, avec un ratio global entre 1,7:1 et 2,3:1 [S4, S9].
2. **Courbe non linéaire, pas de ratio constant.** Sonnette ST quasi nulle de 0 à 30°, environ 20 à 40 % de la contribution entre 30 et 90°, environ 50 % au-delà de 90° [S9]. La bascule postérieure et la rotation externe de l'omoplate n'apparaissent vraiment qu'au-delà de 90° [S4]. Une courbe (polynôme ou spline) pilotée par l'élévation humérothoracique est plus fidèle qu'un facteur constant [S4].
3. **Clavicule : donner la priorité à la rotation axiale postérieure** (≈ 30°, surtout dans la seconde moitié de course) et à la rétraction (≈ 15–20°, surtout entre 130 et 150°). Garder l'élévation de la clavicule faible (< 10°) [S4, S5, S6]. Un « haussement » visible de l'épaule doit rester une pose volontaire, pas un effet automatique de l'élévation.
4. **Couplage clavicule → omoplate** : 30° de rotation postérieure de la clavicule valent environ 20° de sonnette et 10° de bascule postérieure de l'omoplate [S6]. Si la rotation axiale de l'os clavicule ne déplace pas visiblement le volume de l'omoplate et du trapèze, il manque des poids ou un correctif.
5. **Rotation humérale automatique** : en élévation, l'humérus tourne en externe [S4, S5]. Pour un contrôle d'abduction simple, prévoir une rotation axiale couplée, ou au moins vérifier que la torsion du deltoïde et du biceps reste plausible.
6. **Correctifs (formes) pilotés par au moins deux dimensions** : l'épaule ne se corrige pas avec un seul angle [S43]. Utiliser une décomposition proche de l'ISB (plan d'élévation, élévation, rotation axiale [S1, S8]) en se méfiant de la singularité à élévation nulle (bras le long du corps). Près de cette position, piloter par l'élévation seule ou par un vecteur de direction (swing/twist) plutôt que par l'angle de plan.
7. **Points de contrôle visuels par phase** (section 1.8) :
   - 0–30° : moignon de l'épaule immobile ;
   - 30–90° : angle inférieur de l'omoplate qui glisse sur le côté ;
   - > 90° : trapèze supérieur raccourci près du cou, aisselle ouverte et plis axillaires tendus, pas de traversée du deltoïde dans l'acromion.

### 13.2 Coude, avant-bras, poignet
- **Valgus de 10 à 15° en extension** [S16]. La position de repos du rig devrait le montrer.
- **Prono-supination répartie le long de l'avant-bras** (os de torsion ou poids progressifs), autour d'un axe allant de la tête radiale à la tête ulnaire dorsale [S17]. Ne jamais la mettre dans le seul os du poignet : c'est l'origine de l'effet papillote [S43, S45]. Plage cible : environ 80° de pronation et 85–90° de supination [S11].
- Le skinning par quaternions duaux (DQS) limite l'effondrement en torsion [S44], mais fait gonfler le pli du coude et du genou en flexion [S45]. Un correctif de flexion reste nécessaire dans les deux cas.

### 13.3 Main
- Limites du rig : MCP environ 80°, IPP environ 90°, IPD environ 65° [S12]. La flexion de l'IPD devrait suivre celle de l'IPP (couplage tendineux ; rapport exact non vérifié).
- Le pivot du pouce doit se trouver au niveau du trapèze et du scaphoïde, pas à la MCP [S22]. L'opposition combine abduction, flexion et rotation axiale du premier métacarpien.

### 13.4 Rachis, cou, tête
- **Cou** : environ 55 à 70 % de la rotation de la tête à C1–C2 [S32, S33]. Si le rig n'a qu'un ou deux os de cou, mettre la rotation en haut (près de la tête), pas à la base. Coupler une légère inclinaison latérale opposée en haut du cou [S32].
- **Thorax** : environ 25° de rotation entre T1 et L1, surtout dans les segments T6–T11 [S35].
- **Lombaire** : environ 7° de rotation seulement de chaque côté [S37], mais la majeure partie de la flexion et de l'extension du tronc (environ 14° par étage [S36]).
- La torsion du tronc doit donc se faire surtout au thorax, et la flexion surtout au lombaire.
- Plusieurs os par région donnent une courbe au lieu d'une cassure.

### 13.5 Hanche, genou, pied
- **Genou** :
  - coupler une rotation interne du tibia d'environ 20° entre 0 et 120° de flexion [S27] ;
  - autoriser environ 35 à 44° de rotation axiale volontaire genou fléchi, la rotation externe environ double de l'interne [S29] ;
  - bloquer la rotation axiale genou tendu ;
  - prévoir un correctif du creux poplité et un traitement de la rotule.
- **Hanche** : RE environ 40°, RI environ 30 à 38° [S23]. La flexion au-delà d'environ 120–130° [S11, S12] doit entraîner le bassin (rétroversion ; non chiffrée ici).
- **Cheville** : flexion dorsale de 10 à 20°, flexion plantaire de 40 à 55° [S30]. Placer l'inversion-éversion sur un axe oblique sous-talien (environ 40° sur l'horizontale, environ 23° sur l'axe du pied) [S30], pas sur l'axe de la cheville.

### 13.6 Mâchoire, thorax, bassin
- **ATM** : la rotation domine l'ouverture, mais la propulsion est une translation [S40]. Il faut donc au moins un DDL de translation antéro-postérieure du condyle. Ouverture plausible : environ 37 à 43 mm aux incisives [S38, S39].
- **Respiration** : deux composantes distinctes, bras de pompe et anse de seau, de 7 à 13° selon la côte [S41]. Ce n'est pas une mise à l'échelle uniforme.
- **Bassin** : bloc rigide (sacro-iliaques à environ 2,5° au plus [S42]). Aucun poids de cuisse ne doit plier la crête iliaque.

### 13.7 Méthode de contrôle proposée
Pour chaque articulation :
1. Poser le rig à 0 %, 50 % et 100 % de l'amplitude du tableau de la section 12.
2. Mesurer les angles réellement obtenus, dans la convention ISB quand elle existe.
3. Vérifier les couplages : clavicule et omoplate en fonction de l'élévation humérale, tibia en fonction de la flexion du genou, C1–C2 en fonction de la rotation de la tête.
4. Comparer visuellement la surface aux descriptions qualitatives, et les faire valider sur des références photographiques ou des scans avant de les considérer comme acquises.

---

## 14. Ce qui reste non vérifié

- Le texte intégral de Wu et al. 2005 [S1] (définitions exactes des axes, séquence de la clavicule) et de Ludewig et al. 2009 [S5] (seul le résumé est accessible ; les valeurs par angle n'ont pas été lues).
- Inman 1944 [S3] : chiffres lus seulement via McClure [S4] (estimés sur graphiques).
- Amplitudes maximales de la SC (seulement [S10], secondaire). La rotation axiale maximale de 45° de la clavicule n'a pas été trouvée.
- Rotations externe et interne normales de l'épaule (90° et 70°), inclinaisons radiale et ulnaire du poignet (20° et 30°), rotations de hanche de l'AAOS (45° et 45°) : valeurs de manuel non confirmées à la page.
- Kapandji (*Physiologie articulaire*) : non consulté. Aucun chiffre de ce document ne vient de lui.
- Toutes les descriptions de surface (deltoïde, sillons, trapèze, pectoral qui « s'aligne », dépression au-dessus de l'acromion, torsion progressive de la peau de l'avant-bras) : qualitatives, non chiffrées par une source.
- Diminution de l'angle de port en flexion, rythme lombo-pelvien, rapport de couplage IPD/IPP, règle « rotation puis translation » de l'ATM, flexion et extension thoraciques.
- Attribution exacte de la table « AAOS » [S12] : c'est un supplément d'un article PRS Global Open de 2020 dont l'auteur indiqué dans les métadonnées est T. Hendriks. Le lien avec l'article de Botman, Hendriks et al. 2020 est probable mais non vérifié.
- Signe de l'« extension » du coude et du genou chez Soucie [S11] (valeurs positives, probablement de l'hyperextension).

---

## 15. Sources

- **[S1]** Wu G, van der Helm FCT, Veeger HEJ, et al. *ISB recommendation on definitions of joint coordinate systems of various joints for the reporting of human joint motion — Part II: shoulder, elbow, wrist and hand.* J Biomech. 2005;38(5):981–992. doi:10.1016/j.jbiomech.2004.05.042. https://pubmed.ncbi.nlm.nih.gov/15844264/ (métadonnées et résumé seulement)
- **[S2]** Wu G, Siegler S, Allard P, et al. *ISB recommendation on definitions of joint coordinate system of various joints for the reporting of human joint motion — part I: ankle, hip, and spine.* J Biomech. 2002;35(4):543–548. https://pubmed.ncbi.nlm.nih.gov/11934426/
- **[S3]** Inman VT, Saunders JB, Abbott LC. *Observations on the function of the shoulder joint.* J Bone Joint Surg. 1944;26:1–30 ; réimpr. Clin Orthop Relat Res. 1996;(330):3–12. https://pubmed.ncbi.nlm.nih.gov/8804269/ (non lu ; chiffres via [S4])
- **[S4]** McClure PW, Michener LA, Sennett BJ, Karduna AR. *Direct 3-dimensional measurement of scapular kinematics during dynamic movements in vivo.* J Shoulder Elbow Surg. 2001;10(3):269–277. https://pages.uoregon.edu/biomech/obl/articles/2001_mcclure_jses2001.pdf (texte intégral lu ; titre et auteurs repris de la référence bibliographique usuelle, non relus dans l'extraction)
- **[S5]** Ludewig PM, Phadke V, Braman JP, Hassett DR, Cieminski CJ, LaPrade RF. *Motion of the shoulder complex during multiplanar humeral elevation.* J Bone Joint Surg Am. 2009;91(2):378–389. doi:10.2106/JBJS.G.01483. https://pmc.ncbi.nlm.nih.gov/articles/PMC2657311/ (résumé)
- **[S6]** Ludewig PM, Braman JP. *Shoulder impingement: biomechanical considerations in rehabilitation.* Man Ther. 2011;16(1):33–39. doi:10.1016/j.math.2010.08.004. https://pmc.ncbi.nlm.nih.gov/articles/PMC3010321/ (texte)
- **[S7]** Ludewig PM, Reynolds JF. *The association of scapular kinematics and glenohumeral joint pathologies.* J Orthop Sports Phys Ther. 2009;39(2):90–104. doi:10.2519/jospt.2009.2808. https://pmc.ncbi.nlm.nih.gov/articles/PMC2730194/ (texte)
- **[S8]** Ludewig PM, Hassett DR, LaPrade RF, Camargo PR, Braman JP. *Comparison of scapular local coordinate systems.* Clin Biomech. 2010;25(5):415–421. https://pmc.ncbi.nlm.nih.gov/articles/PMC2862764/ (texte ; volume et pages non relus)
- **[S9]** Scibek JS, Carcia CR. *Assessment of scapulohumeral rhythm for scapular plane shoulder elevation using a modified digital inclinometer.* World J Orthop. 2012;3(6):87–94. doi:10.5312/wjo.v3.i6.87. https://pmc.ncbi.nlm.nih.gov/articles/PMC3377910/ (résumé)
- **[S10]** McLaren N (rév. Mytilinaios D). *Sternoclavicular joint.* Kenhub. https://www.kenhub.com/en/library/anatomy/sternoclavicular-joint (source secondaire)
- **[S11]** Soucie JM, Wang C, Forsyth A, et al. *Range of motion measurements: reference values and a database for comparison studies.* Haemophilia. 2011;17(3):500–507 (e-pub nov. 2010). Valeurs lues sur https://archive.cdc.gov/www_cdc_gov/ncbddd/jointrom/index.html
- **[S12]** *Supplementary Digital Content 1 — Normal ROM values according to AAOS* (PRS Global Open, 2020 ; auteur des métadonnées : T. Hendriks). https://cdn-links.lww.com/permalink/prsgo/b/prsgo_8_6_2020_04_17_hendriks_gox-d-20-00155r2_sdc1.pdf (texte lu ; doigts d'après Richard & Parry)
- **[S13]** Gill TK, Shanahan EM, Tucker GR, Buchbinder R, Hill CL. *Shoulder range of movement in the general population: age and gender stratified normative data using a community-based cohort.* BMC Musculoskelet Disord. 2020;21:676. https://pmc.ncbi.nlm.nih.gov/articles/PMC7549223/
- **[S14]** Fleisig GS, Slowik JS, Daggett M, et al. *Active range of motion of the shoulder: a cross-sectional study of 6635 subjects.* JSES Int. 2023. https://pmc.ncbi.nlm.nih.gov/articles/PMC9937824/
- **[S15]** Morrey BF, Askew LJ, Chao EY. *A biomechanical study of normal functional elbow motion.* J Bone Joint Surg Am. 1981;63(6):872–877. https://pubmed.ncbi.nlm.nih.gov/7240327/
- **[S16]** Paraskevas G, Papadopoulos A, Papaziogas B, et al. *Study of the carrying angle of the human elbow joint in full extension: a morphometric analysis.* Surg Radiol Anat. 2004;26(1):19–23. https://pubmed.ncbi.nlm.nih.gov/14648036/
- **[S17]** Tay SC, van Riet R, Kazunari T, Amrami KK, An KN, Berger RA. *In-vivo kinematic analysis of forearm rotation using helical axis analysis.* Clin Biomech. 2010;25(7):655–659. https://pubmed.ncbi.nlm.nih.gov/20483515/
- **[S18]** Palmer AK, Werner FW, Murphy D, Glisson R. *Functional wrist motion: a biomechanical study.* J Hand Surg Am. 1985;10(1):39–46. https://pubmed.ncbi.nlm.nih.gov/3968403/
- **[S19]** Ryu JY, Cooney WP, Askew LJ, An KN, Chao EY. *Functional ranges of motion of the wrist joint.* J Hand Surg Am. 1991;16(3):409–419. https://pubmed.ncbi.nlm.nih.gov/1861019/
- **[S20]** Hume MC, Gellman H, McKellop H, Brumfield RH. *Functional range of motion of the joints of the hand.* J Hand Surg Am. 1990;15(2):240–243. https://pubmed.ncbi.nlm.nih.gov/2324451/
- **[S21]** Bain GI, Polites N, Higgs BG, et al. *The functional range of motion of the finger joints.* J Hand Surg Eur. 2015;40(4):406–411. https://pubmed.ncbi.nlm.nih.gov/24859993/
- **[S22]** Crisco JJ, Morton AM, Moore DC, et al. *Thumb motion is not the same as first carpometacarpal joint motion.* J Biomech. 2025. https://pmc.ncbi.nlm.nih.gov/articles/PMC13159719/
- **[S23]** Kouyoumdjian P, Coulomb R, Sanchez T, Asencio G. *Clinical evaluation of hip joint rotation range of motion in adults.* Orthop Traumatol Surg Res. 2012;98(1):17–23. https://pubmed.ncbi.nlm.nih.gov/22227606/
- **[S24]** Roach KE, Miles TP. *Normal hip and knee active range of motion: the relationship to age.* Phys Ther. 1991;71(9):656–665. https://pubmed.ncbi.nlm.nih.gov/1881956/
- **[S25]** Boone DC, Azen SP. *Normal range of motion of joints in male subjects.* J Bone Joint Surg Am. 1979;61(5):756–759. https://pubmed.ncbi.nlm.nih.gov/457719/ (résumé sans chiffres ; non utilisé pour les valeurs)
- **[S26]** Freeman MAR, Pinskerova V. *The movement of the normal tibio-femoral joint.* J Biomech. 2005;38(2):197–208. https://pubmed.ncbi.nlm.nih.gov/15598446/
- **[S27]** Johal P, Williams A, Wragg P, Hunt D, Gedroyc W. *Tibio-femoral movement in the living knee. A study of weight bearing and non-weight bearing knee kinematics using "interventional" MRI.* J Biomech. 2005;38(2):269–276. https://pubmed.ncbi.nlm.nih.gov/15598453/
- **[S28]** Kim HY, Kim KJ, Yang DS, et al. *Screw-home movement of the tibiofemoral joint during normal gait: three-dimensional analysis.* Clin Orthop Surg. 2015;7(3):303–309. https://pmc.ncbi.nlm.nih.gov/articles/PMC4553277/ (pages non relues)
- **[S29]** Mossberg KA, Smith LK. *Axial rotation of the knee in women.* J Orthop Sports Phys Ther. 1983;4(4):236–240. https://pubmed.ncbi.nlm.nih.gov/18806440/
- **[S30]** Brockett CL, Chapman GJ. *Biomechanics of the ankle.* Orthop Trauma. 2016;30(3):232–238. https://pmc.ncbi.nlm.nih.gov/articles/PMC4994968/ (texte)
- **[S31]** Swinkels RA, Swinkels-Meewisse IE. *Normal values for cervical range of motion.* Spine. 2014;39(5):362–367. https://pubmed.ncbi.nlm.nih.gov/24573069/
- **[S32]** Kang J, Chen G, Zhai X, et al. *In vivo three-dimensional kinematics of the cervical spine during maximal active head rotation.* PLoS One. 2019;14(4):e0215357. https://pmc.ncbi.nlm.nih.gov/articles/PMC6467451/ (texte)
- **[S33]** Lindenmann S, Tsagkaris C, Farshad M, Widmer J. *Kinematics of the cervical spine under healthy and degenerative conditions: a systematic review.* Ann Biomed Eng. 2022;50(12). https://pmc.ncbi.nlm.nih.gov/articles/PMC9794546/ (texte ; 4e auteur non relu)
- **[S34]** Bogduk N, Mercer S. *Biomechanics of the cervical spine. I: Normal kinematics.* Clin Biomech. 2000;15(9):633–648. https://pubmed.ncbi.nlm.nih.gov/10946096/ (résumé sans chiffres)
- **[S35]** Fujimori T, Iwasaki M, Nagamoto Y, et al. *Kinematics of the thoracic spine in trunk rotation: in vivo 3-dimensional analysis.* Spine. 2012;37(21):E1318–E1328. https://pubmed.ncbi.nlm.nih.gov/22772578/
- **[S36]** Pearcy M, Portek I, Shepherd J. *Three-dimensional x-ray analysis of normal movement in the lumbar spine.* Spine. 1984;9(3):294–297. https://pubmed.ncbi.nlm.nih.gov/6374922/ ; et Pearcy MJ. *Stereo radiography of lumbar spine motion.* Acta Orthop Scand Suppl. 1985;212:1–45. https://pubmed.ncbi.nlm.nih.gov/3859987/
- **[S37]** Troke M, Moore AP, Maillardet FJ, Cheek E. *A normative database of lumbar spine ranges of motion.* Man Ther. 2005;10(3):198–206. https://pubmed.ncbi.nlm.nih.gov/16038855/
- **[S38]** Gallagher C, Gallagher V, Whelton H, Cronin M. *The normal range of mouth opening in an Irish population.* J Oral Rehabil. 2004;31(2):110–116. https://pubmed.ncbi.nlm.nih.gov/15009593/
- **[S39]** Campillo B, Martín C, Palma JC, et al. *Electromyographic activity of the jaw muscles and mandibular kinematics in young adults with theoretically ideal dental occlusion: reference values.* Med Oral Patol Oral Cir Bucal. 2017;22(3). https://pmc.ncbi.nlm.nih.gov/articles/PMC5432089/
- **[S40]** Chen CC, Lin CC, Hsieh HP, et al. *In vivo three-dimensional mandibular kinematics and functional point trajectories during temporomandibular activities using 3D fluoroscopy.* Dentomaxillofac Radiol. 2021;50(2). https://pmc.ncbi.nlm.nih.gov/articles/PMC7860955/
- **[S41]** Wilson TA, Rehder K, Krayer S, Hoffman EA, Whitney CG, Rodarte JR. *Geometry and respiratory displacement of human ribs.* J Appl Physiol. 1987;62(5):1872–1877. https://pubmed.ncbi.nlm.nih.gov/3597261/
- **[S42]** Sturesson B, Selvik G, Udén A. *Movements of the sacroiliac joints. A roentgen stereophotogrammetric analysis.* Spine. 1989;14(2):162–165. https://pubmed.ncbi.nlm.nih.gov/2922636/ ; et Sturesson B, Uden A, Vleeming A. Spine. 2000;25(2):214–217 et 25(3):364–368 (PMID 10685486, 10703111).
- **[S43]** Lewis JP, Cordner M, Fong N. *Pose space deformation: a unified approach to shape interpolation and skeleton-driven deformation.* SIGGRAPH 2000, p. 165–172. doi:10.1145/344779.344862. https://www.scribblethink.org/Work/PSD/PSD.pdf (texte)
- **[S44]** Kavan L, Collins S, Žára J, O'Sullivan C. *Geometric skinning with approximate dual quaternion blending.* ACM Trans Graph. 2008;27(4):105. https://users.cs.utah.edu/~ladislav/kavan08geometric/kavan08geometric.html ; page projet : https://users.cs.utah.edu/~ladislav/dq/
- **[S45]** Le BH, Hodgins JK. *Real-time skeletal skinning with optimized centers of rotation.* ACM Trans Graph (SIGGRAPH). 2016. https://la.disneyresearch.com/publication/skinning-with-optimized-cors/ (résumé et communiqué)
- **[S46]** *Axilla* — Radiopaedia (https://radiopaedia.org/articles/axilla) et WSU Gross Anatomy, *Axilla and brachial plexus* (https://learning.medicine.wsu.edu/gross-anatomy/textbook/9-axilla-and-brachial-plexus) : constitution des plis axillaires (sources pédagogiques).
