# Nature du cheveu et intégration au prototype Blender 5.2

20 novembre 2026. Le prototype distingue désormais la **forme intrinsèque au repos**, la section de la fibre et sa réponse mécanique. Une commande continue sert de démonstrateur entre lisse et fortement enroulé. Les paramètres physiques et les formes reposent sur des concepts publiés ; les valeurs des préréglages ne sont pas encore ajustées à un échantillon biologique. Le plugin 0.14 installé et les scènes précédentes restent conservés.

## Résultats scientifiques retenus

**Mesurer une courbure plutôt que déduire une forme depuis une catégorie.** Lasisi et al. proposent une mesure quantitative de la courbure et de la section. Leur étude sur 140 personnes apporte aussi des éléments indiquant que certaines associations entre section et courbure peuvent refléter la structure de l'échantillon plutôt qu'une causalité. Notre commande de nature ne forcera donc ni un diamètre ni une ellipticité, et ne sera pas déduite d'une origine ou d'une morphologie de corps. [Lasisi et al., Scientific Reports, 2021](https://www.nature.com/articles/s41598-021-90409-x). Les méthodes et les données de validation sont décrites sur le [site du projet de recherche](https://tinalasisi.github.io/2020_HairPheno_manuscript/index.html).

**La structure de la fibre et ses rotations comptent.** L'étude comparative de Thibaut et al., de fibres droites à très bouclées, décrit l'importance des rotations de section et une organisation asymétrique associée à la courbure. Cela motive des contrôles distincts de courbure et de torsion matérielle. Cela ne fournit pas une loi numérique universelle reliant forme du follicule et coefficients du solveur. [Thibaut et al., Human hair keratin network and curvature, 2007](https://pubmed.ncbi.nlm.nih.gov/17919197/).

**Dérouler une boucle et étirer la matière sont deux phénomènes différents.** Cloete et al. observent une région initiale particulière dans les courbes de traction des fibres bouclées. Nous conservons donc la longueur de contour et séparons le changement de forme d'un allongement axial du matériau. Cette étude ne suffit pas à fixer un coefficient unique pour tous les cheveux. [Cloete et al., Understanding Curly Hair Mechanics: Fiber Strength, 2020](https://doi.org/10.1016/j.jid.2019.06.141).

**La forme au repos entre dans le modèle mécanique.** Bertails et al. emploient des tiges élastiques avec courbures et torsion naturelles, résistance en flexion et en torsion, gravité et section elliptique. C'est le cadre mécanique retenu pour organiser nos données. Notre intégrateur de géométrie ne reproduit pas leur solveur statique d'équilibre. [Bertails et al., Predicting Natural Hair Shapes by Solving the Statics of Flexible Rods, 2005](https://www-evasion.imag.fr/Publications/2005/BAQLLC05/BertailsElectronicFinalEG.pdf).

## Paramètres séparés

| Paramètre | Unité ou représentation | Usage |
| --- | --- | --- |
| Longueur de contour au repos | m, affichable en cm | Longueur réelle le long de la fibre ; distincte de sa hauteur apparente |
| Courbure naturelle | m⁻¹ | Intensité de la courbure ; pour un arc plan circulaire, inverse du rayon |
| Torsion matérielle au repos | rad/m | Rotation du repère de matière le long de la tige ; distincte en général de la torsion géométrique de sa ligne centrale |
| Sens d'enroulement | ±1 | Boucles dans les deux sens, sans modifier la longueur |
| Variations le long de la fibre et entre fibres | Champs reproductibles | À enrichir pour sortir des hélices régulières du démonstrateur |
| Diamètre équivalent et rapport des axes | m et rapport ≥ 1 | Section et propriétés mécaniques, indépendantes du curseur de nature |
| Module de Young, coefficient de Poisson, masse volumique | Pa, rapport, kg/m³ | Entrées d'un modèle de tige homogène simplifié ; valeurs à mesurer ou à justifier |
| Raie, orientation, regroupement, densité | Réglages de coiffage | Distincts de la nature intrinsèque et du matériau |

Lisse, ondulé, bouclé, frisé et crépu sont des noms pratiques de préréglages. Ils ne remplacent pas ces paramètres ni la diversité des fibres d'une chevelure. Le démonstrateur actuel utilise des hélices régulières ; il ne reproduit pas encore toutes les alternances de courbure, irrégularités, torsions et formes observées dans les cheveux crépus. L'humidité, les traitements et les dommages demanderont un modèle et des données dédiés ; aucun coefficient automatique n'est attribué à ces effets dans ce lot.

## Développement effectué

`tools/hair_nature21.py` intègre une tige de forme intrinsèque donnée dans un repère matériel. Les rotations et l'intégrale de la tangente sont calculées analytiquement sur chaque segment à paramètres constants. L'échantillonnage suit la longueur de contour et devient plus fin lorsque la courbure ou la torsion augmente. Un court segment initial reste droit pour le raccord à la racine.

Le chemin de démonstration `nature(a)` utilise `κ = 900 a²` et `τ = ±κ(2,25 − 2a)` pour `0 ≤ a ≤ 1`. **Ces deux relations sont des choix de démonstration**, pas des relations biologiques publiées. Les paramètres peuvent aussi être fournis directement avec `RestFiber`. Dans le cas homogène hélicoïdal, le rayon dépend de la courbure ET de la torsion ; il ne faut pas appliquer le raccourci rayon = 1/κ à toute hélice.

`apply_to_hair()` applique ces formes à une copie de notre groom. Il conserve racines, UV et surface, adapte le nombre de points et stocke les paramètres au repos dans les attributs des Hair Curves. Changer la nature reconstruit ici les guides de cette copie : la conservation d'un coiffage sculpté lors d'un tel changement reste à développer. Les cinq variantes sont dans `validation/nature-cheveux-21/Prototype-nature-cheveux-02.blend`, en suivi Animation. Une seule est visible à la fois.

Le calcul de section renvoie des rigidités en unités SI pour la future calibration. Pour des demi-axes `a` et `b` : `A = πab`, `I₁ = πab³/4`, `I₂ = πa³b/4`, `J = πa³b³/(a²+b²)` et `G = E/[2(1+ν)]`. Les rigidités sont `EI₁`, `EI₂`, `GJ`, et la masse par longueur `ρA`. C'est une approximation homogène isotrope à section elliptique, pas une reconstruction des couches et de la viscoélasticité du cheveu humain. Les nombres utilisés dans les tests de ces identités sont des entrées mathématiques choisies, pas une calibration biologique.

## Branchement sur Hair Dynamics et XPBD

Les boucles sont créées **avant** Hair Dynamics. Ainsi, elles contribuent à la forme et aux orientations au repos que les contraintes doivent préserver. Les [nœuds Hair Dynamics 5.2](https://docs.blender.org/manual/id/5.2/modeling/geometry_nodes/simulation/hair_dynamics.html) utilisent la géométrie d'entrée comme forme naturelle. Les curseurs Bendiness, Root Bendiness et Stretchiness sont des facteurs de contrôle ; ils ne sont pas des modules de Young. Nous ne leur affectons pas directement des valeurs en pascals.

La mise au repos a été testée dans le vrai mode **Physics (Experimental)**, avec 24 guides, pour trois valeurs de nature et 12 images, gravité et collisions désactivées. Ces essais vérifient la conservation numérique d'une forme non chargée. Ils ne valident ni une déformation sous charge ni la justesse d'un matériau.

**Le lot suivant délimite un premier domaine stable sous gravité.** Les essais initiaux de ce lot 21 présentent un allongement excessif, y compris sur une fibre droite, et ne sont pas des profils valides. Le [banc de dynamique du lot 22](validation/physique-cheveux-22/README.md) vérifie ensuite 12 fibres droites et 12 fibres faiblement courbées sur 48 images, avec un budget d'itérations adapté : allongement inférieur à 0,3 % et racines fixes. Cela montre que le moteur fonctionne dans ces conditions, sans valider les boucles très détaillées ni un matériau biologique. Le profil limité refuse les géométries non couvertes au lieu de supprimer des détails pour les faire passer.

Pour cette raison, le fichier de coiffure reste en mode Animation. Le mode physique n'est pas ajouté au produit installé. La densification de rendu et la résolution des guides physiques devront être étudiées séparément, sans retirer de courbure au repos pour masquer l'erreur.

## Preuves et prochaines vérifications

Rapports dans `validation/nature-cheveux-21/` :

- `validation-mathematique.json` : 21 valeurs de nature ; longueur polygonale à moins de 0,1 % de la longueur demandée, courbure mesurée, symétrie des sens d'enroulement, entrées invalides refusées. Vérification des lois d'échelle de la section et de l'anisotropie géométrique.
- `geometries-au-repos.json` : cinq variantes sur le corps, UV des racines conservées. Ce rapport ne certifie pas leurs collisions ni une coiffure réaliste finale.
- `xpbd-repos-*-iterations12.json` : conservation au repos dans le moteur natif ; `material_response_validated` reste faux.
- `xpbd-gravite-*-iterations*.json` : diagnostics de déplacement, racines et longueur de contour sous gravité. Le succès du contrôle d'activation ne vaut pas validation physique ; le critère d'allongement inférieur à 5 % échoue dans ces essais. Ce seuil est un seuil de diagnostic choisi, pas une limite biologique publiée.
- `Comparaison-fibres-60mm.png` et `fibres-comparaison.json` : exemples géométriques à longueur identique, épaisseur exagérée pour la lisibilité. Ce ne sont pas des mesures de cinq populations ni une classification validée.

La suite consiste à étendre ce domaine aux boucles serrées et aux mouvements de racines, puis aux collisions et aux cheveux denses. Calibrer séparément flexion, torsion, réponse en traction et effets d'environnement à partir de données expérimentales. Garder le diamètre, la section, la couleur et la densité indépendants de la nature du cheveu.
