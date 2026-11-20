# Morphologies corporelles paramétrables

19 novembre 2026. Spécification de modélisation pour Blender 5.2. Première musculature globale et régionale réalisée en 0.9 ; calibration scientifique, adiposité régionale et définition détaillée restent à développer.

## Paramètres proposés

Séparer la masse grasse, le développement musculaire et la structure corporelle. Un personnage peut avoir une musculature importante avec une adiposité faible ou élevée. Les qualificatifs « mince », « corpulent », « musclé » et « fitness » désignent des préréglages éditables de ces paramètres. Ils ne constituent pas des catégories biologiques fermées.

| Famille | Paramètres proposés | Effet géométrique à construire |
| --- | --- | --- |
| Adiposité | Globale ; abdomen/flancs ; bassin/fessiers ; cuisses ; bras ; visage/cou | Dépôts sous-cutanés, contours et plis adaptés aux volumes |
| Musculature | Globale ; épaules ; pectoraux ; dos ; bras ; abdomen ; fessiers ; cuisses ; mollets | Volume et relief propres aux groupes musculaires |
| Structure | Carrure, largeur thoracique et pelvienne, proportions des membres | Structure indépendante de l'adiposité ; complément aux réglages existants |
| Répartition | Dominante centrale ou bassin/cuisses, variations régionales | Distribution des volumes à quantité globale comparable |
| Définition | Relief de surface lié aux muscles et à leur couverture | Visibilité des muscles sans ajouter artificiellement la même masse à tous les groupes |

L'interface commencera par des réglages globaux et permettra d'ouvrir les régions. La définition devra tenir compte de la couverture graisseuse et conserver une correction artistique. Aucun réglage ne sera présenté comme une mesure de condition physique, de force ou de santé.

## Références scientifiques retenues

- **NHANES DXA 2017–2018** : mesures de graisse, tissus maigres et contenu minéral osseux, globalement et par régions. Le fichier corps entier couvre les participants éligibles de 8 à 59 ans ; les exclusions, valeurs invalides et pondérations doivent être respectées. La masse maigre mesurée n'est pas directement la masse des muscles squelettiques. Ce cycle ne peut pas calibrer les formes de 5 et 75 ans. [Documentation officielle DXX_J](https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/DXX_J.htm)
- **Janssen et collègues, 2000** : IRM corps entier de 468 adultes de 18 à 88 ans. Appui pour étudier masse musculaire et répartition selon âge et dimensions corporelles. Examiner le texte complet et l'erratum de 2014 avant de transcrire des valeurs. [Notice et erratum signalé](https://pubmed.ncbi.nlm.nih.gov/10904038/)
- **Shape Up!, 2019** : étude sur 407 adultes associant scans optiques 3D, DXA et analyse en composantes principales. Appui méthodologique pour relier plusieurs dimensions de forme à la composition corporelle. Une relation prédictive forme→composition n'est pas une solution unique pour générer la forme inverse. [Publication](https://pubmed.ncbi.nlm.nih.gov/31553429/)
- **Qiao et collègues, 2024** : estimation de composition corporelle totale et régionale depuis la forme 3D. À examiner pour les mesures de validation et l'ajustement aux données DXA ; aucune réutilisation de modèle ou de scans n'est présumée autorisée. [Publication](https://pubmed.ncbi.nlm.nih.gov/39443585/)

## Construction mathématique proposée

Ces équations décrivent notre architecture à développer ; elles ne sont pas un modèle biologique déjà calibré.

Soit `p` l'ensemble âge, morphologie, structure, adiposité et musculature. La surface commune est construite comme suit :

`X(p) = X_reference(age, morphologie) + D_structure(p) + D_graisse(p) + D_muscles(p) + C_interactions(p)`

Les champs régionaux sont lisses et bornés. Les corrections traitent notamment âge×muscles, âge×graisse et graisse×muscles. Éviter les doubles contributions entre paramètres globaux et régionaux. Les indices de sommets et les UV restent stables. Les unités d'interface seront d'abord artistiques ; afficher un pourcentage de graisse ou des kilogrammes exige une calibration supplémentaire.

Pour un futur ajustement à des mensurations, minimiser :

`E(p) = somme_i w_i [(mesure_i(X(p)) - cible_i) / echelle_i]^2 + lambda R(p)`

`echelle_i` normalise les unités et, lorsqu'elle est connue, l'incertitude du protocole. `R` régularise les déformations et les combinaisons mal documentées. Des contraintes géométriques et des limites de paramètres complètent l'ajustement. Les tours seuls ne déterminent pas la composition interne ni une forme unique.

Le volume d'une surface fermée peut se contrôler par somme des volumes signés de tétraèdres : `V = abs(somme dot(a, cross(b,c)) / 6)`. Ce contrôle demande des normales cohérentes et l'absence d'auto-intersections ; il ne fournit pas le poids biologique sans modèle interne de tissus.

## Ordre de réalisation et validation

1. Corriger et vérifier la base, notamment l'ajustement yeux/orbites déjà identifié.
2. Développer séparément graisse et muscles sur les adultes, puis leurs interactions. Comparer les fonctionnalités de MPFB et CharMorph et produire nos propres champs et correctifs.
3. Adapter les déformations aux quatre âges avec des références appropriées. Ne pas appliquer automatiquement les amplitudes musculaires adultes aux enfants.
4. Vérifier chaque extrême et un ensemble de combinaisons : corps entiers face/profil/trois-quarts, tours régionaux, volume, plis, continuité des articulations, croisements et limites du diagnostic.
5. Vérifier sauvegarde, mélange de préréglages, retour au neutre, indépendance de deux personnages et réouverture dans Blender 5.2.

Les distributions futures conserveront population, protocole, âge, effectif, unités et incertitude. Aucun coefficient statistique ou jeu de scans n'est intégré à ce stade.
