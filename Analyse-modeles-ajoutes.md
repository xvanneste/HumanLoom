# Étude des modèles humains ajoutés — 19 novembre 2026

Trois ensembles ont été trouvés dans `G:/_dev/BlenderDev`. Les sources sont conservées intactes. Les imports, scènes d'inspection, empreintes SHA-256 et mesures sont dans `validation/references-humaines-16`. Aucun de ces nouveaux maillages n'est intégré au plugin installé.

## Utilité des références

| Ensemble | Ce qui a été étudié | Utilisation retenue et limites |
| --- | --- | --- |
| FREE Stylized Basemesh Male — Tam Nguyen | FBX et OBJ importés dans Blender 5.2 ; vues sans texture de face, profil, dos et trois-quarts ; comparaison avec notre candidat adulte 15 à hauteur normalisée | Référence artistique de musculature, transitions entre volumes et topologie du corps. Les épaules, membres et mains sont stylisés ; ne pas les imposer à toutes les morphologies. |
| Beautiful girl practicing yoga pose — 3DCreator3527 | FBX, géométrie réelle comparée à son aperçu, quatre vues orthographiques | Référence locale de forme du tronc, raccord bassin–cuisse, genoux et chevilles en pose. Le grand écart, la rotation du bassin et les vêtements empêchent une comparaison directe de stature et de tours corporels nus. Les métadonnées du fournisseur indiquent une génération par IA ; aucune provenance anthropométrique n'est fournie. |
| Ultimate MetaHuman Body Base Adult — Star Exile Studio | Paquet et manifestes examinés, deux personnages importés dans Unreal 5.8.4, géométries source LOD0 exportées en OBJ et examinées dans Blender 5.2 | Deux références adultes de volumes et de raccords corporels. Les corps complets possèdent chacun 49 104 sommets et 95 330 triangles. L'export CPU permet l'étude sans créer de rig pour notre plugin. |

Le format `.mhpkg` est destiné au flux MetaHuman dans Unreal. L'export géométrique est maintenant réalisé depuis un projet d'étude isolé sous Unreal 5.8.4. Les scènes et huit vues des corps entiers sont dans `validation/unreal-17/blender`. Le projet, la connexion MCP testée et la méthode d'export sont décrits dans `unreal/HumanReferenceStudy/README.md`. [Documentation officielle Epic sur les paquets](https://dev.epicgames.com/documentation/metahuman/buying-metahumans-from-fab)

## Constats techniques confirmés

- **Échelles différentes selon le format.** Le même ensemble masculin a une étendue verticale totale d'environ 2,0898 unités dans le FBX, contre 208,9764 dans l'OBJ importé sans conversion supplémentaire. Le rapport est 100. Le corps seul du FBX mesure environ 2,0599 unités avant subdivision ; la fiche fournisseur annonce 1,90 m. Les dimensions d'import ne sont donc pas prises comme une stature réelle certifiée.
- **Un même modèle, pas deux références indépendantes.** Les cinq objets du FBX totalisent 187 981 sommets et 357 507 faces ; l'OBJ réunit exactement ces mêmes effectifs dans un seul objet et présente les mêmes étendues à un facteur 100 près. Cela indique deux exports du même ensemble. La comparaison n'a pas prétendu démontrer une identité sommet par sommet.
- **Corps masculin exploitable pour examiner les boucles.** Le corps comprend 10 423 sommets et 10 410 faces, dont 10 386 quadrilatères. C'est une seule composante, avec 50 arêtes de bord. Les ouvertures devront être localisées avant toute réutilisation ; elles ne sont pas automatiquement des défauts. Aucun rig, groupe de sommets ou morph n'est présent dans ce FBX. Le corps importé n'a pas de couche UV, contrairement à d'autres objets du fichier.
- **La coiffure fausse le qualificatif global « low-poly ».** Elle comporte 170 211 sommets et 340 179 triangles, répartis en 26 composantes. Elle est retirée de la comparaison de proportions ; la tête et les pieds restent visibles.
- **Femme yoga : surface triangulée et pose figée.** Le fichier comporte un objet de 73 984 sommets et 147 994 faces triangulaires, une composante, une couche UV, 11 arêtes de bord et aucun rig ni morph. Corps, vêtements et cheveux appartiennent au même objet. L'étendue de la pose est d'environ 1,00 unité dans l'axe du grand écart et 0,54 verticalement ; ce dernier nombre ne représente pas une stature debout. Une texture référencée n'est pas fournie à l'emplacement attendu ; les vues en argile évitent d'en dépendre.
- **Paquet MetaHuman confirmé.** L'archive d'environ 482 Mo contient les deux personnages et leurs cartes normales tête/corps. Les manifestes déclarent des personnages éditables pour Unreal 5.6. Les compteurs de LOD à zéro dans ces manifestes ne signifient pas que les corps sont dépourvus de géométrie : ils ne sont pas des mesures de maillage exporté.

Les nœuds parents FBX portent la conversion d'unités et d'axes. La scène comparative conserve leur transformation mondiale lorsqu'elle retire la hiérarchie de présentation. Deux assertions contrôlent ensuite la hauteur importée de la référence et la normalisation effective des deux corps à 1,80 unité. Cette normalisation sert uniquement à comparer des formes.

## Comparaison du masculin avec notre candidat

La scène `comparaison-masculine-normalisee-inspection.blend` juxtapose notre masculin neutre et le corps stylisé. Les deux surfaces sont examinées à subdivision 2. Les vues maintiennent les personnages côte à côte dans les quatre orientations, sans superposition de profil. Les yeux de la référence sont conservés, les cheveux et accessoires exclus. La position à l'écran suit la caméra : notre corps est à gauche dans chaque vue.

Les coupes suivantes sont des descripteurs géométriques à une fraction de la hauteur. Ce ne sont pas des repères anatomiques palpés ni des normes biologiques. L'écartement des membres et les poses diffèrent.

| Niveau technique | Notre largeur / hauteur | Référence largeur / hauteur | Observation limitée à cette coupe |
| --- | ---: | ---: | --- |
| 25 % | 0,0562 | 0,0656 | Composante de jambe droite plus large d'environ 17 % sur la référence |
| 37 % | 0,0878 | 0,0999 | Composante de jambe droite plus large d'environ 14 % sur la référence |
| 53 % | 0,2089 | 0,2148 | Largeur centrale proche, avec une différence d'environ 3 % |
| 61 % | 0,1939 | 0,1699 | Partie centrale plus resserrée d'environ 12 % sur la référence |

À 72 %, la référence présente un contour unique joignant les bras au thorax, alors que notre candidat présente trois contours séparés. Le périmètre brut de cette coupe est exclu comme comparaison de tour de poitrine. Les résultats complets et cette réserve sont dans `comparaison-sections.json`.

La revue des volumes montre des pistes précises pour notre générateur : mieux distinguer les deltoïdes des bras, développer les cuisses et les mollets comme volumes régionaux, traiter la transition entre bassin et cuisse, et structurer le dos au-delà d'un simple changement de largeur du tronc. La taille étroite et les mains amplifiées de la référence restent des choix de style. Un modèle neutre et un modèle musclé ne doivent pas être forcés à partager les mêmes tours.

## Application prévue à notre modélisation

Clarification utilisateur après la revue : conserver notre base actuelle. Le modèle masculin ajouté sert de guide pour les proportions et la répartition des muscles, pas pour remplacer le corps neutre ni lui imposer la taille étroite, les mains ou les proportions stylisées de la référence. Les travaux régionaux ci-dessous visent donc le pôle musculaire et son raccord à la base.

1. Conserver les références comme comparateurs visuels indépendants, avec pose, échelle, région visible et provenance documentées. Elles ne remplacent pas les données scientifiques.
2. Reprendre le pôle musculaire par régions anatomiques et raccords continus, en vérifiant face, profil et dos. Éviter d'obtenir les muscles uniquement par inflation radiale uniforme.
3. Examiner le bassin et les attaches de cuisse avec les deux références importables. Ne pas déduire une longueur debout du modèle en grand écart ni reconstruire arbitrairement sa pose neutre sans squelette.
4. Ajouter le duo MetaHuman à la comparaison normalisée. Son export, son orientation et la réouverture des deux scènes sont vérifiés ; l'identification des surfaces externes pour les mesures reste à effectuer.
5. Maintenir les formes de graisse, minceur et d'âge comme travaux distincts : aucun nouveau modèle de corpulence élevée, enfant, adolescent ou senior n'est fourni dans ce lot. Les règles adultes ne deviennent pas des règles de croissance.

Les descriptions commerciales et les métadonnées sont des informations du fournisseur, pas des résultats scientifiques. Aucun asset ajouté n'est déclaré CC0 par cette étude. Le lot actuel produit une analyse locale et des scènes de comparaison ; il ne redistribue pas ces modèles dans l'extension.

Les trois scènes d'inspection ont été rouvertes dans Blender 5.2. Les deux corps de la scène comparative conservent une hauteur évaluée de 1,80 unité après réouverture ; le résultat est consigné dans `validation/references-humaines-16/controle-reouverture.json`.

## Application réalisée · musculature 0.14

Le pôle adulte a été reconstruit dans huit régions avec raccords aux articulations, saturation du cumul global/local et correction des croisements sous les aisselles. La base neutre est conservée ; aucun sommet des modèles ajoutés n'est redistribué. La version est installée uniquement sur Blender 5.2 et les deux corps existants ont été migrés. Comparatifs du corps entier et rapports : validation/muscles-regionaux-18. Voir Livraison-muscles-regionaux-0.14.md. Les amplitudes restent artistiques ; les modèles de référence ne constituent pas des normes biologiques.
