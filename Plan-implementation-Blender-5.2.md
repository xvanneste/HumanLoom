# Plan d’implémentation du générateur humain pour Blender 5.2 LTS

19 novembre 2026

Mise à jour **0.11** : [finitions du visage âgé et contrôle au niveau de rendu](Livraison-finitions-0.11.md), avec un relief supplémentaire réglable et une correction locale des paupières âgées. 46 réglages sont disponibles. Le statut anatomique reste provisoire pour les chantiers détaillés dans ce bilan.

État courant : **0.10**, 45 réglages et quatre formes d'âge. Le [bilan du lot](Livraison-modelisation-0.10.md) décrit les six axes traités, les preuves et les limites. Les sections de lots précédents conservent l'historique de leurs essais ; les formes d'âge et l'adiposité régionale sont désormais disponibles dans cette première plage contrôlée. La calibration quantitative porte sur la stature, pas sur toute l'anatomie.

## Périmètre actuel · Modélisation

Le [référentiel biologique](Documentation-biologique.md) regroupe les sources scientifiques, les méthodes de mesure à reprendre et le travail de calibration des réglages. La version 0.9 ajoute une première musculature globale et régionale aux outils de repères, de mesure et de diagnostic. Les amplitudes des vingt-neuf réglages restent artistiques. La suite porte sur l'ajustement yeux/orbites, la validation de l'atlas anatomique, la calibration des proportions selon l'âge et l'extension des volumes corporels.

Le premier livrable visé est une base humaine réaliste éditable dans Blender 5.2 LTS. Le travail commence par le corps et le visage, à partir de la paire réaliste inspectée. Les sections sur le rig, les cheveux, les vêtements et l’export décrivent des phases ultérieures dont l’ordre sera décidé après validation du modèle.

1. Préparer une copie de travail des deux corps réalistes au niveau de base du MultiRes. Comparer leur pose, leur échelle et leurs repères anatomiques.
2. Inspecter les deux morphologies d’origine et les intermédiaires à 25 %, 50 % et 75 % en vues de face, de profil et de trois-quarts. Contrôler le volume et les intersections, en particulier au visage, aux épaules, aux hanches, aux mains et aux pieds. Vérifier l’ajustement des yeux séparés.
3. Choisir le maillage et l’UV de référence à partir des mesures et des vues. Tester l’UV commune avec un damier sur les morphologies intermédiaires.
4. Valider la géométrie de base et documenter les corrections anatomiques nécessaires avant de définir les premiers réglages de proportions du corps et du visage.

### Composition corporelle et musculature

Le lot suivant de morphologies séparera adiposité globale et régionale, développement musculaire global et par groupes, structure et définition visible. Les profils « mince », « corpulent », « musclé » et « fitness » seront des configurations éditables. La [spécification technique](Specification-morphologies-corporelles.md) décrit les paramètres, les sources NHANES/IRM/scans 3D, les champs de déformation et la validation des interactions avec l'âge. Ces fonctions étendues ne sont pas encore disponibles ; le réglage actuel de corpulence reste une première approximation artistique.

### Morphologies selon l’âge

**Cibles confirmées par l’utilisateur le 19 novembre 2026 : enfant de 5 ans, adolescent de 15 ans, adulte de 30 ans et personne âgée de 75 ans.** Les références documentaires et les formes doivent être confrontées à ces âges. Les paramètres MPFB des expériences précédentes restent des paramètres internes sans correspondance validée en années.

Prévoir quatre formes de référence, enfant, adolescent, adulte et personne âgée. Le paramètre d’âge doit agir sur les proportions tête/corps, le visage, la longueur relative des membres et les volumes corporels. Prévoir des variations de posture réglables pour les références âgées. Conserver un réglage de taille indépendant pour permettre des personnages de même âge et de tailles différentes.

#### Références biologiques pour calibrer les formes

- **Croissance staturale**. Les tables OMS de 5 à 19 ans fournissent des courbes de taille selon l’âge et le sexe. Les données CDC proposent également des tables de percentiles et des paramètres LMS exploitables pour calibrer une plage de variation. [OMS](https://www.who.int/tools/growth-reference-data-for-5to19-years/indicators/height-for-age) · [Données CDC](https://www.cdc.gov/growthcharts/cdc-data-files.htm)
- **Proportions jambes et tronc**. Une étude longitudinale japonaise examine conjointement taille debout, taille assise et longueur des jambes. Elle observe une croissance des jambes plus rapide que celle de la taille assise avant l’adolescence dans les deux sexes. Les tables américaines de taille assise et de longueur des jambes apportent d’autres références quantitatives. [Étude longitudinale](https://pubmed.ncbi.nlm.nih.gov/21561299/) · [Tables de proportions](https://pmc.ncbi.nlm.nih.gov/articles/PMC7452688/)
- **Développement du visage**. Une étude de trajectoires de croissance utilise les données 3D Facial Norms et décrit des variations de forme et de taille selon l’âge. Sa population de référence est d’ascendance européenne. La disponibilité des scans implique un accès contrôlé. [Étude des trajectoires faciales](https://pmc.ncbi.nlm.nih.gov/articles/PMC10776214/)
- **Vieillissement du visage**. Une étude transversale analyse 456 surfaces faciales 3D entre 14 et 83 ans dans une population d’Europe centrale. Elle sert à identifier des régions à modifier et des différences de trajectoires selon le sexe. [Étude du vieillissement facial](https://pmc.ncbi.nlm.nih.gov/articles/PMC9759541/)
- **Vieillissement du corps**. Une étude longitudinale sur vingt ans chez des personnes de 60 ans et plus examine les variations de composition corporelle en tenant compte de l’alimentation et de l’activité physique. Elle fournit un appui pour dissocier les variations de masse grasse et de masse maigre dans nos futures formes. [Étude longitudinale de composition corporelle](https://pubmed.ncbi.nlm.nih.gov/33255771/)

Application proposée au générateur à partir de ces sources. Calibrer séparément stature, rapport jambes/tronc, développement facial et composition corporelle. L’âge chronologique, le stade de maturation et les variations individuelles devront pouvoir être représentés sans imposer une seule silhouette par âge. Chaque référence devra conserver l’identification de sa population et de sa méthode. Les paramètres expérimentaux MPFB actuels doivent être confrontés à ces mesures avant de recevoir une correspondance en années. La transformation de mesures anthropométriques en déformations sur notre topologie reste à construire.

Construire les références sur la topologie commune du générateur et adapter les yeux à chaque forme. Évaluer les transitions entre les références voisines et les combinaisons avec la morphologie féminine/masculine. Les différences liées à cette dernière doivent être définies pour chaque stade de développement. Les variations individuelles de corpulence et de posture restent des paramètres à définir.

Les deux corps intégrés au prototype 0.2.0 fournissent les références adultes. L’examen des fichiers MPFB a retrouvé des targets corporelles nommées `baby`, `child`, `young` et `old`, combinées avec des variations de morphologie, de poids et de musculature. Elles pourront servir de références de comparaison. Elles utilisent la topologie MakeHuman, qui demande un transfert de correspondance vers notre base Blender Studio avant toute réutilisation. La référence adolescente et les transitions demanderont une validation visuelle propre.

Avant livraison du réglage d’âge, vérifier les silhouettes de face, de profil et de trois-quarts, la proportion de la tête, le positionnement des yeux et la continuité des volumes aux valeurs intermédiaires. Les quatre formes doivent disposer de références validées avant de présenter leurs catégories dans l’interface.

#### Essai du transfert d’âge

Huit références corporelles ont été générées depuis MPFB 2.0.18, soit les quatre stades pour les deux morphologies. Elles sont regroupées dans `validation/age/References-age.blend`. Les portraits alignent les sommets des crânes pour comparer les proportions du visage. Les paramètres d’âge source retenus pour cette étude sont 0,1875, 0,35, 0,5 et 1. Le stade adolescent est une interpolation du système MPFB. Ces valeurs servent à préparer les formes du générateur et demandent une validation anatomique.

Le transfert géométrique automatique sur le corps Blender Studio a été essayé avec interpolation locale sur les triangles, puis avec un champ de déplacement lissé. Les poses et les proportions des deux bases diffèrent. Après alignement en hauteur, l’écart médian entre surfaces est d’environ 1 cm, mais atteint environ 23 à 25 cm dans les régions les moins bien appariées. Les rendus ont révélé des doigts déformés et des corrections instables aux avant-bras. L’expérience est conservée dans `tools/experimental_age_transfer.py`, avec ses limites signalées. Les références sources sont disponibles pour poursuivre le recalage anatomique des épaules, coudes, poignets et doigts avant le prochain transfert. Le réglage d’âge attend ce recalage pour son intégration à l’extension.

À la demande de revue du corps entier, six images de face, de profil et de trois-quarts ont été produites dans `validation/age`, avec les pieds alignés et un espacement permettant de voir chaque silhouette. Des marques sombres sur les cuisses disparaissent lorsque les ombres portées de Workbench sont désactivées. Les corps se chevauchaient également aux épaules dans les portraits précédents. Les images de revue désactivent ces ombres. Le contrôle des huit maillages sources indique une composante connexe par corps, aucun bord ouvert, aucune arête non-manifold, aucune face d’aire nulle et aucune coordonnée non finie. Le rapport est enregistré dans `validation/age/controle-geometrie.json`. Les intersections de surfaces et la qualité anatomique demandent une revue complémentaire.

### Lot 0.4 · Corpulence, variations et préréglages

La corpulence complète les réglages de proportions. Elle agit sur le buste, le bassin, les cuisses et les joues, avec deux amplitudes distinctes pour les valeurs négatives et positives. Un contrôle ciblé vérifie que les sommets de l’intérieur des jambes conservent leur côté de l’axe médian au maximum de corpulence. Le personnage dispose maintenant de huit réglages de corps et douze réglages de visage.

Les préréglages JSON enregistrent l’identifiant de base, la version du format, le mélange de morphologie, les vingt réglages et l’échelle. L’import propose une intensité de mélange entre la configuration actuelle et celle du fichier. La validation du contenu précède les modifications du personnage. Une erreur pendant l’application restaure les réglages précédents. L’export écrit un fichier temporaire dans le dossier choisi, puis remplace la destination lorsque l’écriture a réussi.

Les variations disposent d’une graine, d’une amplitude et d’un choix entre visage, corps et ensemble. Une séquence propre à chaque réglage rend les valeurs du visage identiques pour une même graine en mode Visage ou Corps et visage. Les nouveaux réglages peuvent ainsi être ajoutés sans décaler la séquence des réglages existants.

Les essais ont couvert 120 valeurs extrêmes, 32 combinaisons, la reconstitution d’un personnage depuis un préréglage, le mélange à 0, 50 et 100 %, onze entrées invalides et des échecs simulés d’écriture et d’application. La mise à niveau des bases 0.2 et 0.3 conserve leurs réglages et leur géométrie avant activation des nouveaux paramètres. Les rendus et six préréglages de corpulence sont regroupés dans `validation/modelisation-04`.

### Lot 0.5 · Mesures et référence de stature

Un panneau affiche la stature réelle et la largeur englobante avec les unités de scène. La comparaison utilise les percentiles publiés du tableau 7 NCHS NHANES 2021–2023, pour les adultes des États-Unis. Les groupes d’âge sélectionnent une référence statistique. Leur application ajuste uniformément la taille et ne modifie pas la morphologie liée à l’âge. Les valeurs absentes ne peuvent pas être appliquées.

Un sommet choisi en mode Édition peut servir de repère bassin manuel. Deux distances suivent alors ce point pendant les déformations. Le placement anatomique et la correspondance avec des protocoles de longueur des jambes et de taille assise restent à établir.

L’export de contrôle dimensionnel JSON conserve les mesures, l’écart, la source, le tableau et l’empreinte du fichier de valeurs, ainsi que les réglages du modèle. Les préréglages enregistrent le choix de référence et restent compatibles avec les anciens fichiers. Les essais vérifient les transformations, les unités, les références indisponibles, le suivi du repère et la réouverture. Les images et la scène de comparaison sont dans `validation/calibration-05`.

### Lot 0.6 · Repères et ajustement de dimensions

Dix repères de surface peuvent être placés sur des sommets du corps en mode Édition. Trois coupes mesurent le buste et trois paires mesurent le nez, la bouche et la distance intercanthale. Les sept ajustements incluent le rapport sol→repère bassin / stature. La recherche reste dans les limites du réglage associé et restaure l’état initial si la cible est impossible. Les coupes utilisent le maillage évalué, isolent le contour central du buste et refusent les contours ouverts ou ambigus. L’export dimensionnel version 2 consigne les repères et les méthodes.

Les définitions FaceBase et le protocole abdominal NHANES servent de références méthodologiques. Le placement manuel, la pose et la différence entre coupe de surface et ruban doivent être vérifiés avant toute comparaison de population. Les placements de la scène de revue restent des approximations de test. Les repères sont conservés dans la scène Blender, sans transfert par les préréglages JSON. Les images du corps entier de face, de profil et de trois-quarts, le détail du visage et la scène éditable sont regroupés dans `validation/anatomie-06`.

### Lot 0.7 · Jeux de repères réutilisables

L’export et l’import de repères utilisent un format JSON propre, avec empreinte de la topologie indexée et validation avant transfert. Les préréglages complets peuvent aussi transporter les repères. Les mélanges partiels conservent les repères du destinataire. Les importations fusionnent les points fournis. Les erreurs restaurent les objets et réglages, sans objets de repère orphelins.

Une commande complète les paires faciales manquantes par réflexion sur la forme neutre. Les propositions sont signalées comme restant à vérifier. Les points existants sont conservés. Les tests de transfert, compatibilité, symétrie, restauration et réouverture sont enregistrés dans `validation/reperes-07`. La validation biologique des placements reste un travail distinct.

### Lot 0.8 · Diagnostic et correction de surface

Un diagnostic sur le corps évalué complète les mesures dimensionnelles. Les limites du test des intersections sont explicites et son export est reproductible par empreinte de géométrie. La recherche porte sur les croisements transversaux entre triangles sans sommet commun, avec un budget de 250 000 triangles.

La surface interne des paupières féminines reçoit une couche de correction réversible et ses interactions avec les réglages. Le test passe de 82 paires croisées à zéro sur la surface de subdivision 1. Les nouveaux personnages la contiennent. Les anciens disposent d’une commande d’ajout indépendante de la mise à niveau des réglages. Les vingt réglages, les préréglages et les repères restent compatibles.

Les expériences de transfert d’âge et de champ de croissance restent hors extension. Les cibles de 5, 15, 30 et 75 ans guident désormais leur calibration. Le candidat `age-cibles-05` ajuste les statures de 5 et 15 ans aux médianes OMS sélectionnées et atténue les restes de volumes thoraciques adultes chez l'enfant. Les 21 mélanges neutres et 48 extrêmes de quatre réglages de tête/yeux ne présentent aucun croisement détecté après subdivision de niveau 1. Avant intégration : différencier davantage le visage senior, valider les collisions yeux/corps, adapter les seize autres réglages et vérifier les proportions régionales. Le périmètre de tête reste une section technique, pas une mesure clinique validée.

### Lot 0.9 · Musculature adulte réglable

Neuf réglages supplémentaires portent la musculature globale et huit régions : épaules, pectoraux, dos, bras, abdomen, fessiers, cuisses et mollets. Les corrections locales se combinent au réglage global avec saturation par région afin d'éviter de doubler l'amplitude au maximum. Les champs sont originaux et conservent la topologie. Ils ne sont pas calibrés en kilogrammes ou en pourcentage de masse musculaire.

Le panneau « Musculature » propose six points de départ : référence, mince, fitness, musclé, ample et ample et musclé. Ils règlent corpulence et muscles et remettent les ajustements musculaires régionaux à zéro. Les proportions et le visage sont conservés. Les vingt anciens réglages restent disponibles, soit vingt-neuf réglages au total. Les anciennes configurations se chargent avec les nouveaux réglages neutres. La mise à niveau ajoute les champs sans remplacer la sculpture existante.

Les essais Blender 5.2 couvrent 72 cas muscles/corpulence, 18 profils sur trois morphologies, 174 extrêmes, 32 combinaisons, la saturation, les préréglages, la migration 0.8, l'absence d'orphelins et la réouverture. Les contrôles des mesures et des jeux de repères passent également. Les vues corps entier face/profil/trois-quarts/dos et les JSON sont dans `validation/musculature-09`. La plage de volumes reste modérée ; les grandes adiposités, la définition détaillée et les interactions anatomiques avec l'âge ne sont pas encore livrées. Le défaut d'ajustement yeux/orbites précédemment identifié reste distinct et non corrigé par ce lot.

### Couverture fonctionnelle visée pour la modélisation

MPFB et CharMorph servent de références pour le niveau fonctionnel. Le code, l’interface et les déformations du générateur suivent les besoins de notre base Blender Studio et de Blender 5.2.

| Fonction à couvrir | État du générateur |
| --- | --- |
| Création de plusieurs personnages indépendants | Disponible |
| Proportions globales et réglages régionaux du corps et du visage | Vingt-neuf réglages disponibles, détail régional à enrichir |
| Corpulence | Première plage modérée disponible |
| Musculature | Première plage adulte globale et huit régions ; calibration et détail anatomique à enrichir |
| Morphologies selon l’âge | Cibles 5/15/30/75 en expérimentation ; statures jeunes vérifiées, vieillissement facial et ajustement orbites/yeux à reprendre |
| Formes extrêmes et correctifs entre paramètres | Correction selon le mélange féminin/masculin et extrêmes distincts de corpulence disponibles, autres interactions à traiter |
| Variations reproductibles et contrôle de leur amplitude | Disponible |
| Sauvegarde, chargement et mélange de configurations | Disponible |
| Asymétries locales et réglages fins des paupières, oreilles et lèvres | À développer |
| Mesures et contrôle dimensionnel | Réglage de hauteur disponible, autres mesures à développer |

### Lot précédent · 0.3.0

Le lot de modélisation ajoute 19 réglages natifs au panneau Humain, avec sept réglages de corps et douze réglages de visage. Le corps propose la carrure, la taille, le bassin, la profondeur du buste, la largeur du cou et les longueurs de jambes et de buste. Le visage propose les dimensions de tête, la mâchoire, le menton, les pommettes, le nez, la bouche, le relief des lèvres, l’écartement et la hauteur des yeux, ainsi que le front. Le bouton de taille réelle conserve sa fonction de mise à l’échelle uniforme. Les changements de longueur peuvent ensuite faire varier la hauteur totale.

Chaque déformation est calculée pour les deux corps adultes. Une correction dépendant du mélange féminin/masculin relie ces deux résultats. Les yeux reçoivent les translations nécessaires en conservant leur forme. Les données restent des shape keys et des drivers Blender, sauvegardés avec chaque personnage. La remise à zéro porte sur les 19 réglages. Les personnages de la version précédente disposent du bouton Ajouter les réglages corps et visage. Cet ajout vérifie la topologie, conserve les coordonnées neutres existantes et ne remplace pas le personnage.

Les essais Blender 5.2 ont couvert 114 valeurs extrêmes, sur les morphologies 0, 50 et 100 %, et 32 combinaisons simultanées. Les contrôles ont vérifié les coordonnées finies, les aires de faces positives et, pour les combinaisons, l’orientation des faces par rapport au modèle neutre. Ils ont également vérifié le déplacement des yeux, l’indépendance des personnages, la remise à zéro, la mise à niveau d’une ancienne base et la conservation après sauvegarde et réouverture. Ces essais géométriques sont complétés par des rendus de face, de profil et de trois-quarts du corps et du visage, dans `validation/modelisation-03`.

Le nouveau transfert d’âge utilise les longueurs mesurées des segments de bras MPFB et des repères explicites sur la base Blender Studio. Les nouveaux rendus conservent les doigts séparés. Les raccords aux épaules et les volumes du thorax sur les formes jeunes restent à retravailler. La scène `validation/age-transfert-02/Transfert-age-experimental.blend` permet d’inspecter ce résultat. Les réglages d’âge poursuivent leur développement dans cette scène expérimentale.

### Vérifications du prototype · 0.2.0

L’extension Human Modeling est installée uniquement dans le profil Blender 5.2. Le menu Ajouter → Mesh → Créer un humain crée un corps avec ses deux yeux indépendants. Le panneau Humain propose le mélange de morphologie, le réglage de taille et le niveau de subdivision. Le réglage de taille applique une mise à l’échelle uniforme à la morphologie courante. Un changement ultérieur de morphologie peut modifier la hauteur, qui peut alors être réglée à nouveau. Les personnages des versions précédentes peuvent recevoir l’aperçu lissé depuis ce panneau.

Les essais du script `tools/validate_model.py` ont vérifié cinq morphologies à 0, 25, 50, 75 et 100 %, chacune réglée à 1,75 m. Les maillages et les shape keys sont indépendants, les yeux suivent la valeur de leur personnage, les faces évaluées ont une aire positive et les coordonnées sont finies. Les cinq hauteurs ont été conservées après sauvegarde et réouverture. La version installée a également créé un personnage et réglé sa taille à 1,80 m.

La scène `validation/Comparaison-morphologies.blend` et les rendus de face, de profil et de trois-quarts permettent la revue. L’examen des vues d’ensemble montre une transition progressive de silhouette. Le damier utilise les UV féminines conservées comme référence commune. La densité apparente des carreaux varie autour de la poitrine et des épaules. Une inspection rapprochée des mains, des pieds, des paupières et des coutures UV reste nécessaire avant de considérer l’anatomie et le dépliage comme validés.

## Cible et décisions proposées

- Cibler Blender **5.2 LTS**, avec une version minimale de **5.2.0**. Vérifier la version minimale et le dernier correctif 5.2 disponible au moment de chaque livraison.
- Livrer une base humaine complète avec UV, morphs corporels et faciaux, peau, yeux, rig, deux coiffures et un vêtement de référence. Le premier parcours doit fonctionner hors ligne avec les données incluses.
- Reprendre de MPFB les principes du préréglage versionné, de la reproduction par graine et de la copie d’export. Reprendre de CharMorph le principe du réajustement des accessoires en cours de morphing. Le choix des fichiers à réutiliser dépend de leur provenance, de leur licence et de leur qualité mesurée. Voir le [rapport d’audit](Audit-CharMorph-MPFB.md).
- Conserver un corps, un état de morphologie et une collection identifiables par personnage. Épingler la version de la base et du pack dans les préréglages. Conserver des identifiants stables pour les paramètres, les coiffures et les accessoires.
- Isoler l’accès Python aux entrées de modificateurs Geometry Nodes. Blender 5.2 change cette API, et les groupes fournis avec l’extension devront être testés sur la version minimale. [Notes de version de l’API Python](https://developer.blender.org/docs/release_notes/5.2/python_api/)

## Architecture

### Inspiration fonctionnelle MPFB et CharMorph

L’objectif du projet est d’atteindre au minimum les fonctionnalités de modélisation des deux add-ons avec notre propre architecture. Le prototype utilise des déformations locales sur la base Blender Studio. MPFB alimente les références et les essais de transfert d’âge. L’étude de CharMorph guide la comparaison des fonctionnalités de morphs combinés et de configurations éditables. Le référentiel biologique guide la validation des formes.

| Source examinée | Apport retenu | Application au corps et au visage | État |
| --- | --- | --- | --- |
| MPFB · `services/targetservice.py`, interpolation des macros et calcul de la pile de targets | Combinaison de formes de référence selon plusieurs paramètres | Croiser âge, morphologie et corpulence avec des formes adaptées à chaque combinaison | Références d’âge utilisées. Combinaisons étendues à construire. |
| MPFB · bibliothèque de targets corporelles et faciales | Déformations anatomiques localisées | Comparer les volumes du nez, de la bouche, des joues et du corps aux réglages procéduraux actuels, puis transférer les déformations retenues | Transfert d’âge en cours. Catalogue facial à évaluer sur la base Blender Studio. |
| CharMorph · `lib/morpher_cores.py`, `ShapeKeysComboMorpher` et `_do_all_morphs` | Morphs combinés et limites propres aux paramètres | Prévoir des correctifs pour les combinaisons de réglages qui déforment la silhouette ou les traits du visage | Correction féminine/masculine présente dans 0.3. Les autres interactions restent à traiter. |
| CharMorph · `lib/morpher.py`, formes de base, morphs de détail et mélange de presets | Organisation de la morphologie en plusieurs niveaux | Distinguer les réglages globaux du corps des retouches locales du visage et conserver des configurations éditables | Panneaux Corps et Visage présents. Presets et mélange de configurations à développer. |
| CharMorph · moteur NumPy et stockage en shape keys | Évaluation des morphs sur une topologie stable | Mesurer la latence et la mémoire sur un personnage chargé en morphs avant de choisir les optimisations | La génération des déformations utilise NumPy. Le personnage installé utilise les shape keys et drivers natifs. |

Les prochains essais de modélisation compareront les déformations de référence des deux add-ons aux résultats actuels, avec les mêmes vues et paramètres de contrôle. Les reprises de données ou de code seront consignées avec leur source et leur licence.

| Domaine | Responsabilité |
| --- | --- |
| Données | Packs versionnés contenant topologie, UV, repères anatomiques, morphs, poids, matériaux, coiffures et informations de provenance. Valider les dépendances avant d’ajouter un personnage. |
| Personnage | État éditable sérialisé dans le fichier Blender et dans un préréglage portable. Ordre d’évaluation défini pour la morphologie, les expressions, les vêtements, la surface de cuir chevelu et la coiffure. |
| Adaptation Blender | Opérateurs, collections, shape keys, modificateurs, groupes Geometry Nodes et conversions d’export. Toute génération cible explicitement le personnage courant. |
| Rig et export | Préparer la copie dans une collection de travail, vérifier ses dépendances et la publier une fois valide. Nettoyer les objets de la copie en cas d’échec. |

## Bases candidates inspectées

La scène `human_base_meshes_bundle.blend` a été ouverte dans Blender 5.2.0 LTS depuis une copie temporaire du ZIP `G:/_dev/BlenderDev/human-base-meshes-bundle-v1.4.1.zip`. Blender publie ce bundle sous CC0. [Téléchargements officiels Blender](https://www.blender.org/download/demo-files/)

| Famille | Résultats sur les maillages de base |
| --- | --- |
| `Body Female - Realistic` et `Body Male - Realistic` | 10 582 sommets et 10 590 faces chacun. Corps en une composante fermée, connectivité identique par indices dans la paire, yeux séparés et trois niveaux MultiRes. Les UV diffèrent sur 36 894 des 42 340 coins de faces comparés avec une tolérance de 0,000001, avec un écart maximal d’environ 0,00244 sur un axe UV. |
| `Body Female - Stylized` et `Body Male - Stylized` | 12 502 sommets et 12 500 quads chacun. Corps en une composante fermée, connectivité identique par indices dans la paire et UV identiques aux coins de faces. La connectivité diffère de celle des corps réalistes. |

Les quatre corps n’ont ni shape keys, ni groupes de sommets, ni matériau assigné. La scène ne contient aucune armature ni Hair Curves. Le squelette anatomique est une collection de maillages. La tête générique fournit des exemples de shape keys sur sa propre topologie.

**Choix proposé pour le lot 0.** Évaluer la paire réaliste en premier. La connectivité commune permet de tester un morph par indices. Il faut encore contrôler la correspondance des repères, les intersections et la silhouette aux valeurs intermédiaires. Choisir une référence UV commune et vérifier les textures avant d’utiliser la paire avec le même jeu de matériaux. Garder la paire stylisée comme famille distincte. L’ouverture du fichier a signalé des drivers de masques invalides sur des objets stylisés. Vérifier leurs dépendances avant de réutiliser cette collection.

## Cheveux

Progression de la dynamique : le [banc natif du lot 22](validation/physique-cheveux-22/README.md) conserve la longueur de 12 fibres droites et 12 fibres faiblement courbées sous gravité sur 48 images, avec moins de 0,3 % d'allongement maximal. Un profil limité avec refus des cas hors domaine, un cache intégré et la réouverture sont vérifiés. Les boucles très détaillées, collisions et matériaux biologiques restent à valider ; le produit installé reste en 0.14.

Nature du cheveu, lot expérimental du 20 novembre : [recherche scientifique et état d'implémentation](Recherche-scientifique-cheveux.md). Un modèle de courbure/torsion au repos à longueur conservée et cinq variantes sont disponibles dans `validation/nature-cheveux-21/Prototype-nature-cheveux-02.blend`. Les essais XPBD sans charge conservent les formes. La réponse sous gravité présente un allongement excessif, y compris sur une fibre droite, et reste à diagnostiquer avant intégration. La physique n'est pas validée pour le produit installé.

Mise à jour du 20 novembre 2026 : le périmètre couvre aussi sourcils, moustache, barbe et pilosité corporelle. L'[audit cheveux et pilosité](Audit-cheveux-et-pilosite-Blender-5.2.md) détaille les sources MPFB/CharMorph, le défaut CharMorph reproduit, les capacités vérifiées dans Blender 5.2 et les étapes du prototype. La 0.14 installée reste inchangée pendant cette étude.

### Coiffure native et éditable

Prototype commencé le 20 novembre 2026 : `validation/cheveux-20/Prototype-cheveux-01.blend`, 850 guides et interpolation native, longueur/densité/épaisseur éditables, suivi Hair Dynamics en mode Animation. Les 48 cas d'attache testés et les limites sont consignés dans [le bilan du prototype](validation/cheveux-20/README.md). Il reste séparé de la 0.14 installée pendant la validation de la modélisation. L'intégration au panneau et la physique XPBD ne font pas partie de ce premier prototype.

1. Définir une surface de cuir chevelu dérivée de la tête, avec une topologie et une UV d’attache stables. Tester deux variantes pendant le prototype. Une surface dédiée facilite les masques et les séparations, tandis qu’une attache directe à la tête supprime un transfert de déformation. Le choix dépendra de l’écart mesuré des racines et de la facilité d’édition.
2. Stocker des **Hair Curves** guides, éditables dans Blender. Chaque coiffure référence la version de sa surface d’attache et porte ses réglages de densité, longueur, épaisseur, raie et variation, avec une graine stable. Les premiers cas sont une coupe courte et une coiffure longue avec raie.
3. Attacher les guides sur la surface au repos et interpoler les cheveux avec **Interpolate Hair Curves**. Retenir **Hair Dynamics en mode Animation** comme suivi natif à vérifier dans le prototype 5.2, avec **Capture Rest Geometry** sur la surface. Ne pas cumuler automatiquement ce suivi avec **Deform Curves on Surface**, conservé comme variante de comparaison. Prévoir des masques de densité, une séparation explicite des guides de part et d'autre de la raie et des niveaux distincts pour aperçu/rendu. L'optimisation consistant à simuler seulement les guides avant densification demande une validation séparée de l'ordre des nœuds. [Interpolation des cheveux dans Blender 5.2](https://docs.blender.org/manual/id/5.2/modeling/geometry_nodes/hair/generation/interpolate_hair_curves.html)
4. Fournir un matériau de coiffure avec couleur, variation et rugosité, puis comparer le rendu en Cycles et en EEVEE. Vérifier que modifier les guides, rouvrir le fichier ou remplacer la coiffure laisse les autres personnages intacts.

### Nouveauté de Blender 5.2 et export

- **Hair Dynamics** est retenu pour la simulation des cheveux. Cet asset Geometry Nodes utilise le solveur **XPBD** expérimental de Blender 5.2. Prévoir une surface d’attache et **Capture Rest Geometry**. Tester la simulation sur les guides, les collisions tête et épaules, la remise à zéro, le cache et la réouverture du fichier. La coiffure reste éditable et suit la tête lorsque la simulation est désactivée. [Notes de version Blender 5.2 sur la physique](https://developer.blender.org/docs/release_notes/5.2/physics/)
- Conserver les Hair Curves dans la scène Blender. Pour FBX ou glTF, évaluer une variante maillée sur la copie d’export, avec un budget de géométrie et de textures à définir selon la cible. Valider la réimportation avant d’annoncer une prise en charge. Le choix entre mèches en mesh et cartes de cheveux dépendra du moteur et du budget souhaités.

## Dynamique des vêtements

Retenir **Cloth Dynamics**, l’asset Geometry Nodes de Blender 5.2 qui utilise le même solveur **XPBD** expérimental. Le vêtement est d’abord ajusté à la morphologie au repos. La simulation intervient ensuite sur le vêtement ajusté pendant l’animation. Le prototype utilisera le vêtement de référence pour vérifier les points d’ancrage, les collisions avec le corps, l’étirement, la flexion et la stabilité sur plusieurs poses. Vérifier séparément la réinitialisation et le comportement après réouverture du fichier. [Notes de version Blender 5.2 sur la physique](https://developer.blender.org/docs/release_notes/5.2/physics/)

Le manuel 5.2 indique que **Cloth Dynamics ne gère pas encore l’auto-collision**. Choisir un vêtement simple pour isoler les collisions avec le corps, puis essayer un pli qui se referme sur lui-même pour mesurer cette limite. [Cloth Dynamics 5.2](https://docs.blender.org/manual/en/5.2/modeling/geometry_nodes/simulation/cloth_dynamics.html)

### Références pour le prototype

- **Cheveux**. Utiliser les modes Animation et Physics de Hair Dynamics pour comparer le suivi de la surface à la simulation XPBD sur les mêmes guides. [Hair Dynamics en français](https://docs.blender.org/manual/fr/latest/modeling/geometry_nodes/simulation/hair_dynamics.html) · [Hair Dynamics 5.2](https://docs.blender.org/manual/id/5.2/modeling/geometry_nodes/simulation/hair_dynamics.html)
- **Solveur**. Partir des assets natifs Hair Dynamics et Cloth Dynamics, qui préparent les contraintes et les effecteurs pour XPBD. [XPBD Solver 5.2](https://docs.blender.org/manual/en/5.2/modeling/geometry_nodes/simulation/xpbd_solver.html)
- **Préparation du vêtement**. Le Cloth Filter est un outil de sculpture pour former les plis et le drapé au repos. [Cloth Filter en français](https://docs.blender.org/manual/fr/5.2/sculpt_paint/sculpting/tools/cloth_filter.html)
- **Scénarios de contrôle**. Les exemples du modificateur Cloth classique donnent des cas d’ancrage et de collision à reproduire avec Cloth Dynamics. [Exemples Cloth en français](https://docs.blender.org/manual/fr/5.2/physics/cloth/examples.html)
- **Démonstration complémentaire**. L’article ProjProd donne un aperçu des usages cheveux, fourrure et vêtements. [Article ProjProd](https://www.projprod.com/post/blender-5-2-new-cloth-hair-fur-simulation)

## Séquence indicative après le cadrage de la modélisation

| Lot | Travail prévu | Critère de passage |
| --- | --- | --- |
| 0 · Base et données | Choisir une base dont la provenance est vérifiée. Cartographier UV, morphs, poids, limites anatomiques et points d’attache. Fixer une scène de référence et les mesures de comparaison. | La base, les droits et les versions nécessaires sont documentés. Trois morphologies de contrôle sont définies. |
| 1 · Prototype cheveux | Dans une scène Blender 5.2, comparer attache directe et surface dédiée. Essayer les deux coiffures sur trois morphologies et des poses de tête. | Les racines suivent la surface, la raie reste nette et la coiffure reste éditable après réouverture. Mesurer la latence, la mémoire et l’écart des racines. |
| 2 · Création et morphologie | Prévoir le paquet d’extension, la génération hors ligne, les paramètres corps et visage, les préréglages et les matériaux de base. | Deux humains peuvent cohabiter et être modifiés indépendamment. Un préréglage incomplet indique les ressources manquantes dans Blender. |
| 3 · Rig et vêtements | Poser le rig sur les repères, vérifier les poids, ajuster un vêtement de référence et relier la surface de coiffure au personnage. | Les poses de contrôle valident épaules, hanches, genoux, doigts, mâchoire et attache des cheveux. Un échec de rig laisse le personnage éditable. |
| 4 · Dynamique et finalisation | Prototyper Hair Dynamics sur la coiffure longue et Cloth Dynamics sur le vêtement de référence. Produire une copie d’export avec la géométrie et les matériaux adaptés à la cible. | Vérifier les collisions, la stabilité et la réinitialisation pour les deux simulations. Réimporter la copie et contrôler les unités, la silhouette, les UV, les poids, les expressions et les cheveux. |

## Version future · Humanoïdes externes

Évolution retenue le 19 novembre 2026 pour rendre le générateur utilisable avec des humanoïdes provenant d’autres sources. Cette phase viendra après la consolidation de la modélisation et le développement du rig. Aucun développement de cette fonction n’est engagé dans le lot actuel.

Deux usages doivent être proposés : conserver et exploiter le personnage importé avec ses dépendances, ou l’adapter progressivement aux réglages du générateur. Conserver les fichiers et objets sources dans une collection distincte et effectuer l’adaptation sur une copie.

| Étape | Travail prévu | Critère de passage |
| --- | --- | --- |
| Import et diagnostic | Inventorier maillages, matériaux, UV, clés de forme, modificateurs, armatures, poids, drivers et ressources externes. Définir les formats pris en charge et leurs limites après essais. | Le diagnostic indique les éléments conservés, absents ou incompatibles. Les dépendances nécessaires suivent la copie et le fichier se rouvre correctement. |
| Correspondance anatomique assistée | Identifier les parties du corps, placer ou corriger les repères, normaliser pose et unités sur la copie. Établir une correspondance de surface lorsque la topologie diffère. | Les repères et la correspondance sont contrôlables en vues de face, de profil et de trois-quarts. Le transfert direct par indices reste réservé aux topologies compatibles. |
| Adaptation des réglages | Transférer ou reconstruire les déformations de corps et de visage sur la surface importée. Préserver les clés et modificateurs existants lorsqu’ils sont compatibles. | Les réglages restent éditables et les combinaisons sont vérifiées aux yeux, à la bouche, aux articulations et aux extrémités. Les incompatibilités sont explicites. |
| Rig existant ou futur rig du générateur | Proposer la conservation du rig importé avec correspondance des os, ou l’ajustement du futur rig du générateur. Vérifier les poids et les déformations avant de proposer un transfert d’animation. | Les poses de contrôle valident les articulations, les doigts et le visage. Les drivers et contraintes utiles sont conservés ou leur remplacement est documenté. |

La prise en charge sera progressive, avec des personnages réalistes puis stylisés et des topologies variées. Une conversion automatique universelle ne constitue pas un critère de livraison. Conserver la provenance et les conditions de réutilisation de chaque modèle de référence.

## Vérification avant de figer les choix

Le Blender 5.2.0 LTS installé, build `fbe6228777e7`, expose les Hair Curves, les propriétés `surface` et `surface_uv_map`, ainsi que les nœuds d’interpolation et de déformation attendus. Ce contrôle porte sur la disponibilité de l’API. L’ordre effectif des nœuds, le comportement de la dynamique et la qualité des coiffures seront vérifiés sur les scènes du lot 1.

Pour comparer les deux attaches, mesurer le déplacement des racines par rapport à la surface évaluée et l’écart entre plusieurs captures du même préréglage. Contrôler la ligne frontale, les tempes, la nuque et la raie en vues face, profil et trois-quarts. Fixer les seuils d’acceptation à partir de la scène de référence, sur une machine identifiée. Vérifier également le retour au neutre, l’annulation, la réouverture du fichier et l’indépendance de deux personnages portant la même coiffure.

Les skills Blender internes restent provisoires. Pour les étapes qu’ils couvrent, consigner la procédure suivie, le résultat observé et les écarts en cas de réussite ou d’échec.

## Lot de modélisation 0.12

47 réglages, huit silhouettes éditables et corpulence étendue adaptée aux formes d'âge. Voir Livraison-corpulences-0.12.md pour les preuves et limites. Prochaine étape : atlas de repères anatomiques, calibration régionale et affinement des formes jeunes et âgées. Rig, cheveux et vêtements restent hors du lot actuel.


## Correction morphologique 0.13

La revue utilisateur invalide le critère de silhouette de la 0.12, trop abdominal. La 0.13 ajoute une corpulence globale, des pôles distincts minceur/adiposité et une couche de repères osseux et musculaires. Les anciens volumes restent accessibles pour compatibilité. Voir Recherche-morphologie-globale.md et Livraison-morphologie-globale-0.13.md. La calibration des amplitudes et la diversité des répartitions restent ouvertes.


## Revue anatomique prioritaire · après la 0.13

L'acceptation visuelle de la 0.13 est invalidée par la revue utilisateur. Suspendre les nouvelles fonctions et la diffusion des candidats de corpulence jusqu'à vérification des repères et proportions. Le détail des erreurs confirmées, sources anthropométriques récupérées et critères de reprise figure dans Audit-proportions-et-reprise.md. Les essais adultes restent dans validation/proportions-14 ; le moteur installé n'est pas remplacé par ces expériences.


## Musculature régionale 0.14 · livraison du 19 novembre 2026

Après clarification utilisateur, conserver notre base neutre et utiliser les nouveaux modèles comme guides des volumes musculaires. Le pôle adulte est maintenant repris dans huit régions ; le réglage global partage leur calcul. La 0.14 est installée et chargée uniquement sur Blender 5.2. Deux personnages existants migrés avec réglages conservés, sauvegarde préalable et réouverture vérifiées. Les 123 cas géométriques testés passent. Voir Livraison-muscles-regionaux-0.14.md pour les rapports et limites. La calibration musculaire propre à chaque âge, les répartitions de graisse et les reliefs osseux restent à affiner ; l'absence de croisements ne vaut pas validation anatomique finale.
